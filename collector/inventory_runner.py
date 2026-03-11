"""Runner d'inventaire — orchestre la collecte, consolidation et détection d'anomalies.

Inspiré de l'étude de faisabilité CloudInventory v2 (vCenter + EfficientIP),
adapté pour Proxmox VE + NetBox dans le cadre du BTS SIO SLAM.
"""

import logging
import os
import re
from collections import Counter
from datetime import datetime, timezone
from app import db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly
from collector.mock_virtualisation import fetch_mock_vms
from collector.mock_netbox import fetch_mock_ipam
from collector.netbox_client import fetch_ipam_records
from collector.proxmox_client import fetch_proxmox_vms

logger = logging.getLogger("cloudinventory.runner")


def _notify_webhook(run, anomaly_count):
    """Envoie une notification webhook si configuré et si des anomalies critiques existent."""
    try:
        from flask import current_app
        import requests
        url = current_app.config.get("WEBHOOK_URL", "")
        if not url or anomaly_count == 0:
            return
        payload = {
            "text": (f"CloudInventory Run #{run.id} terminé — "
                     f"{run.vm_count} VMs, {anomaly_count} anomalies détectées"),
            "run_id": run.id,
            "status": run.status,
            "anomaly_count": anomaly_count,
        }
        requests.post(url, json=payload, timeout=10)
        logger.info("Notification webhook envoyée (%d anomalies)", anomaly_count)
    except Exception as e:
        logger.warning("Échec notification webhook : %s", e)


def _notify_email(run, anomaly_count, anomaly_details):
    """Envoie un email HTML récapitulatif si SMTP configuré et si des anomalies existent."""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from flask import current_app

        if not current_app.config.get("SMTP_ENABLED") or anomaly_count == 0:
            return

        smtp_to = current_app.config.get("SMTP_TO", "")
        if not smtp_to:
            return

        # Récupérer le détail des anomalies pour le tableau
        anomaly_rows = (
            db.session.query(Anomaly, Asset)
            .join(Asset, Anomaly.asset_id == Asset.id)
            .filter(Anomaly.run_id == run.id)
            .order_by(Anomaly.type)
            .all()
        )

        # Couleurs par type d'anomalie (bg, text)
        type_colors = {
            "NO_MATCH": ("#dc3545", "#fff"),
            "STATUS_MISMATCH": ("#ffc107", "#000"),
            "HOSTNAME_MISMATCH": ("#fd7e14", "#fff"),
            "DUPLICATE_DNS": ("#6f42c1", "#fff"),
            "DUPLICATE_IP": ("#6f42c1", "#fff"),
        }

        # Lignes du tableau anomalies
        anomaly_table_rows = ""
        for anomaly, asset in anomaly_rows:
            bg, fg = type_colors.get(anomaly.type, ("#6c757d", "#fff"))
            anomaly_table_rows += f"""
            <tr>
              <td style="padding:8px 12px;border-bottom:1px solid #e9ecef;">
                <span style="background:{bg};color:{fg};padding:2px 8px;border-radius:4px;font-size:12px;">{anomaly.type}</span>
              </td>
              <td style="padding:8px 12px;border-bottom:1px solid #e9ecef;font-weight:600;">{asset.vm_name}</td>
              <td style="padding:8px 12px;border-bottom:1px solid #e9ecef;color:#6c757d;font-size:13px;">{anomaly.details or ''}</td>
            </tr>"""

        # Badges résumé par type
        type_badges = ""
        for atype, acount in anomaly_details.items():
            bg, fg = type_colors.get(atype, ("#6c757d", "#fff"))
            type_badges += f'<span style="display:inline-block;background:{bg};color:{fg};padding:4px 10px;border-radius:12px;font-size:13px;margin:3px 6px 3px 0;">{atype}: {acount}</span> '

        # Calcul du taux de matching
        total_vms = run.vm_count or 0
        matched_total = (run.matched_name_count or 0) + (run.matched_fqdn_count or 0) + (run.matched_ip_count or 0)
        match_rate = round(matched_total / total_vms * 100, 1) if total_vms > 0 else 0

        ended = run.ended_at.strftime('%d/%m/%Y %H:%M:%S') if run.ended_at else '—'

        html = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f4f6f9;font-family:Segoe UI,Arial,sans-serif;">
<div style="max-width:650px;margin:20px auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);padding:24px 30px;text-align:center;">
    <h1 style="color:#fff;margin:0;font-size:22px;">CloudInventory</h1>
    <p style="color:#8892b0;margin:6px 0 0;font-size:14px;">Rapport d'inventaire automatique</p>
  </div>

  <!-- Alert banner -->
  <div style="background:#fff3cd;border-left:4px solid #dc3545;padding:16px 24px;margin:20px 24px;border-radius:6px;">
    <strong style="color:#dc3545;font-size:16px;">&#9888; {anomaly_count} anomalie{'s' if anomaly_count > 1 else ''} detectee{'s' if anomaly_count > 1 else ''}</strong>
    <p style="margin:8px 0 0;color:#664d03;font-size:14px;">Run <strong>#{run.id}</strong> termine le {ended}</p>
  </div>

  <!-- Stats -->
  <div style="padding:0 24px;">
    <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #e9ecef;padding-bottom:8px;">Resultats du run</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:16px;">
      <tr>
        <td style="padding:10px;text-align:center;width:25%;">
          <div style="font-size:28px;font-weight:700;color:#0d6efd;">{total_vms}</div>
          <div style="font-size:12px;color:#6c757d;">VMs collectees</div>
        </td>
        <td style="padding:10px;text-align:center;width:25%;">
          <div style="font-size:28px;font-weight:700;color:#198754;">{run.matched_name_count or 0}</div>
          <div style="font-size:12px;color:#6c757d;">Match nom</div>
        </td>
        <td style="padding:10px;text-align:center;width:25%;">
          <div style="font-size:28px;font-weight:700;color:#6f42c1;">{run.matched_fqdn_count or 0}</div>
          <div style="font-size:12px;color:#6c757d;">Match FQDN</div>
        </td>
        <td style="padding:10px;text-align:center;width:25%;">
          <div style="font-size:28px;font-weight:700;color:#0dcaf0;">{run.matched_ip_count or 0}</div>
          <div style="font-size:12px;color:#6c757d;">Match IP</div>
        </td>
      </tr>
    </table>

    <!-- Match rate bar -->
    <div style="background:#e9ecef;border-radius:8px;height:24px;overflow:hidden;margin-bottom:6px;">
      <div style="background:linear-gradient(90deg,#198754,#0dcaf0);height:100%;width:{match_rate}%;border-radius:8px;"></div>
    </div>
    <p style="text-align:center;font-size:13px;color:#6c757d;margin:0 0 20px;">Taux de correspondance : <strong>{match_rate}%</strong> ({matched_total}/{total_vms})</p>

    <!-- Anomaly summary -->
    <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #e9ecef;padding-bottom:8px;">Anomalies par type</h2>
    <p style="margin:12px 0 16px;">{type_badges}</p>

    <!-- Anomaly detail table -->
    <h2 style="font-size:16px;color:#1a1a2e;border-bottom:2px solid #e9ecef;padding-bottom:8px;">Detail des anomalies</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:20px;font-size:14px;">
      <tr style="background:#f8f9fa;">
        <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase;">Type</th>
        <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase;">VM</th>
        <th style="padding:10px 12px;text-align:left;font-size:12px;color:#6c757d;text-transform:uppercase;">Details</th>
      </tr>
      {anomaly_table_rows}
    </table>
  </div>

  <!-- Footer -->
  <div style="background:#f8f9fa;padding:16px 24px;text-align:center;border-top:1px solid #e9ecef;">
    <p style="margin:0;font-size:12px;color:#adb5bd;">CloudInventory — Notification automatique</p>
  </div>

</div>
</body>
</html>"""

        msg = MIMEText(html, "html", "utf-8")
        msg["Subject"] = f"[CloudInventory] Run #{run.id} — {anomaly_count} anomalie{'s' if anomaly_count > 1 else ''}"
        msg["From"] = current_app.config["SMTP_FROM"]
        msg["To"] = smtp_to

        host = current_app.config["SMTP_HOST"]
        port = current_app.config["SMTP_PORT"]
        use_tls = current_app.config["SMTP_USE_TLS"]
        username = current_app.config.get("SMTP_USERNAME", "")
        password = current_app.config.get("SMTP_PASSWORD", "")

        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)

        logger.info("Email de notification envoye a %s (%d anomalies)", smtp_to, anomaly_count)
    except Exception as e:
        logger.warning("Echec envoi email : %s", e)


# ── Table de correspondance lettre → rôle fonctionnel ──
# Reprise de la convention de nommage entreprise (étude de faisabilité v2)
ROLE_MAP = {
    "a": "Application",
    "b": "Base de données",
    "c": "Communication",
    "d": "DNS",
    "f": "Fichiers",
    "h": "Hyperviseur",
    "i": "Impression",
    "j": "Journalisation",
    "l": "Authentification",
    "m": "Messagerie",
    "n": "News",
    "o": "Proxy",
    "p": "Pare-feu",
    "t": "Temps",
    "s": "Supervision",
    "v": "Correctifs",
    "w": "Web",
    "x": "Annuaire",
    "k": "SSI",
    "r": "Ressources",
    "z": "Multifonctions",
}


TAG_ROLE_MAP = {
    "web": "Web",
    "api": "Application",
    "database": "Base de données",
    "cache": "Communication",
    "proxy": "Proxy",
    "loadbalancer": "Proxy",
    "messaging": "Communication",
    "storage": "Fichiers",
    "logs": "Journalisation",
    "backup": "Fichiers",
    "dns": "DNS",
    "auth": "Authentification",
    "mail": "Messagerie",
    "network": "Communication",
    "firewall": "Pare-feu",
    "ntp": "Temps",
    "monitoring": "Supervision",
    "alerting": "Supervision",
    "automation": "Ressources",
    "git": "Ressources",
    "secrets": "SSI",
    "ci": "Ressources",
    "test": "Application",
    "migration": "Ressources",
    "deprecated": "Multifonctions",
}


def _deduce_role(hostname, tags=None):
    """Déduit le rôle fonctionnel à partir du hostname puis des tags.

    Stratégie 1 : lettre suivie d'une séquence de 3 chiffres (ex: web-a500 → 'a' → Application).
    Stratégie 2 : tag role:xxx extrait des tags de la VM.
    """
    if not hostname:
        return "Indéterminé"
    match = re.search(r"([a-zA-Z])(\d{3})", hostname)
    if match:
        letter = match.group(1).lower()
        if letter in ROLE_MAP:
            return ROLE_MAP[letter]
    if tags:
        for t in tags.split(","):
            t = t.strip()
            if t.startswith("role:"):
                role_tag = t.split(":", 1)[1].strip()
                if role_tag in TAG_ROLE_MAP:
                    return TAG_ROLE_MAP[role_tag]
    return "Indéterminé"


def _normalize_hostname(name):
    """Normalise un hostname pour le matching : lowercase, strip, suppression domaine."""
    if not name:
        return ""
    name = name.strip().lower()
    # Supprime le suffixe de domaine si présent (ex: vm.domain.local → vm)
    if "." in name:
        name = name.split(".")[0]
    return name


def _normalize_fqdn(fqdn):
    """Normalise un FQDN: lowercase, strip, extrait le hostname (premier segment)."""
    if not fqdn:
        return ""
    return fqdn.strip().lower().split(".")[0]


def _upsert_assets(vm_list):
    """Insère ou met à jour les assets en base (upsert sur vm_id)."""
    runtime_fields = ("cpu_count", "cpu_usage", "ram_max", "ram_used",
                      "disk_max", "disk_used", "uptime", "os")

    for vm in vm_list:
        asset = Asset.query.filter_by(vm_id=vm["vm_id"]).first()
        if asset:
            asset.vm_name = vm["vm_name"]
            asset.type = vm["type"]
            asset.node = vm["node"]
            asset.status = vm["status"]
            asset.tags = vm.get("tags")
            asset.ip_reported = vm.get("ip_reported")
            asset.fqdn = vm.get("fqdn")
            asset.annotation = vm.get("annotation")
            for f in runtime_fields:
                setattr(asset, f, vm.get(f))
        else:
            asset = Asset(
                vm_id=vm["vm_id"],
                vm_name=vm["vm_name"],
                type=vm["type"],
                node=vm["node"],
                status=vm["status"],
                tags=vm.get("tags"),
                ip_reported=vm.get("ip_reported"),
                fqdn=vm.get("fqdn"),
                annotation=vm.get("annotation"),
                **{f: vm.get(f) for f in runtime_fields},
            )
            db.session.add(asset)
    db.session.flush()


def _upsert_ipam_records(records):
    """Insère ou met à jour les IPAM records (upsert sur ip + dns_name)."""
    for rec in records:
        ipam = IpamRecord.query.filter_by(
            ip=rec["ip"], dns_name=rec["dns_name"]
        ).first()
        if ipam:
            ipam.status = rec.get("status")
            ipam.tenant = rec.get("tenant")
            ipam.site = rec.get("site")
            ipam.meta_zone = rec.get("meta_zone")
        else:
            ipam = IpamRecord(
                ip=rec["ip"],
                dns_name=rec["dns_name"],
                status=rec.get("status"),
                tenant=rec.get("tenant"),
                site=rec.get("site"),
                meta_zone=rec.get("meta_zone"),
            )
            db.session.add(ipam)
    db.session.flush()


def _detect_ipam_anomalies(run, ipam_records=None):
    """Détecte les anomalies DUPLICATE_DNS et DUPLICATE_IP dans les IPAM records."""
    if ipam_records is None:
        ipam_records = IpamRecord.query.all()

    # DUPLICATE_DNS : plusieurs IPAM records avec le même dns_name
    dns_counter = Counter(
        r.dns_name.strip().lower()
        for r in ipam_records
        if r.dns_name and r.dns_name.strip()
    )
    for dns, count in dns_counter.items():
        if count > 1:
            dupes = [r for r in ipam_records if r.dns_name and r.dns_name.strip().lower() == dns]
            ips = ", ".join(d.ip for d in dupes)
            asset = Asset.query.filter(
                db.func.lower(Asset.vm_name) == dns
            ).first()
            if asset:
                db.session.add(Anomaly(
                    run_id=run.id, asset_id=asset.id,
                    type="DUPLICATE_DNS",
                    details=f"DNS '{dns}' présent {count} fois dans NetBox (IPs: {ips})",
                ))

    # DUPLICATE_IP : plusieurs IPAM records avec la même IP
    ip_counter = Counter(r.ip for r in ipam_records if r.ip)
    for ip, count in ip_counter.items():
        if count > 1:
            dupes = [r for r in ipam_records if r.ip == ip]
            names = ", ".join(d.dns_name or "?" for d in dupes)
            asset = Asset.query.filter_by(ip_reported=ip).first()
            if asset:
                db.session.add(Anomaly(
                    run_id=run.id, asset_id=asset.id,
                    type="DUPLICATE_IP",
                    details=f"IP '{ip}' présente {count} fois dans NetBox (DNS: {names})",
                ))
            else:
                logger.warning("DUPLICATE_IP '%s' sans asset correspondant — anomalie non rattachée", ip)


def _consolidate(run, ipam_records=None):
    """Consolide les assets avec les IPAM records via matching multi-stratégie.

    Stratégies de matching (par ordre de priorité) :
      1. MATCHED_NAME : correspondance par hostname normalisé (source de vérité)
      2. MATCHED_FQDN : correspondance par FQDN (premier segment vs dns_name)
      3. MATCHED_IP   : fallback par adresse IP reportée par le guest agent
      4. NO_MATCH     : aucune correspondance trouvée → anomalie
    """
    assets = Asset.query.all()
    if ipam_records is None:
        ipam_records = IpamRecord.query.all()

    # Index 1 : dns_name normalisé → IpamRecord
    dns_index = {}
    for ipam in ipam_records:
        if ipam.dns_name:
            key = _normalize_hostname(ipam.dns_name)
            if key:
                dns_index[key] = ipam

    # Index 2 : IP → IpamRecord (pour fallback)
    ip_index = {}
    for ipam in ipam_records:
        if ipam.ip:
            ip_index.setdefault(ipam.ip, ipam)

    matched_name = 0
    matched_fqdn = 0
    matched_ip = 0
    no_match = 0

    for asset in assets:
        vm_key = _normalize_hostname(asset.vm_name)
        role = _deduce_role(asset.vm_name, asset.tags)

        # Stratégie 1 : matching par hostname
        ipam_match = dns_index.get(vm_key)

        if ipam_match:
            ca = ConsolidatedAsset(
                run_id=run.id,
                asset_id=asset.id,
                ipam_record_id=ipam_match.id,
                ip_final=ipam_match.ip,
                dns_final=ipam_match.dns_name,
                source_ip_dns="NETBOX",
                match_status="MATCHED_NAME",
                role=role,
            )
            matched_name += 1

            # STATUS_MISMATCH : VM stopped mais IP active dans NetBox
            if asset.status == "stopped" and ipam_match.status == "active":
                db.session.add(Anomaly(
                    run_id=run.id, asset_id=asset.id,
                    type="STATUS_MISMATCH",
                    details=f"VM '{asset.vm_name}' est stopped mais l'IP {ipam_match.ip} est active dans NetBox",
                ))

        else:
            # Stratégie 2 : matching par FQDN (premier segment du FQDN vs dns_name)
            fqdn_key = _normalize_fqdn(asset.fqdn)
            ipam_by_fqdn = dns_index.get(fqdn_key) if fqdn_key else None

            if ipam_by_fqdn:
                ca = ConsolidatedAsset(
                    run_id=run.id,
                    asset_id=asset.id,
                    ipam_record_id=ipam_by_fqdn.id,
                    ip_final=ipam_by_fqdn.ip,
                    dns_final=ipam_by_fqdn.dns_name,
                    source_ip_dns="NETBOX",
                    match_status="MATCHED_FQDN",
                    role=role,
                )
                matched_fqdn += 1

            else:
                # Stratégie 3 : fallback par IP
                ipam_by_ip = ip_index.get(asset.ip_reported) if asset.ip_reported else None

                if ipam_by_ip:
                    ca = ConsolidatedAsset(
                        run_id=run.id,
                        asset_id=asset.id,
                        ipam_record_id=ipam_by_ip.id,
                        ip_final=ipam_by_ip.ip,
                        dns_final=ipam_by_ip.dns_name,
                        source_ip_dns="NETBOX",
                        match_status="MATCHED_IP",
                        role=role,
                    )
                    matched_ip += 1

                    # Anomalie : le hostname ne correspond pas au DNS NetBox
                    db.session.add(Anomaly(
                        run_id=run.id, asset_id=asset.id,
                        type="HOSTNAME_MISMATCH",
                        details=f"VM '{asset.vm_name}' matchée par IP ({asset.ip_reported}) "
                                f"mais hostname ≠ DNS NetBox '{ipam_by_ip.dns_name}'",
                    ))
                else:
                    # Stratégie 4 : aucune correspondance
                    ca = ConsolidatedAsset(
                        run_id=run.id,
                        asset_id=asset.id,
                        ipam_record_id=None,
                        ip_final=asset.ip_reported,
                        dns_final=asset.vm_name,
                        source_ip_dns="VIRT",
                        match_status="NO_MATCH",
                        role=role,
                    )
                    no_match += 1

                    db.session.add(Anomaly(
                        run_id=run.id, asset_id=asset.id,
                        type="NO_MATCH",
                        details="Aucune correspondance NetBox (hostname, FQDN ni IP)",
                    ))

        db.session.add(ca)

    return matched_name, matched_fqdn, matched_ip, no_match


def run_inventory():
    """Exécute un run d'inventaire complet.

    Returns:
        Run: L'objet Run créé.
    """
    run = Run(status="RUNNING")
    db.session.add(run)
    db.session.flush()
    logger.info("Run #%d démarré", run.id)

    try:
        # 1. Collecte virtualisation (mock ou Proxmox)
        use_mock_virt = os.getenv("USE_MOCK_VIRT", "true").lower() == "true"
        if use_mock_virt:
            vm_list = fetch_mock_vms()
        else:
            vm_list = fetch_proxmox_vms()
        _upsert_assets(vm_list)
        logger.info("Run #%d — %d VMs collectées (source: %s)",
                     run.id, len(vm_list), "mock" if use_mock_virt else "proxmox")

        # 2. Collecte IPAM/DNS (mock ou NetBox)
        use_mock = os.getenv("USE_MOCK_IPAM", "true").lower() == "true"
        if use_mock:
            ipam_raw = fetch_mock_ipam()
        else:
            ipam_raw = fetch_ipam_records()
        _upsert_ipam_records(ipam_raw)

        # 3. Charger les IPAM records en base (une seule fois, partagé)
        all_ipam = IpamRecord.query.all()

        # 4. Consolidation + anomalies de match (multi-stratégie)
        matched_name, matched_fqdn, matched_ip, no_match = _consolidate(run, all_ipam)

        # 5. Anomalies IPAM (duplicates) — réutilise la même liste
        _detect_ipam_anomalies(run, all_ipam)

        # 6. Compteurs
        run.vm_count = len(vm_list)
        run.ip_count = len(ipam_raw)
        run.matched_name_count = matched_name
        run.matched_fqdn_count = matched_fqdn
        run.matched_ip_count = matched_ip
        run.no_match_count = no_match
        run.status = "SUCCESS"
        run.ended_at = datetime.now(timezone.utc)

        db.session.commit()
        logger.info("Run #%d terminé — %d matched_name, %d matched_fqdn, %d matched_ip, %d no_match",
                     run.id, matched_name, matched_fqdn, matched_ip, no_match)

        # 7. Notifications si anomalies détectées
        anomaly_stats = (
            db.session.query(Anomaly.type, db.func.count(Anomaly.id))
            .filter(Anomaly.run_id == run.id)
            .group_by(Anomaly.type)
            .all()
        )
        anomaly_details = {t: c for t, c in anomaly_stats}
        anomaly_count = sum(anomaly_details.values())
        _notify_webhook(run, anomaly_count)
        _notify_email(run, anomaly_count, anomaly_details)

        # 8. Exports (consolidé JSONL.gz, rapport MD, bruts JSON.gz)
        try:
            from collector.exporter import run_exports
            run_exports(run.id, anomaly_details, vm_list=vm_list, ipam_list=ipam_raw)
        except Exception as export_err:
            logger.warning("Echec exports : %s", export_err)

    except Exception as e:
        logger.error("Run #%d échoué : %s", run.id, e, exc_info=True)
        db.session.rollback()
        # Recréer le run en échec dans une transaction propre
        fail_run = Run(status="FAIL", error_message=str(e),
                       ended_at=datetime.now(timezone.utc))
        db.session.add(fail_run)
        db.session.commit()
        return fail_run

    return run
