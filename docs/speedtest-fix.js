// Speed Test Upload Fix - вставить в docs/index.html вместо функции measureUpload()

async function measureUpload() {
    els.speedPhase.textContent = "Measuring upload...";
    setGauge(0, "upload");
    
    const chunkSize = 256 * 1024; // 256KB chunks
    const chunk = new Uint8Array(chunkSize);
    crypto.getRandomValues(chunk);
    
    const totalChunks = Math.floor(SPEED.maxUploadBytes / chunkSize);
    const parts = [];
    for (let i = 0; i < totalChunks; i++) parts.push(chunk);
    const bigPayload = new Blob(parts);
    
    return new Promise((resolve) => {
        const xhr = new XMLHttpRequest();
        const start = performance.now();
        let lastReport = start;
        let lastLoaded = 0;
        
        xhr.upload.addEventListener("progress", (e) => {
            if (state.speedAbort) {
                xhr.abort();
                resolve(null);
                return;
            }
            
            const now = performance.now();
            if (e.lengthComputable && now - lastReport > 200) {
                const elapsed = (now - lastReport) / 1000;
                const uploaded = e.loaded - lastLoaded;
                const instantMbps = formatMbps(uploaded / elapsed);
                
                setGauge(instantMbps, "upload");
                speedLog(`upload ${Math.round(e.loaded / 1024)} KB / ${Math.round(e.total / 1024)} KB`, `${instantMbps.toFixed(2)} Mbps`);
                
                lastReport = now;
                lastLoaded = e.loaded;
            }
        });
        
        xhr.addEventListener("load", () => {
            const totalElapsed = (performance.now() - start) / 1000;
            const bytes = bigPayload.size;
            
            if (totalElapsed <= 0 || bytes <= 0) {
                resolve(null);
                return;
            }
            
            const mbps = formatMbps(bytes / totalElapsed);
            setGauge(mbps, "upload");
            speedLog(`upload complete ${Math.round(bytes / 1024)} KB`, `${mbps.toFixed(2)} Mbps`);
            resolve(mbps);
        });
        
        xhr.addEventListener("error", () => {
            speedLog("upload", "network error");
            resolve(null);
        });
        
        xhr.addEventListener("abort", () => {
            speedLog("upload", "aborted");
            resolve(null);
        });
        
        xhr.open("POST", SPEED.uploadUrl, true);
        xhr.setRequestHeader("Content-Type", "application/octet-stream");
        xhr.send(bigPayload);
    });
}