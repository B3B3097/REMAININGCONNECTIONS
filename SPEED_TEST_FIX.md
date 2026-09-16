# Исправление Speed Test Upload

## Проблема
`fetch()` API возвращает promise сразу после отправки запроса на сервер, **не дожидаясь** полной передачи данных через сеть. Поэтому замер upload скорости показывает завышенные/некорректные значения.

## Решение
Использовать `XMLHttpRequest` с событием `upload.progress` для отслеживания реального прогресса отправки данных.

## Инструкция по применению

### Вариант 1: Замена функции в docs/index.html

Найти в `docs/index.html` функцию `measureUpload()` (строка ~500-530) и заменить её на:

```javascript
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
```

### Вариант 2: Использовать готовый файл

Скопировать код из `docs/speedtest-fix.js` и вставить в нужное место в `docs/index.html`.

---

## Что изменилось

| Было (fetch) | Стало (XMLHttpRequest) |
|--------------|------------------------|
| ❌ Замер завершается сразу после `.fetch()` | ✅ Замер идёт во время реальной отправки данных |
| ❌ Нет отслеживания прогресса | ✅ Событие `upload.progress` каждые 200ms |
| ❌ Невозможно увидеть промежуточные значения | ✅ Анимация спидометра и лог в реальном времени |
| ❌ Некорректные результаты | ✅ Точные замеры скорости upload |

---

## Техническая информация

**Старый код (fetch):**
```javascript
const response = await fetch(SPEED.uploadUrl, { method: "POST", body: bigPayload });
const elapsed = (performance.now() - start) / 1000;
```
- `fetch()` возвращает promise **после отправки заголовков**, не дожидаясь передачи тела запроса.
- Таймер останавливается слишком рано.

**Новый код (XHR):**
```javascript
xhr.upload.addEventListener("progress", (e) => {
    const uploaded = e.loaded - lastLoaded;
    const instantMbps = formatMbps(uploaded / elapsed);
});
```
- Событие `progress` срабатывает во время реальной передачи данных по сети.
- Вычисляется мгновенная скорость между двумя замерами (differential measurement).

---

## Совместимость

✅ Все современные браузеры (Chrome, Firefox, Safari, Edge)  
✅ Мобильные браузеры (iOS Safari, Chrome Mobile)  
✅ Работает с CORS (если сервер поддерживает)

---

## Тестирование

После применения патча:

1. Открыть Dashboard → Speed Test
2. Нажать "Start test"
3. Проверить:
   - ✅ Ping измеряется корректно
   - ✅ Download измеряется корректно
   - ✅ **Upload теперь показывает реальную скорость** (не мгновенное завершение)
   - ✅ Лог показывает промежуточные значения во время upload
   - ✅ Спидометр плавно анимируется

---

## Альтернативный подход (если нужен Fetch API)

Если хочешь остаться на `fetch()`, можно использовать **ReadableStream** для upload:

```javascript
const stream = new ReadableStream({
    start(controller) {
        let sent = 0;
        const interval = setInterval(() => {
            if (sent >= bigPayload.size) {
                controller.close();
                clearInterval(interval);
                return;
            }
            const chunk = bigPayload.slice(sent, sent + chunkSize);
            controller.enqueue(chunk);
            sent += chunk.size;
            // Track progress here
        }, 100);
    }
});

await fetch(SPEED.uploadUrl, { method: "POST", body: stream });
```

Но это **сложнее** и **менее надёжно**, чем XHR с `upload.progress`.

---

**Рекомендация:** используй исправление с `XMLHttpRequest` — это стандартный способ для upload progress tracking.