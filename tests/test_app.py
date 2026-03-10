"""Tests unitaires CloudInventory — modeles, authentification, routes et consolidation.

Ce fichier couvre :
  - La creation et les relations entre modeles (Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly)
  - L'authentification web (login / logout / protection des pages)
  - Les routes principales du dashboard (inventaire, runs, anomalies, export CSV)
  - Le moteur de consolidation multi-strategie (hostname, FQDN, IP, no match)
  - La comparaison entre deux runs d'inventaire
  - La pagination des listes
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


# ── Helpers ───────────────────────────────────────────────────

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
# 1. MODELES — Creation et relations en base de donnees
# ============================================================

class TestModeles:
    """Verifie que les modeles SQLAlchemy se creent et se relient correctement."""

    def test_creer_un_run_et_verifier_ses_attributs(self, app):
        """Un Run cree en base doit avoir un id, un status et un compteur de VMs."""
        with app.app_context():
            run = _create_run()
            db.session.commit()
            assert run.id is not None
            assert run.status == "SUCCESS"
            assert run.vm_count == 5

    def test_creer_un_asset_avec_metriques_cpu(self, app):
        """Un Asset doit stocker le nom de la VM et les metriques CPU."""
        with app.app_context():
            asset = _create_asset()
            db.session.commit()
            assert asset.id is not None
            assert asset.vm_name == "test-vm"
            assert asset.cpu_usage == 25.0

    def test_creer_un_enregistrement_ipam(self, app):
        """Un IpamRecord doit stocker l'IP, le DNS et le tenant."""
        with app.app_context():
            ipam = _create_ipam()
            db.session.commit()
            assert ipam.id is not None
            assert ipam.tenant == "infra"

    def test_lier_un_asset_a_un_ipam_via_consolidated_asset(self, app):
        """ConsolidatedAsset doit relier un Run, un Asset et un IpamRecord."""
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

    def test_creer_une_anomalie_rattachee_a_un_run(self, app):
        """Une Anomaly doit etre rattachee a un Run et un Asset."""
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
# 2. AUTHENTIFICATION — Login, logout, protection des pages
# ============================================================

class TestAuthentification:
    """Verifie la securite d'acces aux pages de l'application."""

    def test_redirection_vers_login_si_non_connecte(self, client):
        """Un utilisateur non connecte doit etre redirige vers /login."""
        resp = client.get("/")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_connexion_reussie_avec_identifiants_valides(self, client):
        """L'admin peut se connecter et acceder au Dashboard."""
        resp = _login(client)
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data

    def test_connexion_refusee_avec_mauvais_mot_de_passe(self, client):
        """Un mot de passe incorrect affiche un message d'erreur."""
        resp = client.post("/login", data={
            "username": "admin", "password": "wrong"
        }, follow_redirects=True)
        assert b"incorrects" in resp.data

    def test_deconnexion_redirige_vers_login(self, client):
        """Apres logout, l'utilisateur revient sur la page de connexion."""
        _login(client)
        resp = client.get("/logout", follow_redirects=True)
        assert b"login" in resp.data.lower()


# ============================================================
# 3. ROUTES WEB — Dashboard, inventaire, runs, anomalies
# ============================================================

class TestRoutesWeb:
    """Verifie que les pages principales s'affichent correctement."""

    def test_dashboard_accessible_apres_connexion(self, client, app):
        """Le dashboard se charge sans erreur meme sans donnees."""
        _login(client)
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"Dashboard" in resp.data

    def test_inventaire_vide_affiche_message(self, client, app):
        """Sans run, l'inventaire affiche 'Aucun run'."""
        _login(client)
        resp = client.get("/inventory")
        assert resp.status_code == 200
        assert b"Aucun run" in resp.data

    def test_liste_runs_vide_affiche_message(self, client, app):
        """Sans run, la page runs affiche 'Aucun run'."""
        _login(client)
        resp = client.get("/runs")
        assert resp.status_code == 200
        assert b"Aucun run" in resp.data

    def test_anomalies_vide_affiche_message(self, client, app):
        """Sans anomalie, la page affiche 'Aucune anomalie'."""
        _login(client)
        resp = client.get("/anomalies")
        assert resp.status_code == 200
        assert b"Aucune anomalie" in resp.data

    def test_dashboard_affiche_donnees_du_dernier_run(self, client, app):
        """Avec un run en base, le dashboard se charge correctement."""
        _login(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/")
        assert resp.status_code == 200

    def test_inventaire_affiche_les_vms_consolidees(self, client, app):
        """Les VMs consolidees apparaissent dans le tableau d'inventaire."""
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

    def test_recherche_inventaire_par_nom_de_vm(self, client, app):
        """Le filtre ?q= filtre l'inventaire par nom de VM."""
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

    def test_filtre_inventaire_par_tag(self, client, app):
        """Le filtre ?tag= ne retourne que les VMs ayant ce tag."""
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

    def test_tri_inventaire_par_nom_descendant(self, client, app):
        """Le tri ?sort=vm_name&order=desc place 'zulu' avant 'alpha'."""
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

    def test_detail_run_affiche_les_compteurs(self, client, app):
        """La page detail d'un run s'affiche avec ses compteurs."""
        _login(client)
        with app.app_context():
            run = _create_run()
            db.session.commit()
            run_id = run.id
        resp = client.get(f"/runs/{run_id}")
        assert resp.status_code == 200

    def test_detail_run_inexistant_retourne_404(self, client, app):
        """Un run inexistant retourne une erreur 404."""
        _login(client)
        resp = client.get("/runs/999")
        assert resp.status_code == 404

    def test_detail_asset_affiche_nom_et_metriques(self, client, app):
        """La page detail d'un asset affiche son nom."""
        _login(client)
        with app.app_context():
            asset = _create_asset()
            db.session.commit()
            asset_id = asset.id
        resp = client.get(f"/assets/{asset_id}")
        assert resp.status_code == 200
        assert b"test-vm" in resp.data

    def test_export_csv_contient_les_vms(self, client, app):
        """L'export CSV contient les VMs consolidees au format text/csv."""
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
# 4. API REST — Acces JSON avec token JWT
# ============================================================

class TestAPI:
    """Verifie les endpoints de l'API REST (authentification JWT)."""

    def _get_token(self, client):
        resp = client.post("/api/login", json={
            "username": "admin", "password": "admin"
        })
        return resp.get_json()["access_token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_api_stats_sans_donnees_retourne_has_data_false(self, client, app):
        """L'API stats sans run retourne has_data: false."""
        token = self._get_token(client)
        resp = client.get("/api/stats", headers=self._auth(token))
        data = resp.get_json()
        assert data["has_data"] is False

    def test_api_stats_avec_donnees_retourne_les_compteurs(self, client, app):
        """L'API stats avec un run retourne match et evolution."""
        token = self._get_token(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/api/stats", headers=self._auth(token))
        data = resp.get_json()
        assert data["has_data"] is True
        assert "match" in data
        assert "evolution" in data

    def test_api_inventaire_avec_recherche_par_nom(self, client, app):
        """L'API inventaire filtre par ?q= et retourne les VMs correspondantes."""
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

    def test_api_inventaire_vide_retourne_zero(self, client, app):
        """L'API inventaire sans donnees retourne total: 0."""
        token = self._get_token(client)
        resp = client.get("/api/inventory", headers=self._auth(token))
        data = resp.get_json()
        assert data["total"] == 0


# ============================================================
# 5. COMPARAISON DE RUNS — Detection des ajouts et modifications
# ============================================================

class TestComparaisonRuns:
    """Verifie la comparaison entre deux runs d'inventaire."""

    def test_page_comparaison_accessible(self, client, app):
        """La page de comparaison se charge sans erreur."""
        _login(client)
        resp = client.get("/runs/compare")
        assert resp.status_code == 200
        assert b"Comparaison" in resp.data

    def test_comparaison_detecte_vm_ajoutee_et_ip_modifiee(self, client, app):
        """La comparaison detecte une VM ajoutee et un changement d'IP."""
        _login(client)
        with app.app_context():
            run1 = _create_run()
            run2 = _create_run()
            asset1 = _create_asset(vm_id="100", vm_name="vm-common")
            asset2 = _create_asset(vm_id="101", vm_name="vm-new")

            # Run 1 : seulement vm-common
            db.session.add(ConsolidatedAsset(
                run_id=run1.id, asset_id=asset1.id,
                ip_final="10.0.0.1", dns_final="vm-common",
                source_ip_dns="VIRT", match_status="NO_MATCH",
            ))
            # Run 2 : vm-common (IP changee) + vm-new (ajoutee)
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
        assert b"vm-new" in resp.data      # VM ajoutee detectee
        assert b"10.0.0.99" in resp.data   # changement d'IP detecte


# ============================================================
# 6. MOTEUR DE CONSOLIDATION — Matching multi-strategie
# ============================================================

class TestConsolidation:
    """Verifie le coeur metier : consolidation des VMs avec les enregistrements IPAM."""

    def test_run_complet_avec_donnees_mock(self, app):
        """Un run d'inventaire complet (mock) doit reussir et trouver des matchs."""
        with app.app_context():
            from collector.inventory_runner import run_inventory
            run = run_inventory()
            assert run.status == "SUCCESS"
            assert run.vm_count > 0
            assert run.matched_name_count > 0

    def test_matching_par_hostname_identique(self, app):
        """Si le hostname VM == dns_name IPAM, le match est MATCHED_NAME."""
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="web01")
            ipam = _create_ipam(dns_name="web01")
            db.session.commit()

            from collector.inventory_runner import _consolidate
            matched_name, matched_fqdn, matched_ip, no_match = _consolidate(run)
            assert matched_name >= 1

            ca = ConsolidatedAsset.query.filter_by(
                run_id=run.id, asset_id=asset.id
            ).first()
            assert ca is not None
            assert ca.match_status == "MATCHED_NAME"
            assert ca.ipam_record_id == ipam.id

    def test_vm_sans_correspondance_genere_anomalie_no_match(self, app):
        """Une VM sans correspondance IPAM doit etre NO_MATCH avec une anomalie."""
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="orphan-vm")
            db.session.commit()

            from collector.inventory_runner import _consolidate
            matched_name, matched_fqdn, matched_ip, no_match = _consolidate(run)
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

    def test_vm_stopped_avec_ip_active_genere_status_mismatch(self, app):
        """Une VM arretee avec une IP active dans NetBox genere STATUS_MISMATCH."""
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
# 7. PAGINATION — Decoupe des listes longues
# ============================================================

class TestPagination:
    """Verifie que les listes longues sont correctement paginées."""

    def test_inventaire_pagine_sur_deux_pages(self, client, app):
        """30 VMs doivent etre reparties sur 2 pages (20 par page)."""
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

        resp = client.get("/inventory?page=1")
        assert resp.status_code == 200
        assert b"page 1/2" in resp.data

        resp = client.get("/inventory?page=2")
        assert resp.status_code == 200
        assert b"page 2/2" in resp.data

    def test_runs_pagines_sur_deux_pages(self, client, app):
        """30 runs doivent etre repartis sur 2 pages."""
        _login(client)
        with app.app_context():
            for _ in range(30):
                _create_run()
            db.session.commit()
        resp = client.get("/runs?page=1")
        assert resp.status_code == 200
        assert b"page 1/2" in resp.data


# ============================================================
# 8. MATCHING FQDN et IP — Strategies 2 et 3
# ============================================================

class TestMatchingFQDNetIP:
    """Verifie les strategies de matching FQDN et IP du moteur de consolidation."""

    def test_matching_par_fqdn_quand_hostname_differe(self, app):
        """Si le FQDN de la VM correspond au dns_name IPAM, le match est MATCHED_FQDN."""
        with app.app_context():
            run = _create_run()
            # VM avec hostname different mais FQDN qui matche
            asset = Asset(
                vm_id="200", vm_name="srv-renamed-x999", type="qemu",
                node="pve1", status="running", fqdn="web01.domain.local",
            )
            db.session.add(asset)
            _create_ipam(dns_name="web01", ip="10.0.1.10")
            db.session.commit()

            from collector.inventory_runner import _consolidate
            matched_name, matched_fqdn, matched_ip, no_match = _consolidate(run)
            assert matched_fqdn >= 1

            ca = ConsolidatedAsset.query.filter_by(
                run_id=run.id, asset_id=asset.id
            ).first()
            assert ca is not None
            assert ca.match_status == "MATCHED_FQDN"

    def test_matching_par_ip_quand_hostname_et_fqdn_ne_matchent_pas(self, app):
        """Si seule l'IP correspond, le match est MATCHED_IP avec anomalie HOSTNAME_MISMATCH."""
        with app.app_context():
            run = _create_run()
            asset = Asset(
                vm_id="201", vm_name="ghost-vm", type="qemu",
                node="pve1", status="running", ip_reported="10.0.2.10",
            )
            db.session.add(asset)
            _create_ipam(dns_name="db-b500", ip="10.0.2.10")
            db.session.commit()

            from collector.inventory_runner import _consolidate
            matched_name, matched_fqdn, matched_ip, no_match = _consolidate(run)
            assert matched_ip >= 1

            ca = ConsolidatedAsset.query.filter_by(
                run_id=run.id, asset_id=asset.id
            ).first()
            assert ca is not None
            assert ca.match_status == "MATCHED_IP"

            anomaly = Anomaly.query.filter_by(
                run_id=run.id, asset_id=asset.id, type="HOSTNAME_MISMATCH"
            ).first()
            assert anomaly is not None


# ============================================================
# 9. ANOMALIES IPAM — Duplicates DNS et IP
# ============================================================

class TestAnomaliesIPAM:
    """Verifie la detection des doublons DNS et IP dans les enregistrements IPAM."""

    def test_duplicate_dns_detecte(self, app):
        """Deux IPAM records avec le meme dns_name generent une anomalie DUPLICATE_DNS."""
        with app.app_context():
            run = _create_run()
            # Asset avec le meme nom que le DNS duplique
            asset = _create_asset(vm_name="monitoring")
            # Deux IPAM records avec le meme dns_name
            _create_ipam(ip="10.0.4.10", dns_name="monitoring")
            ipam2 = IpamRecord(ip="10.0.8.50", dns_name="monitoring",
                               status="active", tenant="Supervision", site="DC2")
            db.session.add(ipam2)
            db.session.commit()

            from collector.inventory_runner import _detect_ipam_anomalies
            _detect_ipam_anomalies(run)
            db.session.commit()

            anomaly = Anomaly.query.filter_by(
                run_id=run.id, type="DUPLICATE_DNS"
            ).first()
            assert anomaly is not None
            assert "monitoring" in anomaly.details

    def test_duplicate_ip_detecte(self, app):
        """Deux IPAM records avec la meme IP generent une anomalie DUPLICATE_IP."""
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="gitea-repo", vm_id="300")
            asset.ip_reported = "10.0.4.16"
            # Deux IPAM records avec la meme IP
            _create_ipam(ip="10.0.4.16", dns_name="gitea-repo")
            ipam2 = IpamRecord(ip="10.0.4.16", dns_name="gitea-mirror",
                               status="active", tenant="DevOps", site="DC1")
            db.session.add(ipam2)
            db.session.commit()

            from collector.inventory_runner import _detect_ipam_anomalies
            _detect_ipam_anomalies(run)
            db.session.commit()

            anomaly = Anomaly.query.filter_by(
                run_id=run.id, type="DUPLICATE_IP"
            ).first()
            assert anomaly is not None
            assert "10.0.4.16" in anomaly.details


# ============================================================
# 10. DEDUCTION DE ROLE — Convention de nommage et tags
# ============================================================

class TestDeduceRole:
    """Verifie la deduction du role fonctionnel a partir du hostname et des tags."""

    def test_role_par_lettre_et_3_chiffres(self, app):
        """Le pattern lettre+3chiffres deduit le role (ex: a500 -> Application)."""
        with app.app_context():
            from collector.inventory_runner import _deduce_role
            assert _deduce_role("web-a500") == "Application"
            assert _deduce_role("db-b500") == "Base de données"
            assert _deduce_role("dns-d500") == "DNS"
            assert _deduce_role("proxy-o100") == "Proxy"
            assert _deduce_role("fw-p200") == "Pare-feu"

    def test_role_par_tag_role_xxx(self, app):
        """Le tag role:xxx deduit le role quand le pattern lettre+3chiffres est absent."""
        with app.app_context():
            from collector.inventory_runner import _deduce_role
            assert _deduce_role("my-server", "env:prod, role:web") == "Web"
            assert _deduce_role("my-server", "role:database") == "Base de données"
            assert _deduce_role("my-server", "role:monitoring") == "Supervision"

    def test_role_indetermine_sans_convention(self, app):
        """Sans pattern ni tag role:, le role est Indetermine."""
        with app.app_context():
            from collector.inventory_runner import _deduce_role
            assert _deduce_role("random-name") == "Indéterminé"
            assert _deduce_role("") == "Indéterminé"
            assert _deduce_role(None) == "Indéterminé"

    def test_lettre_prioritaire_sur_tag(self, app):
        """Le pattern lettre+3chiffres est prioritaire sur le tag role:."""
        with app.app_context():
            from collector.inventory_runner import _deduce_role
            # a500 -> Application, meme si tag dit "monitoring"
            assert _deduce_role("web-a500", "role:monitoring") == "Application"


# ============================================================
# 11. SECURITE — Open redirect et hash mot de passe
# ============================================================

class TestSecurite:
    """Verifie les mecanismes de securite de l'application."""

    def test_open_redirect_bloque(self, client):
        """Une redirection vers un site externe est bloquee apres login."""
        resp = client.post("/login?next=https://evil.com", data={
            "username": "admin", "password": "admin"
        }, follow_redirects=False)
        assert resp.status_code == 302
        # Doit rediriger vers le dashboard, pas vers evil.com
        assert "evil.com" not in resp.headers["Location"]

    def test_redirect_relative_autorise(self, client):
        """Une redirection relative (chemin interne) est autorisee."""
        resp = client.post("/login?next=/inventory", data={
            "username": "admin", "password": "admin"
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/inventory" in resp.headers["Location"]


# ============================================================
# 12. API ERREURS — Cas limites de l'API REST
# ============================================================

class TestAPIErreurs:
    """Verifie les cas d'erreur de l'API REST."""

    def _get_token(self, client):
        resp = client.post("/api/login", json={
            "username": "admin", "password": "admin"
        })
        return resp.get_json()["access_token"]

    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def test_token_invalide_retourne_422(self, client):
        """Un token JWT invalide retourne une erreur."""
        resp = client.get("/api/stats", headers={"Authorization": "Bearer invalid-token"})
        assert resp.status_code == 422

    def test_purge_runs_conserve_les_derniers(self, client, app):
        """POST /api/runs/purge supprime les anciens runs et conserve les N derniers."""
        token = self._get_token(client)
        with app.app_context():
            for _ in range(5):
                _create_run()
            db.session.commit()
        resp = client.post("/api/runs/purge",
                           json={"keep": 2},
                           headers=self._auth(token))
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["deleted"] == 3
        assert data["kept"] == 2

    def test_purge_runs_parametre_invalide(self, client):
        """POST /api/runs/purge avec keep invalide retourne 400."""
        token = self._get_token(client)
        resp = client.post("/api/runs/purge",
                           json={"keep": -1},
                           headers=self._auth(token))
        assert resp.status_code == 400


# ============================================================
# 13. ALERTES ANOMALIES — Badge navbar et bandeau dashboard
# ============================================================

class TestAlertesAnomalies:
    """Verifie l'affichage des alertes d'anomalies dans l'interface."""

    def test_badge_navbar_anomalies_visible(self, client, app):
        """Le badge rouge apparait dans la navbar quand il y a des anomalies."""
        _login(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="test-vm")
            db.session.add(Anomaly(
                run_id=run.id, asset_id=asset.id,
                type="NO_MATCH", details="Test anomalie",
            ))
            db.session.commit()
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"ci-anomaly-pulse" in resp.data

    def test_badge_navbar_absent_sans_anomalie(self, client, app):
        """Le badge rouge n'apparait pas quand il n'y a pas d'anomalies."""
        _login(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/")
        assert resp.status_code == 200
        # Le badge contient "rounded-pill bg-danger" uniquement quand il y a des anomalies
        assert b'rounded-pill bg-danger' not in resp.data

    def test_bandeau_alerte_dashboard_avec_detail_types(self, client, app):
        """Le bandeau d'alerte affiche le detail par type d'anomalie sur le dashboard."""
        _login(client)
        with app.app_context():
            run = _create_run()
            asset = _create_asset(vm_name="vm-alert")
            db.session.add(Anomaly(
                run_id=run.id, asset_id=asset.id,
                type="NO_MATCH", details="Test 1",
            ))
            db.session.add(Anomaly(
                run_id=run.id, asset_id=asset.id,
                type="STATUS_MISMATCH", details="Test 2",
            ))
            db.session.commit()
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"NO_MATCH" in resp.data
        assert b"STATUS_MISMATCH" in resp.data
        assert b"shield-exclamation" in resp.data

    def test_bandeau_alerte_absent_sans_anomalie(self, client, app):
        """Le bandeau d'alerte n'apparait pas quand il n'y a pas d'anomalies."""
        _login(client)
        with app.app_context():
            _create_run()
            db.session.commit()
        resp = client.get("/")
        assert resp.status_code == 200
        # L'icone shield-exclamation n'apparait que dans le bandeau d'alerte
        assert b"shield-exclamation" not in resp.data

    def test_notification_email_desactivee_par_defaut(self, app):
        """La notification email ne plante pas quand SMTP est desactive."""
        with app.app_context():
            from collector.inventory_runner import _notify_email
            run = _create_run()
            db.session.commit()
            # Ne doit pas lever d'exception
            _notify_email(run, 5, {"NO_MATCH": 3, "STATUS_MISMATCH": 2})
