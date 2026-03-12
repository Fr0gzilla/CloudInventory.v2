"""[API] API REST — endpoints JSON protégés par JWT."""

import os
import logging
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import create_access_token, jwt_required
from app import db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly
from app.auth import _get_admin_password_hash
from app.queries import (
    build_inventory_query, serialize_inventory_item, ram_percent, disk_percent,
    get_stats_data, get_run_comparison_data, export_inventory_csv,
)
from werkzeug.security import check_password_hash

logger = logging.getLogger("cloudinventory.api")

api_bp = Blueprint("api", __name__, url_prefix="/api")


# ──────────────────────────────────────────────
# HEALTH — statut de l'application (pas de JWT)
# ──────────────────────────────────────────────
@api_bp.route("/health", methods=["GET"])
def api_health():
    """Healthcheck de l'application
    ---
    tags:
      - Health
    responses:
      200:
        description: Statut de l'application et dernier run
    """
    from app import APP_VERSION
    from app.scheduler import get_scheduler_info
    last_run = Run.query.order_by(Run.id.desc()).first()
    return jsonify({
        "status": "ok",
        "version": APP_VERSION,
        "last_run": last_run.to_dict() if last_run else None,
        "scheduler": get_scheduler_info(),
    })


# ──────────────────────────────────────────────
# ! AUTH — obtenir un token JWT
# ──────────────────────────────────────────────
@api_bp.route("/login", methods=["POST"])
def api_login():
    """Obtenir un token JWT
    ---
    tags:
      - Authentification
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required: [username, password]
          properties:
            username:
              type: string
              example: admin
            password:
              type: string
              example: admin
    responses:
      200:
        description: Token JWT
        schema:
          type: object
          properties:
            access_token:
              type: string
      400:
        description: Body JSON requis
      401:
        description: Identifiants incorrects
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Body JSON requis"}), 400

    username = data.get("username", "")
    password = data.get("password", "")

    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    pw_hash = _get_admin_password_hash()

    if username != admin_username or not check_password_hash(pw_hash, password):
        return jsonify({"error": "Identifiants incorrects"}), 401

    token = create_access_token(identity=username)
    logger.info("Connexion API réussie pour '%s'", username)
    return jsonify({"access_token": token}), 200


# ──────────────────────────────────────────────
# STATS — tableau de bord
# ──────────────────────────────────────────────
@api_bp.route("/stats", methods=["GET"])
@jwt_required()
def api_stats():
    """Statistiques du dashboard
    ---
    tags:
      - Dashboard
    security:
      - Bearer: []
    responses:
      200:
        description: Statistiques globales (match, anomalies, evolution)
    """
    return jsonify(get_stats_data())


# ──────────────────────────────────────────────
# RUNS — lister / créer / détail / comparer
# ──────────────────────────────────────────────
@api_bp.route("/runs", methods=["GET"])
@jwt_required()
def api_runs_list():
    """Liste paginee des runs
    ---
    tags:
      - Runs
    security:
      - Bearer: []
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 25
    responses:
      200:
        description: Liste paginee des runs
    """
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    pagination = Run.query.order_by(Run.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    runs = [r.to_dict() for r in pagination.items]

    return jsonify({
        "runs": runs,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


@api_bp.route("/runs", methods=["POST"])
@jwt_required()
def api_trigger_run():
    """Lancer un nouvel inventaire
    ---
    tags:
      - Runs
    security:
      - Bearer: []
    responses:
      201:
        description: Run cree et execute
    """
    from collector.inventory_runner import run_inventory
    run = run_inventory()
    return jsonify(run.to_dict()), 201


@api_bp.route("/runs/<int:run_id>", methods=["GET"])
@jwt_required()
def api_run_detail(run_id):
    """Detail d'un run avec inventaire et anomalies
    ---
    tags:
      - Runs
    security:
      - Bearer: []
    parameters:
      - name: run_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Detail du run
      404:
        description: Run introuvable
    """
    run = Run.query.get_or_404(run_id)

    inventory_rows = (
        db.session.query(ConsolidatedAsset, Asset, IpamRecord)
        .join(Asset, ConsolidatedAsset.asset_id == Asset.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.run_id == run_id)
        .all()
    )

    inventory = [serialize_inventory_item(ca, asset, ipam) for ca, asset, ipam in inventory_rows]

    anomaly_rows = (
        db.session.query(Anomaly, Asset)
        .join(Asset, Anomaly.asset_id == Asset.id)
        .filter(Anomaly.run_id == run_id)
        .all()
    )

    anomalies = []
    for anomaly, asset in anomaly_rows:
        anomalies.append({
            "id": anomaly.id,
            "type": anomaly.type,
            "details": anomaly.details,
            "created_at": anomaly.created_at.isoformat() if anomaly.created_at else None,
            "asset": {"id": asset.id, "vm_name": asset.vm_name},
        })

    result = run.to_dict()
    result["inventory"] = inventory
    result["anomalies"] = anomalies
    return jsonify(result)


@api_bp.route("/runs/compare", methods=["GET"])
@jwt_required()
def api_run_compare():
    """Comparer deux runs
    ---
    tags:
      - Runs
    security:
      - Bearer: []
    parameters:
      - name: run1
        in: query
        type: integer
        required: true
      - name: run2
        in: query
        type: integer
        required: true
    responses:
      200:
        description: Differences entre les deux runs (added, removed, changed)
      400:
        description: Parametres run1 et run2 requis
    """
    run1_id = request.args.get("run1", type=int)
    run2_id = request.args.get("run2", type=int)

    if not run1_id or not run2_id:
        return jsonify({"error": "Les paramètres run1 et run2 sont requis"}), 400

    Run.query.get_or_404(run1_id)
    Run.query.get_or_404(run2_id)

    data1 = get_run_comparison_data(run1_id)
    data2 = get_run_comparison_data(run2_id)

    names1 = set(data1.keys())
    names2 = set(data2.keys())

    added = [{"vm_name": n, "status": data2[n][1].status} for n in sorted(names2 - names1)]
    removed = [{"vm_name": n, "status": data1[n][1].status} for n in sorted(names1 - names2)]

    changed = []
    for name in sorted(names1 & names2):
        ca1, asset1, _ = data1[name]
        ca2, asset2, _ = data2[name]
        diffs = []
        if ca1.ip_final != ca2.ip_final:
            diffs.append({"field": "IP", "before": ca1.ip_final, "after": ca2.ip_final})
        if ca1.dns_final != ca2.dns_final:
            diffs.append({"field": "DNS", "before": ca1.dns_final, "after": ca2.dns_final})
        if ca1.match_status != ca2.match_status:
            diffs.append({"field": "Match", "before": ca1.match_status, "after": ca2.match_status})
        if asset1.status != asset2.status:
            diffs.append({"field": "Status", "before": asset1.status, "after": asset2.status})
        if diffs:
            changed.append({"vm_name": name, "changes": diffs})

    return jsonify({
        "run1": run1_id,
        "run2": run2_id,
        "added": added,
        "removed": removed,
        "changed": changed,
    })


# ──────────────────────────────────────────────
# INVENTORY — liste avec filtres et export
# ──────────────────────────────────────────────
@api_bp.route("/inventory", methods=["GET"])
@jwt_required()
def api_inventory():
    """Inventaire pagine avec filtres et tri
    ---
    tags:
      - Inventaire
    security:
      - Bearer: []
    parameters:
      - name: q
        in: query
        type: string
        description: Recherche libre (VM, IP, DNS)
      - name: status
        in: query
        type: string
        enum: [running, stopped]
      - name: node
        in: query
        type: string
      - name: type
        in: query
        type: string
        enum: [qemu, lxc]
      - name: match
        in: query
        type: string
        enum: [MATCHED_NAME, MATCHED_FQDN, MATCHED_IP, NO_MATCH]
      - name: tag
        in: query
        type: string
      - name: role
        in: query
        type: string
        description: Filtrer par role fonctionnel
      - name: zone
        in: query
        type: string
        description: Filtrer par meta zone IPAM
      - name: sort
        in: query
        type: string
        default: vm_name
        enum: [vm_name, status, ip, cpu, ram, match]
      - name: order
        in: query
        type: string
        default: asc
        enum: [asc, desc]
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 25
    responses:
      200:
        description: Liste paginee de l'inventaire
    """
    last_run = Run.query.order_by(Run.id.desc()).first()
    if not last_run:
        return jsonify({"items": [], "total": 0, "page": 1, "pages": 0})

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    node = request.args.get("node", "")
    vm_type = request.args.get("type", "")
    match = request.args.get("match", "")
    tag = request.args.get("tag", "")
    role = request.args.get("role", "")
    zone = request.args.get("zone", "")
    sort = request.args.get("sort", "vm_name")
    order = request.args.get("order", "asc")
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)

    query = build_inventory_query(last_run.id, q, status, node, vm_type, match, tag, role, zone, sort, order)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = [serialize_inventory_item(ca, asset, ipam) for ca, asset, ipam in pagination.items]

    return jsonify({
        "items": items,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
        "run_id": last_run.id,
    })


@api_bp.route("/inventory/export", methods=["GET"])
@jwt_required()
def api_inventory_export():
    """Export CSV de l'inventaire
    ---
    tags:
      - Inventaire
    security:
      - Bearer: []
    produces:
      - text/csv
    responses:
      200:
        description: Fichier CSV de l'inventaire
      404:
        description: Aucun run disponible
    """
    last_run = Run.query.order_by(Run.id.desc()).first()
    if not last_run:
        return jsonify({"error": "Aucun run disponible"}), 404

    return Response(
        export_inventory_csv(last_run.id),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventaire_run{last_run.id}.csv"},
    )


# ──────────────────────────────────────────────
# ASSETS — détail d'une VM
# ──────────────────────────────────────────────
@api_bp.route("/assets/<int:asset_id>", methods=["GET"])
@jwt_required()
def api_asset_detail(asset_id):
    """Detail d'un asset avec historique et anomalies
    ---
    tags:
      - Assets
    security:
      - Bearer: []
    parameters:
      - name: asset_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Detail de l'asset (metriques, historique, anomalies)
      404:
        description: Asset introuvable
    """
    asset = Asset.query.get_or_404(asset_id)

    history_rows = (
        db.session.query(ConsolidatedAsset, Run, IpamRecord)
        .join(Run, ConsolidatedAsset.run_id == Run.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.asset_id == asset_id)
        .order_by(Run.id.desc())
        .limit(30)
        .all()
    )

    history = []
    for ca, run, ipam in history_rows:
        history.append({
            "run_id": run.id,
            "run_date": run.started_at.isoformat() if run.started_at else None,
            "ip": ca.ip_final,
            "dns": ca.dns_final,
            "match_status": ca.match_status,
            "source": ca.source_ip_dns,
            "tenant": ipam.tenant if ipam else None,
            "site": ipam.site if ipam else None,
        })

    anomaly_rows = (
        db.session.query(Anomaly, Run)
        .join(Run, Anomaly.run_id == Run.id)
        .filter(Anomaly.asset_id == asset_id)
        .order_by(Anomaly.id.desc())
        .all()
    )

    anomalies = []
    for anomaly, run in anomaly_rows:
        anomalies.append({
            "id": anomaly.id,
            "run_id": run.id,
            "type": anomaly.type,
            "details": anomaly.details,
            "created_at": anomaly.created_at.isoformat() if anomaly.created_at else None,
        })

    return jsonify({
        "id": asset.id,
        "vm_id": asset.vm_id,
        "vm_name": asset.vm_name,
        "type": asset.type,
        "node": asset.node,
        "status": asset.status,
        "tags": asset.tags,
        "ip_reported": asset.ip_reported,
        "fqdn": asset.fqdn,
        "annotation": asset.annotation,
        "cpu_count": asset.cpu_count,
        "cpu_usage": asset.cpu_usage,
        "ram_max": asset.ram_max,
        "ram_used": asset.ram_used,
        "ram_pct": ram_percent(asset),
        "disk_max": asset.disk_max,
        "disk_used": asset.disk_used,
        "disk_pct": disk_percent(asset),
        "uptime": asset.uptime,
        "history": history,
        "anomalies": anomalies,
    })


# ──────────────────────────────────────────────
# ANOMALIES — liste avec filtres
# ──────────────────────────────────────────────
@api_bp.route("/anomalies", methods=["GET"])
@jwt_required()
def api_anomalies():
    """Liste paginee des anomalies
    ---
    tags:
      - Anomalies
    security:
      - Bearer: []
    parameters:
      - name: type
        in: query
        type: string
        description: Filtrer par type d'anomalie
      - name: run
        in: query
        type: integer
        description: Filtrer par ID de run
      - name: page
        in: query
        type: integer
        default: 1
      - name: per_page
        in: query
        type: integer
        default: 25
    responses:
      200:
        description: Liste paginee des anomalies
    """
    query = (
        db.session.query(Anomaly, Asset, Run)
        .join(Asset, Anomaly.asset_id == Asset.id)
        .join(Run, Anomaly.run_id == Run.id)
        .order_by(Anomaly.id.desc())
    )

    anomaly_type = request.args.get("type", "")
    run_id = request.args.get("run", type=int)

    if anomaly_type:
        query = query.filter(Anomaly.type == anomaly_type)
    if run_id:
        query = query.filter(Anomaly.run_id == run_id)

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 25, type=int)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    items = []
    for anomaly, asset, run in pagination.items:
        items.append({
            "id": anomaly.id,
            "type": anomaly.type,
            "details": anomaly.details,
            "created_at": anomaly.created_at.isoformat() if anomaly.created_at else None,
            "run_id": run.id,
            "run_date": run.started_at.isoformat() if run.started_at else None,
            "asset": {"id": asset.id, "vm_name": asset.vm_name},
        })

    return jsonify({
        "items": items,
        "page": pagination.page,
        "pages": pagination.pages,
        "total": pagination.total,
    })


# ──────────────────────────────────────────────
# PURGE — suppression des anciens runs
# ──────────────────────────────────────────────
@api_bp.route("/runs/purge", methods=["POST"])
@jwt_required()
def api_purge_runs():
    """Purger les anciens runs (garder les N derniers)
    ---
    tags:
      - Runs
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        schema:
          type: object
          properties:
            keep:
              type: integer
              default: 30
              description: Nombre de runs a conserver
    responses:
      200:
        description: Nombre de runs supprimes
    """
    data = request.get_json(silent=True) or {}
    keep = data.get("keep", 30)
    if not isinstance(keep, int) or keep < 1:
        return jsonify({"error": "Le paramètre 'keep' doit être un entier >= 1"}), 400

    all_runs = Run.query.order_by(Run.id.desc()).all()
    to_delete = all_runs[keep:]

    deleted = 0
    for run in to_delete:
        Anomaly.query.filter_by(run_id=run.id).delete()
        ConsolidatedAsset.query.filter_by(run_id=run.id).delete()
        db.session.delete(run)
        deleted += 1

    db.session.commit()
    logger.info("Purge : %d runs supprimés (conservé les %d derniers)", deleted, keep)
    return jsonify({"deleted": deleted, "kept": keep})


