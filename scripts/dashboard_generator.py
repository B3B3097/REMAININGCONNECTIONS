            tbody.innerHTML = workingProxies.map(p => `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-300">${escapeHtml(p.protocol)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">${escapeHtml(p.server)}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
                        ${escapeHtml(p.tcp_latency_ms ? p.tcp_latency_ms.toFixed(0) + ' ms' : (p.latency_ms ? p.latency_ms.toFixed(0) + ' ms' : '-'))}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm">
                        <span class="px-2 py-1 rounded text-xs font-bold ${getScoreColor(p.deep_score)}">
                            ${escapeHtml(p.deep_score != null ? p.deep_score.toFixed(1) : '-')}
                        </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-400 font-mono truncate max-w-[150px]" title="${escapeHtml(p.tls_cipher || '')}">
                        ${escapeHtml(p.tls_cipher || '-')}
                    </td>