"""Tests unitaires CloudInventory — modeles, routes, consolidation."""

import os
import pytest

os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin"
os.environ["USE_MOCK_IPAM"] = "true"

from app import create_app, db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly


@pytest.fixture
def app():
    """Cree une app Flask de test avec une DB en memoire."""
    app = create_app()
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Client HTTP de test."""
    return app.test_client()


def _login(client):
    """Se connecte avec le compte admin."""
    return client.post("/login", data={
        "username": "admin", "password": "admin"
    }, follow_redirects=True)


def _create_run(status="SUCCESS", vm_count=5, matched=3, no_match=2):
    """Cree un run de test."""
    run = Run(status=status, vm_count=vm_count, ip_count=vm_count,
              matched_name_count=matched, no_match_count=no_match)
    db.session.add(run)
    db.session.flush()
    return run


def _create_asset(vm_id="100", vm_name="test-vm", status="running",
                  node="pve1", vm_type="qemu", tags=None,
                  cpu_usage=25.0, ram_max=4294967296, ram_used=2147483648):
    """Cree un asset de test."""
    asset = Asset(
        vm_id=vm_id, vm_name=vm_name, status=status, type=vm_type,
        node=node, tags=tags, cpu_usage=cpu_usage,
        ram_max=ram_max, ram_used=ram_used,
    )
    db.session.add(asset)
    db.session.flush()
    return asset


def _create_ipam(ip="10.0.0.1", dns_name="test-vm", status="active",
                 tenant="infra", site="paris"):
    """Cree un IpamRecord de test."""
    ipam = IpamRecord(ip=ip, dns_name=dns_name, status=status,
                      tenant=tenant, site=site)
    db.session.add(ipam)
    db.session.flush()
    return ipam


# ============================================================
# Tests modeles
# ============================================================

class TestModels:

    def test_run_creation(self, app):
        with app.app_context():
            run = _create_run()
            db.session.commit()
            assert run.id is not None
            assert run.status == "SUCCESS"
            assert run.vm_count == 5

    def test_asset_creation(self, app):
        with app.app_context():
            asset = _create_asset()
            db.session.commit()
            assert asset.id is not None
            assert asset.vm_name == "test-vm"
            assert asset.cpu_usage == 25.0

    def test_ipam_creation(self, app):
        with app.app_context():
            ipam = _create_ipam()
            db.session.commit()
            assert ipam.id is not None
            assert ipam.tenant == "infra"

    def test_consolidated_asset(self, app):
        with app.app_context():
            run = _create_run()
            asset = _create_asset()
            ipam = _create_ipam()
            ca = ConsolidatedAsset(
                run_id=run.id, asset_id=asset.id, ipam_record_id=ipam.id,
                ip_final="10.0.0.1", dns_final="test-vm",
                source_ip_dns="NETBOX", match_status="MATCHED_NAME",
            )
            db.session.add(ca)
            db.session.commit()
            assert ca.match_status == "MATCHED_NAME"
            assert ca.run.id == run.id

    def test_anomaly(self, app):
        with app.app_context():
            run = _create_run()
            asset = _create_asset()
            anomaly = Anomaly(
                run_id=run.id, asset_id=asset.id,
                type="NO_MATCH", details="Test anomaly",
            )
            db.session.add(anomaly)
            db.session.commit()
            assert anomaly.type == "NO_MATCH"


# ============================================================
# Tests authentification
# ============================================================

class TestAuth:

    def test_login_redirect(self, client):
        """Les pages protegees redirigent vers /login."""
        resp = client.get("/")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_login_success(self, client):
        resp = _login(client)
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data

    def test_login_fail(self, client):
        resp = client.post("/login", data={
            "username": "admin", "password": "wrong"
        }, follow_redirects=True)
        assert b"incorrects" in resp.data

    def test_logout(self, client):
        _login(client)
        resp = client.get("/logout", follow_redirects=True)
        assert b"login" in resp.data.lower()


# ============================================================
# Tests routes principales
# ============================================================

class TestRoutes:

    def test_dashboard_empty(self, client, app):
        _login(client)
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data

    def test_inventory_empty(self, client, app):
        _login(client)
        resp = client.get("/inventory")
        assert resp.status_code == 200
        assert b"Aucun run" in resp.data

    def test_runs_empty(self, client, app):
        _login(client)
        resp = client.get("/runs")
        assert resp.status_code == 200
        assert b"Aucun run" in resp.data

    def test_anomalies_empty(self, client, app):
        _login(client)
        resp = client.get("/anomalies")
        assert resp.status_code == 200
        assert b"Aucune anomalie" in resp.data

    def test_dashboard_with_data(self, client, app):
        _login(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/")
        assert resp.status_code == 200

    def test_inventory_with_data(self, client, app):
        _login(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset()
            ipam = _create_ipam()
            ca = ConsolidatedAsset(
                run_id=run.id, asset_id=asset.id, ipam_record_id=ipam.id,
                ip_final="10.0.0.1", dns_final="test-vm",
                source_ip_dns="NETBOX", match_status="MATCHED_NAME",
            )
            db.session.add(ca)
            db.session.commit()
        resp = client.get("/inventory")
        assert resp.status_code == 200
        assert b"test-vm" in resp.data

    def test_inventory_filter_q(self, client, app):
        _login(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset()
            ca = ConsolidatedAsset(
                run_id=run.id, asset_id=asset.id,
                ip_final="10.0.0.1", dns_final="test-vm",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            )
            db.session.add(ca)
            db.session.commit()
        resp = client.get("/inventory?q=test")
        assert resp.status_code == 200
        assert b"test-vm" in resp.data

    def test_inventory_filter_tag(self, client, app):
        _login(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset(tags="env:production, role:web")
            ca = ConsolidatedAsset(
                run_id=run.id, asset_id=asset.id,
                ip_final="10.0.0.1", dns_final="test-vm",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            )
            db.session.add(ca)
            db.session.commit()
        resp = client.get("/inventory?tag=env:production")
        assert resp.status_code == 200
        assert b"test-vm" in resp.data

    def test_inventory_sort(self, client, app):
        _login(client)
        with app.app_context():
            run = _create_run()
            a1 = _create_asset(vm_id="100", vm_name="alpha")
            a2 = _create_asset(vm_id="101", vm_name="zulu")
            for a in [a1, a2]:
                db.session.add(ConsolidatedAsset(
                    run_id=run.id, asset_id=a.id,
                    ip_final="10.0.0.1", dns_final=a.vm_name,
                    source_ip_dns="VIRT", match_status="NO_MATCH",
                ))
            db.session.commit()
        resp = client.get("/inventory?sort=vm_name&order=desc")
        assert resp.status_code == 200
        data = resp.data.decode()
        assert data.index("zulu") < data.index("alpha")

    def test_run_detail(self, client, app):
        _login(client)
        with app.app_context():
            run = _create_run()
            db.session.commit()
            run_id = run.id
        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200

    def test_run_detail_404(self, client, app):
        _login(client)
        resp = client.get("/runs/999")
        assert resp.status_code == 404

    def test_asset_detail(self, client, app):
        _login(client)
        with app.app_context():
            asset = _create_asset()
            db.session.commit()
            asset_id = asset.id
        resp = client.get(f"/assets/{asset_id}")
        assert resp.status_code == 200
        assert b"test-vm" in resp.data

    def test_csv_export(self, client, app):
        _login(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset()
            ca = ConsolidatedAsset(
                run_id=run.id, asset_id=asset.id,
                ip_final="10.0.0.1", dns_final="test-vm",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            )
            db.session.add(ca)
            db.session.commit()
        resp = client.get("/inventory/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        assert b"test-vm" in resp.data


# ============================================================
# Tests API
# ============================================================

class TestAPI:

    def _get_token(self, client):
        resp = client.post("/api/login", json={
            "username": "admin", "password": "admin"
        })
        return resp.get_json()["access_token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_api_stats_empty(self, client, app):
        token = self._get_token(client)
        resp = client.get("/api/stats", headers=self._auth(token))
        data = resp.get_json()
        assert data["has_data"] is False

    def test_api_stats_with_data(self, client, app):
        token = self._get_token(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/api/stats", headers=self._auth(token))
        data = resp.get_json()
        assert data["has_data"] is True
        assert "match" in data
        assert "evolution" in data

    def test_api_inventory_with_data(self, client, app):
        token = self._get_token(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="web-server")
            ca = ConsolidatedAsset(
                run_id=run.id, asset_id=asset.id,
                ip_final="10.0.0.1", dns_final="web-server",
                source_ip_dns="NETBOX", match_status="MATCHED_NAME",
            )
            db.session.add(ca)
            db.session.commit()
        resp = client.get("/api/inventory?q=web", headers=self._auth(token))
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["vm_name"] == "web-server"

    def test_api_inventory_empty(self, client, app):
        token = self._get_token(client)
        resp = client.get("/api/inventory", headers=self._auth(token))
        data = resp.get_json()
        assert data["total"] == 0


# ============================================================
# Tests comparaison de runs
# ============================================================

class TestRunCompare:

    def test_compare_page_loads(self, client, app):
        _login(client)
        resp = client.get("/runs/compare")
        assert resp.status_code == 200
        assert b"Comparaison" in resp.data

    def test_compare_two_runs(self, client, app):
        _login(client)
        with app.app_context():
            run1 = _create_run()
            run2 = _create_run()
            asset1 = _create_asset(vm_id="100", vm_name="vm-common")
            asset2 = _create_asset(vm_id="101", vm_name="vm-new")

            # Run 1 : only vm-common
            db.session.add(ConsolidatedAsset(
                run_id=run1.id, asset_id=asset1.id,
                ip_final="10.0.0.1", dns_final="vm-common",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            ))
            # Run 2 : vm-common (changed IP) + vm-new
            db.session.add(ConsolidatedAsset(
                run_id=run2.id, asset_id=asset1.id,
                ip_final="10.0.0.99", dns_final="vm-common",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            ))
            db.session.add(ConsolidatedAsset(
                run_id=run2.id, asset_id=asset2.id,
                ip_final="10.0.0.2", dns_final="vm-new",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            ))
            db.session.commit()
            r1id, r2id = run1.id, run2.id

        resp = client.get(f"/runs/compare?run1={r1id}&run2={r2id}")
        assert resp.status_code == 200
        assert b"vm-new" in resp.data      # added
        assert b"10.0.0.99" in resp.data   # changed IP


# ============================================================
# Tests consolidation engine
# ============================================================

class TestConsolidation:

    def test_run_inventory(self, app):
        """Test un run complet via run_inventory()."""
        with app.app_context():
            from collector.inventory_runner import run_inventory
            run = run_inventory()
            assert run.status == "SUCCESS"
            assert run.vm_count > 0
            assert run.matched_name_count > 0

    def test_consolidation_matched(self, app):
        """Un asset avec un IPAM dns_name identique doit etre MATCHED_NAME."""
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="web01")
            ipam = _create_ipam(dns_name="web01")
            db.session.commit()

            from collector.inventory_runner import _consolidate
            matched, no_match = _consolidate(run)
            assert matched >= 1

            ca = ConsolidatedAsset.query.filter_by(
                run_id=run.id, asset_id=asset.id
            ).first()
            assert ca is not None
            assert ca.match_status == "MATCHED_NAME"
            assert ca.ipam_record_id == ipam.id

    def test_consolidation_no_match(self, app):
        """Un asset sans IPAM correspondant doit etre NO_MATCH."""
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="orphan-vm")
            db.session.commit()

            from collector.inventory_runner import _consolidate
            matched, no_match = _consolidate(run)
            assert no_match >= 1

            ca = ConsolidatedAsset.query.filter_by(
                run_id=run.id, asset_id=asset.id
            ).first()
            assert ca is not None
            assert ca.match_status == "NO_MATCH"

            anomaly = Anomaly.query.filter_by(
                run_id=run.id, asset_id=asset.id, type="NO_MATCH"
            ).first()
            assert anomaly is not None

    def test_status_mismatch_anomaly(self, app):
        """VM stopped + IP active doit generer STATUS_MISMATCH."""
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="stopped-vm", status="stopped")
            _create_ipam(dns_name="stopped-vm", status="active")
            db.session.commit()

            from collector.inventory_runner import _consolidate
            _consolidate(run)
            db.session.commit()

            anomaly = Anomaly.query.filter_by(
                run_id=run.id, asset_id=asset.id, type="STATUS_MISMATCH"
            ).first()
            assert anomaly is not None


# ============================================================
# Tests pagination
# ============================================================

class TestPagination:

    def test_inventory_pagination(self, client, app):
        _login(client)
        with app.app_context():
            run = _create_run()
            for i in range(30):
                a = _create_asset(vm_id=str(i), vm_name=f"vm-{i:03d}")
                db.session.add(ConsolidatedAsset(
                    run_id=run.id, asset_id=a.id,
                    ip_final=f"10.0.0.{i}", dns_final=a.vm_name,
                    source_ip_dns="VIRT", match_status="NO_MATCH",
                ))
            db.session.commit()

        # Page 1
        resp = client.get("/inventory?page=1")
        assert resp.status_code == 200
        assert b"page 1/2" in resp.data

        # Page 2
        resp = client.get("/inventory?page=2")
        assert resp.status_code == 200
        assert b"page 2/2" in resp.data

    def test_runs_pagination(self, client, app):
        _login(client)
        with app.app_context():
            for _ in range(30):
                _create_run()
            db.session.commit()
        resp = client.get("/runs?page=1")
        assert resp.status_code == 200
        assert b"page 1/2" in resp.data
