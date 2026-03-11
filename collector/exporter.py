"""Exporter — génère les exports consolidés, rapports et bruts après chaque run.

Formats :
  - JSONL.gz : export consolidé (1 ligne = 1 VM), rétention 30 jours
  - report.md : rapport de run lisible (écrasé à chaque run)
  - JSON.gz : exports bruts API (optionnel), rétention 7 jours

Stockage : dossier local ou partage Samba (SMB) configurable via .env.
"""

import gzip
import json
import logging
import os
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from app import db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly

logger = logging.getLogger("cloudinventory.exporter")


def _get_export_config():
    """Récupère la config d'export depuis l'app Flask."""
    from flask import current_app
    return {
        "enabled": current_app.config.get("EXPORT_ENABLED", False),
        "local_path": current_app.config.get("EXPORT_LOCAL_PATH", ""),
        "smb_path": current_app.config.get("EXPORT_SMB_PATH", ""),
        "retention_consolidated": current_app.config.get("EXPORT_RETENTION_CONSOLIDATED", 30),
        "retention_raw": current_app.config.get("EXPORT_RETENTION_RAW", 7),
        "export_raw": current_app.config.get("EXPORT_RAW_ENABLED", False),
    }


def _get_export_dir(config):
    """Détermine et crée le répertoire d'export (Samba ou local)."""
    smb = config["smb_path"]
    if smb:
        path = Path(smb)
    else:
        local = config["local_path"] or os.path.join(os.getcwd(), "exports")
        path = Path(local)

    path.mkdir(parents=True, exist_ok=True)
    return path


def export_consolidated_jsonl(run_id, export_dir):
    """Génère l'export consolidé JSONL.gz pour un run.

    Fichier : consolidated/run_{id}_{date}.jsonl.gz
    """
    subdir = export_dir / "consolidated"
    subdir.mkdir(exist_ok=True)

    run = Run.query.get(run_id)
    if not run:
        return None

    rows = (
        db.session.query(ConsolidatedAsset, Asset, IpamRecord)
        .join(Asset, ConsolidatedAsset.asset_id == Asset.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.run_id == run_id)
        .all()
    )

    ts = run.ended_at or run.started_at or datetime.now(timezone.utc)
    filename = f"run_{run_id}_{ts.strftime('%Y%m%d_%H%M%S')}.jsonl.gz"
    filepath = subdir / filename

    with gzip.open(filepath, "wt", encoding="utf-8") as f:
        for ca, asset, ipam in rows:
            record = {
                "run_id": run_id,
                "vm_id": asset.vm_id,
                "vm_name": asset.vm_name,
                "type": asset.type,
                "node": asset.node,
                "status": asset.status,
                "tags": asset.tags,
                "ip_reported": asset.ip_reported,
                "fqdn": asset.fqdn,
                "os": asset.os,
                "cpu_count": asset.cpu_count,
                "cpu_usage": asset.cpu_usage,
                "ram_max": asset.ram_max,
                "ram_used": asset.ram_used,
                "disk_max": asset.disk_max,
                "disk_used": asset.disk_used,
                "uptime": asset.uptime,
                "ip_final": ca.ip_final,
                "dns_final": ca.dns_final,
                "source_ip_dns": ca.source_ip_dns,
                "match_status": ca.match_status,
                "role": ca.role,
                "ipam_ip": ipam.ip if ipam else None,
                "ipam_dns": ipam.dns_name if ipam else None,
                "ipam_status": ipam.status if ipam else None,
                "ipam_tenant": ipam.tenant if ipam else None,
                "ipam_site": ipam.site if ipam else None,
                "ipam_zone": ipam.meta_zone if ipam else None,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Export consolidé : %s (%d lignes)", filepath.name, len(rows))
    return filepath


def export_report_md(run_id, anomaly_details, export_dir):
    """Génère le rapport de run en Markdown (écrase le précédent).

    Fichier : report.md
    """
    run = Run.query.get(run_id)
    if not run:
        return None

    total_matched = (run.matched_name_count or 0) + (run.matched_fqdn_count or 0) + (run.matched_ip_count or 0)
    total_vms = run.vm_count or 0
    match_rate = round(total_matched / total_vms * 100, 1) if total_vms > 0 else 0
    anomaly_count = sum(anomaly_details.values())

    started = run.started_at.strftime('%d/%m/%Y %H:%M:%S') if run.started_at else '—'
    ended = run.ended_at.strftime('%d/%m/%Y %H:%M:%S') if run.ended_at else '—'

    lines = [
        f"# CloudInventory — Rapport Run #{run.id}",
        "",
        f"**Statut** : {run.status}",
        f"**Début** : {started}",
        f"**Fin** : {ended}",
        "",
        "---",
        "",
        "## Résultats",
        "",
        "| Métrique | Valeur |",
        "|---|---|",
        f"| VMs collectées | {total_vms} |",
        f"| IPs IPAM | {run.ip_count or 0} |",
        f"| Match par nom | {run.matched_name_count or 0} |",
        f"| Match par FQDN | {run.matched_fqdn_count or 0} |",
        f"| Match par IP | {run.matched_ip_count or 0} |",
        f"| No match | {run.no_match_count or 0} |",
        f"| **Taux de correspondance** | **{match_rate}%** ({total_matched}/{total_vms}) |",
        "",
    ]

    if anomaly_count > 0:
        lines.extend([
            "---",
            "",
            f"## Anomalies ({anomaly_count})",
            "",
            "| Type | Nombre |",
            "|---|---|",
        ])
        for atype, acount in anomaly_details.items():
            lines.append(f"| {atype} | {acount} |")
        lines.append("")

        # Détail des anomalies
        anomaly_rows = (
            db.session.query(Anomaly, Asset)
            .join(Asset, Anomaly.asset_id == Asset.id)
            .filter(Anomaly.run_id == run_id)
            .order_by(Anomaly.type)
            .all()
        )
        if anomaly_rows:
            lines.extend([
                "### Détail",
                "",
                "| Type | VM | Détails |",
                "|---|---|---|",
            ])
            for anomaly, asset in anomaly_rows:
                details = (anomaly.details or '').replace('|', '\\|')
                lines.append(f"| `{anomaly.type}` | **{asset.vm_name}** | {details} |")
            lines.append("")
    else:
        lines.extend([
            "---",
            "",
            "## Anomalies",
            "",
            "Aucune anomalie détectée.",
            "",
        ])

    lines.extend([
        "---",
        "",
        f"*Généré automatiquement par CloudInventory le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC*",
    ])

    filepath = export_dir / "report.md"
    filepath.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Rapport Markdown : %s", filepath)
    return filepath


def export_raw_json(run_id, vm_list, ipam_list, export_dir):
    """Génère les exports bruts JSON.gz (optionnel, pour debug/rejeu).

    Fichiers : raw/vms_run_{id}_{date}.json.gz, raw/ipam_run_{id}_{date}.json.gz
    """
    subdir = export_dir / "raw"
    subdir.mkdir(exist_ok=True)

    ts = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    paths = []

    for name, data in [("vms", vm_list), ("ipam", ipam_list)]:
        filename = f"{name}_run_{run_id}_{ts}.json.gz"
        filepath = subdir / filename
        with gzip.open(filepath, "wt", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        paths.append(filepath)
        logger.info("Export brut : %s (%d entrées)", filepath.name, len(data))

    return paths


def cleanup_old_exports(export_dir, retention_consolidated=30, retention_raw=7):
    """Supprime les exports au-delà de la durée de rétention."""
    now = datetime.now(timezone.utc)
    deleted = 0

    # Consolidated : rétention 30 jours
    consolidated_dir = export_dir / "consolidated"
    if consolidated_dir.exists():
        cutoff = now - timedelta(days=retention_consolidated)
        for f in consolidated_dir.glob("*.jsonl.gz"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink()
                deleted += 1
                logger.info("Supprimé (rétention %dj) : %s", retention_consolidated, f.name)

    # Raw : rétention 7 jours
    raw_dir = export_dir / "raw"
    if raw_dir.exists():
        cutoff = now - timedelta(days=retention_raw)
        for f in raw_dir.glob("*.json.gz"):
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime < cutoff:
                f.unlink()
                deleted += 1
                logger.info("Supprimé (rétention %dj) : %s", retention_raw, f.name)

    if deleted:
        logger.info("Nettoyage rétention : %d fichiers supprimés", deleted)


def run_exports(run_id, anomaly_details, vm_list=None, ipam_list=None):
    """Point d'entrée principal — génère tous les exports après un run."""
    config = _get_export_config()
    if not config["enabled"]:
        logger.debug("Exports désactivés (EXPORT_ENABLED=false)")
        return

    export_dir = _get_export_dir(config)

    # 1. Export consolidé JSONL.gz (rétention 30j)
    export_consolidated_jsonl(run_id, export_dir)

    # 2. Rapport Markdown (écrase le précédent)
    export_report_md(run_id, anomaly_details, export_dir)

    # 3. Exports bruts (optionnel, rétention 7j)
    if config["export_raw"] and vm_list and ipam_list:
        export_raw_json(run_id, vm_list, ipam_list, export_dir)

    # 4. Nettoyage rétention
    cleanup_old_exports(
        export_dir,
        retention_consolidated=config["retention_consolidated"],
        retention_raw=config["retention_raw"],
    )
