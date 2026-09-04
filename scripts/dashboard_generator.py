            tbody.innerHTML = workingProxies.map(p => `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">${p.protocol}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">${p.server}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">${p.latency_ms || '-'} ms</td>
                    <td class="px-6 py-4 whitespace-nowrap"><span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Working</span></td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">${p.deep_score != null ? p.deep_score.toFixed(2) : '-'}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">${p.tls_cipher || '-'}</td>
                </tr>
            `).join('');