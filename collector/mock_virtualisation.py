"""Mock de la source A (Virtualisation / Proxmox VE) — dataset fixe Phase 1.

Simule les données runtime remontées par l'API Proxmox VE :
- Identité VM/CT (vm_id, vm_name, type, node, status, tags)
- IP reportée par le QEMU Guest Agent
- Métriques runtime : CPU, RAM, disque, uptime

5 nodes — 40 VMs/CTs au total.
"""

# Constantes pour lisibilité (octets)
_GB = 1_073_741_824  # 1 Go
_MB = 1_048_576       # 1 Mo

MOCK_VMS = [
    # ══════════════════════════════════════════════════════════════
    # pve1 : production — front & applicatif  (8 VMs)
    # ══════════════════════════════════════════════════════════════
    {
        "vm_id": "100", "vm_name": "web-a500", "type": "qemu", "node": "pve1",
        "status": "running", "tags": "env:production, role:web, os:debian-12, criticite:critical, owner:infra-team, backup:daily",
        "ip_reported": "10.0.1.10",
        "cpu_count": 4, "cpu_usage": 32.5,
        "ram_max": 8 * _GB, "ram_used": 5 * _GB + 200 * _MB,
        "disk_max": 50 * _GB, "disk_used": 22 * _GB,
        "uptime": 864000,
    },
    {
        "vm_id": "101", "vm_name": "web-b501", "type": "qemu", "node": "pve1",
        "status": "running", "tags": "env:production, role:web, os:debian-12, criticite:critical, owner:infra-team, backup:daily",
        "ip_reported": "10.0.1.11",
        "cpu_count": 4, "cpu_usage": 28.9,
        "ram_max": 8 * _GB, "ram_used": 4 * _GB + 600 * _MB,
        "disk_max": 50 * _GB, "disk_used": 19 * _GB,
        "uptime": 864000,
    },
    {
        "vm_id": "102", "vm_name": "app-backend", "type": "qemu", "node": "pve1",
        "status": "running", "tags": "env:production, role:api, os:debian-12, criticite:critical, owner:dev-team, backup:daily",
        "ip_reported": "10.0.1.12",
        "cpu_count": 4, "cpu_usage": 22.3,
        "ram_max": 8 * _GB, "ram_used": 3 * _GB + 500 * _MB,
        "disk_max": 40 * _GB, "disk_used": 18 * _GB,
        "uptime": 864000,
    },
    {
        "vm_id": "103", "vm_name": "app-worker", "type": "qemu", "node": "pve1",
        "status": "running", "tags": "env:production, role:api, os:ubuntu-22.04, criticite:high, owner:dev-team, backup:daily",
        "ip_reported": "10.0.1.13",
        "cpu_count": 4, "cpu_usage": 41.7,
        "ram_max": 8 * _GB, "ram_used": 5 * _GB + 900 * _MB,
        "disk_max": 40 * _GB, "disk_used": 12 * _GB,
        "uptime": 864000,
    },
    {
        "vm_id": "104", "vm_name": "cache-redis", "type": "lxc", "node": "pve1",
        "status": "running", "tags": "env:production, role:cache, os:alpine-3.19, criticite:high, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.1.14",
        "cpu_count": 2, "cpu_usage": 8.7,
        "ram_max": 4 * _GB, "ram_used": 3 * _GB + 600 * _MB,
        "disk_max": 10 * _GB, "disk_used": 2 * _GB,
        "uptime": 2592000,
    },
    {
        "vm_id": "105", "vm_name": "proxy-nginx", "type": "lxc", "node": "pve1",
        "status": "running", "tags": "env:production, role:proxy, os:alpine-3.19, criticite:critical, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.1.15",
        "cpu_count": 2, "cpu_usage": 12.4,
        "ram_max": 2 * _GB, "ram_used": 800 * _MB,
        "disk_max": 10 * _GB, "disk_used": 3 * _GB,
        "uptime": 2592000,
    },
    {
        "vm_id": "106", "vm_name": "haproxy-lb", "type": "lxc", "node": "pve1",
        "status": "running", "tags": "env:production, role:loadbalancer, os:alpine-3.19, criticite:critical, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.1.16",
        "cpu_count": 2, "cpu_usage": 9.2,
        "ram_max": 2 * _GB, "ram_used": 700 * _MB,
        "disk_max": 8 * _GB, "disk_used": 2 * _GB,
        "uptime": 2592000,
    },
    {
        "vm_id": "107", "vm_name": "rabbitmq-prod", "type": "lxc", "node": "pve1",
        "status": "running", "tags": "env:production, role:messaging, os:ubuntu-22.04, criticite:high, owner:dev-team, backup:daily",
        "ip_reported": "10.0.1.17",
        "cpu_count": 2, "cpu_usage": 18.4,
        "ram_max": 4 * _GB, "ram_used": 2 * _GB + 800 * _MB,
        "disk_max": 20 * _GB, "disk_used": 8 * _GB,
        "uptime": 1296000,
    },

    # ══════════════════════════════════════════════════════════════
    # pve2 : production — données & stockage  (8 VMs)
    # ══════════════════════════════════════════════════════════════
    {
        "vm_id": "200", "vm_name": "db-b500", "type": "qemu", "node": "pve2",
        "status": "running", "tags": "env:production, role:database, os:debian-12, criticite:critical, owner:data-team, backup:daily",
        "ip_reported": "10.0.2.10",
        "cpu_count": 8, "cpu_usage": 58.1,
        "ram_max": 16 * _GB, "ram_used": 12 * _GB + 800 * _MB,
        "disk_max": 200 * _GB, "disk_used": 145 * _GB,
        "uptime": 1728000,
    },
    {
        "vm_id": "201", "vm_name": "db-replica", "type": "qemu", "node": "pve2",
        "status": "running", "tags": "env:production, role:database, os:debian-12, criticite:high, owner:data-team, backup:daily",
        "ip_reported": "10.0.2.11",
        "cpu_count": 8, "cpu_usage": 35.4,
        "ram_max": 16 * _GB, "ram_used": 9 * _GB + 200 * _MB,
        "disk_max": 200 * _GB, "disk_used": 142 * _GB,
        "uptime": 1728000,
    },
    {
        "vm_id": "202", "vm_name": "nfs-storage", "type": "qemu", "node": "pve2",
        "status": "running", "tags": "env:production, role:storage, os:debian-12, criticite:high, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.2.12",
        "cpu_count": 2, "cpu_usage": 11.3,
        "ram_max": 4 * _GB, "ram_used": 1 * _GB + 800 * _MB,
        "disk_max": 500 * _GB, "disk_used": 312 * _GB,
        "uptime": 5184000,
    },
    {
        "vm_id": "203", "vm_name": "minio-s3", "type": "qemu", "node": "pve2",
        "status": "running", "tags": "env:production, role:storage, os:ubuntu-22.04, criticite:high, owner:data-team, backup:weekly",
        "ip_reported": "10.0.2.13",
        "cpu_count": 4, "cpu_usage": 19.8,
        "ram_max": 8 * _GB, "ram_used": 4 * _GB + 300 * _MB,
        "disk_max": 1000 * _GB, "disk_used": 687 * _GB,
        "uptime": 3456000,
    },
    {
        "vm_id": "204", "vm_name": "log-elastic", "type": "qemu", "node": "pve2",
        "status": "running", "tags": "env:production, role:logs, os:ubuntu-22.04, criticite:high, owner:infra-team, backup:daily",
        "ip_reported": "10.0.2.14",
        "cpu_count": 4, "cpu_usage": 62.7,
        "ram_max": 16 * _GB, "ram_used": 14 * _GB + 200 * _MB,
        "disk_max": 200 * _GB, "disk_used": 178 * _GB,
        "uptime": 1728000,
    },
    {
        "vm_id": "205", "vm_name": "log-kibana", "type": "lxc", "node": "pve2",
        "status": "running", "tags": "env:production, role:logs, os:alpine-3.19, criticite:medium, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.2.15",
        "cpu_count": 2, "cpu_usage": 14.2,
        "ram_max": 4 * _GB, "ram_used": 2 * _GB + 100 * _MB,
        "disk_max": 20 * _GB, "disk_used": 6 * _GB,
        "uptime": 1728000,
    },
    {
        "vm_id": "206", "vm_name": "backup-srv", "type": "qemu", "node": "pve2",
        "status": "stopped", "tags": "env:production, role:backup, os:debian-12, criticite:high, owner:infra-team, backup:none",
        "ip_reported": None,
        "cpu_count": 4, "cpu_usage": 0.0,
        "ram_max": 8 * _GB, "ram_used": 0,
        "disk_max": 500 * _GB, "disk_used": 320 * _GB,
        "uptime": 0,
    },
    {
        "vm_id": "207", "vm_name": "backup-offsite", "type": "qemu", "node": "pve2",
        "status": "stopped", "tags": "env:production, role:backup, os:debian-12, criticite:medium, owner:infra-team, backup:none",
        "ip_reported": None,
        "cpu_count": 2, "cpu_usage": 0.0,
        "ram_max": 4 * _GB, "ram_used": 0,
        "disk_max": 300 * _GB, "disk_used": 210 * _GB,
        "uptime": 0,
    },

    # ══════════════════════════════════════════════════════════════
    # pve3 : infra & services réseau  (8 VMs)
    # ══════════════════════════════════════════════════════════════
    {
        "vm_id": "300", "vm_name": "dns-d500", "type": "lxc", "node": "pve3",
        "status": "running", "tags": "env:production, role:dns, os:alpine-3.19, criticite:critical, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.3.10",
        "cpu_count": 1, "cpu_usage": 3.5,
        "ram_max": 1 * _GB, "ram_used": 400 * _MB,
        "disk_max": 8 * _GB, "disk_used": 2 * _GB,
        "uptime": 7776000,
    },
    {
        "vm_id": "301", "vm_name": "dns-secondary", "type": "lxc", "node": "pve3",
        "status": "running", "tags": "env:production, role:dns, os:alpine-3.19, criticite:high, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.3.11",
        "cpu_count": 1, "cpu_usage": 2.1,
        "ram_max": 1 * _GB, "ram_used": 350 * _MB,
        "disk_max": 8 * _GB, "disk_used": 2 * _GB,
        "uptime": 7776000,
    },
    {
        "vm_id": "302", "vm_name": "ldap-auth", "type": "qemu", "node": "pve3",
        "status": "running", "tags": "env:production, role:auth, os:debian-12, criticite:critical, owner:security-team, backup:daily",
        "ip_reported": "10.0.3.12",
        "cpu_count": 2, "cpu_usage": 5.3,
        "ram_max": 4 * _GB, "ram_used": 1 * _GB + 200 * _MB,
        "disk_max": 20 * _GB, "disk_used": 8 * _GB,
        "uptime": 5184000,
    },
    {
        "vm_id": "303", "vm_name": "mail-smtp", "type": "qemu", "node": "pve3",
        "status": "running", "tags": "env:production, role:mail, os:debian-12, criticite:high, owner:infra-team, backup:daily",
        "ip_reported": "10.0.3.13",
        "cpu_count": 2, "cpu_usage": 15.8,
        "ram_max": 4 * _GB, "ram_used": 2 * _GB + 300 * _MB,
        "disk_max": 50 * _GB, "disk_used": 31 * _GB,
        "uptime": 3456000,
    },
    {
        "vm_id": "304", "vm_name": "vpn-gateway", "type": "lxc", "node": "pve3",
        "status": "running", "tags": "env:production, role:network, os:alpine-3.19, criticite:critical, owner:security-team, backup:weekly",
        "ip_reported": "10.0.3.14",
        "cpu_count": 2, "cpu_usage": 3.1,
        "ram_max": 2 * _GB, "ram_used": 600 * _MB,
        "disk_max": 8 * _GB, "disk_used": 2 * _GB,
        "uptime": 7776000,
    },
    {
        "vm_id": "305", "vm_name": "firewall-pf", "type": "qemu", "node": "pve3",
        "status": "running", "tags": "env:production, role:firewall, os:rocky-9, criticite:critical, owner:security-team, backup:weekly",
        "ip_reported": "10.0.3.15",
        "cpu_count": 2, "cpu_usage": 6.8,
        "ram_max": 4 * _GB, "ram_used": 1 * _GB + 500 * _MB,
        "disk_max": 16 * _GB, "disk_used": 5 * _GB,
        "uptime": 7776000,
    },
    {
        "vm_id": "306", "vm_name": "ntp-srv", "type": "lxc", "node": "pve3",
        "status": "running", "tags": "env:production, role:ntp, os:alpine-3.19, criticite:medium, owner:infra-team, backup:none",
        "ip_reported": "10.0.3.16",
        "cpu_count": 1, "cpu_usage": 0.4,
        "ram_max": 512 * _MB, "ram_used": 120 * _MB,
        "disk_max": 4 * _GB, "disk_used": 1 * _GB,
        "uptime": 15552000,
    },
    {
        "vm_id": "307", "vm_name": "syslog-central", "type": "lxc", "node": "pve3",
        "status": "running", "tags": "env:production, role:logs, os:alpine-3.19, criticite:high, owner:infra-team, backup:daily",
        "ip_reported": "10.0.3.17",
        "cpu_count": 2, "cpu_usage": 22.1,
        "ram_max": 4 * _GB, "ram_used": 3 * _GB + 100 * _MB,
        "disk_max": 100 * _GB, "disk_used": 72 * _GB,
        "uptime": 2592000,
    },

    # ══════════════════════════════════════════════════════════════
    # pve4 : supervision & monitoring  (8 VMs)
    # ══════════════════════════════════════════════════════════════
    {
        "vm_id": "400", "vm_name": "monitoring", "type": "qemu", "node": "pve4",
        "status": "running", "tags": "env:production, role:monitoring, os:ubuntu-22.04, criticite:critical, owner:infra-team, backup:daily",
        "ip_reported": "10.0.4.10",
        "cpu_count": 4, "cpu_usage": 45.2,
        "ram_max": 8 * _GB, "ram_used": 6 * _GB + 100 * _MB,
        "disk_max": 100 * _GB, "disk_used": 67 * _GB,
        "uptime": 1296000,
    },
    {
        "vm_id": "401", "vm_name": "grafana-dash", "type": "lxc", "node": "pve4",
        "status": "running", "tags": "env:production, role:monitoring, os:alpine-3.19, criticite:high, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.4.11",
        "cpu_count": 2, "cpu_usage": 10.5,
        "ram_max": 4 * _GB, "ram_used": 1 * _GB + 800 * _MB,
        "disk_max": 20 * _GB, "disk_used": 7 * _GB,
        "uptime": 1296000,
    },
    {
        "vm_id": "402", "vm_name": "prometheus-ts", "type": "qemu", "node": "pve4",
        "status": "running", "tags": "env:production, role:monitoring, os:ubuntu-22.04, criticite:high, owner:infra-team, backup:daily",
        "ip_reported": "10.0.4.12",
        "cpu_count": 4, "cpu_usage": 38.6,
        "ram_max": 8 * _GB, "ram_used": 6 * _GB + 500 * _MB,
        "disk_max": 150 * _GB, "disk_used": 98 * _GB,
        "uptime": 1296000,
    },
    {
        "vm_id": "403", "vm_name": "alertmanager", "type": "lxc", "node": "pve4",
        "status": "running", "tags": "env:production, role:alerting, os:alpine-3.19, criticite:high, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.4.13",
        "cpu_count": 1, "cpu_usage": 4.2,
        "ram_max": 2 * _GB, "ram_used": 800 * _MB,
        "disk_max": 10 * _GB, "disk_used": 3 * _GB,
        "uptime": 1296000,
    },
    {
        "vm_id": "404", "vm_name": "uptime-kuma", "type": "lxc", "node": "pve4",
        "status": "running", "tags": "env:production, role:monitoring, os:alpine-3.19, criticite:medium, owner:infra-team, backup:weekly",
        "ip_reported": "10.0.4.14",
        "cpu_count": 1, "cpu_usage": 6.3,
        "ram_max": 2 * _GB, "ram_used": 900 * _MB,
        "disk_max": 10 * _GB, "disk_used": 4 * _GB,
        "uptime": 864000,
    },
    {
        "vm_id": "405", "vm_name": "ansible-ctrl", "type": "qemu", "node": "pve4",
        "status": "running", "tags": "env:production, role:automation, os:debian-12, criticite:high, owner:devops-team, backup:weekly",
        "ip_reported": "10.0.4.15",
        "cpu_count": 2, "cpu_usage": 7.9,
        "ram_max": 4 * _GB, "ram_used": 1 * _GB + 600 * _MB,
        "disk_max": 30 * _GB, "disk_used": 14 * _GB,
        "uptime": 432000,
    },
    {
        "vm_id": "406", "vm_name": "gitea-repo", "type": "qemu", "node": "pve4",
        "status": "running", "tags": "env:production, role:git, os:debian-12, criticite:high, owner:devops-team, backup:daily",
        "ip_reported": "10.0.4.16",
        "cpu_count": 2, "cpu_usage": 13.1,
        "ram_max": 4 * _GB, "ram_used": 2 * _GB + 400 * _MB,
        "disk_max": 80 * _GB, "disk_used": 52 * _GB,
        "uptime": 2592000,
    },
    {
        "vm_id": "407", "vm_name": "vault-secrets", "type": "qemu", "node": "pve4",
        "status": "running", "tags": "env:production, role:secrets, os:ubuntu-22.04, criticite:critical, owner:security-team, backup:daily",
        "ip_reported": "10.0.4.17",
        "cpu_count": 2, "cpu_usage": 2.8,
        "ram_max": 4 * _GB, "ram_used": 1 * _GB + 100 * _MB,
        "disk_max": 10 * _GB, "disk_used": 3 * _GB,
        "uptime": 5184000,
    },

    # ══════════════════════════════════════════════════════════════
    # pve5 : dev, test & staging  (8 VMs)
    # ══════════════════════════════════════════════════════════════
    {
        "vm_id": "500", "vm_name": "dev-frontend", "type": "qemu", "node": "pve5",
        "status": "running", "tags": "env:dev, role:web, os:debian-12, criticite:low, owner:dev-team, backup:none",
        "ip_reported": "10.0.5.10",
        "cpu_count": 2, "cpu_usage": 18.9,
        "ram_max": 4 * _GB, "ram_used": 2 * _GB + 100 * _MB,
        "disk_max": 30 * _GB, "disk_used": 12 * _GB,
        "uptime": 259200,
    },
    {
        "vm_id": "501", "vm_name": "dev-api", "type": "qemu", "node": "pve5",
        "status": "stopped", "tags": "env:dev, role:api, os:debian-12, criticite:low, owner:dev-team, backup:none",
        "ip_reported": None,
        "cpu_count": 2, "cpu_usage": 0.0,
        "ram_max": 4 * _GB, "ram_used": 0,
        "disk_max": 30 * _GB, "disk_used": 15 * _GB,
        "uptime": 0,
    },
    {
        "vm_id": "502", "vm_name": "test-db", "type": "lxc", "node": "pve5",
        "status": "running", "tags": "env:dev, role:database, os:alpine-3.19, criticite:low, owner:dev-team, backup:weekly",
        "ip_reported": "10.0.5.12",
        "cpu_count": 2, "cpu_usage": 25.6,
        "ram_max": 4 * _GB, "ram_used": 3 * _GB + 400 * _MB,
        "disk_max": 40 * _GB, "disk_used": 28 * _GB,
        "uptime": 432000,
    },
    {
        "vm_id": "503", "vm_name": "ci-runner", "type": "lxc", "node": "pve5",
        "status": "running", "tags": "env:dev, role:ci, os:ubuntu-22.04, criticite:medium, owner:devops-team, backup:none",
        "ip_reported": "10.0.5.13",
        "cpu_count": 4, "cpu_usage": 78.3,
        "ram_max": 8 * _GB, "ram_used": 7 * _GB + 200 * _MB,
        "disk_max": 60 * _GB, "disk_used": 42 * _GB,
        "uptime": 86400,
    },
    {
        "vm_id": "504", "vm_name": "staging-web", "type": "qemu", "node": "pve5",
        "status": "running", "tags": "env:staging, role:web, os:debian-12, criticite:medium, owner:dev-team, backup:weekly",
        "ip_reported": "10.0.5.14",
        "cpu_count": 2, "cpu_usage": 15.2,
        "ram_max": 4 * _GB, "ram_used": 2 * _GB + 500 * _MB,
        "disk_max": 40 * _GB, "disk_used": 16 * _GB,
        "uptime": 604800,
    },
    {
        "vm_id": "505", "vm_name": "staging-api", "type": "qemu", "node": "pve5",
        "status": "running", "tags": "env:staging, role:api, os:debian-12, criticite:medium, owner:dev-team, backup:weekly",
        "ip_reported": "10.0.5.15",
        "cpu_count": 2, "cpu_usage": 11.7,
        "ram_max": 4 * _GB, "ram_used": 1 * _GB + 900 * _MB,
        "disk_max": 30 * _GB, "disk_used": 10 * _GB,
        "uptime": 604800,
    },
    {
        "vm_id": "506", "vm_name": "staging-db", "type": "lxc", "node": "pve5",
        "status": "running", "tags": "env:staging, role:database, os:alpine-3.19, criticite:medium, owner:data-team, backup:daily",
        "ip_reported": "10.0.5.16",
        "cpu_count": 2, "cpu_usage": 20.3,
        "ram_max": 4 * _GB, "ram_used": 3 * _GB,
        "disk_max": 40 * _GB, "disk_used": 22 * _GB,
        "uptime": 604800,
    },
    {
        "vm_id": "507", "vm_name": "sandbox-test", "type": "qemu", "node": "pve5",
        "status": "stopped", "tags": "env:dev, role:test, os:ubuntu-22.04, criticite:low, owner:dev-team, backup:none",
        "ip_reported": None,
        "cpu_count": 1, "cpu_usage": 0.0,
        "ram_max": 2 * _GB, "ram_used": 0,
        "disk_max": 20 * _GB, "disk_used": 8 * _GB,
        "uptime": 0,
    },

    # ══════════════════════════════════════════════════════════════
    # VMs sans correspondance NetBox (NO_MATCH attendu)
    # ══════════════════════════════════════════════════════════════
    {
        "vm_id": "999", "vm_name": "unknown-x999", "type": "qemu", "node": "pve2",
        "status": "running", "tags": None,
        "ip_reported": "10.0.9.1",
        "cpu_count": 1, "cpu_usage": 2.1,
        "ram_max": 2 * _GB, "ram_used": 400 * _MB,
        "disk_max": 20 * _GB, "disk_used": 5 * _GB,
        "uptime": 172800,
    },
    {
        "vm_id": "998", "vm_name": "temp-migration", "type": "qemu", "node": "pve1",
        "status": "stopped", "tags": "env:production, role:migration, os:debian-12, criticite:low, owner:infra-team, backup:none",
        "ip_reported": None,
        "cpu_count": 2, "cpu_usage": 0.0,
        "ram_max": 4 * _GB, "ram_used": 0,
        "disk_max": 100 * _GB, "disk_used": 88 * _GB,
        "uptime": 0,
    },
    {
        "vm_id": "997", "vm_name": "old-legacy", "type": "qemu", "node": "pve3",
        "status": "stopped", "tags": "env:production, role:deprecated, os:debian-11, criticite:low, owner:infra-team, backup:none",
        "ip_reported": None,
        "cpu_count": 1, "cpu_usage": 0.0,
        "ram_max": 2 * _GB, "ram_used": 0,
        "disk_max": 40 * _GB, "disk_used": 35 * _GB,
        "uptime": 0,
    },
    {
        "vm_id": "996", "vm_name": "ghost-vm", "type": "qemu", "node": "pve4",
        "status": "running", "tags": None,
        "ip_reported": "10.0.9.2",
        "cpu_count": 1, "cpu_usage": 0.5,
        "ram_max": 1 * _GB, "ram_used": 200 * _MB,
        "disk_max": 10 * _GB, "disk_used": 3 * _GB,
        "uptime": 345600,
    },
    {
        "vm_id": "995", "vm_name": "decom-windows", "type": "qemu", "node": "pve5",
        "status": "stopped", "tags": "env:production, role:deprecated, os:windows-server-2022, criticite:low, owner:infra-team, backup:none",
        "ip_reported": None,
        "cpu_count": 4, "cpu_usage": 0.0,
        "ram_max": 8 * _GB, "ram_used": 0,
        "disk_max": 120 * _GB, "disk_used": 95 * _GB,
        "uptime": 0,
    },
]


def fetch_mock_vms():
    """Retourne le dataset mock de VMs/CTs (simule l'API Proxmox VE).

    Returns:
        list[dict]: Liste de VMs simulées avec métriques runtime.
    """
    return MOCK_VMS
