# CloudInventory

Application web locale d'inventaire et de supervision d'un parc virtualisé (BTS SIO).

Consolide les données de **deux plateformes** :
- **Virtualisation** (mock Phase 1 / Proxmox Phase 2) — existence, statut, node, type des VMs/CTs
- **IPAM/DNS (NetBox)** — source de vérité réseau (IP/DNS déclarés)

## Prérequis

- Python 3.x
- NetBox en Docker (netbox-docker) sur `http://localhost:8000`

## Installation

```bash
# 1. Cloner le dépôt
git clone <url> && cd CloudInventory.v2

# 2. Environnement virtuel
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows

# 3. Dépendances
pip install -r requirements.txt

# 4. Configuration
cp .env.example .env
# Éditer .env : renseigner NETBOX_TOKEN
```

## Lancer NetBox (Docker)

```bash
cd netbox/netbox-docker
docker compose up -d
# Créer un superuser
docker compose exec netbox /opt/netbox/netbox/manage.py createsuperuser
```

Puis dans l'UI NetBox (`http://localhost:8000`) :
1. Créer un token API (profil utilisateur)
2. Ajouter 3 IP de test (IPAM > IP Addresses) :
   - `10.0.0.10/24` — dns_name `web-a500`
   - `10.0.0.11/24` — dns_name `db-b500`
   - `10.0.0.12/24` — dns_name `dns-d500`

## Lancer l'application

```bash
python run.py
```

Accès : `http://localhost:5000`

## Fonctionnalités

- **Dashboard** (`/`) : dernier run, compteurs, bouton lancer inventaire
- **Inventaire** (`/inventory`) : vue consolidée avec filtres (recherche, status, node, type, match)
- **Runs** (`/runs`) : historique des 100 derniers runs
- **Détail run** (`/runs/<id>`) : inventaire + anomalies du run
- **Détail VM** (`/assets/<id>`) : infos, historique consolidations, anomalies
- **Anomalies** (`/anomalies`) : liste avec filtres par type et run

## Structure

```
├── app/
│   ├── __init__.py          # Factory Flask + SQLAlchemy
│   ├── models.py            # 5 tables : run, asset, ipam_record, consolidated_asset, anomaly
│   ├── routes.py            # Routes avec JOIN explicites
│   └── templates/           # Templates HTML (Bootstrap)
├── collector/
│   ├── netbox_client.py     # Client API NetBox (pagination)
│   ├── mock_virtualisation.py  # Mock source A (Phase 1)
│   └── inventory_runner.py  # Runner d'inventaire (consolidation + anomalies)
├── run.py                   # Point d'entrée
├── requirements.txt
├── .env.example
└── .gitignore
```
