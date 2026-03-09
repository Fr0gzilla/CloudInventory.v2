# Cahier des Charges — CloudInventory v1.0

## Table des matieres

1. [Presentation du projet](#1-presentation-du-projet)
2. [Contexte et problematique](#2-contexte-et-problematique)
3. [Objectifs du projet](#3-objectifs-du-projet)
4. [Perimetre fonctionnel](#4-perimetre-fonctionnel)
5. [Architecture technique](#5-architecture-technique)
6. [Modele de donnees](#6-modele-de-donnees)
7. [Description des fonctionnalites](#7-description-des-fonctionnalites)
8. [API REST](#8-api-rest)
9. [Securite et authentification](#9-securite-et-authentification)
10. [Interface utilisateur](#10-interface-utilisateur)
11. [Infrastructure et deploiement](#11-infrastructure-et-deploiement)
12. [Jeux de donnees de test](#12-jeux-de-donnees-de-test)
13. [Tests et validation](#13-tests-et-validation)
14. [Contraintes techniques](#14-contraintes-techniques)
15. [Evolutions prevues](#15-evolutions-prevues)
16. [Livrables](#16-livrables)
17. [Glossaire](#17-glossaire)

---

## 1. Presentation du projet

### 1.1 Intitule

**CloudInventory** — Application web d'inventaire et de supervision d'infrastructure virtualisee.

### 1.2 Cadre

Projet realise dans le cadre du **BTS SIO option SLAM** (Solutions Logicielles et Applications Metiers), epreuve E5 — Production et fourniture de services informatiques.

### 1.3 Auteur

Marceau — Etudiant BTS SIO SLAM.

### 1.4 Version

v1.0 — Phase 1 (donnees simulees).

---

## 2. Contexte et problematique

### 2.1 Contexte

Dans une infrastructure virtualisee, les machines virtuelles (VM) et conteneurs (CT) sont geres via un hyperviseur (Proxmox VE), tandis que les adresses IP et les enregistrements DNS sont geres dans un outil IPAM (NetBox). Ces deux sources de verite sont independantes et peuvent diverger au fil du temps.

### 2.2 Problematique

Sans outil centralise, les administrateurs systeme font face a plusieurs difficultes :

- **Manque de visibilite** : pas de vue consolidee entre l'hyperviseur et l'IPAM.
- **Incoherences non detectees** : une VM peut etre arretee alors que son IP reste active dans NetBox, ou inversement.
- **Machines orphelines** : des VM existent dans l'hyperviseur sans aucune correspondance dans l'IPAM (aucune documentation reseau).
- **Doublons** : des enregistrements DNS ou IP dupliques passent inapercus.
- **Absence d'historique** : aucun suivi de l'evolution du parc dans le temps.

### 2.3 Solution proposee

CloudInventory automatise la collecte, la consolidation et l'analyse des donnees provenant de ces deux sources. Il genere un inventaire consolide, detecte automatiquement les anomalies et offre un suivi historique via une interface web intuitive et une API REST documentee.

---

## 3. Objectifs du projet

### 3.1 Objectifs fonctionnels

| # | Objectif | Priorite |
|---|----------|----------|
| OF1 | Collecter automatiquement les donnees de virtualisation (VM/CT) | Haute |
| OF2 | Collecter automatiquement les donnees IPAM/DNS (NetBox) | Haute |
| OF3 | Consolider les deux sources en un inventaire unique | Haute |
| OF4 | Detecter automatiquement les anomalies d'infrastructure | Haute |
| OF5 | Fournir un tableau de bord avec indicateurs cles et graphiques | Haute |
| OF6 | Permettre la consultation et le filtrage de l'inventaire | Haute |
| OF7 | Exporter l'inventaire au format CSV | Moyenne |
| OF8 | Comparer deux executions (runs) pour suivre l'evolution | Moyenne |
| OF9 | Consulter l'historique detaille de chaque asset | Moyenne |
| OF10 | Exposer une API REST documentee (Swagger/OpenAPI) | Moyenne |

### 3.2 Objectifs techniques

| # | Objectif | Priorite |
|---|----------|----------|
| OT1 | Authentification securisee (sessions web + JWT API) | Haute |
| OT2 | Base de donnees relationnelle avec ORM | Haute |
| OT3 | Architecture modulaire (Blueprints Flask) | Haute |
| OT4 | Conteneurisation Docker | Moyenne |
| OT5 | Couverture de tests automatises (40+ tests) | Moyenne |
| OT6 | Interface responsive (mobile/tablette/desktop) | Moyenne |

---

## 4. Perimetre fonctionnel

### 4.1 Dans le perimetre (Phase 1)

- Collecte de donnees a partir de **sources simulees** (mock Proxmox + mock NetBox).
- Consolidation automatique avec algorithme de correspondance par nom DNS.
- Detection de 4 types d'anomalies.
- Interface web complete avec tableau de bord, inventaire, historique, anomalies.
- API REST avec authentification JWT et documentation Swagger.
- Export CSV de l'inventaire.
- Comparaison entre deux executions.
- Deploiement Docker.

### 4.2 Hors perimetre (Phase 2 — evolutions)

- Connexion reelle a l'API Proxmox VE.
- Connexion reelle a l'API NetBox (client deja developpe).
- Planification automatique des collectes (cron/scheduler).
- Gestion multi-utilisateurs avec roles et permissions.
- Notifications par email ou webhook en cas d'anomalie critique.
- Tableaux de bord personnalisables.

---

## 5. Architecture technique

### 5.1 Stack technologique

| Composant | Technologie | Version |
|-----------|-------------|---------|
| Langage backend | Python | 3.x |
| Framework web | Flask | 3.1.0 |
| ORM | Flask-SQLAlchemy | 3.1.1 |
| Auth sessions | Flask-Login | 0.6.3 |
| Auth API (JWT) | Flask-JWT-Extended | 4.7.1 |
| Doc API | Flasgger (Swagger/OpenAPI) | 0.9.7.1 |
| Client HTTP | requests | 2.32.3 |
| Variables d'env | python-dotenv | 1.1.0 |
| Base de donnees | SQLite | integre |
| Tests | pytest | 8.3.4 |
| Framework CSS | Bootstrap | 5.3.3 |
| Icones | Bootstrap Icons | 1.11.3 |
| Graphiques | Chart.js | 4.4.7 |
| Moteur de templates | Jinja2 | integre (Flask) |
| Conteneurisation | Docker + Docker Compose | - |
| Versioning | Git / GitHub | - |

### 5.2 Architecture applicative

```
CloudInventory/
|
|-- app/                          # Application Flask
|   |-- __init__.py               # Factory + init extensions
|   |-- auth.py                   # Blueprint authentification
|   |-- models.py                 # Modeles SQLAlchemy (5 tables)
|   |-- routes.py                 # Blueprint routes web
|   |-- api.py                    # Blueprint API REST
|   |-- queries.py                # Requetes et helpers partages
|   |-- templates/                # Templates Jinja2 (9 pages)
|
|-- collector/                    # Module de collecte
|   |-- inventory_runner.py       # Orchestrateur principal
|   |-- mock_virtualisation.py    # Donnees simulees Proxmox
|   |-- mock_netbox.py            # Donnees simulees NetBox
|   |-- netbox_client.py          # Client API NetBox (reel)
|
|-- tests/                        # Tests automatises
|   |-- test_app.py               # Tests web (modeles, routes)
|   |-- test_api.py               # Tests API REST (JWT)
|
|-- run.py                        # Point d'entree
|-- requirements.txt              # Dependances Python
|-- Dockerfile                    # Image Docker
|-- docker-compose.yml            # Orchestration conteneurs
|-- .env                          # Configuration locale
```

### 5.3 Schema d'architecture

```
+-------------------+          +-------------------+
|   Source A         |          |   Source B         |
|   Proxmox VE      |          |   NetBox (IPAM)    |
|   (mock Phase 1)  |          |   (mock Phase 1)   |
+--------+----------+          +----------+---------+
         |                                |
         v                                v
+------------------------------------------------+
|            Moteur de consolidation              |
|         (collector/inventory_runner.py)         |
|                                                 |
|  1. Collecte VM/CT    2. Collecte IPAM          |
|  3. Upsert en base    4. Correspondance DNS     |
|  5. Detection anomalies  6. Finalisation run    |
+------------------------+-----------------------+
                         |
                         v
              +----------+---------+
              |     SQLite DB      |
              |  (5 tables ORM)    |
              +----------+---------+
                         |
            +------------+------------+
            |                         |
            v                         v
   +--------+--------+      +--------+--------+
   |  Interface Web   |      |    API REST      |
   |  (Flask-Login)   |      |  (JWT + Swagger) |
   |                  |      |                  |
   |  - Dashboard     |      |  POST /api/login |
   |  - Inventaire    |      |  GET  /api/stats |
   |  - Runs          |      |  GET  /api/runs  |
   |  - Anomalies     |      |  GET  /api/inv.  |
   |  - Export CSV     |      |  GET  /api/anom. |
   +------------------+      +-----------------+
```

---

## 6. Modele de donnees

### 6.1 Dictionnaire des donnees

#### Table `run` — Executions d'inventaire

| Champ | Type | Contrainte | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK, auto-increment | Identifiant unique du run |
| started_at | DATETIME | NOT NULL, default=now | Date/heure de debut |
| ended_at | DATETIME | nullable | Date/heure de fin |
| status | VARCHAR(20) | NOT NULL | Statut : RUNNING, SUCCESS, FAIL |
| error_message | TEXT | nullable | Message d'erreur en cas d'echec |
| vm_count | INTEGER | default=0 | Nombre de VM collectees |
| ip_count | INTEGER | default=0 | Nombre d'enregistrements IPAM collectes |
| matched_name_count | INTEGER | default=0 | Correspondances par nom DNS |
| matched_ip_count | INTEGER | default=0 | Correspondances par IP |
| no_match_count | INTEGER | default=0 | VM sans correspondance |

#### Table `asset` — Machines virtuelles et conteneurs

| Champ | Type | Contrainte | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK, auto-increment | Identifiant interne |
| vm_id | VARCHAR(50) | UNIQUE, NOT NULL | Identifiant source (Proxmox VMID) |
| vm_name | VARCHAR(255) | NOT NULL | Nom de la VM/CT |
| type | VARCHAR(20) | | Type : qemu (VM) ou lxc (conteneur) |
| node | VARCHAR(100) | | Noeud hyperviseur hebergeant l'asset |
| status | VARCHAR(50) | | Statut : running, stopped |
| tags | TEXT | nullable | Tags au format CSV (ex: "env:prod,role:web") |
| ip_reported | VARCHAR(45) | nullable | Adresse IP rapportee par l'hyperviseur |
| cpu_count | INTEGER | nullable | Nombre de vCPU alloues |
| cpu_usage | FLOAT | nullable | Utilisation CPU en pourcentage |
| ram_max | BIGINT | nullable | RAM allouee en octets |
| ram_used | BIGINT | nullable | RAM utilisee en octets |
| disk_max | BIGINT | nullable | Espace disque alloue en octets |
| disk_used | BIGINT | nullable | Espace disque utilise en octets |
| uptime | INTEGER | nullable | Duree de fonctionnement en secondes |

#### Table `ipam_record` — Enregistrements IPAM/DNS

| Champ | Type | Contrainte | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK, auto-increment | Identifiant interne |
| ip | VARCHAR(45) | UNIQUE, NOT NULL | Adresse IP |
| dns_name | VARCHAR(255) | nullable | Nom DNS associe |
| status | VARCHAR(50) | nullable | Statut : active, reserved, deprecated |
| tenant | VARCHAR(100) | nullable | Organisation/tenant proprietaire |
| site | VARCHAR(100) | nullable | Site physique (datacenter) |

#### Table `consolidated_asset` — Inventaire consolide

| Champ | Type | Contrainte | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK, auto-increment | Identifiant interne |
| run_id | INTEGER | FK → run.id, NOT NULL | Run de reference |
| asset_id | INTEGER | FK → asset.id, NOT NULL | Asset associe |
| ipam_record_id | INTEGER | FK → ipam_record.id, nullable | Enregistrement IPAM associe (si match) |
| ip_final | VARCHAR(45) | nullable | IP consolidee finale |
| dns_final | VARCHAR(255) | nullable | DNS consolide final |
| source_ip_dns | VARCHAR(20) | | Source des donnees IP/DNS : NETBOX ou VIRT |
| match_status | VARCHAR(30) | | Resultat : MATCHED_NAME, MATCHED_IP, NO_MATCH |
| role | VARCHAR(100) | default="Indetermine" | Role fonctionnel de l'asset |

#### Table `anomaly` — Anomalies detectees

| Champ | Type | Contrainte | Description |
|-------|------|------------|-------------|
| id | INTEGER | PK, auto-increment | Identifiant interne |
| run_id | INTEGER | FK → run.id, NOT NULL | Run ayant detecte l'anomalie |
| asset_id | INTEGER | FK → asset.id, NOT NULL | Asset concerne |
| type | VARCHAR(50) | NOT NULL | Type d'anomalie (voir 6.2) |
| details | TEXT | nullable | Description detaillee |
| created_at | DATETIME | default=now | Date de detection |

### 6.2 Types d'anomalies detectees

| Code | Description | Condition de declenchement |
|------|-------------|---------------------------|
| NO_MATCH | VM sans correspondance IPAM | Aucun enregistrement DNS ne correspond au nom de la VM |
| STATUS_MISMATCH | Incoherence de statut | VM arretee (stopped) mais IP active dans NetBox |
| DUPLICATE_DNS | Doublon DNS | Meme nom DNS present dans plusieurs enregistrements IPAM |
| DUPLICATE_IP | Doublon IP | Meme adresse IP presente dans plusieurs enregistrements IPAM |

### 6.3 Relations entre entites

```
Run (1) ----< (N) ConsolidatedAsset (N) >---- (1) Asset
                        |
                        | (N..0)
                        v
                   IpamRecord (1)

Run (1) ----< (N) Anomaly (N) >---- (1) Asset
```

- Un **Run** produit plusieurs **ConsolidatedAsset** et plusieurs **Anomaly**.
- Un **Asset** peut apparaitre dans plusieurs runs (historique).
- Un **ConsolidatedAsset** est lie a exactement un **Asset** et optionnellement a un **IpamRecord**.
- Une **Anomaly** est liee a un **Run** et a un **Asset**.

---

## 7. Description des fonctionnalites

### 7.1 Tableau de bord (Dashboard)

**Route** : `GET /`

**Description** : Page d'accueil affichant une vue synthetique de l'etat de l'infrastructure.

**Elements affiches** :
- 4 cartes statistiques : nombre total de VM, correspondances, non-correspondances, anomalies.
- 3 graphiques interactifs (Chart.js) :
  - **Doughnut** : repartition correspondances / non-correspondances.
  - **Barres** : anomalies par type (NO_MATCH, STATUS_MISMATCH, etc.).
  - **Ligne** : evolution sur les 10 derniers runs (VM, matched, no_match).
- Bouton "Lancer l'inventaire" (appel AJAX asynchrone).
- Informations du dernier run (date, statut, compteurs).

**Donnees chargees en AJAX** : `GET /ajax/stats` retourne les statistiques au format JSON.

---

### 7.2 Execution d'un inventaire (Run)

**Routes** :
- `POST /run` — declenchement classique avec redirection.
- `POST /ajax/run` — declenchement AJAX avec reponse JSON.

**Pipeline d'execution (6 etapes)** :

1. **Initialisation** : creation d'un enregistrement `Run` avec status=RUNNING.
2. **Collecte virtualisation** : appel a `fetch_mock_vms()` → liste de VM/CT avec metriques.
3. **Collecte IPAM** : appel a `fetch_mock_ipam()` → liste d'enregistrements IP/DNS.
4. **Upsert en base** : insertion ou mise a jour des `Asset` (par vm_id) et `IpamRecord` (par ip).
5. **Consolidation** :
   - Construction d'un index DNS (insensible a la casse).
   - Pour chaque asset : recherche de correspondance par nom DNS.
   - Si match : `match_status=MATCHED_NAME`, `source=NETBOX`, verification de coherence de statut.
   - Si pas de match : `match_status=NO_MATCH`, `source=VIRT`, creation d'anomalie NO_MATCH.
6. **Detection d'anomalies IPAM** : recherche de doublons DNS et IP dans les enregistrements IPAM.
7. **Finalisation** : mise a jour du run avec status=SUCCESS, compteurs et horodatage.

**Gestion d'erreur** : en cas d'exception, rollback de la transaction, status=FAIL avec message d'erreur.

---

### 7.3 Inventaire consolide

**Route** : `GET /inventory`

**Description** : Liste paginee de l'inventaire consolide du dernier run.

**Fonctionnalites** :
- **Pagination** : 25 elements par page.
- **Recherche textuelle** : filtre sur nom VM, IP ou DNS (parametre `q`).
- **Filtres avances** :
  - Statut VM (running/stopped)
  - Noeud hyperviseur (pve1 a pve5)
  - Type (qemu/lxc)
  - Statut de correspondance (MATCHED_NAME/NO_MATCH)
  - Tags (filtre par categorie:valeur)
- **Tri** : par nom VM, statut, IP, CPU, RAM, correspondance (ASC/DESC).
- **Recherche live AJAX** : `GET /ajax/inventory/search` met a jour le tableau en temps reel.
- **Export CSV** : `GET /inventory/export` telecharge un fichier CSV (separateur `;`).

**Colonnes du tableau** :
VM, Noeud, Statut, Type, IP, DNS, CPU (%), RAM (%), Disque (%), Uptime, Match, Source.

---

### 7.4 Historique des runs

**Route** : `GET /runs`

**Description** : Liste paginee de toutes les executions d'inventaire.

**Informations par run** :
- ID, date de debut, duree, statut (badge couleur).
- Compteurs : VM collectees, correspondances, non-correspondances.
- Lien vers le detail du run.

---

### 7.5 Detail d'un run

**Route** : `GET /runs/<run_id>`

**Description** : Vue detaillee d'une execution specifique.

**Contenu** :
- Statistiques du run (compteurs, duree, statut).
- Tableau de l'inventaire consolide pour ce run.
- Tableau des anomalies detectees lors de ce run.

---

### 7.6 Comparaison de runs

**Route** : `GET /runs/compare?run1=X&run2=Y`

**Description** : Comparaison cote a cote de deux executions pour identifier les changements.

**Resultats** :
- **Ajouts** (vert) : VM presentes dans le run 2 mais absentes du run 1.
- **Suppressions** (rouge) : VM presentes dans le run 1 mais absentes du run 2.
- **Modifications** (orange) : VM presentes dans les deux runs mais avec des differences sur l'IP, le DNS, le statut de correspondance ou le statut VM.

---

### 7.7 Detail d'un asset

**Route** : `GET /assets/<asset_id>`

**Description** : Fiche detaillee d'une machine virtuelle ou d'un conteneur.

**Contenu** :
- Informations de l'asset : nom, type, noeud, statut, tags, IP.
- Metriques : CPU, RAM (utilise/total + pourcentage), disque (utilise/total + pourcentage), uptime.
- Historique sur les 30 derniers runs : evolution de l'IP, du DNS, du statut de correspondance.
- Liste des anomalies associees a cet asset.

---

### 7.8 Anomalies

**Route** : `GET /anomalies`

**Description** : Liste paginee de toutes les anomalies detectees.

**Fonctionnalites** :
- **Filtres** : par type d'anomalie, par ID de run.
- **Pagination** : 25 elements par page.
- **Informations** : run associe, date, VM concernee, type, details.

---

## 8. API REST

### 8.1 Generalites

- **Prefixe** : `/api/`
- **Format** : JSON (entree et sortie).
- **Documentation** : Swagger UI accessible sur `/apidocs`.
- **Authentification** : JWT (Bearer token).

### 8.2 Authentification

| Methode | Endpoint | Description |
|---------|----------|-------------|
| POST | `/api/login` | Obtenir un token JWT |

**Corps de la requete** :
```json
{
  "username": "admin",
  "password": "admin"
}
```

**Reponse** :
```json
{
  "access_token": "eyJhbGciOiJIUzI1..."
}
```

**Utilisation** : header `Authorization: Bearer <token>` sur toutes les routes protegees.

### 8.3 Endpoints

| Methode | Endpoint | Description | Parametres |
|---------|----------|-------------|------------|
| GET | `/api/stats` | Statistiques du dashboard | - |
| GET | `/api/runs` | Liste des runs (pagine) | page, per_page |
| POST | `/api/runs` | Lancer un nouveau run | - |
| GET | `/api/runs/<id>` | Detail d'un run | - |
| GET | `/api/runs/compare` | Comparer deux runs | run1, run2 (requis) |
| GET | `/api/inventory` | Inventaire consolide (pagine) | q, status, node, type, match, tag, sort, order, page, per_page |
| GET | `/api/inventory/export` | Export CSV | - |
| GET | `/api/assets/<id>` | Detail d'un asset | - |
| GET | `/api/anomalies` | Liste des anomalies (pagine) | type, run, page, per_page |

### 8.4 Codes de retour

| Code | Signification |
|------|---------------|
| 200 | Succes |
| 201 | Ressource creee (POST /api/runs) |
| 400 | Requete invalide (parametres manquants) |
| 401 | Non authentifie (token manquant ou invalide) |
| 404 | Ressource introuvable |

---

## 9. Securite et authentification

### 9.1 Authentification web (Flask-Login)

- **Methode** : authentification par formulaire (username + mot de passe).
- **Stockage** : cookie de session signe avec `SECRET_KEY`.
- **Compte** : utilisateur unique defini par variables d'environnement (`ADMIN_USERNAME`, `ADMIN_PASSWORD`).
- **Protection** : toutes les routes web sont protegees par le decorateur `@login_required`.
- **Redirection** : un utilisateur non connecte est automatiquement redirige vers `/login`.

### 9.2 Authentification API (JWT)

- **Methode** : JSON Web Token via `Flask-JWT-Extended`.
- **Obtention** : `POST /api/login` avec identifiants JSON.
- **Transmission** : header HTTP `Authorization: Bearer <token>`.
- **Protection** : toutes les routes API sont protegees par le decorateur `@jwt_required()`.
- **Cle de signature** : `JWT_SECRET_KEY` (variable d'environnement).

### 9.3 Variables sensibles

Toutes les donnees sensibles sont stockees dans le fichier `.env` (non versionne) :

| Variable | Description | Valeur par defaut |
|----------|-------------|-------------------|
| SECRET_KEY | Cle de signature des sessions Flask | change-me |
| JWT_SECRET_KEY | Cle de signature des tokens JWT | = SECRET_KEY |
| ADMIN_USERNAME | Nom d'utilisateur administrateur | admin |
| ADMIN_PASSWORD | Mot de passe administrateur | admin |
| DATABASE_URL | URI de connexion a la base de donnees | sqlite:///cloudinventory.db |
| NETBOX_URL | URL de l'instance NetBox | - |
| NETBOX_TOKEN | Token d'API NetBox | - |
| USE_MOCK_IPAM | Utiliser les donnees simulees | true |

---

## 10. Interface utilisateur

### 10.1 Charte graphique

- **Framework CSS** : Bootstrap 5.3.3 (responsive, mobile-first).
- **Police** : Inter (Google Fonts).
- **Couleur principale** : `#2563eb` (bleu).
- **Barre de navigation** : degrade lineaire `#0f172a → #1e293b`.
- **Theme** : clair/sombre avec bascule (persistance via localStorage).

### 10.2 Pages de l'application

| Page | Route | Description |
|------|-------|-------------|
| Connexion | `/login` | Formulaire d'authentification |
| Tableau de bord | `/` | Vue synthetique avec graphiques |
| Inventaire | `/inventory` | Liste filtrable et paginee |
| Historique des runs | `/runs` | Liste des executions |
| Detail d'un run | `/runs/<id>` | Inventaire + anomalies du run |
| Comparaison de runs | `/runs/compare` | Diff entre deux runs |
| Detail d'un asset | `/assets/<id>` | Fiche VM avec historique |
| Anomalies | `/anomalies` | Liste filtrable des anomalies |
| Documentation API | `/apidocs` | Swagger UI interactive |

### 10.3 Responsivite

L'interface est concue pour s'adapter a 3 formats :
- **Mobile** (< 768px) : colonnes masquees, navigation simplifiee.
- **Tablette** (768px — 1024px) : affichage intermediaire.
- **Desktop** (> 1024px) : affichage complet avec toutes les colonnes.

### 10.4 Elements visuels

- **Badges de statut** : SUCCESS (vert), FAIL (rouge), RUNNING (jaune).
- **Badges de correspondance** : MATCHED_NAME (bleu), NO_MATCH (rouge).
- **Graphiques interactifs** : Chart.js (doughnut, barres, lignes).
- **Effets** : ombres sur les cartes, survol interactif.

---

## 11. Infrastructure et deploiement

### 11.1 Deploiement local (developpement)

```bash
# 1. Cloner le depot
git clone <url> && cd CloudInventory.v2-1

# 2. Creer l'environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Installer les dependances
pip install -r requirements.txt

# 4. Configurer l'environnement
cp .env.example .env

# 5. Lancer l'application
python run.py
# → http://127.0.0.1:5050
```

### 11.2 Deploiement Docker

```bash
# Construction et lancement
docker-compose up --build

# → http://localhost:5050
```

**docker-compose.yml** :
- Service `web` : build depuis le Dockerfile.
- Port : 5050.
- Volume : persistance de la base SQLite.
- Variables d'environnement : configurees dans le fichier compose.
- Politique de redemarrage : `unless-stopped`.

**Dockerfile** :
- Image de base : `python:3.12-slim`.
- Installation des dependances via `requirements.txt`.
- Exposition du port 5050.

---

## 12. Jeux de donnees de test

### 12.1 Donnees de virtualisation (mock)

40 VM/CT reparties sur 5 noeuds hyperviseurs :

| Noeud | Nombre | Role | Exemples |
|-------|--------|------|----------|
| pve1 | 8 | Production Web/App | web-a500, app-backend, proxy-nginx, haproxy-lb |
| pve2 | 8 | Production Data/Stockage | db-b500, db-replica, nfs-storage, log-elastic |
| pve3 | 8 | Infrastructure/Reseau | dns-d500, ldap-auth, vpn-gateway, firewall-pf |
| pve4 | 8 | Supervision/DevOps | monitoring, grafana-dash, prometheus-ts, vault-secrets |
| pve5 | 8 | Dev/Test/Staging | dev-frontend, ci-runner, staging-web, sandbox-test |

**+ 5 VM "orphelines"** (sans correspondance IPAM volontaire) :
`unknown-x999`, `temp-migration`, `old-legacy`, `ghost-vm`, `decom-windows`.

### 12.2 Donnees IPAM (mock NetBox)

- 40 enregistrements correspondant aux VM nommees.
- 2 enregistrements orphelins (sans VM) : `decom-server`, `old-printer`.
- Tenants : Production, Infra, Dev, Staging, Supervision, DevOps.
- Site : DC1.

### 12.3 Anomalies attendues

Avec ces donnees, chaque run detecte :
- **5 anomalies NO_MATCH** : les 5 VM orphelines.
- **Anomalies STATUS_MISMATCH** : VM arretees avec IP active.
- **Anomalies DUPLICATE_DNS/IP** : si presentes dans les donnees IPAM.

---

## 13. Tests et validation

### 13.1 Framework de test

- **pytest 8.3.4** avec base SQLite en memoire.
- **2 fichiers de tests** : `test_app.py` (web) et `test_api.py` (API).
- **40+ tests automatises**.

### 13.2 Couverture des tests

| Module | Tests | Couverture |
|--------|-------|------------|
| Modeles (Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly) | 8 | Creation, relations, valeurs par defaut |
| Authentification web | 6 | Login OK/KO, acces protege, redirection, logout |
| Routes web (dashboard, runs, inventaire, assets, anomalies) | 10 | Affichage, pagination, filtres, export CSV |
| Consolidation (inventory_runner) | 6 | Pipeline complet, correspondances, anomalies |
| API REST (auth JWT) | 4 | Login, token, acces protege |
| API REST (endpoints) | 20 | Stats, runs, inventaire, assets, anomalies, comparaison |

### 13.3 Execution des tests

```bash
pytest -v
```

---

## 14. Contraintes techniques

### 14.1 Contraintes de performance

- Pagination a 25 elements pour limiter la charge (configurable via `PER_PAGE`).
- Recherche AJAX limitee a 100 resultats.
- Historique d'asset limite aux 30 derniers runs.

### 14.2 Contraintes de securite

- Mot de passe administrateur configurable (non code en dur).
- Cles secretes via variables d'environnement.
- Fichier `.env` exclu du versioning (`.gitignore`).
- Authentification obligatoire sur toutes les routes.

### 14.3 Contraintes de compatibilite

- Python 3.10+ requis.
- Navigateurs supportes : Chrome, Firefox, Edge, Safari (versions recentes).
- Compatible Windows, Linux, macOS (developpement et deploiement).

---

## 15. Evolutions prevues

### Phase 2 — Connexion aux sources reelles

| Evolution | Description | Complexite |
|-----------|-------------|------------|
| API Proxmox VE | Connexion reelle a l'hyperviseur pour collecter les VM/CT | Moyenne |
| API NetBox | Utilisation du client NetBox deja developpe (`netbox_client.py`) | Faible |
| Planification | Execution automatique des inventaires (cron ou APScheduler) | Faible |
| Multi-utilisateurs | Gestion de comptes avec roles (admin, lecteur) | Moyenne |
| Notifications | Alertes email/webhook en cas d'anomalie critique | Moyenne |
| Metriques avancees | Graphiques d'evolution CPU/RAM/disque par asset | Moyenne |
| HTTPS | Certificat SSL pour le deploiement en production | Faible |
| Backup automatique | Sauvegarde planifiee de la base SQLite | Faible |

---

## 16. Livrables

| Livrable | Format | Description |
|----------|--------|-------------|
| Code source | Git (GitHub) | Application complete avec historique de commits |
| Documentation technique | Markdown | Cahier des charges, diagrammes UML, fiche E5 |
| Diagrammes UML | Mermaid (Markdown) | MCD, MLD, diagrammes de sequence (8 diagrammes) |
| Tests automatises | Python (pytest) | 40+ tests couvrant modeles, routes, API, consolidation |
| Conteneur Docker | Dockerfile + docker-compose | Deploiement conteneurise pret a l'emploi |
| Documentation API | Swagger/OpenAPI | Documentation interactive accessible sur `/apidocs` |

---

## 17. Glossaire

| Terme | Definition |
|-------|-----------|
| **VM** | Machine Virtuelle — systeme d'exploitation virtualise complet (type qemu dans Proxmox) |
| **CT** | Conteneur — environnement isole leger (type lxc dans Proxmox) |
| **Proxmox VE** | Plateforme de virtualisation open source basee sur KVM et LXC |
| **NetBox** | Outil open source de gestion d'infrastructure reseau (IPAM, DCIM) |
| **IPAM** | IP Address Management — gestion centralisee des adresses IP |
| **DNS** | Domain Name System — systeme de resolution de noms de domaine |
| **Run** | Execution complete du pipeline de collecte et consolidation |
| **Asset** | Machine virtuelle ou conteneur gere dans l'infrastructure |
| **Consolidation** | Processus de rapprochement entre les donnees de virtualisation et l'IPAM |
| **Anomalie** | Incoherence detectee entre les deux sources de donnees |
| **JWT** | JSON Web Token — standard d'authentification pour les API REST |
| **ORM** | Object-Relational Mapping — correspondance objet-relationnel (SQLAlchemy) |
| **Blueprint** | Module Flask permettant de decouper l'application en composants |
| **Swagger** | Specification OpenAPI pour documenter et tester les API REST |
| **Mock** | Donnees simulees remplacant une source reelle pour le developpement/test |
