from datetime import datetime, timezone
from app import db


class Run(db.Model):
    __tablename__ = "run"

    id = db.Column(db.Integer, primary_key=True)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    ended_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default="RUNNING")  # RUNNING / SUCCESS / FAIL
    error_message = db.Column(db.Text, nullable=True)
    vm_count = db.Column(db.Integer, default=0)
    ip_count = db.Column(db.Integer, default=0)
    matched_name_count = db.Column(db.Integer, default=0)
    matched_ip_count = db.Column(db.Integer, default=0)
    no_match_count = db.Column(db.Integer, default=0)

    consolidated_assets = db.relationship("ConsolidatedAsset", backref="run", lazy=True)
    anomalies = db.relationship("Anomaly", backref="run", lazy=True)


class Asset(db.Model):
    __tablename__ = "asset"

    id = db.Column(db.Integer, primary_key=True)
    vm_id = db.Column(db.String(50))
    vm_name = db.Column(db.String(100))
    type = db.Column(db.String(20))  # qemu / lxc
    node = db.Column(db.String(100))
    status = db.Column(db.String(20))  # running / stopped
    tags = db.Column(db.String(200), nullable=True)
    ip_reported = db.Column(db.String(45), nullable=True)

    # Métriques runtime (Proxmox VE / QEMU Guest Agent)
    cpu_count = db.Column(db.Integer, nullable=True)
    cpu_usage = db.Column(db.Float, nullable=True)       # % utilisation CPU
    ram_max = db.Column(db.BigInteger, nullable=True)     # RAM max en octets
    ram_used = db.Column(db.BigInteger, nullable=True)    # RAM utilisée en octets
    disk_max = db.Column(db.BigInteger, nullable=True)    # Disque max en octets
    disk_used = db.Column(db.BigInteger, nullable=True)   # Disque utilisé en octets
    uptime = db.Column(db.Integer, nullable=True)         # Uptime en secondes

    consolidated_assets = db.relationship("ConsolidatedAsset", backref="asset", lazy=True)
    anomalies = db.relationship("Anomaly", backref="asset", lazy=True)


class IpamRecord(db.Model):
    __tablename__ = "ipam_record"

    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(45))
    dns_name = db.Column(db.String(200), nullable=True)
    status = db.Column(db.String(50), nullable=True)
    tenant = db.Column(db.String(100), nullable=True)
    site = db.Column(db.String(100), nullable=True)

    consolidated_assets = db.relationship("ConsolidatedAsset", backref="ipam_record", lazy=True)


class ConsolidatedAsset(db.Model):
    __tablename__ = "consolidated_asset"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("run.id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"), nullable=False)
    ipam_record_id = db.Column(db.Integer, db.ForeignKey("ipam_record.id"), nullable=True)
    ip_final = db.Column(db.String(45), nullable=True)
    dns_final = db.Column(db.String(200), nullable=True)
    source_ip_dns = db.Column(db.String(20))  # NETBOX / VIRT
    match_status = db.Column(db.String(30))  # MATCHED_NAME / MATCHED_IP / NO_MATCH
    role = db.Column(db.String(50), default="Indéterminé")


class Anomaly(db.Model):
    __tablename__ = "anomaly"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("run.id"), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey("asset.id"), nullable=False)
    type = db.Column(db.String(50))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
