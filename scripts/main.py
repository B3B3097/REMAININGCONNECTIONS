import asyncio
import aiohttp
import os
import csv
import json
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Директория для экспорта данных
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Список источников (примеры открытых источников прокси)
PROXY_SOURCES = [
    "https://raw.githubusercontent.com/clash-verge-rev/clash-verge-rev.github.io/main/docs/proxy/list.txt",
    # Добавьте сюда ваши актуальные источники
]

async def fetch_source(session, url):
    """Безопасная загрузка данных из источника"""
    try:
        async with session.get(url, timeout=15) as response:
            if response.status == 200:
                text = await response.text()
                return text.splitlines()
    except Exception as e:
        logging.warning(f"Ошибка при запросе к {url}: {e}")
    return []

async def collect_proxies():
    """Асинхронный сбор прокси из всех источников"""
    all_proxies = set()
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_source(session, url) for url in PROXY_SOURCES]
        results = await asyncio.gather(*tasks)
        for result in results:
            for proxy in result:
                cleaned = proxy.strip()
                if cleaned and not cleaned.startswith("#"):
                    all_proxies.add(cleaned)
                    
    logging.info(f"Успешно собрано уникальных прокси: {len(all_proxies)}")
    return list(all_proxies)

def export_data(proxies):
    """Экспорт данных в различные форматы (Текст, CSV, PAC)"""
    if not proxies:
        logging.warning("Список прокси пуст, экспорт пропущен.")
        return False

    # 1. Текстовый формат
    txt_path = os.path.join(OUTPUT_DIR, "proxies.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("\n".join(proxies))

    # 2. CSV формат
    csv_path = os.path.join(OUTPUT_DIR, "proxies.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Proxy String"])
        for p in proxies:
            writer.writerow([p])

    # 3. PAC формат (пример базовой структуры)
    pac_path = os.path.join(OUTPUT_DIR, "proxy.pac")
    with open(pac_path, "w", encoding="utf-8") as f:
        f.write("function FindProxyForURL(url, host) {\n")
        f.write("    return 'PROXY 127.0.0.1:1080; DIRECT';\n")
        f.write("}\n")

    logging.info("Экспорт данных во все форматы завершен успешно.")
    return True

async def main():
    proxies = await collect_proxies()
    export_data(proxies)

if __name__ == "__main__":
    asyncio.run(main())
