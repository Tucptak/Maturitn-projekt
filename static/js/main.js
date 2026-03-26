/**
 * QuizApp - Hlavní JavaScript
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
