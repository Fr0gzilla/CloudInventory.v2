"""Tests de l'API REST CloudInventory — authentification JWT, endpoints CRUD.

Ce fichier couvre :
  - L'authentification JWT (login, token, acces refuse)
  - Les endpoints statistiques (/api/stats)
  - La gestion des runs (/api/runs) : liste, detail, declenchement, comparaison
  - L'inventaire consolide (/api/inventory) : liste, recherche, export CSV
  - Le detail des assets (/api/assets)
  - Les anomalies (/api/anomalies) : liste et filtre par type
"""

import os
import pytest

os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "admin"
os.environ["USE_MOCK_IPAM"] = "true"

from app import create_app, db
from app.models import Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture
def app():
    """Cree une app Flask de test avec une base de donnees SQLite en memoire."""
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
    """Client HTTP de test."""
    return app.test_client()


# ── Helpers ───────────────────────────────────────────────────

def _get_token(client):
    """Obtient un token JWT via /api/login."""
    resp = client.post("/api/login", json={
        "username": "admin", "password": "admin"
    })
    return resp.get_json()["access_token"]


def _auth_header(token):
    """Retourne le header Authorization Bearer."""
    return {"Authorization": f"Bearer {token}"}


def _create_run(status="SUCCESS", vm_count=5, matched=3, no_match=2):
    """Cree un run de test."""
    run = Run(status=status, vm_count=vm_count, ip_count=vm_count,
              matched_name_count=matched, no_match_count=no_match)
    db.session.add(run)
    db.session.flush()
    return run


def _create_asset(vm_id="100", vm_name="test-vm", status="running",
                  node="pve1", vm_type="qemu", cpu_usage=25.0,
                  ram_max=4294967296, ram_used=2147483648):
    """Cree un asset de test."""
    asset = Asset(vm_id=vm_id, vm_name=vm_name, status=status, type=vm_type,
                  node=node, cpu_usage=cpu_usage, ram_max=ram_max,
                  ram_used=ram_used)
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
# 1. AUTHENTIFICATION JWT — Securite de l'API
# ============================================================

class TestAuthentificationJWT:
    """Verifie que l'API est protegee par des tokens JWT."""

    def test_login_api_retourne_un_token_jwt(self, client):
        """Un login valide retourne un access_token JWT."""
        resp = client.post("/api/login", json={
            "username": "admin", "password": "admin"
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert "access_token" in data

    def test_login_api_refuse_un_mauvais_mot_de_passe(self, client):
        """Un mot de passe incorrect retourne 401 Unauthorized."""
        resp = client.post("/api/login", json={
            "username": "admin", "password": "wrong"
        })
        assert resp.status_code == 401

    def test_login_api_refuse_une_requete_sans_body(self, client):
        """Une requete sans body JSON retourne 400 Bad Request."""
        resp = client.post("/api/login", content_type="application/json")
        assert resp.status_code == 400

    def test_acces_refuse_sans_token_jwt(self, client):
        """Un endpoint protege sans token retourne 401."""
        resp = client.get("/api/stats")
        assert resp.status_code == 401


# ============================================================
# 2. STATISTIQUES — Compteurs du dashboard
# ============================================================

class TestStatistiques:
    """Verifie l'endpoint /api/stats utilise par le dashboard."""

    def test_stats_sans_donnees_indique_base_vide(self, client):
        """Sans run, l'API retourne has_data: false."""
        token = _get_token(client)
        resp = client.get("/api/stats", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["has_data"] is False

    def test_stats_avec_un_run_retourne_compteurs_et_evolution(self, client, app):
        """Avec un run, l'API retourne les donnees match et evolution."""
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
# 3. RUNS — Historique des cycles d'inventaire
# ============================================================

class TestRuns:
    """Verifie les endpoints CRUD des runs d'inventaire."""

    def test_liste_runs_vide(self, client):
        """Sans run, la liste retourne un tableau vide."""
        token = _get_token(client)
        resp = client.get("/api/runs", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_liste_runs_avec_donnees(self, client, app):
        """Avec un run en base, la liste le retourne avec son status."""
        token = _get_token(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/api/runs", headers=_auth_header(token))
        data = resp.get_json()
        assert data["total"] == 1
        assert data["runs"][0]["status"] == "SUCCESS"

    def test_detail_run_par_id(self, client, app):
        """Le detail d'un run retourne ses informations completes."""
        token = _get_token(client)
        with app.app_context():
            run = _create_run()
            db.session.commit()
            run_id = run.id
        resp = client.get(f"/api/runs/{run_id}", headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == run_id

    def test_detail_run_inexistant_retourne_404(self, client):
        """Un run inexistant retourne 404 Not Found."""
        token = _get_token(client)
        resp = client.get("/api/runs/999", headers=_auth_header(token))
        assert resp.status_code == 404

    def test_declenchement_run_via_api(self, client):
        """POST /api/runs declenche un run complet et retourne SUCCESS."""
        token = _get_token(client)
        resp = client.post("/api/runs", headers=_auth_header(token))
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "SUCCESS"
        assert data["vm_count"] > 0

    def test_comparaison_deux_runs_detecte_changement_ip(self, client, app):
        """La comparaison detecte un changement d'IP entre deux runs."""
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

    def test_comparaison_sans_parametres_retourne_400(self, client):
        """La comparaison sans run1/run2 retourne 400 Bad Request."""
        token = _get_token(client)
        resp = client.get("/api/runs/compare", headers=_auth_header(token))
        assert resp.status_code == 400


# ============================================================
# 4. INVENTAIRE — Liste consolidee des VMs
# ============================================================

class TestInventaire:
    """Verifie les endpoints d'inventaire consolide."""

    def _seed(self, app):
        """Cree un jeu de donnees : 1 run + 1 VM matchee."""
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

    def test_inventaire_vide_retourne_liste_vide(self, client):
        """Sans donnees, l'inventaire retourne une liste vide."""
        token = _get_token(client)
        resp = client.get("/api/inventory", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_inventaire_retourne_les_vms_consolidees(self, client, app):
        """L'inventaire retourne les VMs avec leur statut de matching."""
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory", headers=_auth_header(token))
        data = resp.get_json()
        assert data["total"] == 1
        assert data["items"][0]["vm_name"] == "web-server"

    def test_recherche_inventaire_filtre_par_nom(self, client, app):
        """Le parametre ?q= filtre l'inventaire par nom de VM."""
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory?q=web", headers=_auth_header(token))
        assert resp.get_json()["total"] == 1

    def test_recherche_sans_resultat_retourne_zero(self, client, app):
        """Une recherche sans correspondance retourne total: 0."""
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory?q=zzz", headers=_auth_header(token))
        assert resp.get_json()["total"] == 0

    def test_export_csv_contient_les_donnees(self, client, app):
        """L'export CSV retourne un fichier text/csv avec les VMs."""
        self._seed(app)
        token = _get_token(client)
        resp = client.get("/api/inventory/export", headers=_auth_header(token))
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        assert b"web-server" in resp.data

    def test_export_csv_vide_retourne_404(self, client):
        """L'export CSV sans donnees retourne 404."""
        token = _get_token(client)
        resp = client.get("/api/inventory/export", headers=_auth_header(token))
        assert resp.status_code == 404


# ============================================================
# 5. ASSETS — Detail des machines virtuelles
# ============================================================

class TestAssets:
    """Verifie l'endpoint de detail d'un asset."""

    def test_detail_asset_retourne_nom_historique_et_anomalies(self, client, app):
        """Le detail d'un asset inclut son nom, son historique et ses anomalies."""
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

    def test_detail_asset_inexistant_retourne_404(self, client):
        """Un asset inexistant retourne 404 Not Found."""
        token = _get_token(client)
        resp = client.get("/api/assets/999", headers=_auth_header(token))
        assert resp.status_code == 404


# ============================================================
# 6. ANOMALIES — Detection des incoherences
# ============================================================

class TestAnomalies:
    """Verifie les endpoints de gestion des anomalies."""

    def test_liste_anomalies_vide(self, client):
        """Sans anomalie, la liste retourne un tableau vide."""
        token = _get_token(client)
        resp = client.get("/api/anomalies", headers=_auth_header(token))
        assert resp.status_code == 200
        assert resp.get_json()["items"] == []

    def test_liste_anomalies_avec_donnees(self, client, app):
        """Avec une anomalie NO_MATCH, l'API la retourne."""
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

    def test_filtre_anomalies_par_type(self, client, app):
        """Le filtre ?type= retourne uniquement les anomalies du type demande."""
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


# ============================================================
# 7. PURGE — Suppression des anciens runs via API
# ============================================================

class TestPurgeAPI:
    """Verifie l'endpoint de purge des anciens runs."""

    def test_purge_supprime_les_anciens_runs(self, client, app):
        """POST /api/runs/purge conserve les N derniers et supprime le reste."""
        token = _get_token(client)
        with app.app_context():
            for _ in range(5):
                _create_run()
            db.session.commit()
        resp = client.post("/api/runs/purge",
                           json={"keep": 3},
                           headers=_auth_header(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["deleted"] == 2
        assert data["kept"] == 3

    def test_purge_sans_token_retourne_401(self, client):
        """POST /api/runs/purge sans authentification retourne 401."""
        resp = client.post("/api/runs/purge", json={"keep": 5})
        assert resp.status_code == 401

    def test_purge_avec_keep_invalide_retourne_400(self, client):
        """POST /api/runs/purge avec keep=0 retourne 400."""
        token = _get_token(client)
        resp = client.post("/api/runs/purge",
                           json={"keep": 0},
                           headers=_auth_header(token))
        assert resp.status_code == 400


# ============================================================
# 8. RUN TO_DICT — Serialisation centralisee
# ============================================================

class TestRunToDict:
    """Verifie que Run.to_dict() retourne les bonnes cles."""

    def test_to_dict_contient_toutes_les_cles(self, app):
        """Run.to_dict() contient id, status, vm_count, matched_name_count, etc."""
        with app.app_context():
            run = _create_run()
            db.session.commit()
            d = run.to_dict()
            assert d["id"] == run.id
            assert d["status"] == "SUCCESS"
            assert d["vm_count"] == 5
            assert "matched_fqdn_count" in d
            assert "matched_ip_count" in d

    def test_trigger_run_api_utilise_to_dict(self, client):
        """POST /api/runs retourne les memes cles que to_dict."""
        token = _get_token(client)
        resp = client.post("/api/runs", headers=_auth_header(token))
        data = resp.get_json()
        assert "id" in data
        assert "status" in data
        assert "matched_fqdn_count" in data
