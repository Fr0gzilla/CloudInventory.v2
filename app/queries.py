"""Requetes et helpers partages entre les routes web et l'API REST."""

from app import db
from app.models import Asset, IpamRecord, ConsolidatedAsset


def build_inventory_query(run_id, q="", status="", node="", vm_type="",
                          match="", tag="", sort="vm_name", order="asc"):
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
        "match_status": ca.match_status,
        "source": ca.source_ip_dns,
        "tenant": ipam.tenant if ipam else None,
        "site": ipam.site if ipam else None,
        "cpu_usage": asset.cpu_usage,
        "ram_pct": ram_percent(asset),
        "uptime": asset.uptime,
    }
