// Speed Test Upload Fix
// This implementation is intended to replace the inline measureUpload()
// in docs/index.html. It is kept here as the canonical reference.

async function measureUpload() {
    els.speedPhase.textContent = "Measuring upload...";
    setGauge(0, "upload");

    const chunkSize = 256 * 1024;
    const maxBytes = Math.max(0, Number(SPEED.maxUploadBytes) || 0);
    const chunk = new Uint8Array(chunkSize);

    // Web Crypto accepts at most 65536 bytes per call.
    for (let offset = 0; offset < chunk.length; offset += 65536) {
        crypto.getRandomValues(chunk.subarray(offset, Math.min(offset + 65536, chunk.length)));
    }

    const parts = [];
    let remaining = maxBytes;
    while (remaining > 0) {
        const size = Math.min(chunk.length, remaining);
        parts.push(size === chunk.length ? chunk : chunk.slice(0, size));
        remaining -= size;
    }
    const bigPayload = new Blob(parts, { type: "application/octet-stream" });

    return new Promise((resolve) => {
        const xhr = new XMLHttpRequest();
        const start = performance.now();
        let lastReport = start;
        let lastLoaded = 0;
        let settled = false;

        const finish = (value, message, detail = "") => {
            if (settled) return;
            settled = true;
            if (message) speedLog(message, detail);
            resolve(value);
        };

        xhr.timeout = 15000;

        xhr.upload.addEventListener("progress", (event) => {
            if (state.speedAbort) {
                xhr.abort();
                return;
            }

            const now = performance.now();
            if (event.lengthComputable && now - lastReport > 200) {
                const elapsed = (now - lastReport) / 1000;
                const uploaded = event.loaded - lastLoaded;
                const instantMbps = formatMbps(uploaded / elapsed);

                setGauge(instantMbps, "upload");
                speedLog(
                    `upload ${Math.round(event.loaded / 1024)} KB / ${Math.round(event.total / 1024)} KB`,
                    `${instantMbps.toFixed(2)} Mbps`
                );
                lastReport = now;
                lastLoaded = event.loaded;
            }
        });

        xhr.addEventListener("load", () => {
            if (state.speedAbort) {
                finish(null, "upload", "aborted");
                return;
            }
            if (xhr.status < 200 || xhr.status >= 300) {
                finish(null, "upload", `HTTP ${xhr.status}`);
                return;
            }

            const totalElapsed = (performance.now() - start) / 1000;
            if (totalElapsed <= 0 || bigPayload.size <= 0) {
                finish(null);
                return;
            }

            const mbps = formatMbps(bigPayload.size / totalElapsed);
            setGauge(mbps, "upload");
            finish(
                mbps,
                `upload complete ${Math.round(bigPayload.size / 1024)} KB`,
                `${mbps.toFixed(2)} Mbps`
            );
        });

        xhr.addEventListener("error", () => finish(null, "upload", "network error"));
        xhr.addEventListener("timeout", () => finish(null, "upload", "timeout"));
        xhr.addEventListener("abort", () => finish(null, "upload", "aborted"));

        try {
            xhr.open("POST", SPEED.uploadUrl, true);
            xhr.setRequestHeader("Content-Type", "application/octet-stream");
            xhr.send(bigPayload);
        } catch (error) {
            finish(null, "upload", `error: ${error.message || "request failed"}`);
        }
    });
}
@@END@@Теперь исправляю inline-реализацию в `docs/index.html`, потому что именно она реально вызывается страницей; внешний файл является только справочной версией и сам по себе не переопределяет IIFE-код. Сначала перечитываю файл перед правкой.@@TOOL@@ READ_FILE
@@ARGS@@ {"path":"docs/index.html"}
@@END@@Применяю точечную правку inline `measureUpload()` в `docs/index.html`: исправляю генерацию 10 МБ payload и делаю сетевой запрос отменяемым и корректно завершаемым.@@TOOL@@ EDIT_FILE
@@ARGS@@ {"path":"docs/index.html"}
@@CONTENT@@@@
-            async function measureUpload() {
-                els.speedPhase.textContent = "Measuring upload...";
-                setGauge(0, "upload");
-                const chunkSize = 256 * 1024;
-                const chunk = new Uint8Array(chunkSize);
-                crypto.getRandomValues(chunk);
-                const totalChunks = Math.floor(SPEED.maxUploadBytes / chunkSize);
-                const parts = [];
-                for (let i = 0; i < totalChunks; i++) parts.push(chunk);
-                const bigPayload = new Blob(parts);
-                const start = performance.now();
-                try {
-                    const response = await fetch(SPEED.uploadUrl, { method: "POST", body: bigPayload, mode: "cors", cache: "no-store" });
-                    const elapsed = (performance.now() - start) / 1000;
-                    const bytes = bigPayload.size;
-                    if (!response.ok && response.status !== 0) speedLog(`upload ${Math.round(bytes / 1024)} KB`, `HTTP ${response.status}`);
-                    if (elapsed <= 0 || bytes <= 0) return null;
-                    const mbps = formatMbps(bytes / elapsed);
-                    setGauge(mbps, "upload");
-                    speedLog(`upload ${Math.round(bytes / 1024)} KB`, `${mbps.toFixed(2)} Mbps`);
-                    return mbps;
-                } catch (e) { speedLog("upload", "error: " + (e.message || "")); return null; }
-            }
+            async function measureUpload() {
+                els.speedPhase.textContent = "Measuring upload...";
+                setGauge(0, "upload");
+
+                const chunkSize = 256 * 1024;
+                const maxBytes = Math.max(0, Number(SPEED.maxUploadBytes) || 0);
+                const chunk = new Uint8Array(chunkSize);
+                for (let offset = 0; offset < chunk.length; offset += 65536) {
+                    crypto.getRandomValues(chunk.subarray(offset, Math.min(offset + 65536, chunk.length)));
+                }
+
+                const parts = [];
+                let remaining = maxBytes;
+                while (remaining > 0) {
+                    const size = Math.min(chunk.length, remaining);
+                    parts.push(size === chunk.length ? chunk : chunk.slice(0, size));
+                    remaining -= size;
+                }
+                const bigPayload = new Blob(parts, { type: "application/octet-stream" });
+
+                return new Promise((resolve) => {
+                    const xhr = new XMLHttpRequest();
+                    const start = performance.now();
+                    let lastReport = start;
+                    let lastLoaded = 0;
+                    let settled = false;
+
+                    const finish = (value, message, detail = "") => {
+                        if (settled) return;
+                        settled = true;
+                        if (message) speedLog(message, detail);
+                        resolve(value);
+                    };
+
+                    xhr.timeout = 15000;
+                    xhr.upload.addEventListener("progress", (event) => {
+                        if (state.speedAbort) {
+                            xhr.abort();
+                            return;
+                        }
+                        const now = performance.now();
+                        if (event.lengthComputable && now - lastReport > 200) {
+                            const elapsed = (now - lastReport) / 1000;
+                            const uploaded = event.loaded - lastLoaded;
+                            const instantMbps = formatMbps(uploaded / elapsed);
+                            setGauge(instantMbps, "upload");
+                            speedLog(
+                                `upload ${Math.round(event.loaded / 1024)} KB / ${Math.round(event.total / 1024)} KB`,
+                                `${instantMbps.toFixed(2)} Mbps`
+                            );
+                            lastReport = now;
+                            lastLoaded = event.loaded;
+                        }
+                    });
+                    xhr.addEventListener("load", () => {
+                        if (state.speedAbort) {
+                            finish(null, "upload", "aborted");
+                            return;
+                        }
+                        if (xhr.status < 200 || xhr.status >= 300) {
+                            finish(null, "upload", `HTTP ${xhr.status}`);
+                            return;
+                        }
+                        const elapsed = (performance.now() - start) / 1000;
+                        if (elapsed <= 0 || bigPayload.size <= 0) {
+                            finish(null);
+                            return;
+                        }
+                        const mbps = formatMbps(bigPayload.size / elapsed);
+                        setGauge(mbps, "upload");
+                        finish(mbps, `upload complete ${Math.round(bigPayload.size / 1024)} KB`, `${mbps.toFixed(2)} Mbps`);
+                    });
+                    xhr.addEventListener("error", () => finish(null, "upload", "network error"));
+                    xhr.addEventListener("timeout", () => finish(null, "upload", "timeout"));
+                    xhr.addEventListener("abort", () => finish(null, "upload", "aborted"));
+                    try {
+                        xhr.open("POST", SPEED.uploadUrl, true);
+                        xhr.setRequestHeader("Content-Type", "application/octet-stream");
+                        xhr.send(bigPayload);
+                    } catch (error) {
+                        finish(null, "upload", `error: ${error.message || "request failed"}`);
+                    }
+                });
+            }
@@
-                const pingResult = await measurePing();
+                const pingResult = await measurePing();
+                if (state.speedAbort) return finishSpeedTest(true);
@@
-                const dl = await measureDownload();
+                const dl = await measureDownload();
+                if (state.speedAbort) return finishSpeedTest(true);
@@
-                const ul = await measureUpload();
+                const ul = await measureUpload();
+                if (state.speedAbort) return finishSpeedTest(true);
*** End Patch
@@END@@Вношу дополнительную правку в `index.html`: добавляю отсутствующую функцию завершения отменённого теста и исправляю jitter/download, чтобы Stop не приводил к ложному результату или ошибке `ReferenceError`.@@TOOL@@ EDIT_FILE
@@ARGS@@ {"path":"docs/index.html"}
@@CONTENT@@@@
-                if (state.speedAbort) break;
+                if (state.speedAbort) {
+                    try { await reader.cancel(); } catch (e) {}
+                    return null;
+                }
@@
-                samples.sort((a, b) => a - b);
-                const trimmed = samples.length > 4 ? samples.slice(1, -1) : samples;
+                const sortedSamples = [...samples].sort((a, b) => a - b);
+                const trimmed = sortedSamples.length > 4 ? sortedSamples.slice(1, -1) : sortedSamples;
@@
-            async function runSpeedTest() {
+            function finishSpeedTest(aborted = false) {
+                state.speedRunning = false;
+                els.speedStartBtn.classList.remove("hidden");
+                els.speedStopBtn.classList.add("hidden");
+                els.speedStartBtn.disabled = false;
+                els.speedPhase.textContent = aborted ? "Test stopped" : "Test finished";
+                if (aborted) speedLog("=== Test aborted ===", "");
+            }
+
+            async function runSpeedTest() {
@@
-                els.speedPhase.textContent = "Test finished";
-                speedLog("=== Test finished ===", "");
-                state.speedRunning = false;
-                els.speedStartBtn.classList.remove("hidden");
-                els.speedStopBtn.classList.add("hidden");
-                els.speedStartBtn.disabled = false;
-                showToast("Speed test finished", "success");
+                speedLog("=== Test finished ===", "");
+                finishSpeedTest();
+                showToast("Speed test finished", "success");
*** End Patch
@@END@@Проверяю изменённые файлы и убеждаюсь, что в `index.html` не осталось ссылок на несуществующие функции, а workflow содержит строгую валидацию.@@TOOL@@ READ_FILE
@@ARGS@@ {"path":"docs/speedtest-fix.js"}
@@END@@Проверяю `deploy.yml` после обновления, чтобы подтвердить итоговую конфигурацию перед коммитом.@@TOOL@@ READ_FILE
@@ARGS@@ {"path":".github/workflows/deploy.yml"}
@@END@@Проверяю inline-код страницы после правок, особенно `measureUpload`, `finishSpeedTest` и обработку остановки.@@TOOL@@ READ_FILE
@@ARGS@@ {"path":"docs/index.html"}
@@END@@Проверяю историю коммитов, чтобы убедиться, что изменения действительно записаны в `main`.@@TOOL@@ GET_COMMITS
@@ARGS@@ {"path":""}
@@END@@Повторяю проверку истории с корректным параметром, чтобы получить последний коммит после изменений.@@TOOL@@ GET_COMMITS
@@ARGS@@ {}