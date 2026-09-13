#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
generate_search_queries.py

Автогенератор поисковых запросов для проекта мониторинга:
- подписок;
- ТГ-прокси;
- Open Source утилит;
- конкретного целевого репозитория.

Примеры запуска:

    python scripts/generate_search_queries.py

    python scripts/generate_search_queries.py \
        --target Throne \
        --target-aliases throne-proxy throne-client throne-vpn

    python scripts/generate_search_queries.py \
        --output-dir .github/generated \
        --max-repo-queries 1200 \
        --max-code-queries 700 \
        --max-topic-queries 300 \
        --max-gitverse-queries 700

Результаты:
    .github/generated/queries.json
    .github/generated/matrix_subscriptions_repo.json
    .github/generated/matrix_tg_proxies_repo.json
    .github/generated/matrix_utilities_repo.json
    .github/generated/queries_subscriptions_repo.yaml
    .github/generated/queries_tg_proxies_repo.yaml
    .github/generated/queries_utilities_repo.yaml
    и т.д.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
from collections import Counter


# =========================================================
# 1. Базовые словари и константы
# =========================================================

SUB_PROTOCOLS = [
    "vless",
    "vmess",
    "xray",
    "reality",
    "sing-box",
    "singbox",
    "clash",
    "clash-meta",
    "mihomo",
    "shadowsocks",
    "shadowsocks-rust",
    "trojan",
    "trojan-go",
    "hysteria",
    "hysteria2",
    "hy2",
    "tuic",
    "wireguard",
]

SUB_SCHEMES = [
    "vless://",
    "vmess://",
    "ss://",
    "trojan://",
    "hysteria2://",
    "hy2://",
    "tuic://",
]

TG_PROTOCOLS = [
    "mtproto",
    "mtproxy",
    "telegram proxy",
    "tg proxy",
    "t.me/proxy",
    "tg://proxy",
    "mtproto secret",
    "mtproxy secret",
]

UTIL_PROTOCOLS = [
    "v2ray",
    "xray",
    "vless",
    "vmess",
    "sing-box",
    "singbox",
    "clash",
    "clash-meta",
    "mihomo",
    "shadowsocks",
    "trojan",
    "hysteria",
    "hysteria2",
    "tuic",
    "wireguard",
]

UTIL_TOOLS = [
    "v2rayn",
    "v2rayng",
    "nekoray",
    "nekobox",
    "hiddify",
    "clash-verge",
    "clash-nyanpasu",
    "flclash",
    "sing-box-gui",
    "sing-box-client",
    "box4proxy",
    "streisand",
    "karing",
    "shadowrocket",
    "amnezia-vpn",
    "outline-client",
    "matsuridayo",
    "clashx",
    "v2ray-desktop",
    "geph",
    "psiphon",
    "hysteria-client",
]

PLATFORMS = [
    "android",
    "ios",
    "iphone",
    "ipad",
    "windows",
    "linux",
    "ubuntu",
    "debian",
    "fedora",
    "arch",
    "macos",
    "desktop",
    "mobile",
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
    "eu",
    "asia",
    "global",
]

SUB_INTENTS_EN = [
    "subscription",
    "subscriptions",
    "sub",
    "subs",
    "node list",
    "nodes",
    "free nodes",
    "proxy list",
    "config list",
    "aggregator",
    "aggregation",
    "collector",
    "mirror",
    "archive",
    "daily update",
    "auto update",
]

SUB_INTENTS_RU = [
    "подписка",
    "подписки",
    "подписка прокси",
    "подписка vpn",
    "узлы",
    "бесплатные узлы",
    "конфиги",
    "конфигурации",
    "обход блокировок",
    "остаться на связи",
    "рабочие подписки",
    "актуальные подписки",
]

TG_INTENTS_EN = [
    "proxy",
    "proxies",
    "telegram proxy",
    "tg proxy",
    "mtproto proxy",
    "mtproxy list",
    "proxy list",
    "free proxy",
    "secret",
    "server port secret",
    "tg link",
    "tg links",
]

TG_INTENTS_RU = [
    "телеграм прокси",
    "тг прокси",
    "мтпрокси",
    "мтпрото",
    "прокси телеграм",
    "прокси список",
    "бесплатный прокси",
    "секрет",
    "остаться на связи",
]

UTIL_INTENTS_EN = [
    "client",
    "gui",
    "ui",
    "app",
    "application",
    "manager",
    "dashboard",
    "desktop",
    "mobile",
    "cross platform",
    "open source",
    "release",
    "releases",
    "binary",
    "binaries",
]

UTIL_INTENTS_RU = [
    "клиент",
    "приложение",
    "программа",
    "интерфейс",
    "менеджер",
    "панель",
    "утилита",
    "утилиты",
    "обход блокировок",
]

SUB_FILENAMES = [
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
    "sub.yml",
    "subscription.yaml",
    "subscription.yml",
    "proxies.yaml",
    "proxies.yml",
    "mihomo.yaml",
    "mihomo.yml",
    "sing-box.json",
    "singbox.json",
    "wireguard.conf",
    "wg.conf",
]

TG_FILENAMES = [
    "mtproxy.txt",
    "mtproxy-list.txt",
    "mtproto.txt",
    "tg-proxy.txt",
    "tg-proxies.txt",
    "telegram-proxy.txt",
    "telegram-proxies.txt",
    "proxy.txt",
    "proxies.txt",
    "proxy-list.txt",
    "list.txt",
    "tg.txt",
    "tg.md",
    "proxy.md",
    "proxies.md",
    "mtproxy.md",
    "mtproto.md",
    "README.md",
    "free-tg-proxy.txt",
    "tg-proxy.json",
    "mtproxy.json",
    "mtproto.json",
    "proxy.yaml",
    "proxies.yaml",
]

UTIL_FILENAMES = [
    "README.md",
    "RELEASE.md",
    "CHANGELOG.md",
    "package.json",
    "pubspec.yaml",
    "build.gradle",
    "build.gradle.kts",
    "Cargo.toml",
    "go.mod",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "CMakeLists.txt",
]

TOPICS = [
    "v2ray",
    "xray",
    "vless",
    "vmess",
    "reality",
    "sing-box",
    "singbox",
    "clash",
    "clash-meta",
    "mihomo",
    "shadowsocks",
    "shadowsocks-rust",
    "trojan",
    "hysteria",
    "hysteria2",
    "tuic",
    "wireguard",
    "censorship-circumvention",
    "anti-censorship",
    "gfw",
    "circumvention",
]

SUB_TOPICS = [
    "v2ray",
    "xray",
    "vless",
    "vmess",
    "reality",
    "sing-box",
    "singbox",
    "clash",
    "clash-meta",
    "mihomo",
    "shadowsocks",
    "trojan",
    "hysteria",
    "hysteria2",
    "tuic",
    "wireguard",
    "v2ray-subscription",
    "clash-subscription",
    "free-nodes",
    "proxy-subscription",
    "subscription",
    "subscriptions",
    "censorship-circumvention",
    "anti-censorship",
]

TG_TOPICS = [
    "mtproto",
    "mtproxy",
    "telegram-proxy",
    "tg-proxy",
    "mtproto-proxy",
]

UTIL_TOPICS = [
    "v2ray",
    "xray",
    "vless",
    "vmess",
    "sing-box",
    "singbox",
    "clash",
    "clash-meta",
    "mihomo",
    "shadowsocks",
    "trojan",
    "hysteria",
    "hysteria2",
    "tuic",
    "wireguard",
    "censorship-circumvention",
    "anti-censorship",
    "gfw",
    "v2ray-client",
    "clash-client",
    "sing-box-client",
    "shadowsocks-client",
    "proxy-client",
    "vpn-client",
    "proxy-gui",
    "nekoray",
    "nekobox",
    "hiddify",
    "v2rayn",
    "v2rayng",
    "clash-verge",
    "clash-nyanpasu",
    "flclash",
    "box4proxy",
    "karing",
]

LANGUAGES = [
    "Go",
    "Python",
    "Kotlin",
    "Dart",
    "TypeScript",
    "JavaScript",
    "C#",
    "C++",
    "Rust",
    "Java",
    "Swift",
    "Shell",
]

STAR_FILTERS = [
    "stars:>5",
    "stars:>20",
    "stars:>100",
    "stars:>500",
    "stars:>1000",
]

RECENT_DAYS = [
    7,
    30,
    90,
    180,
    365,
]

STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "this",
    "that",
    "are",
    "was",
    "were",
    "not",
    "you",
    "your",
    "our",
    "out",
    "new",
    "file",
    "files",
    "update",
    "updated",
    "github",
    "gitverse",
    "http",
    "https",
    "html",
    "json",
    "yaml",
    "yml",
    "txt",
    "readme",
    "null",
    "true",
    "false",
    "config",
    "configs",
    "configuration",
    "proxy",
    "proxies",
    "vpn",
    "subscription",
    "subscriptions",
    "sub",
    "client",
    "clients",
    "server",
    "servers",
    "list",
    "lists",
    "free",
    "node",
    "nodes",
}

HARVEST_KEYS = {
    "name",
    "repo",
    "full_name",
    "description",
    "topics",
    "platform_labels",
    "protocol_hint",
    "region_hint",
    "query_slug",
    "last_commit_message",
    "secret_type",
}

WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{2,}|[А-Яа-яЁё]{3,}")


# =========================================================
# 2. Утилиты
# =========================================================

def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def make_query_id(query: str) -> str:
    return hashlib.md5(query.encode("utf-8")).hexdigest()[:12]


def normalize_for_dedupe(query: str) -> str:
    return collapse_spaces(query.lower())


def build_query(*parts) -> str:
    cleaned = []

    for part in parts:
        if not part:
            continue

        if isinstance(part, (list, tuple, set)):
            part = " ".join(str(x) for x in part if x)

        part = collapse_spaces(str(part))

        if part:
            cleaned.append(part)

    return collapse_spaces(" ".join(cleaned))


def safe_int(val, default: int) -> int:
    try:
        if val is None or str(val).strip() == "":
            return default
        return int(val)
    except (ValueError, TypeError):
        return default


def make_entry(category: str, qtype: str, query: str, priority: int, reason: str, qualifiers=None) -> dict:
    query = collapse_spaces(query)

    if not query:
        return None

    qualifiers = qualifiers or []

    full_query_parts = [query]

    if qualifiers:
        full_query_parts.extend(qualifiers)

    full_query = collapse_spaces(" ".join(full_query_parts))

    return {
        "id": make_query_id(full_query),
        "category": category,
        "type": qtype,
        "query": query,
        "full_query": full_query,
        "qualifiers": qualifiers,
        "priority": int(priority),
        "reason": reason,
    }


def finalize_entries(entries, limit: int, category: str, qtype: str):
    seen = set()
    unique = []

    for entry in entries:
        if not entry:
            continue

        key = normalize_for_dedupe(entry["full_query"])

        if key in seen:
            continue

        seen.add(key)
        unique.append(entry)

    # Небольшой шум для разнообразия при одинаковом приоритете
    for entry in unique:
        entry["_noise"] = random.random()

    unique.sort(
        key=lambda x: (
            x["priority"],
            x["_noise"],
        ),
        reverse=True,
    )

    if limit > 0 and len(unique) > limit:
        unique = unique[:limit]

    result = []

    for idx, entry in enumerate(unique, start=1):
        entry.pop("_noise", None)
        entry["slug"] = f"{category}-{qtype}-{idx:04d}"
        result.append(entry)

    return result


# =========================================================
# 3. Автоадаптация по уже найденным данным
# =========================================================

JUNK_TERMS = {
    # File formats & packaging
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx",
    "tar", "gz", "tgz", "zip", "7z", "rar", "bz2", "xz", "zst",
    "dmg", "pkg", "deb", "rpm", "apk", "exe", "msi", "appimage", "iso", "img", "bin",
    "dvd", "rom", "dylib", "dll", "so", "aar",
    "sha256", "sha512", "md5", "sig", "asc", "blockmap",
    # Programming languages & web dev noise
    "javascript", "typescript", "python", "html", "css", "scss",
    "java", "rust", "react", "vue", "angular", "photoshop", "excel",
    "autocad", "cad", "claude", "mcp", "llm", "agent", "agents",
    "antigravity", "electron", "hacktoberfest", "docker", "nodejs",
    "api", "cli", "terminal", "pro", "tool", "framework",
    # Arch noise
    "amd64", "arm64", "aarch64", "x86_64", "x86", "i386", "armv7",
    "linux_amd64", "linux-arm64", "linux-x86_64",
    # Generic descriptors that lead to broad non-proxy queries
    "web", "app", "apps", "desktop", "mobile", "manager", "dashboard", "gui",
    "release", "releases", "binary", "binaries", "cross-platform", "open-source",
    "linux", "windows", "macos", "android", "ios", "native", "data", "code",
    "visual", "more", "security", "self-hosted", "application",
}


def harvest_value(value, counter: Counter):
    if value is None:
        return

    if isinstance(value, str):
        words = WORD_RE.findall(value.lower())

        for word in words:
            word = word.strip()

            if len(word) < 3 or len(word) > 24:
                continue

            if word in STOPWORDS or word in JUNK_TERMS:
                continue

            # Skip words with numbers unless recognized protocols/versions
            if any(char.isdigit() for char in word) and word not in {"hy2", "hysteria2", "socks5", "v2ray", "trojan-go"}:
                continue

            counter[word] += 1

    elif isinstance(value, (list, tuple, set)):
        for item in value:
            harvest_value(item, counter)


def harvest_terms_from_json(obj, counter: Counter):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in HARVEST_KEYS:
                harvest_value(value, counter)
            else:
                harvest_terms_from_json(value, counter)

    elif isinstance(obj, list):
        for item in obj:
            harvest_terms_from_json(item, counter)


def load_adaptive_terms(paths, top_n: int = 80):
    counter = Counter()

    for path in paths:
        if not path:
            continue

        if not os.path.exists(path):
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            harvest_terms_from_json(data, counter)
            print(f"[+] Harvested terms from: {path}")
        except Exception as e:
            print(f"[!] Failed to harvest {path}: {e}")

    terms = [word for word, _ in counter.most_common(top_n)]
    print(f"[+] Adaptive terms loaded: {len(terms)}")

    return terms


# =========================================================
# 4. Генерация запросов для целевого репозитория
# =========================================================

def generate_target_queries(target: str, aliases=None):
    entries = []

    if not target:
        return entries

    aliases = aliases or []

    variants = set()

    base = collapse_spaces(target)

    if base:
        variants.add(base)
        variants.add(base.lower())
        variants.add(base.upper())
        variants.add(base.replace(" ", "-"))
        variants.add(base.replace(" ", "_"))
        variants.add(base.replace(" ", ""))
        variants.add(base.replace("-", " "))
        variants.add(base.replace("_", " "))

    for alias in aliases:
        alias = collapse_spaces(alias)

        if not alias:
            continue

        variants.add(alias)
        variants.add(alias.lower())
        variants.add(alias.replace(" ", "-"))
        variants.add(alias.replace(" ", "_"))
        variants.add(alias.replace(" ", ""))

    variants = sorted(variants)

    for variant in variants:
        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f'"{variant}" in:name',
                priority=100,
                reason="target exact name",
                qualifiers=["fork:true", "archived:false"],
            )
        )

        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f'"{variant}" in:name,description,readme',
                priority=98,
                reason="target name/description/readme",
                qualifiers=["fork:true", "archived:false"],
            )
        )

        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f'"{variant}" mirror',
                priority=95,
                reason="target mirror",
                qualifiers=["fork:true", "archived:false"],
            )
        )

        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f'"{variant}" fork',
                priority=90,
                reason="target fork",
                qualifiers=["fork:true", "archived:false"],
            )
        )

        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f'"{variant}" alternative',
                priority=85,
                reason="target alternative",
                qualifiers=["fork:true", "archived:false"],
            )
        )

        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f'"{variant}" release',
                priority=80,
                reason="target release",
                qualifiers=["fork:true", "archived:false"],
            )
        )

        entries.append(
            make_entry(
                category="target",
                qtype="code",
                query=f'"{variant}"',
                priority=92,
                reason="target code mention",
            )
        )

    # Если target указан как owner/repo
    if "/" in base:
        owner, repo = base.split("/", 1)

        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f"user:{owner}",
                priority=99,
                reason="target owner",
                qualifiers=["fork:true", "archived:false"],
            )
        )

        entries.append(
            make_entry(
                category="target",
                qtype="repo",
                query=f"{owner} {repo}",
                priority=99,
                reason="target owner repo",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    return finalize_entries(entries, limit=500, category="target", qtype="mixed")


# =========================================================
# 5. Генерация запросов для подписок
# =========================================================

def generate_subscription_repo_queries(extra_terms=None, target_terms=None):
    entries = []
    extra_terms = extra_terms or []
    target_terms = target_terms or []

    all_protocols = SUB_PROTOCOLS[:]

    # Протокол + назначение
    for protocol in all_protocols:
        for intent in SUB_INTENTS_EN:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(protocol, intent),
                    priority=92,
                    reason="protocol+intent",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

        for intent in SUB_INTENTS_RU:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(protocol, intent),
                    priority=88,
                    reason="protocol+ru-intent",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    # Протокол + платформа
    for protocol in all_protocols:
        for platform in PLATFORMS:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(protocol, platform, "subscription"),
                    priority=84,
                    reason="protocol+platform",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    # Протокол + регион
    for protocol in all_protocols[:12]:
        for region in REGIONS:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(protocol, region, "nodes"),
                    priority=70,
                    reason="protocol+region",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    # Ру-сегмент
    for intent in SUB_INTENTS_RU:
        for word in ["остаться на связи", "обход блокировок", "рабочие подписки"]:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(intent, word),
                    priority=82,
                    reason="ru intent",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    # Свежие репозитории
    now = dt.datetime.utcnow()

    for days in RECENT_DAYS:
        date = (now - dt.timedelta(days=days)).strftime("%Y-%m-%d")

        for protocol in all_protocols[:14]:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(protocol, "subscription", f"pushed:>{date}"),
                    priority=80,
                    reason=f"recent {days} days",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    # Звездность
    for star in STAR_FILTERS:
        for protocol in all_protocols[:12]:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(protocol, "subscription", star),
                    priority=65,
                    reason="stars filter",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    # Языки
    for protocol in all_protocols[:10]:
        for language in LANGUAGES:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="repo",
                    query=build_query(protocol, f"language:{language}"),
                    priority=45,
                    reason="protocol+language",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    # Адаптивные термины
    for term in extra_terms:
        entries.append(
            make_entry(
                category="subscriptions",
                qtype="repo",
                query=build_query(term, "subscription"),
                priority=60,
                reason="adaptive term",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    # Целевые термины
    for term in target_terms:
        entries.append(
            make_entry(
                category="subscriptions",
                qtype="repo",
                query=build_query(term, "subscription"),
                priority=97,
                reason="target term",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    return entries


def generate_subscription_code_queries(extra_terms=None):
    entries = []
    extra_terms = extra_terms or []

    # Direct URI schemes (highest signal for free nodes/subs)
    for scheme in SUB_SCHEMES:
        entries.append(
            make_entry(
                category="subscriptions",
                qtype="code",
                query=scheme,
                priority=98,
                reason="direct uri scheme",
            )
        )
        for fn in ["sub.txt", "nodes.txt", "list.txt", "clash.yaml", "sing-box.json"]:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="code",
                    query=f"{scheme} filename:{fn}",
                    priority=95,
                    reason="scheme+filename",
                )
            )

    # Specific protocol + filename
    for proto in SUB_PROTOCOLS:
        for filename in SUB_FILENAMES:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="code",
                    query=build_query(proto, f"filename:{filename}"),
                    priority=86,
                    reason="proto+filename",
                )
            )

    # Adaptive terms + subscription filenames
    for term in extra_terms[:20]:
        for fn in ["sub.txt", "nodes.txt", "config.yaml", "clash.yaml"]:
            entries.append(
                make_entry(
                    category="subscriptions",
                    qtype="code",
                    query=build_query(term, f"filename:{fn}"),
                    priority=75,
                    reason="adaptive+filename",
                )
            )

    return entries


def generate_subscription_topic_queries():
    entries = []

    for topic in SUB_TOPICS:
        entries.append(
            make_entry(
                category="subscriptions",
                qtype="topic",
                query=f"topic:{topic}",
                priority=80,
                reason="topic",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    return entries


def generate_subscription_gitverse_queries(extra_terms=None):
    entries = []
    extra_terms = extra_terms or []

    base_terms = SUB_PROTOCOLS + SUB_INTENTS_EN + SUB_INTENTS_RU + extra_terms

    for term in base_terms:
        entries.append(
            make_entry(
                category="subscriptions",
                qtype="gitverse",
                query=term,
                priority=75,
                reason="gitverse term",
            )
        )

    return entries


# =========================================================
# 6. Генерация запросов для ТГ-прокси
# =========================================================

def generate_tg_proxy_repo_queries(extra_terms=None, target_terms=None):
    entries = []
    extra_terms = extra_terms or []
    target_terms = target_terms or []

    terms = TG_PROTOCOLS + TG_INTENTS_EN + TG_INTENTS_RU

    for term in terms:
        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="repo",
                query=build_query(term),
                priority=90,
                reason="tg base term",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    for proto in TG_PROTOCOLS:
        for intent in TG_INTENTS_EN:
            entries.append(
                make_entry(
                    category="tg_proxies",
                    qtype="repo",
                    query=build_query(proto, intent),
                    priority=92,
                    reason="tg proto+intent",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    for proto in TG_PROTOCOLS:
        for intent in TG_INTENTS_RU:
            entries.append(
                make_entry(
                    category="tg_proxies",
                    qtype="repo",
                    query=build_query(proto, intent),
                    priority=86,
                    reason="tg proto+ru",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    for region in REGIONS:
        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="repo",
                query=build_query("mtproxy", region),
                priority=72,
                reason="tg region",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    now = dt.datetime.utcnow()

    for days in RECENT_DAYS:
        date = (now - dt.timedelta(days=days)).strftime("%Y-%m-%d")

        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="repo",
                query=build_query("mtproxy OR mtproto", f"pushed:>{date}"),
                priority=80,
                reason=f"tg recent {days} days",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    for term in extra_terms:
        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="repo",
                query=build_query(term, "proxy"),
                priority=60,
                reason="adaptive",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    for term in target_terms:
        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="repo",
                query=build_query(term, "proxy"),
                priority=96,
                reason="target",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    return entries


def generate_tg_proxy_code_queries(extra_terms=None):
    entries = []
    extra_terms = extra_terms or []

    patterns = [
        "tg://proxy",
        "t.me/proxy",
        "https://t.me/proxy",
        "tg://proxy?server",
        "t.me/proxy?server",
        "server port secret mtproto",
        "mtproxy secret",
        "mtproto secret",
        "dd secret telegram",
        "ee secret mtproto",
    ]

    for pattern in patterns:
        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="code",
                query=pattern,
                priority=95,
                reason="tg exact pattern",
            )
        )

    tg_specific_terms = [
        "mtproto",
        "mtproxy",
        "telegram proxy",
        "tg proxy",
        "t.me/proxy",
        "tg://proxy",
    ]

    for term in tg_specific_terms:
        for filename in TG_FILENAMES:
            entries.append(
                make_entry(
                    category="tg_proxies",
                    qtype="code",
                    query=build_query(term, f"filename:{filename}"),
                    priority=88,
                    reason="tg term+filename",
                )
            )

    return entries


def generate_tg_proxy_topic_queries():
    entries = []

    for topic in TG_TOPICS:
        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="topic",
                query=f"topic:{topic}",
                priority=85,
                reason="tg topic",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    return entries


def generate_tg_proxy_gitverse_queries(extra_terms=None):
    entries = []
    extra_terms = extra_terms or []

    terms = TG_PROTOCOLS + TG_INTENTS_EN + TG_INTENTS_RU + extra_terms

    for term in terms:
        entries.append(
            make_entry(
                category="tg_proxies",
                qtype="gitverse",
                query=term,
                priority=75,
                reason="gitverse tg term",
            )
        )

    return entries


# =========================================================
# 7. Генерация запросов для утилит
# =========================================================

def generate_utilities_repo_queries(extra_terms=None, target_terms=None):
    entries = []
    extra_terms = extra_terms or []
    target_terms = target_terms or []

    # Known circumvention clients and tools
    for tool in UTIL_TOOLS:
        entries.append(
            make_entry(
                category="utilities",
                qtype="repo",
                query=build_query(tool),
                priority=96,
                reason="util known tool",
                qualifiers=["fork:true", "archived:false"],
            )
        )
        for intent in ["client", "gui", "release"]:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="repo",
                    query=build_query(tool, intent),
                    priority=93,
                    reason="util tool+intent",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    for protocol in UTIL_PROTOCOLS:
        for intent in UTIL_INTENTS_EN:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="repo",
                    query=build_query(protocol, intent),
                    priority=92,
                    reason="util proto+intent",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

        for intent in UTIL_INTENTS_RU:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="repo",
                    query=build_query(protocol, intent),
                    priority=85,
                    reason="util proto+ru",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    for protocol in UTIL_PROTOCOLS:
        for platform in PLATFORMS:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="repo",
                    query=build_query(protocol, platform, "client"),
                    priority=90,
                    reason="util proto+platform",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    for star in STAR_FILTERS:
        for protocol in UTIL_PROTOCOLS[:12]:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="repo",
                    query=build_query(protocol, "client", star),
                    priority=70,
                    reason="util stars",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    now = dt.datetime.utcnow()

    for days in RECENT_DAYS:
        date = (now - dt.timedelta(days=days)).strftime("%Y-%m-%d")

        for protocol in UTIL_PROTOCOLS[:12]:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="repo",
                    query=build_query(protocol, "client", f"pushed:>{date}"),
                    priority=78,
                    reason=f"util recent {days} days",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    for language in LANGUAGES:
        for protocol in UTIL_PROTOCOLS[:10]:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="repo",
                    query=build_query(protocol, f"language:{language}"),
                    priority=50,
                    reason="util language",
                    qualifiers=["fork:true", "archived:false"],
                )
            )

    for term in extra_terms:
        entries.append(
            make_entry(
                category="utilities",
                qtype="repo",
                query=build_query(term, "client"),
                priority=62,
                reason="adaptive util",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    for term in target_terms:
        entries.append(
            make_entry(
                category="utilities",
                qtype="repo",
                query=build_query(term),
                priority=98,
                reason="target util",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    return entries


def generate_utilities_code_queries(extra_terms=None):
    entries = []
    extra_terms = extra_terms or []

    # Require tool or protocol to avoid generic code searches
    targets = UTIL_TOOLS[:15] + [f"{p} client" for p in UTIL_PROTOCOLS[:10]] + [f"{p} gui" for p in UTIL_PROTOCOLS[:10]]
    for target in targets:
        for filename in ["README.md", "package.json", "Cargo.toml", "go.mod", "pubspec.yaml", "build.gradle"]:
            entries.append(
                make_entry(
                    category="utilities",
                    qtype="code",
                    query=build_query(target, f"filename:{filename}"),
                    priority=75,
                    reason="util target+filename",
                )
            )

    return entries


def generate_utilities_topic_queries():
    entries = []

    for topic in UTIL_TOPICS:
        entries.append(
            make_entry(
                category="utilities",
                qtype="topic",
                query=f"topic:{topic}",
                priority=82,
                reason="util topic",
                qualifiers=["fork:true", "archived:false"],
            )
        )

    return entries


def generate_utilities_gitverse_queries(extra_terms=None):
    entries = []
    extra_terms = extra_terms or []

    terms = UTIL_PROTOCOLS + UTIL_INTENTS_EN + UTIL_INTENTS_RU + extra_terms

    for term in terms:
        entries.append(
            make_entry(
                category="utilities",
                qtype="gitverse",
                query=term,
                priority=72,
                reason="gitverse util term",
            )
        )

    return entries


# =========================================================
# 8. Запись результатов
# =========================================================

def write_json(path: str, payload: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"[+] Saved JSON: {path}")


def write_txt(path: str, entries):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for entry in entries:
            f.write(entry["full_query"] + "\n")

    print(f"[+] Saved TXT: {path}")


def write_yaml(path: str, entries):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    lines = [
        "# Auto-generated search queries",
        "# Do not edit manually if generated by CI.",
        "queries:",
    ]

    for entry in entries:
        lines.append(f"  - slug: {json.dumps(entry['slug'], ensure_ascii=False)}")
        lines.append(f"    query: {json.dumps(entry['query'], ensure_ascii=False)}")
        lines.append(f"    full_query: {json.dumps(entry['full_query'], ensure_ascii=False)}")
        lines.append(f"    category: {json.dumps(entry['category'], ensure_ascii=False)}")
        lines.append(f"    type: {json.dumps(entry['type'], ensure_ascii=False)}")
        lines.append(f"    priority: {entry['priority']}")
        lines.append(f"    reason: {json.dumps(entry['reason'], ensure_ascii=False)}")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[+] Saved YAML: {path}")


def write_matrix_json(path: str, entries):
    matrix = []

    for entry in entries:
        matrix.append({
            "slug": entry["slug"],
            "query": entry["query"],
            "full_query": entry["full_query"],
            "priority": entry["priority"],
            "reason": entry["reason"],
        })

    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(matrix, f, ensure_ascii=False, indent=2)

    print(f"[+] Saved matrix JSON: {path}")


# =========================================================
# 9. Основной генератор
# =========================================================

def generate_all(args):
    random.seed(args.seed)

    adaptive_terms = load_adaptive_terms(args.existing_data, top_n=args.adaptive_terms)

    target_terms = []

    if args.target:
        target_terms = [args.target]

        if args.target_aliases:
            target_terms.extend(args.target_aliases)

    # TARGET
    target_entries = generate_target_queries(args.target, args.target_aliases or [])

    # SUBSCRIPTIONS
    sub_repo_raw = generate_subscription_repo_queries(adaptive_terms, target_terms)
    sub_code_raw = generate_subscription_code_queries(adaptive_terms)
    sub_topic_raw = generate_subscription_topic_queries()
    sub_gitverse_raw = generate_subscription_gitverse_queries(adaptive_terms)

    sub_repo = finalize_entries(sub_repo_raw, args.max_repo_queries, "subscriptions", "repo")
    sub_code = finalize_entries(sub_code_raw, args.max_code_queries, "subscriptions", "code")
    sub_topic = finalize_entries(sub_topic_raw, args.max_topic_queries, "subscriptions", "topic")
    sub_gitverse = finalize_entries(sub_gitverse_raw, args.max_gitverse_queries, "subscriptions", "gitverse")

    # TG PROXIES
    tg_repo_raw = generate_tg_proxy_repo_queries(adaptive_terms, target_terms)
    tg_code_raw = generate_tg_proxy_code_queries(adaptive_terms)
    tg_topic_raw = generate_tg_proxy_topic_queries()
    tg_gitverse_raw = generate_tg_proxy_gitverse_queries(adaptive_terms)

    tg_repo = finalize_entries(tg_repo_raw, args.max_repo_queries, "tg_proxies", "repo")
    tg_code = finalize_entries(tg_code_raw, args.max_code_queries, "tg_proxies", "code")
    tg_topic = finalize_entries(tg_topic_raw, args.max_topic_queries, "tg_proxies", "topic")
    tg_gitverse = finalize_entries(tg_gitverse_raw, args.max_gitverse_queries, "tg_proxies", "gitverse")

    # UTILITIES
    util_repo_raw = generate_utilities_repo_queries(adaptive_terms, target_terms)
    util_code_raw = generate_utilities_code_queries(adaptive_terms)
    util_topic_raw = generate_utilities_topic_queries()
    util_gitverse_raw = generate_utilities_gitverse_queries(adaptive_terms)

    util_repo = finalize_entries(util_repo_raw, args.max_repo_queries, "utilities", "repo")
    util_code = finalize_entries(util_code_raw, args.max_code_queries, "utilities", "code")
    util_topic = finalize_entries(util_topic_raw, args.max_topic_queries, "utilities", "topic")
    util_gitverse = finalize_entries(util_gitverse_raw, args.max_gitverse_queries, "utilities", "gitverse")

    payload = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "generator": "generate_search_queries.py",
        "target": args.target,
        "target_aliases": args.target_aliases or [],
        "adaptive_terms": adaptive_terms,
        "categories": {
            "target": {
                "mixed": target_entries,
            },
            "subscriptions": {
                "repo": sub_repo,
                "code": sub_code,
                "topic": sub_topic,
                "gitverse": sub_gitverse,
            },
            "tg_proxies": {
                "repo": tg_repo,
                "code": tg_code,
                "topic": tg_topic,
                "gitverse": tg_gitverse,
            },
            "utilities": {
                "repo": util_repo,
                "code": util_code,
                "topic": util_topic,
                "gitverse": util_gitverse,
            },
        },
        "summary": {
            "target": len(target_entries),
            "subscriptions_repo": len(sub_repo),
            "subscriptions_code": len(sub_code),
            "subscriptions_topic": len(sub_topic),
            "subscriptions_gitverse": len(sub_gitverse),
            "tg_proxies_repo": len(tg_repo),
            "tg_proxies_code": len(tg_code),
            "tg_proxies_topic": len(tg_topic),
            "tg_proxies_gitverse": len(tg_gitverse),
            "utilities_repo": len(util_repo),
            "utilities_code": len(util_code),
            "utilities_topic": len(util_topic),
            "utilities_gitverse": len(util_gitverse),
        },
    }

    return payload


# =========================================================
# 10. CLI
# =========================================================

def main():
    parser = argparse.ArgumentParser(
        description="Автогенератор поисковых запросов для GitHub/Gitverse."
    )

    parser.add_argument(
        "--output-dir",
        default=".github/generated",
        help="Куда сохранять сгенерированные файлы",
    )

    parser.add_argument(
        "--target",
        default="",
        help="Целевой репозиторий или проект, например: Throne или owner/repo",
    )

    parser.add_argument(
        "--target-aliases",
        nargs="*",
        default=[],
        help="Дополнительные варианты имени целевого проекта",
    )

    parser.add_argument(
        "--existing-data",
        nargs="*",
        default=[
            "data/subscriptions_found.json",
            "data/found.json",
            "data/tg_proxies_found.json",
            "data/utils_found.json",
        ],
        help="JSON-файлы, из которых можно вытащить адаптивные ключевые слова",
    )

    parser.add_argument(
        "--adaptive-terms",
        type=lambda v: safe_int(v, 80),
        default=80,
        help="Сколько адаптивных терминов брать из существующих данных",
    )

    parser.add_argument(
        "--max-repo-queries",
        type=lambda v: safe_int(v, 900),
        default=900,
        help="Лимит запросов для репозиториев на категорию",
    )

    parser.add_argument(
        "--max-code-queries",
        type=lambda v: safe_int(v, 600),
        default=600,
        help="Лимит запросов для кода на категорию",
    )

    parser.add_argument(
        "--max-topic-queries",
        type=lambda v: safe_int(v, 250),
        default=250,
        help="Лимит запросов для тем",
    )

    parser.add_argument(
        "--max-gitverse-queries",
        type=lambda v: safe_int(v, 600),
        default=600,
        help="Лимит запросов для Gitverse",
    )

    parser.add_argument(
        "--seed",
        type=lambda v: safe_int(v, 1337),
        default=1337,
        help="Seed для воспроизводимой генерации",
    )

    args = parser.parse_args()

    print("==================================================")
    print(" Search Query Generator")
    print("==================================================")

    payload = generate_all(args)

    output_dir = args.output_dir

    os.makedirs(output_dir, exist_ok=True)

    # Общий JSON
    write_json(os.path.join(output_dir, "queries.json"), payload)

    # Целевые запросы
    target_entries = payload["categories"]["target"]["mixed"]
    write_txt(os.path.join(output_dir, "queries_target.txt"), target_entries)
    write_yaml(os.path.join(output_dir, "queries_target.yaml"), target_entries)
    write_matrix_json(os.path.join(output_dir, "matrix_target.json"), target_entries)

    # Подписки
    for qtype in ["repo", "code", "topic", "gitverse"]:
        entries = payload["categories"]["subscriptions"][qtype]

        write_txt(
            os.path.join(output_dir, f"queries_subscriptions_{qtype}.txt"),
            entries,
        )

        write_yaml(
            os.path.join(output_dir, f"queries_subscriptions_{qtype}.yaml"),
            entries,
        )

        write_matrix_json(
            os.path.join(output_dir, f"matrix_subscriptions_{qtype}.json"),
            entries,
        )

    # ТГ прокси
    for qtype in ["repo", "code", "topic", "gitverse"]:
        entries = payload["categories"]["tg_proxies"][qtype]

        write_txt(
            os.path.join(output_dir, f"queries_tg_proxies_{qtype}.txt"),
            entries,
        )

        write_yaml(
            os.path.join(output_dir, f"queries_tg_proxies_{qtype}.yaml"),
            entries,
        )

        write_matrix_json(
            os.path.join(output_dir, f"matrix_tg_proxies_{qtype}.json"),
            entries,
        )

    # Утилиты
    for qtype in ["repo", "code", "topic", "gitverse"]:
        entries = payload["categories"]["utilities"][qtype]

        write_txt(
            os.path.join(output_dir, f"queries_utilities_{qtype}.txt"),
            entries,
        )

        write_yaml(
            os.path.join(output_dir, f"queries_utilities_{qtype}.yaml"),
            entries,
        )

        write_matrix_json(
            os.path.join(output_dir, f"matrix_utilities_{qtype}.json"),
            entries,
        )

    print("==================================================")
    print(" Generation summary")
    print("==================================================")

    for key, value in payload["summary"].items():
        print(f"{key}: {value}")

    print("==================================================")
    print(f"Output directory: {output_dir}")
    print("Done.")


if __name__ == "__main__":
    main()