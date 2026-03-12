"""Requetes et helpers partages entre les routes web et l'API REST."""

import csv
import io
from app import db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly


def build_inventory_query(run_id, q="", status="", node="", vm_type="",
                          match="", tag="", role="", zone="",
                          sort="vm_name", order="asc"):
    """Construit la requete inventaire avec filtres et tri."""
    query = (
        db.session.query(ConsolidatedAsset, Asset, IpamRecord)
        .join(Asset, ConsolidatedAsset.asset_id == Asset.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.run_id == run_id)
    )

    if q:
        pattern = f"%{q}%"
        query = query.filter(
            db.or_(
                Asset.vm_name.ilike(pattern),
                ConsolidatedAsset.ip_final.ilike(pattern),
                ConsolidatedAsset.dns_final.ilike(pattern),
            )
        )
    if status:
        query = query.filter(Asset.status == status)
    if node:
        query = query.filter(Asset.node == node)
    if vm_type:
        query = query.filter(Asset.type == vm_type)
    if match:
        query = query.filter(ConsolidatedAsset.match_status == match)
    if tag:
        query = query.filter(Asset.tags.ilike(f"%{tag}%"))
    if role:
        query = query.filter(ConsolidatedAsset.role == role)
    if zone:
        query = query.filter(IpamRecord.meta_zone == zone)

    sort_map = {
        "vm_name": Asset.vm_name,
        "status": Asset.status,
        "ip": ConsolidatedAsset.ip_final,
        "cpu": Asset.cpu_usage,
        "ram": Asset.ram_used,
        "match": ConsolidatedAsset.match_status,
    }
    sort_col = sort_map.get(sort, Asset.vm_name)
    query = query.order_by(sort_col.desc() if order == "desc" else sort_col.asc())

    return query


def ram_percent(asset):
    """Calcule le pourcentage RAM utilise, ou None si donnees manquantes."""
    if asset.ram_max and asset.ram_max > 0 and asset.ram_used is not None:
        return round(asset.ram_used / asset.ram_max * 100)
    return None


def disk_percent(asset):
    """Calcule le pourcentage disque utilise, ou None si donnees manquantes."""
    if asset.disk_max and asset.disk_max > 0 and asset.disk_used is not None:
        return round(asset.disk_used / asset.disk_max * 100, 1)
    return None


def serialize_inventory_item(ca, asset, ipam):
    """Serialise un item d'inventaire en dict JSON-compatible."""
    return {
        "id": asset.id,
        "vm_name": asset.vm_name,
        "node": asset.node,
        "status": asset.status,
        "type": asset.type,
        "tags": asset.tags,
        "ip": ca.ip_final or "",
        "dns": ca.dns_final or "",
        "fqdn": asset.fqdn or "",
        "os": asset.os or "",
        "annotation": asset.annotation or "",
        "match_status": ca.match_status,
        "role": ca.role or "Indéterminé",
        "source": ca.source_ip_dns,
        "tenant": ipam.tenant if ipam else None,
        "site": ipam.site if ipam else None,
        "meta_zone": ipam.meta_zone if ipam else None,
        "cpu_usage": asset.cpu_usage,
        "ram_pct": ram_percent(asset),
        "disk_pct": disk_percent(asset),
        "uptime": asset.uptime,
    }


def get_stats_data():
    """Calcule les statistiques du dashboard (partage web + API)."""
    last_run = Run.query.order_by(Run.id.desc()).first()
    if not last_run:
        return {"has_data": False}

    match_data = {
        "matched_name": last_run.matched_name_count,
        "matched_fqdn": last_run.matched_fqdn_count or 0,
        "matched_ip": last_run.matched_ip_count or 0,
        "no_match": last_run.no_match_count,
    }

    anomaly_stats = (
        db.session.query(Anomaly.type, db.func.count(Anomaly.id))
        .filter(Anomaly.run_id == last_run.id)
        .group_by(Anomaly.type)
        .all()
    )
    anomaly_data = {t: c for t, c in anomaly_stats}

    recent_runs = Run.query.filter(Run.status == "SUCCESS").order_by(Run.id.desc()).limit(10).all()
    recent_runs.reverse()
    evolution = {
        "labels": [f"#{r.id}" for r in recent_runs],
        "matched_name": [r.matched_name_count for r in recent_runs],
        "matched_fqdn": [r.matched_fqdn_count or 0 for r in recent_runs],
        "matched_ip": [r.matched_ip_count or 0 for r in recent_runs],
        "no_match": [r.no_match_count for r in recent_runs],
        "vms": [r.vm_count for r in recent_runs],
    }

    return {
        "has_data": True,
        "match": match_data,
        "anomalies": anomaly_data,
        "evolution": evolution,
    }


def get_run_comparison_data(run_id):
    """Recupere les donnees d'un run pour la comparaison (partage web + API)."""
    rows = (
        db.session.query(ConsolidatedAsset, Asset, IpamRecord)
        .join(Asset, ConsolidatedAsset.asset_id == Asset.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.run_id == run_id)
        .all()
    )
    return {asset.vm_name: (ca, asset, ipam) for ca, asset, ipam in rows}


def export_inventory_csv(run_id):
    """Genere le contenu CSV de l'inventaire d'un run (partage web + API)."""
    rows = (
        db.session.query(ConsolidatedAsset, Asset, IpamRecord)
        .join(Asset, ConsolidatedAsset.asset_id == Asset.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.run_id == run_id)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Hostname", "Hote", "Etat", "Type", "IP", "FQDN", "OS",
        "Note", "Role", "Tenant", "Site", "Meta Zone",
        "CPU (%)", "RAM (%)", "Disque (%)",
        "Uptime (s)", "Match", "Source",
    ])
    for ca, asset, ipam in rows:
        writer.writerow([
            asset.vm_name, asset.node, asset.status, asset.type,
            ca.ip_final or "", asset.fqdn or "",
            asset.os or "", asset.annotation or "",
            ca.role or "Indéterminé",
            ipam.tenant if ipam else "",
            ipam.site if ipam else "",
            ipam.meta_zone if ipam else "",
            asset.cpu_usage if asset.cpu_usage is not None else "",
            ram_percent(asset) or "", disk_percent(asset) or "",
            asset.uptime if asset.uptime is not None else "",
            ca.match_status, ca.source_ip_dns,
        ])

    return output.getvalue()
