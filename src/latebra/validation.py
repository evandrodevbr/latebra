"""URL validation and SSRF protection for latebra.

Validates that URLs are safe before pipeline dispatch.
Blocks private/reserved IPs and metadata endpoints.

Autor: Evandro Fonseca Junior
Licença: MIT
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

# ── Blocked networks (RFC 1918 + loopback + link-local + metadata) ──
_BLOCKED_NETWORKS: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = [
    ipaddress.ip_network("10.0.0.0/8"),          # RFC 1918 Class A
    ipaddress.ip_network("172.16.0.0/12"),        # RFC 1918 Class B
    ipaddress.ip_network("192.168.0.0/16"),       # RFC 1918 Class C
    ipaddress.ip_network("127.0.0.0/8"),          # Loopback
    ipaddress.ip_network("169.254.0.0/16"),       # Link-local
    ipaddress.ip_network("0.0.0.0/8"),            # Current network
    ipaddress.ip_network("100.64.0.0/10"),        # CGNAT (RFC 6598)
    ipaddress.ip_network("::1/128"),              # IPv6 loopback
    ipaddress.ip_network("fe80::/10"),            # IPv6 link-local
    ipaddress.ip_network("fc00::/7"),             # IPv6 unique local
]

# ── Blocked hostnames ────────────────────────────
_BLOCKED_HOSTNAMES: set[str] = {
    "localhost",
    "localhost.localdomain",
    "localhost6.localdomain6",
    "ip6-localhost",
    "ip6-loopback",
    "0.0.0.0",
    "[::]",
}

# ── Blocked specific IPs (metadata endpoints, etc.) ──
_BLOCKED_IPS: set[str] = {
    "169.254.169.254",  # AWS / cloud metadata endpoint
}

# ── Allowed schemes ──────────────────────────────
_ALLOWED_SCHEMES: set[str] = {"http", "https"}


def _is_blocked_ip(ip_str: str) -> bool:
    """Check if an IP address is in any blocked network or IP set."""
    if ip_str in _BLOCKED_IPS:
        return True

    # Remove zone index for IPv6 (e.g., fe80::1%eth0)
    if "%" in ip_str:
        ip_str = ip_str.split("%")[0]

    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        # Not a valid IP — could be a hostname not yet resolved
        return False

    for network in _BLOCKED_NETWORKS:
        if addr in network:
            return True

    return False


def _resolve_hostname(hostname: str) -> list[str]:
    """Resolve hostname to IP addresses using getaddrinfo.

    Returns list of IP strings. Returns empty list on resolution failure.
    Socket is opened per-call for thread safety.
    """
    ips: list[str] = []
    try:
        # Strip brackets from IPv6 literal (e.g., [::1] → ::1)
        clean = hostname.strip("[]")
        for family in (socket.AF_INET, socket.AF_INET6):
            try:
                info = socket.getaddrinfo(clean, None, family, socket.SOCK_STREAM)
                for item in info:
                    raw = item[4][0]
                    addr = str(raw) if not isinstance(raw, str) else raw
                    if addr not in ips:
                        ips.append(addr)
            except socket.gaierror:
                continue
    except Exception:
        pass
    return ips


def validate(url: str) -> str:
    """Validate a URL is safe to scrape.

    Checks:
        1. URL is syntactically valid
        2. Scheme is http or https only
        3. Hostname is not blocked
        4. Resolved IP is not in private/reserved ranges
        5. Not a metadata endpoint

    Args:
        url: The URL to validate.

    Returns:
        The validated (and potentially normalized) URL string.

    Raises:
        ValueError: If the URL fails any validation check.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    # Parse URL
    parsed = urlparse(url)

    # Scheme check
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"Unsupported URL scheme '{parsed.scheme}'. "
            f"Only {', '.join(sorted(_ALLOWED_SCHEMES))} are allowed."
        )

    if not parsed.hostname:
        raise ValueError("URL must include a hostname")

    hostname = parsed.hostname.lower()

    # Hostname blocklist
    if hostname in _BLOCKED_HOSTNAMES:
        raise ValueError(f"Hostname '{hostname}' is blocked")

    # IP literal check (e.g., http://127.0.0.1/)
    if _is_blocked_ip(hostname):
        raise ValueError(f"IP address '{hostname}' is in a blocked range")

    # Resolve hostname and check all resolved IPs
    resolved = _resolve_hostname(hostname)
    for ip in resolved:
        if _is_blocked_ip(ip):
            raise ValueError(
                f"Hostname '{hostname}' resolves to blocked IP '{ip}'"
            )

    # Rebuild URL without fragment for consistency
    normalized = parsed._replace(fragment="").geturl()
    return normalized
