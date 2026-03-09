"""Routes Flask — dashboard, runs, inventory, assets, anomalies, AJAX."""

from flask import Blueprint, render_template, redirect, url_for, request, jsonify, Response
from flask_login import login_required
from app import db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly
from app.queries import (
    build_inventory_query, ram_percent, disk_percent,
    get_stats_data, get_run_comparison_data, export_inventory_csv,
)

main_bp = Blueprint("main", __name__)

PER_PAGE = 25


def _get_tag_filters():
    """Extrait les catégories et valeurs de tags pour les filtres."""
    all_tags = [r[0] for r in db.session.query(Asset.tags).filter(Asset.tags.isnot(None)).distinct().all()]
    categories = {}
    for tags_str in all_tags:
        for t in tags_str.split(","):
            t = t.strip()
            if ":" in t:
                cat, val = t.split(":", 1)
                categories.setdefault(cat.strip(), set()).add(val.strip())
    return {k: sorted(v) for k, v in sorted(categories.items())}


# ---------- Dashboard ----------
@main_bp.route("/")
@login_required
def dashboard():
    last_run = Run.query.order_by(Run.id.desc()).first()
    total_runs = Run.query.count()
    total_assets = Asset.query.count()
    total_anomalies = Anomaly.query.count() if last_run else 0
    return render_template(
        "dashboard.html", run=last_run,
        total_runs=total_runs, total_assets=total_assets,
        total_anomalies=total_anomalies,
    )


# ---------- AJAX : lancer inventaire ----------
@main_bp.route("/ajax/run", methods=["POST"])
@login_required
def ajax_trigger_run():
    from collector.inventory_runner import run_inventory
    run = run_inventory()
    return jsonify({
        "id": run.id,
        "status": run.status,
        "vm_count": run.vm_count,
        "ip_count": run.ip_count,
        "matched_name_count": run.matched_name_count,
        "no_match_count": run.no_match_count,
        "error_message": run.error_message,
    })


# ---------- Lancer inventaire (POST classique) ----------
@main_bp.route("/run", methods=["POST"])
@login_required
def trigger_run():
    from collector.inventory_runner import run_inventory
    run = run_inventory()
    return redirect(url_for("main.run_detail", run_id=run.id))


# ---------- AJAX : stats dashboard ----------
@main_bp.route("/ajax/stats")
@login_required
def ajax_stats():
    return jsonify(get_stats_data())


# ---------- Liste des runs (avec pagination) ----------
@main_bp.route("/runs")
@login_required
def runs_list():
    page = request.args.get("page", 1, type=int)
    pagination = Run.query.order_by(Run.id.desc()).paginate(
        page=page, per_page=PER_PAGE, error_out=False
    )
    all_runs = Run.query.filter(Run.status == "SUCCESS").order_by(Run.id.desc()).all()
    return render_template("runs.html", runs=pagination.items, pagination=pagination, all_runs=all_runs)


# ---------- Détail d'un run ----------
@main_bp.route("/runs/<int:run_id>")
@login_required
def run_detail(run_id):
    run = Run.query.get_or_404(run_id)

    inventory = (
        db.session.query(ConsolidatedAsset, Asset, IpamRecord)
        .join(Asset, ConsolidatedAsset.asset_id == Asset.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.run_id == run_id)
        .all()
    )

    anomalies = (
        db.session.query(Anomaly, Asset)
        .join(Asset, Anomaly.asset_id == Asset.id)
        .filter(Anomaly.run_id == run_id)
        .all()
    )

    return render_template(
        "run_detail.html", run=run, inventory=inventory, anomalies=anomalies
    )


# ---------- Inventaire (avec pagination, tri, filtre tags) ----------
@main_bp.route("/inventory")
@login_required
def inventory():
    last_run = Run.query.order_by(Run.id.desc()).first()
    if not last_run:
        return render_template("inventory.html", items=[], run=None, filters={},
                               pagination=None, tag_filters={})

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    node = request.args.get("node", "")
    vm_type = request.args.get("type", "")
    match = request.args.get("match", "")
    tag = request.args.get("tag", "")
    sort = request.args.get("sort", "vm_name")
    order = request.args.get("order", "asc")
    page = request.args.get("page", 1, type=int)

    query = build_inventory_query(last_run.id, q, status, node, vm_type, match, tag, sort, order)
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    filters = {
        "statuses": [r[0] for r in db.session.query(Asset.status).distinct().all()],
        "nodes": [r[0] for r in db.session.query(Asset.node).distinct().all()],
        "types": [r[0] for r in db.session.query(Asset.type).distinct().all()],
        "matches": [r[0] for r in db.session.query(ConsolidatedAsset.match_status).distinct().all()],
    }

    tag_filters = _get_tag_filters()

    return render_template(
        "inventory.html", items=pagination.items, run=last_run, filters=filters,
        pagination=pagination, tag_filters=tag_filters,
        q=q, status=status, node=node, vm_type=vm_type, match=match, tag=tag,
        sort=sort, order=order,
    )


# ---------- AJAX : recherche live inventaire ----------
@main_bp.route("/ajax/inventory/search")
@login_required
def ajax_inventory_search():
    last_run = Run.query.order_by(Run.id.desc()).first()
    if not last_run:
        return jsonify({"items": [], "total": 0})

    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    node = request.args.get("node", "")
    vm_type = request.args.get("type", "")
    match = request.args.get("match", "")
    tag = request.args.get("tag", "")
    sort = request.args.get("sort", "vm_name")
    order = request.args.get("order", "asc")

    query = build_inventory_query(last_run.id, q, status, node, vm_type, match, tag, sort, order)
    results = query.limit(100).all()

    items = []
    for ca, asset, ipam in results:
        items.append({
            "id": asset.id,
            "vm_name": asset.vm_name,
            "status": asset.status,
            "ip": ca.ip_final or "",
            "dns": ca.dns_final or "",
            "tenant": ipam.tenant if ipam else None,
            "site": ipam.site if ipam else None,
            "cpu_usage": asset.cpu_usage,
            "ram_pct": ram_percent(asset),
            "match_status": ca.match_status,
        })

    return jsonify({"items": items, "total": len(items)})


# ---------- Export CSV ----------
@main_bp.route("/inventory/export")
@login_required
def inventory_export():
    last_run = Run.query.order_by(Run.id.desc()).first()
    if not last_run:
        return "Aucun run", 404

    return Response(
        export_inventory_csv(last_run.id),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inventaire_run{last_run.id}.csv"},
    )


# ---------- Détail VM ----------
@main_bp.route("/assets/<int:asset_id>")
@login_required
def asset_detail(asset_id):
    asset = Asset.query.get_or_404(asset_id)

    history = (
        db.session.query(ConsolidatedAsset, Run, IpamRecord)
        .join(Run, ConsolidatedAsset.run_id == Run.id)
        .outerjoin(IpamRecord, ConsolidatedAsset.ipam_record_id == IpamRecord.id)
        .filter(ConsolidatedAsset.asset_id == asset_id)
        .order_by(Run.id.desc())
        .limit(30)
        .all()
    )

    anomalies = (
        db.session.query(Anomaly, Run)
        .join(Run, Anomaly.run_id == Run.id)
        .filter(Anomaly.asset_id == asset_id)
        .order_by(Anomaly.id.desc())
        .all()
    )

    return render_template(
        "asset_detail.html", asset=asset, history=history, anomalies=anomalies
    )


# ---------- Page anomalies (avec pagination) ----------
@main_bp.route("/anomalies")
@login_required
def anomalies_list():
    query = (
        db.session.query(Anomaly, Asset, Run)
        .join(Asset, Anomaly.asset_id == Asset.id)
        .join(Run, Anomaly.run_id == Run.id)
        .order_by(Anomaly.id.desc())
    )

    anomaly_type = request.args.get("type", "")
    run_id = request.args.get("run", "")

    if anomaly_type:
        query = query.filter(Anomaly.type == anomaly_type)
    if run_id:
        query = query.filter(Anomaly.run_id == int(run_id))

    page = request.args.get("page", 1, type=int)
    pagination = query.paginate(page=page, per_page=PER_PAGE, error_out=False)

    types = [r[0] for r in db.session.query(Anomaly.type).distinct().all()]
    run_ids = [r[0] for r in db.session.query(Anomaly.run_id).distinct().order_by(Anomaly.run_id.desc()).all()]

    return render_template(
        "anomalies.html", items=pagination.items, types=types, run_ids=run_ids,
        anomaly_type=anomaly_type, run_id=run_id, pagination=pagination,
    )


# ---------- Comparaison de runs ----------
@main_bp.route("/runs/compare")
@login_required
def run_compare():
    run1_id = request.args.get("run1", type=int)
    run2_id = request.args.get("run2", type=int)

    all_runs = Run.query.filter(Run.status == "SUCCESS").order_by(Run.id.desc()).all()

    if not run1_id or not run2_id:
        return render_template("run_compare.html", all_runs=all_runs,
                               run1=None, run2=None, added=[], removed=[], changed=[])

    run1 = Run.query.get_or_404(run1_id)
    run2 = Run.query.get_or_404(run2_id)

    data1 = get_run_comparison_data(run1_id)
    data2 = get_run_comparison_data(run2_id)

    names1 = set(data1.keys())
    names2 = set(data2.keys())

    added = [(data2[n][1], data2[n][0]) for n in sorted(names2 - names1)]
    removed = [(data1[n][1], data1[n][0]) for n in sorted(names1 - names2)]

    changed = []
    for name in sorted(names1 & names2):
        ca1, asset1, _ = data1[name]
        ca2, asset2, _ = data2[name]
        diffs = []
        if ca1.ip_final != ca2.ip_final:
            diffs.append(("IP", ca1.ip_final or "\u2014", ca2.ip_final or "\u2014"))
        if ca1.dns_final != ca2.dns_final:
            diffs.append(("DNS", ca1.dns_final or "\u2014", ca2.dns_final or "\u2014"))
        if ca1.match_status != ca2.match_status:
            diffs.append(("Match", ca1.match_status, ca2.match_status))
        if asset1.status != asset2.status:
            diffs.append(("Status", asset1.status, asset2.status))
        if diffs:
            changed.append((asset2, diffs))

    return render_template("run_compare.html", all_runs=all_runs,
                           run1=run1, run2=run2, run1_id=run1_id, run2_id=run2_id,
                           added=added, removed=removed, changed=changed)
