"""Client pour l'API NetBox — récupère les IP addresses avec pagination."""

import os
import requests


def fetch_ipam_records():
    """Récupère toutes les IP addresses depuis NetBox (avec pagination).

    Returns:
        list[dict]: Liste de dicts avec ip, dns_name, status, tenant, site.
    """
    base_url = os.getenv("NETBOX_URL", "http://127.0.0.1:8000").rstrip("/")
    token = os.getenv("NETBOX_TOKEN", "")
    verify_ssl = os.getenv("NETBOX_VERIFY_SSL", "true").lower() == "true"

    url = f"{base_url}/api/ipam/ip-addresses/"
    # NetBox v4+ tokens nbt_ utilisent Bearer, les anciens utilisent Token
    if token.startswith("nbt_"):
        auth_prefix = "Bearer"
    else:
        auth_prefix = "Token"
    headers = {
        "Authorization": f"{auth_prefix} {token}",
        "Accept": "application/json",
    }

    records = []

    while url:
        resp = requests.get(url, headers=headers, verify=verify_ssl, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for entry in data.get("results", []):
            address = entry.get("address", "")
            ip = address.split("/")[0] if address else ""

            dns_name = (entry.get("dns_name") or "").strip()
            status_obj = entry.get("status")
            status = status_obj.get("value", "") if isinstance(status_obj, dict) else str(status_obj or "")

            tenant_obj = entry.get("tenant")
            tenant = tenant_obj.get("name", "") if isinstance(tenant_obj, dict) and tenant_obj else None

            site_obj = entry.get("site")
            site = site_obj.get("name", "") if isinstance(site_obj, dict) and site_obj else None

            records.append({
                "ip": ip,
                "dns_name": dns_name,
                "status": status,
                "tenant": tenant,
                "site": site,
            })

        url = data.get("next")

    return records
