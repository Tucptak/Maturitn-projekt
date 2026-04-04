/**
 * Braniac – Statistics chart rendering (Chart.js 4.x)
 */
document.addEventListener('DOMContentLoaded', function () {
    var C = window.Chart;
    if (!C) return;

    /* Dark theme defaults */
    C.defaults.color = '#cbd5e1';
    C.defaults.borderColor = '#334155';
    C.defaults.font.family = "'Segoe UI', system-ui, -apple-system, sans-serif";

    var d = window.statsData || {};
    var purple = 'rgba(99,102,241,';
    var teal   = 'rgba(34,211,154,';
    var amber  = 'rgba(245,158,11,';
    var pink   = 'rgba(236,72,153,';

    function hasData(arr) {
        return arr && arr.length > 0 && arr.some(function (v) { return v !== 0 && v !== null; });
    }

    function emptyMsg(id, msg) {
        var el = document.getElementById(id);
        if (!el) return;
        var p = document.createElement('p');
        p.className = 'stats-empty';
        p.textContent = msg || 'Nedostatek dat pro zobrazení grafu.';
        el.parentNode.replaceChild(p, el);
    }

    /* ── Distribution histogram (global) ── */
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

    /* ── Category bar chart (global) ── */
    (function () {
        var el = document.getElementById('catBarChart');
        if (!el || !d.cat_bars) return;
        if (!d.cat_bars.labels || !d.cat_bars.labels.length) {
            emptyMsg('catBarChart', 'Žádná data pro kategorie.');
            return;
        }
        var colors = d.cat_bars.data.map(function (v) {
            if (v >= 80) return 'rgba(34,197,94,0.7)';
            if (v >= 60) return 'rgba(99,102,241,0.7)';
            if (v >= 40) return 'rgba(245,158,11,0.7)';
            return 'rgba(239,68,68,0.7)';
        });
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

    /* ── Trend line (global) ── */
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

    /* ── Comparison: user vs global trend (user page) ── */
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

    /* ── Scatter: accuracy vs speed (user page) ── */
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

    /* ── Mastery horizontal bar (user page) ── */
    (function () {
        var el = document.getElementById('masteryChart');
        if (!el || !d.mastery) return;
        if (!d.mastery.labels || !d.mastery.labels.length) {
            emptyMsg('masteryChart', 'Min. 2 pokusy v kategorii.');
            return;
        }
        var colors = d.mastery.data.map(function (v) {
            if (v >= 80) return 'rgba(34,197,94,0.7)';
            if (v >= 60) return 'rgba(99,102,241,0.7)';
            if (v >= 40) return 'rgba(245,158,11,0.7)';
            return 'rgba(239,68,68,0.7)';
        });
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
