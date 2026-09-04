#!/usr/bin/env python3
"""
Protocol Definitions and Constants for REMAININGCONNECTIONS.

This module serves as the single source of truth for all network protocol definitions,
including port numbers, header structures, transport mechanisms, and common vulnerabilities.
It is designed to be comprehensive to support validation, parsing, and analysis tools.
"""

from enum import Enum
from typing import Dict, List, Set, Tuple, Optional


class ProtocolType(Enum):
    """Supported proxy and subscription protocols."""
    VLESS = "vless"
    VMESS = "vmess"
    TROJAN = "trojan"
    SHADOWSOCKS = "ss"
    HYPERSIA_2 = "hysteria2"
    TUIC = "tuic"
    WIREGUARD = "wg"
    SOCKS5 = "socks5"
    HTTP = "http"
    MTPROTO = "mtproto"
    NAIVEPROXY = "naiveproxy"
    CHAOS = "chaos"
    MUX = "mux"


class TransportLayer(Enum):
    """Transport mechanisms supported by modern proxies."""
    TCP = "tcp"
    WS = "ws"
    GRPC = "grpc"
    HTTP_UPGRADE = "httpupgrade"
    QUIC = "quic"
    KCP = "mkcp"
    SPLITHttp = "splithttp"
    REALITY = "reality" # Security layer, often paired with transport
    TLS = "tls"
    PLAIN = "plain"


class ShadowsocksMethod(Enum):
    """Common encryption methods for Shadowsocks."""
    AES_128_GCM = "aes-128-gcm"
    AES_256_GCM = "aes-256-gcm"
    CHACHA20_IETF = "chacha20-ietf"
    CHACHA20_POLY1305 = "chacha20-ietf-poly1305"
    XCHACHA20_POLY1305 = "xchacha20-ietf-poly1305"
    AEAD_CHACHA20_POLY1305 = "aead_chacha20_poly1305"
    NONE = "none"


class VmessSecurity(Enum):
    """Encryption security types for VLESS/VMess."""
    AUTO = "auto"
    NONE = "none"
    AES_128_GCM = "aes-128-gcm"
    CHACHA20_POLY1305 = "chacha20-poly1305"
    ZERO = "zero"


class GrpcServiceMode(Enum):
    """GRPC Service Mode settings."""
    GUN = "gun"
    MULTI = "multi"


class HeaderType(Enum):
    """Header types for TCP/HTTP fake headers."""
    NONE = "none"
    RTSP = "rtsp"
    HTTP = "http"
    TLS = "tls"


class ProxyConfigKeys:
    """Standard keys found in JSON/YAML proxy configurations."""
    # Common
    SERVER = "server"
    PORT = "port"
    NAME = "name"
    UUID = "uuid"
    PASSWORD = "password"
    
    # VLESS/VMess
    FLOW = "flow"
    ENCRYPTION = "encryption"
    SECURITY = "security"
    SNIS = "sni"
    ALPN = "alpn"
    FP = "fp" # Fingerprint
    PUBLIC_KEY = "publicKey"
    SHORT_ID = "shortId"
    SPIDER_X = "spiderX"
    
    # Stream Settings
    NETWORK = "network"
    SECURITY_LAYER = "security"
    REALITY_SETTINGS = "realitySettings"
    WS_SETTINGS = "wsSettings"
    GRPC_SETTINGS = "grpcSettings"
    HTTP_SETTINGS = "httpSettings"
    KCP_SETTINGS = "mkcpSettings"
    
    # HTTP/WS
    HOST = "host"
    PATH = "path"
    HEADERS = "headers"
    
    # QUIC
    QUIC_SECURITY = "quicSecurity"
    QUIC_KEY = "key"
    QUIC_HEADER = "header"
    
    # KCP
    KCP_HEADER_TYPE = "type"
    KCP_SEED = "seed"
    
    # Shadowsocks
    METHOD = "method"
    OBDURANCE = "obfs" # Obfuscation
    
    # Hysteria
    AUTH = "auth"
    OBFS_PASS = "obfs-password"
    DOWN = "down"
    UP = "up"
    OBFS_TYPE = "obfs.type"
    
    # Wireguard
    LOCAL_ADDRESS = "localAddress"
    PRIVATE_KEY = "privateKey"
    PEER_PUBLIC_KEY = "peerPublicKey"
    RESERVED = "reserved"
    MTU = "mtu"


# Comprehensive Mapping of Ports
STANDARD_PORTS: Dict[str, List[int]] = {
    "HTTPS": [443, 8443, 2053, 2083, 2087, 2096],
    "HTTP": [80, 8080, 8880, 2052, 2082, 2086, 2095],
    "WS_GRPC": [443, 8443, 2053, 2083, 2087, 2096],
    "KCP": [443, 80, 8888, 51820],
    "QUIC": [443, 8443, 2053, 2083]
}

# Known Vulnerabilities / Risk Indicators
RISK_INDICATORS = {
    "PLAIN_PASSWORD": "Password stored in plaintext without hashing",
    "WIDE_OPEN_SOCKS": "SOCKS proxy open to the world (no auth)",
    "MISSING_TLS": "No TLS/SSL encryption detected on sensitive connection",
    "WEAK_CIPHER": "Deprecated or weak encryption algorithm used",
    "DEFAULT_PORT": "Running on default port, potentially flagged by firewalls",
    "NO_AUTH": "Authentication mechanism missing",
    "HOMEGROWN_PROTOCOL": "Proprietary protocol not widely audited"
}

# Performance Benchmarks (Approximate RTT ms)
PERFORMANCE_BENCHMARKS = {
    "EXCELLENT": 50,
    "GOOD": 100,
    "FAIR": 200,
    "POOR": 500,
    "CRITICAL": 1000
}

# Regex Patterns for URI Parsing
URI_PATTERNS = {
    "VLESS": r"^vless://([a-f0-9\-]+)@([^:]+):(\d+)\?(.*)$",
    "VMESS": r"^vmess://(.+)$", # Base64 encoded
    "TROJAN": r"^trojan://([^@]+)@([^:]+):(\d+)\?(.*)$",
    "SS": r"^ss://([A-Za-z0-9\-_+=/]+)@([^:]+):(\d+)(?:#(.+))?$",
    "HYSTERIA2": r"^hysteria2://([^@]+)@([^:]+):(\d+)(?:\?(.*))?$",
    "WG": r"^wireguard://([^@]+)@([^:]+):(\d+)/?(.*)$",
    "MTPROTO": r"^tg://proxy\?server=([^&]+)&port=(\d+)&secret=([^&]+)"
}

# Detailed Configuration Schema Examples
SCHEMA_EXAMPLES = {
    "VLESS_REALITY_WS": {
        "protocol": "vless",
        "name": "Example-Reality",
        "server": "example.com",
        "port": 443,
        "uuid": "00000000-0000-0000-0000-000000000000",
        "flow": "xtls-rprx-vision",
        "encryption": "none",
        "network": "ws",
        "security": "reality",
        "sni": "cdn.example.com",
        "fp": "chrome",
        "pbk": "public-key-string-here",
        "sid": "short-id",
        "spiderX": "/start",
        "ws-opts": {
            "path": "/realpath",
            "headers": {"Host": "cdn.example.com"}
        }
    },
    "TROJAN_GRPC": {
        "protocol": "trojan",
        "name": "Trojan-GRPC-Cloud",
        "server": "cloud.example.com",
        "port": 443,
        "password": "super-secret-password",
        "network": "grpc",
        "security": "tls",
        "sni": "cloud.example.com",
        "fp": "firefox",
        "alpn": ["http/1.1", "h2"],
        "grpc-opts": {
            "grpc-service-name": "api.service.internal"
        }
    },
    "HYSTERIA2": {
        "protocol": "hysteria2",
        "name": "Hy2-Fast",
        "server": "hy.example.com",
        "port": 443,
        "password": "hysteria-pass",
        "obfs": {
            "type": "salamander",
            "password": "fake-obfs-pass"
        },
        "skip-cert-verify": False,
        "mport": "443-1200"
    }
}


def get_protocol_by_uri(uri: str) -> Optional[ProtocolType]:
    """Determine protocol type based on URI scheme."""
    if not uri:
        return None
    lower_uri = uri.lower().split('://')[0]
    try:
        if lower_uri == "vless":
            return ProtocolType.VLESS
        elif lower_uri == "vmess":
            return ProtocolType.VMESS
        elif lower_uri == "trojan":
            return ProtocolType.TROJAN
        elif lower_uri.startswith("ss://"):
            return ProtocolType.SHADOWSOCKS
        elif lower_uri == "hysteria2" or lower_uri == "hy2":
            return ProtocolType.HYPERSIA_2
        elif lower_uri == "tuic":
            return ProtocolType.TUIC
        elif lower_uri == "wireguard" or lower_uri == "wg":
            return ProtocolType.WIREGUARD
        elif lower_uri == "socks" or lower_uri == "socks5":
            return ProtocolType.SOCKS5
        elif lower_uri in ("http", "https"):
            return ProtocolType.HTTP
        elif lower_uri == "tg":
            return ProtocolType.MTPROTO
        else:
            return None
    except Exception:
        return None


def is_secure_transport(network: str, security: str) -> bool:
    """Check if the combination of network and security is considered secure."""
    secure_security = {"tls", "reality"}
    # Some transports like ws/httpupgrade are often used with TLS
    if security in secure_security:
        return True
    # Plain TCP without TLS is generally insecure for public proxies
    if network in ("tcp", "ws") and security == "none":
        return False
    return True