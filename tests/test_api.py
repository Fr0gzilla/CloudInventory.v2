"""Tests de l'API REST avec authentification JWT."""

import os
import pytest

os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin"
os.environ["USE_MOCK_IPAM"] = "true"

from app import create_app, db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly


@pytest.fixture
def app():
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _get_token(client):
    """Obtient un token JWT via /api/login."""
    resp = client.post("/api/login", json={
        "username": "admin", "password": "admin"
    })
    return resp.get_json()["access_token"]


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _create_run(status="SUCCESS", vm_count=5, matched=3, no_match=2):
    run = Run(status=status, vm_count=vm_count, ip_count=vm_count,
              matched_name_count=matched, no_match_count=no_match)
    db.session.add(run)
    db.session.flush()
    return run


def _create_asset(vm_id="100", vm_name="test-vm", status="running",
                  node="pve1", vm_type="qemu", cpu_usage=25.0,
                  ram_max=4294967296, ram_used=2147483648):
    asset = Asset(vm_id=vm_id, vm_name=vm_name, status=status, type=vm_type,
                  node=node, cpu_usage=cpu_usage, ram_max=ram_max,
                  ram_used=ram_used)
    db.session.add(asset)
    db.session.flush()
    return asset


def _create_ipam(ip="10.0.0.1", dns_name="test-vm", status="active",
                 tenant="infra", site="paris"):
    ipam = IpamRecord(ip=ip, dns_name=dns_name, status=status,
                      tenant=tenant, site=site)
    db.session.add(ipam)
    db.session.flush()
    return ipam


# ============================================================
# Auth JWT
# ============================================================

class TestAPIAuth:

    def test_login_success(self, client):
        resp = client.post("/api/login", json={
            "username": "admin", "password": "admin"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data

    def test_login_bad_password(self, client):
        resp = client.post("/api/login", json={
            "username": "admin", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_login_no_body(self, client):
        resp = client.post("/api/login", content_type="application/json")
        assert resp.status_code == 400

    def test_protected_route_without_token(self, client):
        resp = client.get("/api/stats")
        assert resp.status_code == 401


# ============================================================
# Stats
# ============================================================

class TestAPIStats:

    def test_stats_empty(self, client):
        token = _get_token(client)
        resp = client.get("/api/stats", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["has_data"] is False

    def test_stats_with_data(self, client, app):
        token = _get_token(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/api/stats", headers=_auth_header(token))
        data = resp.get_json()
        assert data["has_data"] is True
        assert "match" in data
        assert "evolution" in data


# ============================================================
# Runs
# ============================================================

class TestAPIRuns:

    def test_runs_list_empty(self, client):
        token = _get_token(client)
        resp = client.get("/api/runs", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_runs_list_with_data(self, client, app):
        token = _get_token(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/api/runs", headers=_auth_header(token))
        data = resp.get_json()
        assert data["total"] == 1
        assert data["runs"][0]["status"] == "SUCCESS"

    def test_run_detail(self, client, app):
        token = _get_token(client)
        with app.app_context():
            run = _create_run()
            db.session.commit()
            run_id = run.id
        resp = client.get(f"/api/runs/{run_id}", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == run_id

    def test_run_detail_404(self, client):
        token = _get_token(client)
        resp = client.get("/api/runs/999", headers=_auth_header(token))
        assert resp.status_code == 404

    def test_trigger_run(self, client):
        token = _get_token(client)
        resp = client.post("/api/runs", headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "SUCCESS"
        assert data["vm_count"] > 0

    def test_run_compare(self, client, app):
        token = _get_token(client)
        with app.app_context():
            run1 = _create_run()
            run2 = _create_run()
            asset = _create_asset()
            db.session.add(ConsolidatedAsset(
                run_id=run1.id, asset_id=asset.id,
                ip_final="10.0.0.1", dns_final="test-vm",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            ))
            db.session.add(ConsolidatedAsset(
                run_id=run2.id, asset_id=asset.id,
                ip_final="10.0.0.99", dns_final="test-vm",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            ))
            db.session.commit()
            r1, r2 = run1.id, run2.id
        resp = client.get(f"/api/runs/compare?run1={r1}&run2={r2}",
                          headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert "changed" in data

    def test_run_compare_missing_params(self, client):
        token = _get_token(client)
        resp = client.get("/api/runs/compare", headers=_auth_header(token))
        assert resp.status_code == 400


# ============================================================
# Inventory
# ============================================================

class TestAPIInventory:

    def _seed(self, app):
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="web-server")
            ipam = _create_ipam(dns_name="web-server")
            ca = ConsolidatedAsset(
                run_id=run.id, asset_id=asset.id, ipam_record_id=ipam.id,
                ip_final="10.0.0.1", dns_final="web-server",
                source_ip_dns="NETBOX", match_status="MATCHED_NAME",
            )
            db.session.add(ca)
            db.session.commit()

    def test_inventory_empty(self, client):
        token = _get_token(client)
        resp = client.get("/api/inventory", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_inventory_with_data(self, client, app):
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory", headers=_auth_header(token))
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["vm_name"] == "web-server"

    def test_inventory_filter_q(self, client, app):
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory?q=web", headers=_auth_header(token))
        assert resp.get_json()["total"] == 1

    def test_inventory_filter_no_result(self, client, app):
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory?q=zzz", headers=_auth_header(token))
        assert resp.get_json()["total"] == 0

    def test_inventory_export_csv(self, client, app):
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory/export", headers=_auth_header(token))
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        assert b"web-server" in resp.data

    def test_inventory_export_empty(self, client):
        token = _get_token(client)
        resp = client.get("/api/inventory/export", headers=_auth_header(token))
        assert resp.status_code == 404


# ============================================================
# Assets
# ============================================================

class TestAPIAssets:

    def test_asset_detail(self, client, app):
        token = _get_token(client)
        with app.app_context():
            asset = _create_asset()
            db.session.commit()
            aid = asset.id
        resp = client.get(f"/api/assets/{aid}", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["vm_name"] == "test-vm"
        assert "history" in data
        assert "anomalies" in data

    def test_asset_detail_404(self, client):
        token = _get_token(client)
        resp = client.get("/api/assets/999", headers=_auth_header(token))
        assert resp.status_code == 404


# ============================================================
# Anomalies
# ============================================================

class TestAPIAnomalies:

    def test_anomalies_empty(self, client):
        token = _get_token(client)
        resp = client.get("/api/anomalies", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_anomalies_with_data(self, client, app):
        token = _get_token(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset()
            anomaly = Anomaly(run_id=run.id, asset_id=asset.id,
                              type="NO_MATCH", details="Pas de correspondance")
            db.session.add(anomaly)
            db.session.commit()
        resp = client.get("/api/anomalies", headers=_auth_header(token))
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["type"] == "NO_MATCH"

    def test_anomalies_filter_type(self, client, app):
        token = _get_token(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset()
            db.session.add(Anomaly(run_id=run.id, asset_id=asset.id,
                                   type="NO_MATCH", details="test"))
            db.session.add(Anomaly(run_id=run.id, asset_id=asset.id,
                                   type="STATUS_MISMATCH", details="test"))
            db.session.commit()
        resp = client.get("/api/anomalies?type=NO_MATCH",
                          headers=_auth_header(token))
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["type"] == "NO_MATCH"
