# Default HTML Template (Embedded to ensure portability)
DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REMAININGCONNECTIONS | Live Monitor</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        body { 
            font-family: 'Inter', sans-serif; 
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); 
            color: #e2e8f0; 
            min-height: 100vh;
        }
        .glass-panel {
            background: rgba(30, 41, 59, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 1rem;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.1);
        }
        .gradient-text {
            background: linear-gradient(to right, #38bdf8, #818cf8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .glow-button {
            transition: all 0.3s ease;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.5);
        }
        .glow-button:hover {
            box-shadow: 0 0 20px rgba(56, 189, 248, 0.8);
            transform: translateY(-2px);
        }
        .status-dot {
            height: 10px;
            width: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        .status-working { background-color: #22c55e; box-shadow: 0 0 8px #22c55e; }
        .status-failed { background-color: #ef4444; }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
    </style>
</head>
<body class="antialiased p-4 md:p-8">
    
    <header class="max-w-7xl mx-auto mb-10 text-center relative">
        <h1 class="text-5xl md:text-6xl font-bold gradient-text mb-2 tracking-tight">REMAININGCONNECTIONS</h1>
        <p class="text-slate-400 text-lg mb-6">Система мониторинга и анализа соединений</p>
        
        <div class="flex flex-col sm:flex-row justify-center items-center gap-4 mt-6">
            <a href="https://t.me/YOUR_CHANNEL_NAME_HERE" target="_blank" class="glow-button px-6 py-3 bg-blue-600 rounded-xl font-semibold text-white flex items-center gap-2">
                📢 Наш Telegram Канал
            </a>
            <a href="https://remainconnected.vercel.app/" target="_blank" class="glow-button px-6 py-3 bg-indigo-600 rounded-xl font-semibold text-white flex items-center gap-2 hover:bg-indigo-500">
                🌐 Официальное зеркало (Белые списки)
            </a>
        </div>
        <div id="build-info" class="text-xs text-slate-500 mt-4"></div>
    </header>

    <main class="max-w-7xl mx-auto space-y-6">
        <!-- Stats Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <div class="glass-panel p-6 relative overflow-hidden group">
                <div class="absolute top-0 right-0 w-24 h-24 bg-blue-500/10 rounded-full -mr-10 -mt-10 transition-transform group-hover:scale-150"></div>
                <h3 class="text-slate-400 text-sm font-medium uppercase tracking-wider">Всего прокси</h3>
                <div id="stat-total-proxies" class="text-4xl font-bold mt-2 text-white">...</div>
            </div>
            
            <div class="glass-panel p-6 relative overflow-hidden group">
                <div class="absolute top-0 right-0 w-24 h-24 bg-green-500/10 rounded-full -mr-10 -mt-10 transition-transform group-hover:scale-150"></div>
                <h3 class="text-slate-400 text-sm font-medium uppercase tracking-wider">Активные</h3>
                <div id="stat-working-proxies" class="text-4xl font-bold mt-2 text-green-400">...</div>
            </div>
            
            <div class="glass-panel p-6 relative overflow-hidden group">
                <div class="absolute top-0 right-0 w-24 h-24 bg-yellow-500/10 rounded-full -mr-10 -mt-10 transition-transform group-hover:scale-150"></div>
                <h3 class="text-slate-400 text-sm font-medium uppercase tracking-wider">Подписки</h3>
                <div id="stat-subs" class="text-4xl font-bold mt-2 text-yellow-400">...</div>
            </div>
            
            <div class="glass-panel p-6 relative overflow-hidden group">
                <div class="absolute top-0 right-0 w-24 h-24 bg-purple-500/10 rounded-full -mr-10 -mt-10 transition-transform group-hover:scale-150"></div>
                <h3 class="text-slate-400 text-sm font-medium uppercase tracking-wider">Uptime</h3>
                <div id="stat-uptime" class="text-4xl font-bold mt-2 text-purple-400">--%</div>
            </div>
        </div>

        <!-- Charts Section -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div class="glass-panel p-6">
                <h3 class="text-lg font-semibold mb-4 text-slate-200 flex items-center gap-2">
                    <span class="w-2 h-6 bg-blue-500 rounded-full"></span> Распределение протоколов
                </h3>
                <canvas id="protocolChart" height="200"></canvas>
            </div>
            <div class="glass-panel p-6">
                <h3 class="text-lg font-semibold mb-4 text-slate-200 flex items-center gap-2">
                    <span class="w-2 h-6 bg-indigo-500 rounded-full"></span> Задержка (Latency)
                </h3>
                <canvas id="latencyChart" height="200"></canvas>
            </div>
        </div>

        <!-- Recent Updates Table -->
        <div class="glass-panel p-6">
            <div class="flex justify-between items-center mb-6">
                <h3 class="text-lg font-semibold text-slate-200 flex items-center gap-2">
                    <span class="w-2 h-6 bg-green-500 rounded-full"></span> Топ быстрых соединений
                </h3>
                <span class="text-xs text-slate-500 bg-slate-800 px-2 py-1 rounded">Обновлено: <span id="timestamp"></span></span>
            </div>
            
            <div class="overflow-x-auto rounded-lg border border-slate-700">
                <table class="min-w-full divide-y divide-slate-700">
                    <thead class="bg-slate-800/50">
                        <tr>
                            <th class="px-6 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Протокол</th>
                            <th class="px-6 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Сервер</th>
                            <th class="px-6 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Задержка</th>
                            <th class="px-6 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Глубокий Score</th>
                            <th class="px-6 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">TLS Шифр</th>
                            <th class="px-6 py-4 text-left text-xs font-bold text-slate-400 uppercase tracking-wider">Статус</th>
                        </tr>
                    </thead>
                    <tbody id="proxy-table-body" class="divide-y divide-slate-700 bg-slate-900/30">
                        <!-- Rows injected here -->
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <footer class="mt-12 text-center text-slate-500 text-sm pb-6">
        <p>Powered by REMAININGCONNECTIONS Engine v2.0</p>
    </footer>

    <script>
        const CONFIG_DATA = {{ CONFIG_JSON }};

        document.addEventListener('DOMContentLoaded', () => {
            renderStats(CONFIG_DATA);
            renderCharts(CONFIG_DATA);
            renderTable(CONFIG_DATA);
            document.getElementById('timestamp').innerText = new Date().toLocaleTimeString();
            document.getElementById('build-info').innerText = "Build: " + (CONFIG_DATA.build_info || "Auto");
        });

        function renderStats(data) {
            const proxies = data.proxies || [];
            const subs = data.subscriptions || [];
            
            const totalP = proxies.length;
            const workingP = proxies.filter(p => p.status === 'working').length;
            const uptime = totalP > 0 ? Math.round((workingP / totalP) * 100) : 0;

            animateValue("stat-total-proxies", 0, totalP, 1000);
            animateValue("stat-working-proxies", 0, workingP, 1000);
            document.getElementById('stat-subs').innerText = subs.length;
            document.getElementById('stat-uptime').innerText = uptime + "%";
        }
        
        function animateValue(id, start, end, duration) {
            if (start === end) return;
            const range = end - start;
            let current = start;
            const increment = end > start ? 1 : -1;
            const stepTime = Math.abs(Math.floor(duration / range));
            const obj = document.getElementById(id);
            const timer = setInterval(function() {
                current += increment;
                obj.innerHTML = current;
                if (current == end) {
                    clearInterval(timer);
                }
            }, stepTime < 10 ? 10 : stepTime); // Min 10ms step
            obj.innerHTML = end; // Force end immediately for large numbers
        }

        function renderCharts(data) {
            const proxies = data.proxies || [];
            
            // Protocol Distribution
            const protocols = {};
            proxies.forEach(p => {
                const proto = p.protocol || 'unknown';
                protocols[proto] = (protocols[proto] || 0) + 1;
            });

            const ctx1 = document.getElementById('protocolChart').getContext('2d');
            new Chart(ctx1, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(protocols),
                    datasets: [{
                        data: Object.values(protocols),
                        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                        borderWidth: 0
                    }]
                },
                options: { 
                    responsive: true, 
                    plugins: { legend: { position: 'bottom', labels: { color: '#cbd5e1' } } },
                    cutout: '70%'
                }
            });

            // Latency
            const latencies = proxies.map(p => p.tcp_latency_ms || p.latency_ms || 0).filter(l => l > 0);
            const buckets = { '<100ms': 0, '100-300ms': 0, '>300ms': 0 };
            latencies.forEach(l => {
                if (l < 100) buckets['<100ms']++;
                else if (l <= 300) buckets['100-300ms']++;
                else buckets['>300ms']++;
            });

            const ctx2 = document.getElementById('latencyChart').getContext('2d');
            new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: Object.keys(buckets),
                    datasets: [{
                        label: 'Количество',
                        data: Object.values(buckets),
                        backgroundColor: '#6366f1',
                        borderRadius: 6
                    }]
                },
                options: { 
                    responsive: true, 
                    scales: { 
                        y: { beginAtZero: true, grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
                        x: { grid: { display: false }, ticks: { color: '#94a3b8' } }
                    },
                    plugins: { legend: { display: false } }
                }
            });
        }

        function renderTable(data) {
            const tbody = document.getElementById('proxy-table-body');
            const workingProxies = (data.proxies || [])
                .filter(p => p.status === 'working')
                .sort((a, b) => (a.tcp_latency_ms || a.latency_ms || 999) - (b.tcp_latency_ms || b.latency_ms || 999))
                .slice(0, 15); 

            if (workingProxies.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-4 text-center text-slate-500">Нет активных прокси для отображения</td></tr>';
                return;
            }

            tbody.innerHTML = workingProxies.map(p => `
                <tr class="hover:bg-slate-800/50 transition-colors">
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-bold text-blue-300">${p.protocol}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">${p.server}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                        ${p.tcp_latency_ms ? p.tcp_latency_ms.toFixed(0) + ' ms' : (p.latency_ms ? p.latency_ms.toFixed(0) + ' ms' : '-')}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        <span class="px-2 py-1 rounded text-xs font-bold ${getScoreColor(p.deep_score)}">
                            ${p.deep_score != null ? p.deep_score.toFixed(1) : '-'}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-400 font-mono truncate max-w-[150px]" title="${p.tls_cipher || ''}">
                        ${p.tls_cipher || '-'}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-900 text-green-300 border border-green-700">
                            <span class="status-dot status-working"></span> Working
                        </span>
                    </td>
                </tr>
            `).join('');
        }
        
        function getScoreColor(score) {
            if (!score) return 'bg-gray-700 text-gray-300';
            if (score >= 80) return 'bg-green-900 text-green-300 border border-green-700';
            if (score >= 50) return 'bg-yellow-900 text-yellow-300 border border-yellow-700';
            return 'bg-red-900 text-red-300 border border-red-700';
        }
    </script>
</body>
</html>"""