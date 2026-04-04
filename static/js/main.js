/**
 * Braniac - Hlavní JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Mobile navigation toggle
    const navToggle = document.getElementById('navToggle');
    const navMenu = document.querySelector('.nav-menu');
    
    if (navToggle && navMenu) {
        navToggle.addEventListener('click', function() {
            navMenu.classList.toggle('active');
        });
    }
    
    // Auto-hide flash messages
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(function(flash) {
        setTimeout(function() {
            flash.style.animation = 'slideOut 0.3s ease forwards';
            setTimeout(function() {
                flash.remove();
            }, 300);
        }, 5000);
    });
    
    // Add slideOut animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0; }
        }
    `;
    document.head.appendChild(style);
});

/**
 * Pomocná funkce pro HTTP požadavky
 */
async function fetchAPI(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
    };
    
    const response = await fetch(url, { ...defaultOptions, ...options });
    
    if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Chyba serveru' }));
        throw new Error(error.error || 'Něco se pokazilo');
    }
    
    return response.json();
}

/**
 * Formátování času
 */
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Achievement Pop-Up Notification System
 */
function showAchievementToast(achievement) {
    const container = document.getElementById('achievement-notifications');
    if (!container) return;

    const tierLabels = { gold: '🥇 Zlatý úspěch', silver: '🥈 Stříbrný úspěch', bronze: '🥉 Bronzový úspěch' };

    const toast = document.createElement('div');
    toast.className = `achievement-toast tier-${achievement.tier}`;
    toast.innerHTML = `
        <div class="achievement-toast-icon">
            <img src="/static/assets/achievements/${achievement.icon}" alt="">
        </div>
        <div class="achievement-toast-content">
            <span class="achievement-toast-label ${achievement.tier}">${tierLabels[achievement.tier] || 'Úspěch'}</span>
            <span class="achievement-toast-name">${achievement.name}</span>
            <span class="achievement-toast-msg">Gratulujeme! 🎉</span>
        </div>
    `;
    container.appendChild(toast);

    // Auto-dismiss after 4 seconds
    setTimeout(function() {
        toast.classList.add('removing');
        setTimeout(function() { toast.remove(); }, 350);
    }, 4000);
}

function showAchievementQueue(achievements) {
    if (!achievements || achievements.length === 0) return;
    var delay = 0;
    achievements.forEach(function(ach) {
        setTimeout(function() { showAchievementToast(ach); }, delay);
        delay += 800; // stagger multiple notifications
    });
}

/**
 * Leaderboard – live player-name search (starts-with, case-insensitive)
 */
(function() {
    var search = document.getElementById('leaderboard-search');
    if (!search) return;
    var rows = document.querySelectorAll('#leaderboard-body tr');
    var noMatch = document.getElementById('leaderboard-no-match');

    search.addEventListener('input', function() {
        var value = this.value.toLowerCase();
        var visible = 0;
        rows.forEach(function(row) {
            var name = row.getAttribute('data-name') || '';
            var show = name.startsWith(value);
            row.style.display = show ? '' : 'none';
            if (show) visible++;
        });
        if (noMatch) noMatch.style.display = visible === 0 ? '' : 'none';
    });
})();

/**
 * Leaderboard – quiz search filter (custom dropdown)
 */
(function() {
    var input = document.getElementById('quiz-search');
    if (!input) return;
    var hidden = document.getElementById('quiz-search-id');
    var form = input.closest('form');
    var dropdown = document.getElementById('quiz-search-dropdown');
    var options = dropdown.querySelectorAll('.quiz-search-option');

    function filterOptions() {
        var val = input.value.toLowerCase();
        var any = false;
        options.forEach(function(opt) {
            var match = opt.getAttribute('data-name').toLowerCase().indexOf(val) !== -1;
            opt.classList.toggle('hidden', !match);
            if (match) any = true;
        });
        dropdown.classList.toggle('active', any && val.length > 0);
    }

    input.addEventListener('focus', function() {
        if (input.value.length > 0) filterOptions();
    });

    input.addEventListener('input', function() {
        if (this.value === '' && hidden.value) {
            hidden.value = '';
            form.submit();
            return;
        }
        filterOptions();
    });

    options.forEach(function(opt) {
        opt.addEventListener('mousedown', function(e) {
            e.preventDefault();
            input.value = opt.getAttribute('data-name');
            hidden.value = opt.getAttribute('data-id');
            dropdown.classList.remove('active');
            form.submit();
        });
    });

    input.addEventListener('blur', function() {
        dropdown.classList.remove('active');
    });
})();

/**
 * Leaderboard – custom difficulty select
 */
(function() {
    var select = document.getElementById('difficulty-select');
    if (!select) return;
    var trigger = document.getElementById('difficulty-trigger');
    var hidden = document.getElementById('difficulty-value');
    var form = select.closest('form');
    var options = select.querySelectorAll('.custom-select-option');

    trigger.addEventListener('click', function() {
        select.classList.toggle('open');
    });

    options.forEach(function(opt) {
        opt.addEventListener('mousedown', function(e) {
            e.preventDefault();
            hidden.value = opt.getAttribute('data-value');
            trigger.firstChild.textContent = opt.textContent;
            select.classList.remove('open');
            form.submit();
        });
    });

    document.addEventListener('click', function(e) {
        if (!select.contains(e.target)) {
            select.classList.remove('open');
        }
    });
})();

/**
 * Leaderboard – mini-profile hover popover
 */
function _mpEsc(str) {
    var d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

(function() {
    var popover = document.getElementById('mp-popover');
    if (!popover) return;

    var body = document.getElementById('mp-body');
    var cache = {};
    var showTimer = null;
    var hideTimer = null;
    var currentUserId = null;

    function buildHtml(data) {
        var avatarHtml;
        if (data.avatar_img) {
            avatarHtml = '<img src="/static/assets/' + encodeURIComponent(data.avatar_img) + '" alt="" class="mp-avatar mp-avatar-img">';
        } else {
            avatarHtml = '<div class="mp-avatar">' + _mpEsc(data.avatar) + '</div>';
        }
        var html = '<div class="mp-header">' +
            avatarHtml +
            '<div><strong>' + _mpEsc(data.name) + '</strong></div>' +
        '</div>';

        html += '<div class="mp-stats">' +
            '<div class="mp-stat"><span class="mp-stat-value">' + data.stats.total_games + '</span><span class="mp-stat-label">Her</span></div>' +
            '<div class="mp-stat"><span class="mp-stat-value">' + data.stats.average_score + '%</span><span class="mp-stat-label">Průměrné skóre</span></div>' +
            '<div class="mp-stat"><span class="mp-stat-value">' + data.stats.best_score + '%</span><span class="mp-stat-label">Nejlepší</span></div>' +
            '<div class="mp-stat"><span class="mp-stat-value">' + data.stats.perfect_count + '</span><span class="mp-stat-label">💯 Perfektní</span></div>' +
        '</div>';

        if (data.favorite_category) {
            html += '<div class="mp-section"><div class="mp-section-title">Oblíbená kategorie</div>' +
                '<span>' + _mpEsc(data.favorite_category) + '</span></div>';
        }
        if (data.best_category) {
            html += '<div class="mp-section"><div class="mp-section-title">Nejsilnější kategorie</div>' +
                '<span>' + _mpEsc(data.best_category.name) + ' (' + data.best_category.score + '%)</span></div>';
        }

        if (data.achievements && data.achievements.length > 0) {
            html += '<div class="mp-section"><div class="mp-section-title">Nejlepší úspěchy</div>';
            data.achievements.forEach(function(a) {
                var tierIcon = a.tier === 'gold' ? '🥇' : a.tier === 'silver' ? '🥈' : '🥉';
                html += '<div class="mp-achievement">' +
                    '<img src="/static/assets/achievements/' + encodeURIComponent(a.icon) + '" alt="">' +
                    '<span class="mp-achievement-name">' + _mpEsc(a.name) + '</span>' +
                    '<span class="mp-achievement-tier">' + tierIcon + '</span></div>';
            });
            html += '</div>';
        }

        return html;
    }

    function positionPopover(el) {
        var rect = el.getBoundingClientRect();
        var pw = 340;
        var left = rect.right + 12;
        var top = rect.top + rect.height / 2;

        // If not enough space on the right, show on the left
        if (left + pw > window.innerWidth - 8) {
            left = rect.left - pw - 12;
        }
        if (left < 8) left = 8;

        // Vertically center on the name, but clamp within viewport
        popover.style.left = left + 'px';
        popover.style.top = top + 'px';
        // After rendering, adjust if it overflows bottom
        var ph = popover.offsetHeight;
        if (top + ph > window.innerHeight - 8) {
            top = window.innerHeight - ph - 8;
        }
        if (top < 8) top = 8;
        popover.style.top = top + 'px';
    }

    function showPopover(el) {
        var userId = el.getAttribute('data-user-id');
        if (!userId) return;
        currentUserId = userId;

        if (cache[userId]) {
            body.innerHTML = cache[userId];
            popover.classList.add('active');
            positionPopover(el);
            return;
        }

        body.innerHTML = '<p class="text-muted text-center">Načítání…</p>';
        popover.classList.add('active');
        positionPopover(el);

        fetch('/leaderboard/profile/' + encodeURIComponent(userId))
            .then(function(r) { return r.json(); })
            .then(function(data) {
                var html = buildHtml(data);
                cache[userId] = html;
                if (currentUserId === userId) {
                    body.innerHTML = html;
                    positionPopover(el);
                }
            })
            .catch(function() {
                if (currentUserId === userId) {
                    body.innerHTML = '<p class="text-muted text-center">Nepodařilo se načíst profil.</p>';
                }
            });
    }

    function hidePopover() {
        popover.classList.remove('active');
        currentUserId = null;
    }

    document.querySelectorAll('.player-name.clickable').forEach(function(el) {
        el.addEventListener('mouseenter', function() {
            clearTimeout(hideTimer);
            var target = this;
            showTimer = setTimeout(function() { showPopover(target); }, 300);
        });
        el.addEventListener('mouseleave', function() {
            clearTimeout(showTimer);
            hideTimer = setTimeout(hidePopover, 200);
        });
    });

    popover.addEventListener('mouseenter', function() {
        clearTimeout(hideTimer);
    });
    popover.addEventListener('mouseleave', function() {
        hideTimer = setTimeout(hidePopover, 200);
    });
})();
