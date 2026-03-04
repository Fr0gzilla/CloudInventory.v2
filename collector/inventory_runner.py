"""Runner d'inventaire — orchestre la collecte, consolidation et détection d'anomalies."""

import os
from collections import Counter
from datetime import datetime, timezone
from app import db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly
from collector.mock_virtualisation import fetch_mock_vms
from collector.mock_netbox import fetch_mock_ipam
from collector.netbox_client import fetch_ipam_records


def _upsert_assets(vm_list):
    """Insère ou met à jour les assets en base (upsert sur vm_id)."""
    runtime_fields = ("cpu_count", "cpu_usage", "ram_max", "ram_used",
                      "disk_max", "disk_used", "uptime")

    for vm in vm_list:
        asset = Asset.query.filter_by(vm_id=vm["vm_id"]).first()
        if asset:
            asset.vm_name = vm["vm_name"]
            asset.type = vm["type"]
            asset.node = vm["node"]
            asset.status = vm["status"]
            asset.tags = vm.get("tags")
            asset.ip_reported = vm.get("ip_reported")
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
                **{f: vm.get(f) for f in runtime_fields},
            )
            db.session.add(asset)
    db.session.flush()


def _upsert_ipam_records(records):
    """Insère ou met à jour les IPAM records (upsert sur ip)."""
    for rec in records:
        ipam = IpamRecord.query.filter_by(ip=rec["ip"]).first()
        if ipam:
            ipam.dns_name = rec["dns_name"]
            ipam.status = rec.get("status")
            ipam.tenant = rec.get("tenant")
            ipam.site = rec.get("site")
        else:
            ipam = IpamRecord(
                ip=rec["ip"],
                dns_name=rec["dns_name"],
                status=rec.get("status"),
                tenant=rec.get("tenant"),
                site=rec.get("site"),
            )
            db.session.add(ipam)
    db.session.flush()


def _detect_ipam_anomalies(run):
    """Détecte les anomalies DUPLICATE_DNS et DUPLICATE_IP dans les IPAM records."""
    ipam_records = IpamRecord.query.all()

    # DUPLICATE_DNS : plusieurs IPAM records avec le même dns_name
    dns_counter = Counter(
        r.dns_name.strip().lower()
        for r in ipam_records
        if r.dns_name and r.dns_name.strip()
    )
    for dns, count in dns_counter.items():
        if count > 1:
            dupes = IpamRecord.query.filter(
                db.func.lower(IpamRecord.dns_name) == dns
            ).all()
            ips = ", ".join(d.ip for d in dupes)
            # Rattacher à un asset ayant ce dns_name si possible
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
            dupes = IpamRecord.query.filter_by(ip=ip).all()
            names = ", ".join(d.dns_name or "?" for d in dupes)
            db.session.add(Anomaly(
                run_id=run.id, asset_id=Asset.query.first().id,
                type="DUPLICATE_IP",
                details=f"IP '{ip}' présente {count} fois dans NetBox (DNS: {names})",
            ))


def _consolidate(run):
    """Consolide les assets avec les IPAM records et génère les anomalies."""
    assets = Asset.query.all()
    ipam_records = IpamRecord.query.all()

    # Index dns_name (lower) -> IpamRecord
    dns_index = {}
    for ipam in ipam_records:
        if ipam.dns_name:
            key = ipam.dns_name.strip().lower()
            if key:
                dns_index[key] = ipam

    matched_name = 0
    no_match = 0

    for asset in assets:
        vm_key = asset.vm_name.strip().lower() if asset.vm_name else ""
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
            ca = ConsolidatedAsset(
                run_id=run.id,
                asset_id=asset.id,
                ipam_record_id=None,
                ip_final=asset.ip_reported,
                dns_final=asset.vm_name,
                source_ip_dns="VIRT",
                match_status="NO_MATCH",
            )
            no_match += 1

            db.session.add(Anomaly(
                run_id=run.id, asset_id=asset.id,
                type="NO_MATCH",
                details="Aucune correspondance NetBox (dns_name) pour le nom de la VM",
            ))

        db.session.add(ca)

    return matched_name, no_match


def run_inventory():
    """Exécute un run d'inventaire complet.

    Returns:
        Run: L'objet Run créé.
    """
    run = Run(status="RUNNING")
    db.session.add(run)
    db.session.flush()

    try:
        # 1. Collecte virtualisation (mock)
        vm_list = fetch_mock_vms()
        _upsert_assets(vm_list)

        # 2. Collecte IPAM/DNS (mock ou NetBox)
        use_mock = os.getenv("USE_MOCK_IPAM", "true").lower() == "true"
        if use_mock:
            ipam_records = fetch_mock_ipam()
        else:
            ipam_records = fetch_ipam_records()
        _upsert_ipam_records(ipam_records)

        # 3. Consolidation + anomalies de match
        matched_name, no_match = _consolidate(run)

        # 4. Anomalies IPAM (duplicates)
        _detect_ipam_anomalies(run)

        # 5. Compteurs
        run.vm_count = len(vm_list)
        run.ip_count = len(ipam_records)
        run.matched_name_count = matched_name
        run.no_match_count = no_match
        run.status = "SUCCESS"
        run.ended_at = datetime.now(timezone.utc)

        db.session.commit()

    except Exception as e:
        db.session.rollback()
        run.status = "FAIL"
        run.error_message = str(e)
        run.ended_at = datetime.now(timezone.utc)
        db.session.add(run)
        db.session.commit()

    return run
