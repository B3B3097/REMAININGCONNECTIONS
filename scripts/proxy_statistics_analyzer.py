#!/usr/bin/env python3
"""Advanced proxy statistics analyzer with metrics and visualizations."""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ProxyMetrics:
    """Statistical metrics for proxy analysis."""
    total_count: int
    working_count: int
    failed_count: int
    timeout_count: int
    invalid_count: int
    working_percentage: float
    avg_latency_ms: float | None
    median_latency_ms: float | None
    p95_latency_ms: float | None
    p99_latency_ms: float | None
    min_latency_ms: float | None
    max_latency_ms: float | None
    latency_std_dev: float | None
    protocols: dict[str, int]
    regions: dict[str, int]
    sources: dict[str, int]
    status_distribution: dict[str, int]


def calculate_percentile(values: list[float], percentile: float) -> float:
    """Calculate percentile from sorted values."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = (len(sorted_values) - 1) * (percentile / 100)
    floor = int(index)
    ceil = floor + 1
    if ceil >= len(sorted_values):
        return sorted_values[-1]
    return sorted_values[floor] + (sorted_values[ceil] - sorted_values[floor]) * (index - floor)


def analyze_proxy_data(data: dict[str, Any]) -> ProxyMetrics:
    """Analyze proxy data and calculate comprehensive metrics."""
    proxies = data.get("proxies", [])
    
    if not proxies:
        return ProxyMetrics(
            total_count=0,
            working_count=0,
            failed_count=0,
            timeout_count=0,
            invalid_count=0,
            working_percentage=0.0,
            avg_latency_ms=None,
            median_latency_ms=None,
            p95_latency_ms=None,
            p99_latency_ms=None,
            min_latency_ms=None,
            max_latency_ms=None,
            latency_std_dev=None,
            protocols={},
            regions={},
            sources={},
            status_distribution={},
        )
    
    # Count statuses
    status_counter = Counter()
    protocol_counter = Counter()
    region_counter = Counter()
    source_counter = Counter()
    
    latencies: list[float] = []
    
    for proxy in proxies:
        status = proxy.get("status", "unknown")
        status_counter[status] += 1
        
        # Extract protocol
        protocol = proxy.get("protocol", "unknown")
        protocol_counter[protocol] += 1
        
        # Extract region hints
        region = proxy.get("region_hint") or proxy.get("region") or "unknown"
        region_counter[region] += 1
        
        # Extract sources
        sources = proxy.get("sources", [])
        if sources:
            for source_entry in sources:
                source = source_entry.get("source", "unknown")
                source_counter[source] += 1
        else:
            source_counter["unknown"] += 1
        
        # Collect latencies
        latency = proxy.get("latency_ms") or proxy.get("ping")
        if latency is not None and isinstance(latency, (int, float)) and latency > 0:
            latencies.append(float(latency))
    
    # Calculate latency statistics
    avg_latency = statistics.mean(latencies) if latencies else None
    median_latency = statistics.median(latencies) if latencies else None
    p95_latency = calculate_percentile(latencies, 95) if latencies else None
    p99_latency = calculate_percentile(latencies, 99) if latencies else None
    min_latency = min(latencies) if latencies else None
    max_latency = max(latencies) if latencies else None
    std_dev = statistics.stdev(latencies) if len(latencies) > 1 else None
    
    working_count = status_counter.get("working", 0)
    failed_count = sum(
        status_counter[s] for s in status_counter
        if s not in {"working", "unverified"}
    )
    timeout_count = status_counter.get("timeout", 0)
    invalid_count = status_counter.get("invalid", 0)
    
    working_percentage = (working_count / len(proxies) * 100) if proxies else 0.0
    
    return ProxyMetrics(
        total_count=len(proxies),
        working_count=working_count,
        failed_count=failed_count,
        timeout_count=timeout_count,
        invalid_count=invalid_count,
        working_percentage=round(working_percentage, 2),
        avg_latency_ms=round(avg_latency, 2) if avg_latency else None,
        median_latency_ms=round(median_latency, 2) if median_latency else None,
        p95_latency_ms=round(p95_latency, 2) if p95_latency else None,
        p99_latency_ms=round(p99_latency, 2) if p99_latency else None,
        min_latency_ms=round(min_latency, 2) if min_latency else None,
        max_latency_ms=round(max_latency, 2) if max_latency else None,
        latency_std_dev=round(std_dev, 2) if std_dev else None,
        protocols=dict(protocol_counter.most_common()),
        regions=dict(region_counter.most_common(20)),
        sources=dict(source_counter.most_common()),
        status_distribution=dict(status_counter),
    )


def analyze_subscription_data(data: dict[str, Any]) -> dict[str, Any]:
    """Analyze subscription data with node-level metrics."""
    subscriptions = data.get("subscriptions", [])
    
    if not subscriptions:
        return {
            "total_subscriptions": 0,
            "total_nodes": 0,
            "working_subscriptions": 0,
            "metrics": {},
        }
    
    total_nodes = sum(sub.get("total_configs", 0) for sub in subscriptions)
    working_subs = sum(1 for sub in subscriptions if sub.get("status") == "working")
    
    # Analyze probe results
    total_probed = 0
    total_working_nodes = 0
    latencies: list[float] = []
    protocol_counter = Counter()
    
    for sub in subscriptions:
        probe = sub.get("xray_probe", {})
        total_probed += probe.get("total_probed", 0)
        total_working_nodes += probe.get("working_count", 0)
        
        # Collect working config latencies
        working_configs = probe.get("working_configs", [])
        for config in working_configs:
            latency = config.get("latency_ms")
            if latency and isinstance(latency, (int, float)):
                latencies.append(float(latency))
            
            # Extract protocol from verification
            verification = config.get("verification", "")
            if "xray_" in verification:
                protocol = verification.replace("xray_", "").split("_")[0]
                protocol_counter[protocol] += 1
    
    avg_latency = statistics.mean(latencies) if latencies else None
    
    return {
        "total_subscriptions": len(subscriptions),
        "total_nodes": total_nodes,
        "working_subscriptions": working_subs,
        "total_probed_nodes": total_probed,
        "total_working_nodes": total_working_nodes,
        "working_ratio": round(total_working_nodes / total_probed, 3) if total_probed else 0.0,
        "avg_node_latency_ms": round(avg_latency, 2) if avg_latency else None,
        "protocols": dict(protocol_counter.most_common()),
    }


def generate_performance_report(
    proxy_metrics: ProxyMetrics | None = None,
    subscription_metrics: dict[str, Any] | None = None,
) -> str:
    """Generate human-readable performance report."""
    lines = [
        "=" * 70,
        "PROXY PERFORMANCE REPORT",
        "=" * 70,
        "",
    ]
    
    if proxy_metrics:
        lines.extend([
            "PROXY STATISTICS:",
            f"  Total Proxies: {proxy_metrics.total_count:,}",
            f"  Working: {proxy_metrics.working_count:,} ({proxy_metrics.working_percentage:.1f}%)",
            f"  Failed: {proxy_metrics.failed_count:,}",
            f"  Timeout: {proxy_metrics.timeout_count:,}",
            f"  Invalid: {proxy_metrics.invalid_count:,}",
            "",
            "LATENCY STATISTICS:",
        ])
        
        if proxy_metrics.avg_latency_ms:
            lines.extend([
                f"  Average: {proxy_metrics.avg_latency_ms:.2f} ms",
                f"  Median: {proxy_metrics.median_latency_ms:.2f} ms",
                f"  Min: {proxy_metrics.min_latency_ms:.2f} ms",
                f"  Max: {proxy_metrics.max_latency_ms:.2f} ms",
                f"  P95: {proxy_metrics.p95_latency_ms:.2f} ms",
                f"  P99: {proxy_metrics.p99_latency_ms:.2f} ms",
                f"  Std Dev: {proxy_metrics.latency_std_dev:.2f} ms" if proxy_metrics.latency_std_dev else "",
            ])
        else:
            lines.append("  No latency data available")
        
        lines.extend([
            "",
            "TOP PROTOCOLS:",
        ])
        
        for protocol, count in list(proxy_metrics.protocols.items())[:10]:
            lines.append(f"  {protocol}: {count:,}")
        
        lines.extend([
            "",
            "TOP REGIONS:",
        ])
        
        for region, count in list(proxy_metrics.regions.items())[:10]:
            lines.append(f"  {region}: {count:,}")
        
        lines.append("")
    
    if subscription_metrics:
        lines.extend([
            "SUBSCRIPTION STATISTICS:",
            f"  Total Subscriptions: {subscription_metrics['total_subscriptions']:,}",
            f"  Total Nodes: {subscription_metrics['total_nodes']:,}",
            f"  Working Subscriptions: {subscription_metrics['working_subscriptions']:,}",
            f"  Probed Nodes: {subscription_metrics['total_probed_nodes']:,}",
            f"  Working Nodes: {subscription_metrics['total_working_nodes']:,}",
            f"  Working Ratio: {subscription_metrics['working_ratio']:.1%}",
        ])
        
        if subscription_metrics.get("avg_node_latency_ms"):
            lines.append(f"  Avg Node Latency: {subscription_metrics['avg_node_latency_ms']:.2f} ms")
        
        lines.extend([
            "",
            "NODE PROTOCOLS:",
        ])
        
        for protocol, count in subscription_metrics.get("protocols", {}).items():
            lines.append(f"  {protocol}: {count:,}")
        
        lines.append("")
    
    lines.extend([
        "=" * 70,
        "",
    ])
    
    return "\n".join(lines)


def main():
    """CLI for proxy statistics analyzer."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--proxy-data",
        type=Path,
        help="Path to proxy JSON data file",
    )
    parser.add_argument(
        "--subscription-data",
        type=Path,
        help="Path to subscription JSON data file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Save report to file",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format",
    )
    
    args = parser.parse_args()
    
    proxy_metrics = None
    subscription_metrics = None
    
    # Analyze proxy data
    if args.proxy_data and args.proxy_data.exists():
        proxy_data = json.loads(args.proxy_data.read_text(encoding="utf-8"))
        proxy_metrics = analyze_proxy_data(proxy_data)
    
    # Analyze subscription data
    if args.subscription_data and args.subscription_data.exists():
        subscription_data = json.loads(args.subscription_data.read_text(encoding="utf-8"))
        subscription_metrics = analyze_subscription_data(subscription_data)
    
    # Generate output
    if args.format == "json":
        output = {
            "proxy_metrics": proxy_metrics.__dict__ if proxy_metrics else None,
            "subscription_metrics": subscription_metrics,
        }
        result = json.dumps(output, indent=2, ensure_ascii=False)
    else:
        result = generate_performance_report(proxy_metrics, subscription_metrics)
    
    # Save or print
    if args.output:
        args.output.write_text(result, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()