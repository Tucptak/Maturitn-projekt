/**
 * Brainiac – Vykreslování statistických grafů (Chart.js 4.x)
 * 
 * Tento soubor se načítá na stránkách stats.html a user_stats.html.
 * Data přepravuje globální proměnná window.statsData, kterou šablona
 * naplní z Python backendu (stats.py) přes {{ ... | tojson }}.
 * 
 * Grafy:
 *   Globální dashboard (stats.html):
 *     - distChart:       histogram rozložení skóre v 10% binech
 *     - catBarChart:     horizontální bar – kategorie podle průměrného skóre
 *     - trendChart:      line – průměrné skóre v čase (trend)
 *
 *   Per-user dashboard (user_stats.html):
 *     - comparisonChart: line – uživatel vs globální průměr
 *     - scatterChart:    scatter – přesnost vs rychlost
 *     - masteryChart:    horizontální bar – skóre podle kategorií
 *
 * Pokud pro daný graf nejsou data, zobrazí se text "Nedostatek dat".
 */
document.addEventListener('DOMContentLoaded', function () {
    var C = window.Chart;
    if (!C) return;  // Chart.js není načtený – stránka nemá grafy

    /* Výchozí barvy pro tmavý design – nastaví se globálně pro všechny grafy */
    C.defaults.color = '#cbd5e1';
    C.defaults.borderColor = '#334155';
    C.defaults.font.family = "'Segoe UI', system-ui, -apple-system, sans-serif";

    // window.statsData je objekt naplněný šablonou z Python backendu (stats.py)
    // Obsahuje klíče: distribution, cat_bars, trend, comparison, scatter, mastery
    var d = window.statsData || {};

    // Barvy grafů (RGBA s variabilní průhledností – doplní se '0.6)' apod.)
    var purple = 'rgba(99,102,241,';
    var teal   = 'rgba(34,211,154,';
    var amber  = 'rgba(245,158,11,';
    var pink   = 'rgba(236,72,153,';

    /**
     * Zkontroluje, zda pole obsahuje alespoň jednu nenulovou hodnotu.
     * Pokud ne, graf nemá smysl vykreslovat.
     */
    function hasData(arr) {
        return arr && arr.length > 0 && arr.some(function (v) { return v !== 0 && v !== null; });
    }

    /**
     * Nahradí canvas element textem "Nedostatek dat" – voláno když graf nemá data.
     */
    function emptyMsg(id, msg) {
        var el = document.getElementById(id);
        if (!el) return;
        var p = document.createElement('p');
        p.className = 'stats-empty';
        p.textContent = msg || 'Nedostatek dat pro zobrazení grafu.';
        el.parentNode.replaceChild(p, el);
    }

    /* ── Histogram rozložení skóre (globální dashboard) ─────────────────────
       Data z: stats.py → _distribution() → {labels: ['0–10%', ...], data: [count, ...]}
       Zobrazuje kolik her skončilo v daném procentuálním rozmezí. */
    (function () {
        var el = document.getElementById('distChart');
        if (!el || !d.distribution) return;
        if (!hasData(d.distribution.data)) { emptyMsg('distChart'); return; }
        new C(el, {
            type: 'bar',
            data: {
                labels: d.distribution.labels,
                datasets: [{
                    label: 'Počet her',
                    data: d.distribution.data,
                    backgroundColor: purple + '0.6)',
                    borderColor: purple + '1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#1e293b' } },
                    x: { grid: { display: false } }
                }
            }
        });
    })();

    /* ── Sloupcový graf kategorií (globální dashboard) ──────────────────────
       Data z: stats.py → _category_bars() → {labels, data (avg %), counts}
       Barvy podle skóre: zelená ≥80%, fialová ≥60%, oranžová ≥40%, červená <40%. */
    (function () {
        var el = document.getElementById('catBarChart');
        if (!el || !d.cat_bars) return;
        if (!d.cat_bars.labels || !d.cat_bars.labels.length) {
            emptyMsg('catBarChart', 'Žádná data pro kategorie.');
            return;
        }
        // Barvy podle úspěšnosti: zelená ≥80%, fialová ≥60%, oranžová ≥40%, červená <40%
        var colors = d.cat_bars.data.map(function (v) {
        new C(el, {
            type: 'bar',
            data: {
                labels: d.cat_bars.labels,
                datasets: [{
                    label: 'Průměrné skóre %',
                    data: d.cat_bars.data,
                    backgroundColor: colors,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, max: 100, grid: { color: '#1e293b' } },
                    y: { grid: { display: false } }
                }
            }
        });
    })();

    /* ── Trendová čára (globální dashboard) ─────────────────────────────────
       Data z: stats.py → _trend() → {labels: ['2025-01-01', ...], data: [avg%, ...]}
       Teal barva s výplní pod čarou. */
    (function () {
        var el = document.getElementById('trendChart');
        if (!el || !d.trend) return;
        if (!hasData(d.trend.data)) { emptyMsg('trendChart'); return; }
        new C(el, {
            type: 'line',
            data: {
                labels: d.trend.labels,
                datasets: [{
                    label: 'Průměrné skóre %',
                    data: d.trend.data,
                    borderColor: teal + '1)',
                    backgroundColor: teal + '0.15)',
                    fill: true,
                    tension: 0.3,
                    pointRadius: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, max: 100, grid: { color: '#1e293b' } },
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } }
                }
            }
        });
    })();

    /* ── Porovnání: uživatel vs globální průměr (user dashboard) ────────────
       Data z: stats.py → _user_comparison() → {labels, user_data, global_data}
       Fialová = uživatel (plná čára), žlutá = průměr komunity (přerušovaná). */
    (function () {
        var el = document.getElementById('comparisonChart');
        if (!el || !d.comparison) return;
        var c = d.comparison;
        if (!c.labels || c.labels.length < 2) {
            emptyMsg('comparisonChart', 'Nedostatek dat (min. 2 dny).');
            return;
        }
        new C(el, {
            type: 'line',
            data: {
                labels: c.labels,
                datasets: [
                    {
                        label: 'Vaše skóre %',
                        data: c.user_data,
                        borderColor: purple + '1)',
                        backgroundColor: purple + '0.1)',
                        fill: false, tension: 0.3, pointRadius: 3, spanGaps: true
                    },
                    {
                        label: 'Průměr komunity',
                        data: c.global_data,
                        borderColor: amber + '0.8)',
                        backgroundColor: amber + '0.05)',
                        fill: false, tension: 0.3, pointRadius: 2,
                        borderDash: [6, 3], spanGaps: true
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, max: 100, grid: { color: '#1e293b' } },
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 10 } }
                }
            }
        });
    })();

    /* ── Scatter: přesnost vs rychlost (user dashboard) ────────────────────
       Data z: stats.py → _user_scatter() → [{x: čas/otázku, y: skóre%, label: název}]
       Každý bod = jeden pokus. X = průměrný čas na otázku, Y = procentuální skóre. */
    (function () {
        var el = document.getElementById('scatterChart');
        if (!el || !d.scatter) return;
        if (!d.scatter.length) { emptyMsg('scatterChart', 'Zatím žádné pokusy.'); return; }
        new C(el, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Pokus',
                    data: d.scatter,
                    backgroundColor: pink + '0.6)',
                    borderColor: pink + '1)',
                    pointRadius: 5,
                    pointHoverRadius: 7
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                var p = ctx.raw;
                                return p.label + ': ' + p.y + '% za ' + p.x + 's/ot.';
                            }
                        }
                    },
                    legend: { display: false }
                },
                scales: {
                    x: { title: { display: true, text: 'Průměrný čas na otázku (s)' }, grid: { color: '#1e293b' } },
                    y: { title: { display: true, text: 'Skóre (%)' }, beginAtZero: true, max: 100, grid: { color: '#1e293b' } }
                }
            }
        });
    })();

    /* ── Mastery: skóre podle kategorií (user dashboard) ────────────────────
       Data z: stats.py → _user_mastery() → {labels, data (avg %), attempts}
       Barvy podle skóre – stejná logika jako catBarChart. */
    (function () {
        var el = document.getElementById('masteryChart');
        if (!el || !d.mastery) return;
        if (!d.mastery.labels || !d.mastery.labels.length) {
            emptyMsg('masteryChart', 'Min. 2 pokusy v kategorii.');
            return;
        }
        // Barvy podle úspěšnosti – stejná logika jako catBarChart
        var colors = d.mastery.data.map(function (v) {
        new C(el, {
            type: 'bar',
            data: {
                labels: d.mastery.labels,
                datasets: [{
                    label: 'Průměrné skóre %',
                    data: d.mastery.data,
                    backgroundColor: colors,
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, max: 100, grid: { color: '#1e293b' } },
                    y: { grid: { display: false } }
                }
            }
        });
    })();
});
