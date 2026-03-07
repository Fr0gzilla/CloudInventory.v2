# BTS SERVICES INFORMATIQUES AUX ORGANISATIONS — SESSION 2025
## Epreuve E5 - Conception et developpement d'applications (option SLAM)
### ANNEXE 7-1-B : Fiche descriptive de realisation professionnelle (recto)

---

## DESCRIPTION D'UNE REALISATION PROFESSIONNELLE

| | |
|---|---|
| **Nom, prenom :** | *(a completer)* |
| **N. candidat :** | *(a completer)* |
| **N. realisation :** | *(a completer)* |
| **Epreuve ponctuelle** | ☐ |
| **Controle en cours de formation** | ☐ |
| **Date :** | ...... / ...... / ............ |

**Organisation support de la realisation professionnelle**

*(a completer)*

**Intitule de la realisation professionnelle**

**CloudInventory -- Application web d'inventaire et de supervision d'un parc virtualise**

**Periode de realisation :** *(a completer)*
**Lieu :** *(a completer)*

**Modalite :** ☐ Seul(e) ☐ En equipe

### Competences travaillees

- ☑ Concevoir et developper une solution applicative
- ☑ Assurer la maintenance corrective ou evolutive d'une solution applicative
- ☑ Gerer les donnees

### Conditions de realisation (ressources fournies, resultats attendus)

Dans un contexte ou les organisations gerent des infrastructures virtualisees de plus en plus complexes, la supervision et l'inventaire des machines virtuelles constituent un enjeu operationnel majeur. Les equipes d'infrastructure doivent s'assurer de la coherence entre les ressources declarees dans les systemes de virtualisation (Proxmox VE) et les enregistrements reseau declares dans les outils d'IPAM/DNS (NetBox). Pourtant, cette verification repose encore frequemment sur des audits manuels, fastidieux et sujets a erreur, ne permettant pas un suivi continu et fiable de l'etat du parc.

Le projet CloudInventory s'inscrit dans ce contexte et vise a proposer une solution centralisee, automatisee et pedagogique pour l'inventaire et la supervision d'un parc virtualise. La realisation a ete effectuee dans un cadre pedagogique (BTS SIO), a partir d'un cahier des charges fonctionnel definissant les objectifs, le perimetre et les fonctionnalites attendues de la solution. Les ressources fournies comprenaient les besoins fonctionnels, les contraintes techniques ainsi que les attentes en matiere de securite, d'ergonomie et d'evolutivite.

La solution developpee prend la forme d'une application web locale d'inventaire qui consolide les donnees de deux sources independantes :
- **Source A -- Virtualisation** (mock en Phase 1, Proxmox VE en Phase 2) : fournit l'existence, le statut, le noeud, le type (VM/CT), les metriques de performance (CPU, RAM, disque, uptime) et les tags des machines virtuelles et conteneurs.
- **Source B -- IPAM/DNS (NetBox)** : source de verite reseau fournissant les adresses IP, les noms DNS declares, le statut des IP, le tenant et le site.

L'application permet de lancer des cycles d'inventaire (runs) qui collectent les donnees des deux sources, les consolident par correspondance de nom DNS, et detectent automatiquement les anomalies d'infrastructure : machines non documentees dans l'IPAM (NO_MATCH), incoherences de statut entre la virtualisation et le reseau (STATUS_MISMATCH), doublons DNS (DUPLICATE_DNS) et conflits d'adresses IP (DUPLICATE_IP).

Les utilisateurs peuvent consulter un tableau de bord synthetique avec des graphiques (Chart.js), parcourir l'inventaire consolide avec des filtres avances (recherche, statut, noeud, type, tags, correspondance), exporter les donnees en CSV, comparer deux runs cote a cote pour identifier les changements, et suivre l'historique des anomalies.

Le resultat attendu est une application web fonctionnelle et operationnelle, permettant de centraliser la supervision d'un parc virtualise au sein d'une plateforme unique. La solution doit faciliter la detection des ecarts entre les sources de donnees, assurer le suivi de l'evolution du parc dans le temps et proposer des mecanismes de visualisation favorisant la prise de decision.

L'application doit egalement s'appuyer sur une architecture securisee, evolutive et maintenable, integrant des bonnes pratiques de developpement web. Elle doit etre deployable localement dans un environnement reproductible et permettre une evolution future des fonctionnalites (integration Proxmox reel, alerting, RBAC) sans remise en cause de l'architecture existante.

---

## PAGE 2 — Description des ressources documentaires, materielles et logicielles utilisees

### Ressources documentaires

La realisation du projet CloudInventory s'est appuyee sur plusieurs ressources documentaires afin de cadrer, structurer et securiser le developpement de la plateforme. Un cahier des charges fonctionnel a ete utilise pour definir les objectifs du projet, le perimetre de realisation ainsi que les fonctionnalites attendues. Des cas d'utilisation ont permis de modeliser les interactions entre les differents acteurs du systeme (administrateur d'infrastructure) et d'identifier les besoins fonctionnels associes.

Un dossier technique a egalement ete redige afin de formaliser l'architecture de l'application, le modele de donnees et les choix techniques retenus. Les documentations officielles des technologies employees ont ete consultees tout au long du projet afin de garantir une mise en oeuvre conforme aux bonnes pratiques de developpement et de securite. Ces ressources ont notamment concerne le framework Flask, le langage Python, l'ORM SQLAlchemy, la base de donnees SQLite, le framework CSS Bootstrap 5, la bibliotheque Chart.js, ainsi que l'API REST de NetBox pour l'integration IPAM/DNS.

Enfin, des ressources liees aux bonnes pratiques en administration systeme et reseau ont ete etudiees afin d'integrer des mecanismes de detection d'anomalies pertinents, notamment pour la reconciliation des donnees entre virtualisation et IPAM, la detection de doublons DNS/IP et les incoherences de statut.

### Ressources materielles

Le developpement de l'application a ete realise a l'aide d'ordinateurs personnels, permettant la mise en place d'un environnement de travail complet et autonome. Ces equipements ont servi a la conception, au developpement, aux tests fonctionnels ainsi qu'a la validation de la plateforme dans des conditions proches d'un contexte professionnel.

L'utilisation d'un environnement virtuel Python (venv) et d'une base de donnees SQLite embarquee a permis de limiter la dependance au materiel et de garantir un environnement de developpement reproductible, independamment de la configuration des postes utilises. Pour les tests d'integration avec NetBox, une instance NetBox en Docker (netbox-docker) a ete deployee localement.

### Ressources logicielles

Sur le plan logiciel, le developpement de la plateforme CloudInventory repose sur une architecture web basee sur des technologies open source. La partie backend de l'application a ete developpee en langage Python a l'aide du framework Flask 3.1.0, assurant la gestion de la logique metier, de l'authentification des utilisateurs, du traitement des cycles d'inventaire, de la consolidation des donnees et de la detection des anomalies.

La persistance des donnees est assuree par une base de donnees relationnelle SQLite, utilisee via l'ORM Flask-SQLAlchemy 3.1.1 pour le stockage des informations relatives aux runs d'inventaire, aux assets (VM/CT), aux enregistrements IPAM, aux consolidations et aux anomalies. Le schema comporte cinq tables interconnectees.

La couche de presentation repose sur l'utilisation de templates Flask (Jinja2) et du framework CSS Bootstrap 5.3.3, permettant de proposer une interface ergonomique, responsive et accessible, avec un systeme de theme clair/sombre. Les graphiques de visualisation sont generes a l'aide de Chart.js 4.4.7.

L'authentification est geree par Flask-Login 0.6.3, avec un systeme de session securisee. Les appels a l'API NetBox sont effectues via la bibliotheque Python requests 2.32.3, avec gestion de la pagination.

La gestion de versions du projet est assuree par Git, avec un depot heberge sur la plateforme GitHub. La suite de tests repose sur pytest 8.3.4, avec plus de 40 cas de tests couvrant les modeles, les routes, la consolidation et les API.

Enfin, la configuration de l'application est externalisee via python-dotenv 1.1.0, permettant de gerer les variables d'environnement (identifiants, URLs, tokens) de maniere securisee.

---

## PAGE 3 — Modalites d'acces aux productions et a leur documentation

Les productions realisees dans le cadre de ce projet sont accessibles via un depot GitHub public intitule *CloudInventory*. Ce depot contient l'integralite du code source de l'application ainsi que les fichiers necessaires a son installation et a son execution en environnement local.

La documentation est centralisee dans un README detaille, present a la racine du depot. Celui-ci decrit le contexte et les objectifs de la plateforme, les prerequis (Python 3.x, NetBox en Docker), ainsi qu'une procedure d'installation complete incluant la creation de l'environnement virtuel, l'installation des dependances, la configuration des variables d'environnement et le lancement de l'application.

Le README fournit egalement la description des fonctionnalites disponibles (Dashboard, Inventaire, Runs, Detail run, Detail VM, Anomalies) ainsi que la structure du projet.

Des documents complementaires au format PDF viennent completer la documentation afin de detailler la conception, l'architecture et les schemas explicatifs de la realisation professionnelle. L'ensemble de ces elements permet au jury d'acceder facilement aux productions et a leur documentation dans le cadre de l'evaluation.

---

## PAGE 4 — Descriptif de la realisation professionnelle (verso, eventuellement pages suivantes)

### Descriptif de la realisation professionnelle, y compris les productions realisees et schemas explicatifs

La realisation professionnelle presentee consiste en le developpement d'une application web d'inventaire et de supervision d'un parc virtualise, nommee **CloudInventory**. Ce projet repond a un besoin croissant de visibilite et de controle sur les infrastructures virtualisees, dans un contexte ou la multiplication des machines virtuelles et conteneurs rend les audits manuels inefficaces et ou les ecarts entre les systemes de virtualisation et les referentiels reseau (IPAM/DNS) constituent une source majeure d'incidents.

La plateforme a pour objectif de proposer un outil centralise et automatise, permettant de collecter, consolider et analyser les donnees provenant de deux sources distinctes : l'hyperviseur (Proxmox VE, simule en Phase 1) et le systeme IPAM/DNS (NetBox). L'application permet aux administrateurs d'infrastructure de lancer des cycles d'inventaire, de visualiser l'etat du parc, de detecter les anomalies et de suivre l'evolution dans le temps.

La solution repose sur une **architecture 3-tiers**, assurant une separation claire entre les differentes couches du systeme. La couche presentation est implementee a l'aide de templates Flask (Jinja2) et stylisee avec Bootstrap 5.3.3, afin de proposer une interface claire, ergonomique et responsive, avec un systeme de theme clair/sombre et des graphiques interactifs (Chart.js). La couche applicative est developpee en Python avec le framework Flask 3.1.0, qui gere la logique metier, l'authentification, le lancement des cycles d'inventaire, la consolidation multi-sources et la detection d'anomalies. La couche de persistance repose sur une base de donnees relationnelle SQLite, assurant le stockage et la coherence des donnees.

La conception des donnees a ete realisee en plusieurs etapes. Un Modele Conceptuel de Donnees (MCD) a tout d'abord ete elabore afin d'identifier les entites principales du systeme (Run, Asset, IpamRecord, ConsolidatedAsset, Anomaly) ainsi que leurs relations et cardinalites. Ce modele conceptuel a ensuite ete transforme en schema relationnel (MLD), servant de base a l'implementation de la base de donnees SQLite via l'ORM SQLAlchemy. Cette demarche a permis de garantir la coherence des donnees et de faciliter l'evolution future de l'application.

> **📌 INSERER ICI → Schema 1 : Modele Conceptuel de Donnees (MCD)**
> *(Diagrammes_CloudInventory.md → section 1, diagramme erDiagram Mermaid)*
> *Affiche les 5 entites avec leurs attributs et les 5 associations avec cardinalites*

Les entites du MCD sont les suivantes :

- **RUN** : idRun, started_at, ended_at, status, error_message, vm_count, ip_count, matched_name_count, matched_ip_count, no_match_count
- **ASSET** : idAsset, vm_id, vm_name, type, node, status, tags, ip_reported, cpu_count, cpu_usage, ram_max, ram_used, disk_max, disk_used, uptime
- **IPAM_RECORD** : idIpamRecord, ip, dns_name, status, tenant, site
- **CONSOLIDATED_ASSET** : idConsolidatedAsset, run_id, asset_id, ipam_record_id, ip_final, dns_final, source_ip_dns, match_status, role
- **ANOMALY** : idAnomaly, run_id, asset_id, type, details, created_at

---

### Associations et cardinalites

**PRODUIRE**

**RUN** (1,1) --- (0,n) **CONSOLIDATED_ASSET**

Un run produit plusieurs assets consolides. Un asset consolide appartient a un seul run.

**CONSOLIDER**

**ASSET** (1,1) --- (0,n) **CONSOLIDATED_ASSET**

Un asset peut apparaitre dans plusieurs consolidations (une par run). Chaque consolidation concerne un seul asset.

**ASSOCIER**

**IPAM_RECORD** (0,1) --- (0,n) **CONSOLIDATED_ASSET**

Un enregistrement IPAM peut etre associe a plusieurs consolidations. Une consolidation peut ne pas avoir d'enregistrement IPAM (NO_MATCH).

**DETECTER**

**RUN** (1,1) --- (0,n) **ANOMALY**

Un run peut detecter plusieurs anomalies. Chaque anomalie est liee a un seul run.

**CONCERNER**

**ASSET** (1,1) --- (0,n) **ANOMALY**

Un asset peut etre concerne par plusieurs anomalies. Une anomalie concerne un seul asset.

---

> **📌 INSERER ICI → Schema 2 : Schema relationnel de la base de donnees SQLite (MLD)**
> *(Diagrammes_CloudInventory.md → section 2, diagramme erDiagram Mermaid avec FK)*
> *Affiche les 5 tables avec leurs colonnes, types, PK, FK et les liens entre elles*

---

## PAGE 5+ — Diagrammes de sequence UML

Afin de formaliser le fonctionnement de l'application avant et pendant le developpement, plusieurs diagrammes de sequence UML ont ete realises. Ces diagrammes permettent de representer les interactions entre les differents acteurs du systeme (administrateur d'infrastructure) et les composants techniques (frontend, backend, base de donnees, sources de donnees externes).

---

### Diagramme de sequence 1 — Authentification

Un premier diagramme de sequence decrit le processus d'authentification. Il met en evidence la saisie des identifiants par l'administrateur, la transmission des donnees au backend Flask, la verification des identifiants depuis les variables d'environnement (.env), la creation de la session via Flask-Login et l'acces au tableau de bord. Le diagramme illustre egalement le cas d'echec d'authentification et le processus de deconnexion.

> **📌 INSERER ICI → Schema 3 : Diagramme de sequence UML -- Authentification**
> *(Diagrammes_CloudInventory.md → section 3)*
> *Acteurs : Administrateur, Frontend, Backend Flask, Session Flask-Login, Variables .env*
> *Flux : GET / → redirect /login → POST /login → verification .env → session → redirect Dashboard*
> *Alt : identifiants invalides → message d'erreur*
> *Deconnexion : GET /logout → destruction session → redirect /login*

---

### Diagramme de sequence 2 — Lancement d'un cycle d'inventaire (Run)

Un second diagramme presente le processus principal de l'application : le lancement d'un cycle d'inventaire. Ce schema met en evidence les 6 etapes du pipeline de consolidation :

1. **Initialisation** : creation d'un objet Run en base avec le statut RUNNING
2. **Collecte Virtualisation** : appel au mock (40 VM/CT) ou a l'API Proxmox
3. **Collecte IPAM/DNS** : appel au mock ou a l'API NetBox avec pagination
4. **Upsert** : insertion ou mise a jour des Assets et IpamRecords par cle unique
5. **Consolidation** : correspondance par nom DNS, creation des ConsolidatedAssets, detection des NO_MATCH et STATUS_MISMATCH
6. **Detection anomalies IPAM** : identification des DUPLICATE_DNS et DUPLICATE_IP

Le diagramme illustre les interactions entre l'administrateur, le frontend (AJAX), le backend Flask, le moteur d'inventaire (InventoryRunner), les sources de donnees (Mock Virtualisation, NetBox API) et la base de donnees SQLite.

> **📌 INSERER ICI → Schema 4 : Diagramme de sequence UML -- Lancement d'un cycle d'inventaire**
> *(Diagrammes_CloudInventory.md → section 4)*
> *Acteurs : Administrateur, Frontend, Backend, InventoryRunner, Mock Virtualisation, NetBox API, Base de donnees*
> *6 blocs colores pour les 6 etapes du pipeline*
> *Boucle sur chaque asset pour la consolidation avec alt MATCHED/NO_MATCH*

---

### Diagramme de sequence 3 — Consultation de l'inventaire avec filtres et export

Un autre diagramme de sequence decrit la consultation de l'inventaire consolide par l'administrateur. Ce schema met en evidence :
- Le chargement initial de la page avec le dernier run et les 25 premiers resultats pagines
- L'application de filtres (statut, noeud, type, recherche textuelle, tags)
- L'export CSV de l'inventaire complet
- La recherche AJAX en temps reel

> **📌 INSERER ICI → Schema 5 : Diagramme de sequence UML -- Consultation de l'inventaire**
> *(Diagrammes_CloudInventory.md → section 5)*
> *Acteurs : Administrateur, Frontend, Backend, Base de donnees*
> *3 flux : chargement initial, filtrage, export CSV, recherche AJAX*

---

### Diagramme de sequence 4 — Comparaison de deux runs

Un diagramme de sequence detaille la fonctionnalite de comparaison de deux runs. Il illustre :
- La selection de deux runs a comparer
- Le chargement des assets consolides des deux runs
- L'analyse des differences par ensemble (VMs ajoutees, supprimees, modifiees)
- L'affichage de la comparaison cote a cote avec code couleur
- La navigation vers le detail d'une VM modifiee

> **📌 INSERER ICI → Schema 6 : Diagramme de sequence UML -- Comparaison de deux runs**
> *(Diagrammes_CloudInventory.md → section 6)*
> *Acteurs : Administrateur, Frontend, Backend, Base de donnees*
> *Bloc d'analyse : AJOUTEES = Run2 - Run1, SUPPRIMEES = Run1 - Run2, MODIFIEES = delta*

---

### Diagramme de sequence 5 — Detection et consultation des anomalies

Enfin, un diagramme de sequence detaille le systeme de detection des anomalies et leur consultation. Il illustre :
- La detection automatique des 4 types d'anomalies pendant un run (NO_MATCH, STATUS_MISMATCH, DUPLICATE_DNS, DUPLICATE_IP)
- La consultation de la liste des anomalies avec filtres par type et par run
- La navigation vers l'asset concerne par une anomalie

> **📌 INSERER ICI → Schema 7 : Diagramme de sequence UML -- Detection et consultation des anomalies**
> *(Diagrammes_CloudInventory.md → section 7)*
> *4 blocs colores pour les 4 types d'anomalies detectees*
> *Consultation : GET /anomalies → filtrage → navigation vers asset*

---

### Diagramme de sequence 6 — Dashboard et statistiques

Un dernier diagramme presente le fonctionnement du tableau de bord. Il illustre le chargement des statistiques du dernier run, l'appel AJAX a l'API /api/stats pour alimenter les graphiques Chart.js (Doughnut pour les correspondances, Bar pour les anomalies, Line pour l'evolution), et le lancement rapide d'un inventaire depuis le dashboard.

> **📌 INSERER ICI → Schema 8 : Diagramme de sequence UML -- Dashboard et statistiques**
> *(Diagrammes_CloudInventory.md → section 8)*
> *Acteurs : Administrateur, Frontend, Backend, Base de donnees, Chart.js*
> *Chargement asynchrone des graphiques via AJAX /api/stats*

---

## DERNIERE PAGE — Conclusion

La plateforme integre un systeme de detection d'anomalies automatise, reposant sur la reconciliation des donnees entre les sources de virtualisation et d'IPAM/DNS. Quatre types d'anomalies sont detectes a chaque cycle d'inventaire, permettant aux administrateurs d'identifier rapidement les ecarts de configuration et de prendre les mesures correctives appropriees. Des mecanismes de visualisation (graphiques Chart.js, tableaux filtarbles, comparaison de runs) ont ete mis en oeuvre afin de renforcer la lisibilite des donnees et de favoriser la prise de decision.

L'application est deployable localement grace a l'utilisation d'un environnement virtuel Python et d'une base de donnees SQLite embarquee, permettant de mettre en place un environnement de developpement reproductible. La suite de tests pytest (40+ cas de tests) garantit la non-regression des fonctionnalites.

Cette realisation professionnelle a permis de mobiliser des competences en analyse des besoins, conception applicative (Merise MCD/MLD), modelisation de bases de donnees, developpement web full-stack (Flask, Jinja2, Bootstrap, Chart.js), integration d'API REST (NetBox), tests automatises (pytest) et travail collaboratif (Git/GitHub). Le projet a ete concu de maniere evolutive, afin de pouvoir integrer ulterieurement de nouvelles fonctionnalites (integration Proxmox reel, alerting, RBAC, trending) sans remise en cause de l'architecture existante.
