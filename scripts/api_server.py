#!/usr/bin/env python3
"""
Lightweight Async API Server for REMAININGCONNECTIONS.

Provides endpoints to:
- Retrieve real-time proxy statistics.
- Trigger specific discovery workflows manually.
- Serve health metrics data.
- Manage local configuration settings.

This server acts as a bridge between the automated GitHub Actions environment 
and a local frontend interface or external automation tools.

Dependencies:
    aiohttp (already in requirements.txt)
    asyncio
    json
    logging
    pathlib
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from aiohttp import web
except ImportError:
    print("Error: aiohttp is required. Install it via: pip install aiohttp")
    sys.exit(1)

logger = logging.getLogger("APIServer")


@dataclass
class AppState:
    """Holds shared state for the application."""
    data_dir: str = "data"
    config_manager: Any = None # Placeholder for ConfigManager instance
    workflows: Dict[str, bool] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)
    
    # In-memory cache for stats
    stats_cache: Dict[str, Any] = field(default_factory=dict)
    last_update: float = 0.0


class DataHandler:
    """Handles reading and formatting data for API responses."""
    
    def __init__(self, app_state: AppState):
        self.state = app_state
        
    def get_latest_json(self, filename: str) -> Optional[Dict]:
        filepath = Path(self.state.data_dir) / filename
        if not filepath.exists():
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading {filename}: {e}")
            return None

    def calculate_stats(self) -> Dict[str, Any]:
        """Calculate comprehensive stats from available data."""
        proxies_data = self.get_latest_json("tg_proxies_found.json")
        subs_data = self.get_latest_json("subscriptions_found.json")
        
        stats = {
            "timestamp": datetime.utcnow().isoformat(),
            "proxies": {},
            "subscriptions": {},
            "uptime_seconds": round(time.time() - self.state.start_time, 2)
        }
        
        if proxies_data:
            proxs = proxies_data.get("proxies", [])
            working = sum(1 for p in proxs if p.get("status") == "working")
            total = len(proxs)
            rate = (working / total * 100) if total > 0 else 0
            
            protocols = {}
            for p in proxs:
                proto = p.get("protocol", "unknown")
                protocols[proto] = protocols.get(proto, 0) + 1
                
            stats["proxies"] = {
                "total": total,
                "working": working,
                "rate": round(rate, 2),
                "protocols": protocols
            }
            
        if subs_data:
            subs = subs_data.get("subscriptions", [])
            working_sub = sum(1 for s in subs if s.get("status") == "working")
            stats["subscriptions"] = {
                "total": len(subs),
                "working": working_sub,
                "offline": len(subs) - working_sub
            }
            
        return stats


class APIServer:
    """Main API Server class using aiohttp."""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8080, data_dir: str = "data"):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.state = AppState(data_dir=data_dir)
        self.handler = DataHandler(self.state)
        
        self._setup_routes()
        self._setup_middlewares()
        
    def _setup_routes(self):
        """Define API routes."""
        self.app.router.add_get('/api/v1/stats', self.handle_stats)
        self.app.router.add_get('/api/v1/proxies', self.handle_proxies)
        self.app.router.add_get('/api/v1/subscriptions', self.handle_subscriptions)
        self.app.router.add_post('/api/v1/triggers/{workflow_name}', self.handle_trigger_workflow)
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/', self.handle_index)
        
    def _setup_middlewares(self):
        """Add middleware (e.g., logging, CORS)."""
        # Simple CORS middleware
        @web.middleware
        async def cors_middleware(request, handler):
            response = await handler(request)
            if isinstance(response, web.Response):
                response.headers['Access-Control-Allow-Origin'] = '*'
                response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return response
            
        self.app.middlewares.append(cors_middleware)

    # --- Handlers ---

    async def handle_index(self, request):
        return web.Response(text="<h1>REMAININGCONNECTIONS API</h1><p>Use /api/v1/stats for data.</p>")

    async def handle_health(self, request):
        return web.json_response({
            "status": "healthy",
            "version": "1.0.0",
            "uptime": round(time.time() - self.state.start_time, 2)
        })

    async def handle_stats(self, request):
        """Return aggregated statistics."""
        stats = self.handler.calculate_stats()
        return web.json_response(stats)

    async def handle_proxies(self, request):
        """Return raw proxy data."""
        data = self.handler.get_latest_json("tg_proxies_found.json")
        if not data:
            return web.json_response({"error": "No proxy data found"}, status=404)
        return web.json_response(data)

    async def handle_subscriptions(self, request):
        """Return raw subscription data."""
        data = self.handler.get_latest_json("subscriptions_found.json")
        if not data:
            return web.json_response({"error": "No subscription data found"}, status=404)
        return web.json_response(data)

    async def handle_trigger_workflow(self, request):
        """Simulate triggering a workflow (in a real env, this would hit GitHub API)."""
        wf_name = request.match_info['workflow_name']
        
        # Check if workflow is allowed
        allowed_workflows = ["tg-proxy-discovery", "subscription-discovery", "utils-discovery"]
        
        if wf_name not in allowed_workflows:
            return web.json_response({"error": f"Workflow '{wf_name}' not allowed or not found."}, status=404)
            
        # Simulate trigger
        logger.info(f"Triggering workflow: {wf_name}")
        # Here you would call GitHubClient.trigger_workflow(...)
        
        return web.json_response({
            "message": f"Workflow '{wf_name}' triggered successfully.",
            "workflow": wf_name,
            "timestamp": datetime.utcnow().isoformat()
        })

    async def run(self):
        """Start the server."""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        logger.info(f"Starting server on http://{self.host}:{self.port}")
        await site.start()
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(3600)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await runner.cleanup()


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    
    args = parser.parse_args()
    
    server = APIServer(host=args.host, port=args.port, data_dir=args.data_dir)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()