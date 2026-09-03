*** Begin Patch
*** Update File: scripts/probe_subscription_configs.py
@@
     nodes = uri_lines(content)[:nodes_per_subscription]
     if not nodes:
-        item["status"] = "invalid"
-        item["xray_probe"] = {"status": "invalid", "reason": "no_xray_uri_to_probe", "checked_at": utc_timestamp()}
+        item["status"] = "unverified" if validation["valid"] else "invalid"
+        item["xray_probe"] = {
+            "status": "unverified" if validation["valid"] else "invalid",
+            "reason": (
+                "structured_config_requires_format_conversion"
+                if validation["valid"]
+                else "no_supported_config_to_probe"
+            ),
+            "checked_at": utc_timestamp(),
+        }
@@
-    payload["subscriptions"] = await asyncio.gather(
-        *(guarded(item) for item in subscriptions[: args.max_subscriptions])
-    )
+    probe_targets = subscriptions[: args.max_subscriptions]
+    checked = await asyncio.gather(*(guarded(item) for item in probe_targets))
+    payload["subscriptions"] = checked + subscriptions[args.max_subscriptions:]
*** End Patch