"""Client pour l'API Proxmox VE — récupère les VM/CT avec métriques."""

import os
import requests


def _get_session():
    """Crée une session requests configurée pour Proxmox."""
    base_url = os.getenv("PROXMOX_URL", "https://pve.local:8006").rstrip("/")
    token_id = os.getenv("PROXMOX_TOKEN_ID", "")
    token_secret = os.getenv("PROXMOX_TOKEN_SECRET", "")
    verify_ssl = os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"

    session = requests.Session()
    session.headers.update({
        "Authorization": f"PVEAPIToken={token_id}={token_secret}",
        "Accept": "application/json",
    })
    session.verify = verify_ssl

    return session, base_url


def _parse_tags(tag_string):
    """Convertit les tags Proxmox (séparés par ';') en format CSV."""
    if not tag_string:
        return None
    # Proxmox stocke les tags séparés par ';'
    tags = [t.strip() for t in tag_string.split(";") if t.strip()]
    return ", ".join(tags) if tags else None


def _fetch_vm_status(session, base_url, node, vmid, vm_type):
    """Récupère le statut détaillé d'une VM ou d'un CT."""
    url = f"{base_url}/api2/json/nodes/{node}/{vm_type}/{vmid}/status/current"
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", {})
    except requests.RequestException:
        return {}


def _fetch_vm_config(session, base_url, node, vmid, vm_type):
    """Récupère la config d'une VM ou CT pour extraire les tags."""
    url = f"{base_url}/api2/json/nodes/{node}/{vm_type}/{vmid}/config"
    try:
        resp = session.get(url, timeout=15)
        resp.raise_for_status()
        return resp.json().get("data", {})
    except requests.RequestException:
        return {}


def _extract_ip(vm_type, status_data, config_data):
    """Extrait l'IP reportée depuis les données disponibles."""
    # Pour les VM QEMU : via QEMU Guest Agent (si disponible dans status)
    if vm_type == "qemu":
        # L'agent remonte parfois l'IP dans les données de status
        nics = status_data.get("nics", {})
        for nic_data in nics.values():
            for ip_info in nic_data.get("ip-addresses", []):
                addr = ip_info.get("ip-address", "")
                if addr and not addr.startswith("127.") and ip_info.get("ip-address-type") == "ipv4":
                    return addr

    # Pour LXC : l'IP est souvent dans la config (net0, net1, etc.)
    for key, val in config_data.items():
        if key.startswith("net") and isinstance(val, str) and "ip=" in val:
            for part in val.split(","):
                if part.strip().startswith("ip="):
                    ip = part.strip().split("=", 1)[1]
                    return ip.split("/")[0]  # retirer le masque CIDR

    return None


def fetch_proxmox_vms():
    """Récupère toutes les VM et CT depuis l'API Proxmox VE.

    Returns:
        list[dict]: Liste de dicts compatibles avec le format attendu par _upsert_assets().
    """
    session, base_url = _get_session()

    # 1. Lister les nœuds du cluster
    resp = session.get(f"{base_url}/api2/json/nodes", timeout=15)
    resp.raise_for_status()
    nodes = resp.json().get("data", [])

    results = []

    for node_info in nodes:
        node = node_info["node"]

        # 2. Pour chaque nœud, lister les VM (qemu) et les CT (lxc)
        for vm_type in ("qemu", "lxc"):
            list_url = f"{base_url}/api2/json/nodes/{node}/{vm_type}"
            try:
                resp = session.get(list_url, timeout=15)
                resp.raise_for_status()
                vms = resp.json().get("data", [])
            except requests.RequestException:
                continue

            for vm in vms:
                vmid = str(vm.get("vmid", ""))
                name = vm.get("name", f"vm-{vmid}")
                status = vm.get("status", "unknown")

                # 3. Récupérer le statut détaillé et la config
                status_data = _fetch_vm_status(session, base_url, node, vmid, vm_type)
                config_data = _fetch_vm_config(session, base_url, node, vmid, vm_type)

                # CPU
                cpu_count = config_data.get("cores", vm.get("cpus", 1))
                if vm_type == "lxc":
                    cpu_count = config_data.get("cores", 1)
                cpu_usage_raw = status_data.get("cpu", vm.get("cpu", 0))
                cpu_usage = round(cpu_usage_raw * 100, 1) if cpu_usage_raw else 0.0

                # RAM
                ram_max = status_data.get("maxmem", vm.get("maxmem", 0))
                ram_used = status_data.get("mem", vm.get("mem", 0))

                # Disque
                disk_max = status_data.get("maxdisk", vm.get("maxdisk", 0))
                disk_used = status_data.get("disk", vm.get("disk", 0))

                # Uptime
                uptime = status_data.get("uptime", vm.get("uptime", 0))

                # Tags
                tags = _parse_tags(config_data.get("tags", vm.get("tags", "")))

                # IP
                ip_reported = _extract_ip(vm_type, status_data, config_data)

                results.append({
                    "vm_id": vmid,
                    "vm_name": name,
                    "type": vm_type,
                    "node": node,
                    "status": status,
                    "tags": tags,
                    "ip_reported": ip_reported,
                    "cpu_count": cpu_count,
                    "cpu_usage": cpu_usage,
                    "ram_max": ram_max,
                    "ram_used": ram_used,
                    "disk_max": disk_max,
                    "disk_used": disk_used,
                    "uptime": uptime,
                })

    return results
