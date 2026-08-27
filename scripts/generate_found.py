#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_found.py

Генератор массивного found.json / subscriptions_found.json для дашборда.

Примеры запуска:

    python scripts/generate_found.py --count 300
    python scripts/generate_found.py --count 800 --output data/subscriptions_found.json
    python scripts/generate_found.py --count 1200 --output docs/data.json

Файл специально делает много реалистичных полей:
- source: github / gitverse
- updated_mins_ago
- configs_count
- has_bs
- status
- subscription_url
- config_path
- last_commit_message
- content_sample
- summary / top_by_configs / top_by_freshness
"""

import argparse
import datetime
import json
import os
import random


# =========================================================
# 1. Константы для генерации
# =========================================================

GITHUB_ORGS = [
    "remainingconnections",
    "netwatch-labs",
    "free-nodes",
    "proxy-aggregator",
    "open-subscriptions",
    "v2ray-collective",
    "xray-hub",
    "singbox-world",
    "clash-meta-ru",
    "shadowsocks-mirror",
    "trojan-global",
    "hysteria-fast",
    "reality-core",
    "tuic-relay",
    "wireguard-open",
    "sub-converter-tools",
    "anti-block-lab",
    "stay-connected",
]

GITVERSE_ORGS = [
    "gitverse-proxy",
    "gitverse-labs",
    "ru-netwatch",
    "svoboda-net",
    "obhod-blokirovok",
    "podpiski-ru",
    "free-vpn-gitverse",
    "anti-zapret-gitverse",
    "remain-connection",
    "nodes-archive",
]

PROTOCOLS = [
    "vless",
    "vmess",
    "shadowsocks",
    "trojan",
    "hysteria2",
    "tuic",
    "wireguard",
]

REGIONS = [
    "nl",
    "de",
    "fr",
    "fi",
    "se",
    "pl",
    "lt",
    "lv",
    "ee",
    "ro",
    "bg",
    "es",
    "it",
    "ch",
    "uk",
    "us",
    "ca",
    "sg",
    "jp",
    "kr",
]

NAME_CORES = [
    "alpha",
    "beta",
    "gamma",
    "delta",
    "omega",
    "nova",
    "zen",
    "core",
    "hub",
    "mirror",
    "relay",
    "gateway",
    "stream",
    "turbo",
    "secure",
    "ghost",
    "shadow",
    "wave",
    "pulse",
    "vector",
    "orbit",
    "quantum",
    "fusion",
    "matrix",
    "phoenix",
]

CONFIG_PATHS = [
    "sub.txt",
    "subscribe.txt",
    "subscription.txt",
    "subscriptions.txt",
    "v2ray.txt",
    "xray.txt",
    "nodes.txt",
    "proxy.txt",
    "proxies.txt",
    "list.txt",
    "clash.yaml",
    "clash.yml",
    "config.yaml",
    "config.yml",
    "sub.yaml",
    "subscription.yaml",
    "proxies.yaml",
    "mihomo.yaml",
    "sing-box.json",
    "wireguard.conf",
]

COMMIT_MESSAGES = [
    "auto: update nodes",
    "chore: daily refresh",
    "fix: remove dead endpoints",
    "feat: add new region",
    "perf: optimize proxy list",
    "update: refresh subscription",
    "merge: pull new configs",
    "sync: mirror from source",
    "cleanup: remove duplicates",
    "hotfix: replace blocked ip",
    "ci: automatic rebuild",
    "add: new protocol entries",
    "rotate: keys and endpoints",
    "revalidate: check bs/cs status",
    "patch: improve connectivity",
    "deploy: publish latest list",
    "scan: validate active nodes",
    "renew: expired certificates",
    "backup: snapshot subscription",
    "restore: working endpoints",
]

BS_KEYWORDS = [
    "whitelist",
    "white_list",
    "белый список",
    "белые списки",
    "bs",
    "bypass",
]


# =========================================================
# 2. Утилиты
# =========================================================

def iso_now():
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def iso_minutes_ago(minutes):
    dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=minutes)
    return dt.isoformat().replace("+00:00", "Z")


def make_fake_ip():
    return (
        f"{random.randint(45, 213)}."
        f"{random.randint(0, 255)}."
        f"{random.randint(0, 255)}."
        f"{random.randint(2, 254)}"
    )


def slugify(value):
    return (
        value.lower()
        .replace(" ", "-")
        .replace("_", "-")
        .replace(":", "-")
    )


# =========================================================
# 3. Генерация контента
# =========================================================

def make_content_sample(protocol, path, region):
    ip = make_fake_ip()
    port = random.choice([443, 8443, 2053, 2083, 2087, 2096, 8080, 8880])
    node_name = f"{region}-{random.randint(100, 999)}"

    if path and path.lower().endswith((".yaml", ".yml")):
        return "\n".join(
            [
                "proxies:",
                f"  - name: '{node_name}'",
                f"    type: {protocol if protocol != 'wireguard' else 'wireguard'}",
                f"    server: {ip}",
                f"    port: {port}",
                "    udp: true",
                "    tls: true",
                f"    # generated_sample_for_{node_name}",
            ]
        )

    if protocol == "wireguard":
        return "\n".join(
            [
                "[Interface]",
                f"PrivateKey = {node_name}FAKEKEY{random.randint(1000, 9999)}",
                f"Address = 10.0.0.{random.randint(2, 254)}/32",
                "DNS = 1.1.1.1, 8.8.8.8",
                "",
                "[Peer]",
                f"PublicKey = {node_name}FAKEPUBLICKEY{random.randint(1000, 9999)}",
                f"Endpoint = {ip}:{port}",
                "AllowedIPs = 0.0.0.0/0, ::/0",
            ]
        )

    if protocol == "vmess":
        return f"vmess://eyJ2IjoiMiIsInBzIjoibm9kZS17node_name}",
        # Оставим простой читаемый вариант, чтобы не ломать восприятие:
        return f"vmess://{node_name}@{ip}:{port}?network=tcp&security=tls"

    if protocol == "shadowsocks":
        return f"ss://cmM0LW1kNTpwYXNzd29yZA==@{ip}:{port}#{node_name}"

    if protocol == "trojan":
        return f"trojan://{node_name}@{ip}:{port}?security=tls&type=tcp#{node_name}"

    if protocol == "hysteria2":
        return f"hysteria2://{node_name}@{ip}:{port}?insecure=1#{node_name}"

    if protocol == "tuic":
        return f"tuic://{node_name}@{ip}:{port}?congestion_control=bbr#{node_name}"

    return f"{protocol}://{node_name}@{ip}:{port}?security=tls&type=tcp#{node_name}"


# =========================================================
# 4. Генерация одной подписки
# =========================================================

def generate_subscription(idx):
    # Источники: примерно каждый 7-й будет Gitverse
    source = "gitverse" if idx % 7 == 0 else "github"

    protocol = random.choice(PROTOCOLS)
    region = random.choice(REGIONS)
    core = random.choice(NAME_CORES)

    name = slugify(f"{core}-{protocol}-{region}-{idx:03d}")
    org = random.choice(GITVERSE_ORGS if source == "gitverse" else GITHUB_ORGS)
    repo_full = f"{org}/{name}"

    branch = random.choice(["main", "master"])

    # Обновление: свежие / средние / старые
    r = random.random()
    if r < 0.52:
        updated_mins_ago = random.randint(1, 240)
    elif r < 0.85:
        updated_mins_ago = random.randint(241, 4320)
    else:
        updated_mins_ago = random.randint(4321, 120000)

    # Есть ли конфиги
    has_configs = random.random() > 0.075
    configs_count = 0 if not has_configs else random.randint(6, 9800)

    # Путь к файлу подписки
    has_path = random.random() > 0.08
    config_path = random.choice(CONFIG_PATHS) if has_path else None

    # URL
    if source == "github":
        repo_url = f"https://github.com/{repo_full}"
    else:
        repo_url = f"https://gitverse.ru/{repo_full}"

    # subscription_url
    subscription_url = None
    if has_configs and config_path:
        if source == "github":
            subscription_url = f"https://raw.githubusercontent.com/{repo_full}/{branch}/{config_path}"
        else:
            subscription_url = f"https://gitverse.ru/{repo_full}/raw/branch/{branch}/{config_path}"

    # BS
    has_bs = False
    if has_configs:
        has_bs = random.random() < 0.44

    # Статус
    if configs_count <= 0:
        status = "unknown"
    elif updated_mins_ago > 20160:
        status = "stale"
    else:
        status = "active"

    # content_sample
    content_sample = None
    if has_configs:
        content_sample = make_content_sample(
            protocol=protocol,
            path=config_path or "sub.txt",
            region=region,
        )

    return {
        "id": idx,
        "name": name,
        "source": source,
        "source_label": "GitHub" if source == "github" else "Gitverse",
        "repo": repo_full,
        "url": repo_url,
        "subscription_url": subscription_url,
        "config_path": config_path,
        "protocol_hint": protocol,
        "region_hint": region,
        "updated_mins_ago": updated_mins_ago,
        "updated_iso": iso_minutes_ago(updated_mins_ago),
        "configs_count": configs_count,
        "has_bs": has_bs,
        "bs_label": "БС" if has_bs else "ЧС",
        "status": status,
        "health_score": random.randint(10, 100) if has_configs else 0,
        "last_commit_message": random.choice(COMMIT_MESSAGES),
        "content_sample": content_sample,
        "tags": [
            source,
            protocol,
            region,
            status,
            "bs" if has_bs else "cs",
        ],
    }


# =========================================================
# 5. Генерация итогового found.json
# =========================================================

def generate_payload(count):
    subscriptions = [
        generate_subscription(i)
        for i in range(1, count + 1)
    ]

    github_count = sum(1 for x in subscriptions if x["source"] == "github")
    gitverse_count = sum(1 for x in subscriptions if x["source"] == "gitverse")

    active_count = sum(1 for x in subscriptions if x["status"] == "active")
    stale_count = sum(1 for x in subscriptions if x["status"] == "stale")
    unknown_count = sum(1 for x in subscriptions if x["status"] == "unknown")

    bs_count = sum(1 for x in subscriptions if x["has_bs"])
    cs_count = len(subscriptions) - bs_count

    total_configs = sum(x["configs_count"] for x in subscriptions)

    top_by_configs = sorted(
        subscriptions,
        key=lambda x: x["configs_count"],
        reverse=True,
    )[:25]

    top_by_freshness = sorted(
        subscriptions,
        key=lambda x: x["updated_mins_ago"],
    )[:25]

    return {
        "generated_at": iso_now(),
        "generator": "generate_found.py",
        "schema_version": "1.0",
        "project": "REMAININGCONNECTIONS dashboard",
        "telegram_channel": "https://t.me/REMAININGCONNECTIONS",
        "candidates_found": len(subscriptions) * 17 + random.randint(111, 999),
        "probed_count": len(subscriptions),
        "summary": {
            "total_subscriptions": len(subscriptions),
            "github": github_count,
            "gitverse": gitverse_count,
            "active": active_count,
            "stale": stale_count,
            "unknown": unknown_count,
            "with_bs": bs_count,
            "without_bs": cs_count,
            "total_configs": total_configs,
        },
        "top_by_configs": [
            {
                "id": x["id"],
                "name": x["name"],
                "source": x["source"],
                "repo": x["repo"],
                "configs_count": x["configs_count"],
                "updated_mins_ago": x["updated_mins_ago"],
                "has_bs": x["has_bs"],
                "status": x["status"],
            }
            for x in top_by_configs
        ],
        "top_by_freshness": [
            {
                "id": x["id"],
                "name": x["name"],
                "source": x["source"],
                "repo": x["repo"],
                "updated_mins_ago": x["updated_mins_ago"],
                "configs_count": x["configs_count"],
                "has_bs": x["has_bs"],
                "status": x["status"],
            }
            for x in top_by_freshness
        ],
        "subscriptions": subscriptions,
    }


# =========================================================
# 6. CLI
# =========================================================

def main():
    parser = argparse.ArgumentParser(
        description="Генератор массивного found.json для дашборда подписок."
    )

    parser.add_argument(
        "--count",
        type=int,
        default=300,
        help="Сколько подписок сгенерировать (по умолчанию 300)",
    )

    parser.add_argument(
        "--output",
        type=str,
        default="data/found.json",
        help="Куда сохранить файл (по умолчанию data/found.json)",
    )

    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Seed для рандома, чтобы данные были воспроизводимыми",
    )

    args = parser.parse_args()

    random.seed(args.seed)

    payload = generate_payload(args.count)

    output_path = os.path.abspath(args.output)
    output_dir = os.path.dirname(output_path)

    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    file_size = os.path.getsize(output_path)

    print("==================================================")
    print(" found.json успешно сгенерирован")
    print("==================================================")
    print(f"Файл: {output_path}")
    print(f"Подписок: {args.count}")
    print(f"Размер: {file_size / 1024:.2f} KB")
    print("==================================================")


if __name__ == "__main__":
    main()