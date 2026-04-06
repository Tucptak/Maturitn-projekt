"""
Statistiky – globální dashboard a per-user deep-dive.

Tento modul obsahuje komplexní SQL dotazy pro zobrazování statistik:

Globální dashboard (/stats/):
  - Počítadla: celkem her, správných odpovědí, aktivních hráčů
  - Feed posledních her
  - Hot topics (nejhranější kategorie)
  - Histogram rozložení skóre (10% biny)
  - Sloupcový graf kategorií podle průměrného skóre
  - Trendová čára (průměrné skóre v čase)
  - Nejtěžší otázky (nejvyšší error rate)

Per-user dashboard (/stats/user/<id>):
  - Scatter plot: přesnost vs rychlost
  - Série (streaky): nejdelší řada perfektních výsledků
  - Mastery: průměrné skóre podle kategorií
  - Porovnání s globálním průměrem
  - Osobní rekordy v každé kategorii

Všechny grafy podporují filtry (period + category) přes query string.
AJAX varianty (/stats/api/...) vrací JSON pro dynamické přenačítání bez refreshe.
CSV export umožňuje stažení dat.

Blueprint: stats_bp (URL prefix: /stats)
Šablony: templates/stats.html, templates/user_stats.html
"""
import csv
import io
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, Response, abort
from flask_login import current_user, login_required
from sqlalchemy import func, case
from database import db
from models import User, Quiz, Question, Answer, GameResult, UserAnswer, pct

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


# ── Helpers ──────────────────────────────────────────────────────────────────# Všechny helper funkce přijímají (since, category) filtry.
# 'since' je datetime objekt nebo None, 'category' je string nebo ''.
def _parse_filters():
    """Parse časového období a kategorie z query stringu.
    
    Používá se ve všech routach tohoto modulu.
    Vrací (period_str, category_str, since_datetime_or_None).
    """
    period = request.args.get('period', '30d')
    category = request.args.get('category', '')
    now = datetime.utcnow()
    if period == 'today':
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == '7d':
        since = now - timedelta(days=7)
    elif period == '30d':
        since = now - timedelta(days=30)
    else:
        since = None
    return period, category, since


def _base_q(since=None, category=None):
    """Základní GameResult dotaz s volitelnými filtry.
    
    JOIN na Quiz je nutný pro filtrování podle kategorie.
    Na tuto funkci navazují další buildery.
    """
    q = GameResult.query.join(Quiz, GameResult.quiz_id == Quiz.id)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    return q


def _categories():
    return [c[0] for c in db.session.query(Quiz.category).distinct().order_by(Quiz.category).all()]


# ── Global data builders ────────────────────────────────────────────────────

def _counters(since, category):
    """Základní počítadla: celkem her, správných odpovědí, aktivních hráčů.
    
    Každé počítadlo je samostatný SQL dotaz s COUNT/DISTINCT.
    """
    q = GameResult.query
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.join(Quiz, GameResult.quiz_id == Quiz.id).filter(Quiz.category == category)
    total_games = q.count()

    ua_q = db.session.query(func.count(UserAnswer.id)).join(
        GameResult, UserAnswer.game_id == GameResult.id
    ).filter(UserAnswer.is_correct == True)
    if since:
        ua_q = ua_q.filter(GameResult.date >= since)
    if category:
        ua_q = ua_q.join(Quiz, GameResult.quiz_id == Quiz.id).filter(Quiz.category == category)
    total_correct = ua_q.scalar() or 0

    user_q = db.session.query(func.count(func.distinct(GameResult.user_id)))
    if since:
        user_q = user_q.filter(GameResult.date >= since)
    if category:
        user_q = user_q.join(Quiz, GameResult.quiz_id == Quiz.id).filter(Quiz.category == category)
    total_players = user_q.scalar() or 0

    return {'total_games': total_games, 'total_correct': total_correct, 'total_players': total_players}


def _recent_feed(since, category, limit=20):
    """Posledních N odehraných her – feed na dashboardu.
    
    JOIN přes User pro jméno a avatar, přes Quiz pro název a kategorii.
    """
    q = _base_q(since, category).join(
        User, GameResult.user_id == User.id
    ).order_by(GameResult.date.desc()).limit(limit)
    feed = []
    for gr in q.all():
        pct = round(gr.score / gr.max_score * 100) if gr.max_score > 0 else 0
        feed.append({
            'user_name': gr.user.name,
            'user_avatar': gr.user.avatar,
            'user_id': gr.user.id,
            'user_initial': gr.user.name[0].upper() if gr.user.name else '?',
            'quiz_name': gr.quiz.name,
            'quiz_category': gr.quiz.category,
            'score_pct': pct,
            'time_spent': gr.time_spent,
            'date': gr.date.strftime('%d.%m. %H:%M') if gr.date else ''
        })
    return feed


def _hot_topics(since, category, limit=8):
    """Nejhranější kategorie (min 10 her) – GROUP BY Quiz.category."""
    q = db.session.query(
        Quiz.category, func.count(GameResult.id).label('cnt')
    ).join(Quiz, GameResult.quiz_id == Quiz.id)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    return [{'category': r[0], 'count': r[1]}
            for r in q.group_by(Quiz.category).having(
                func.count(GameResult.id) >= 10
            ).order_by(func.count(GameResult.id).desc()).limit(limit).all()]


def _distribution(since, category):
    """Histogram rozložení skóre v 10% binech (reálná data, ne syntetická křivka).
    
    Rozdělí všechny výsledky do 10 košů: 0–10%, 10–20%, ..., 90–100%.
    """
    rows = _base_q(since, category).filter(
        GameResult.max_score > 0
    ).with_entities(GameResult.score, GameResult.max_score).all()
    bins = [0] * 10
    for s, m in rows:
        bins[min(int(s / m * 10), 9)] += 1
    return {'labels': [f'{i * 10}\u2013{(i + 1) * 10}%' for i in range(10)], 'data': bins}


def _category_bars(since, category, limit=8):
    """Top kategorie podle průměrného skóre (min 8 her) – horizontální sloupcový graf."""
    q = db.session.query(
        Quiz.category,
        func.avg(GameResult.score * 100.0 / GameResult.max_score),
        func.count(GameResult.id)
    ).join(Quiz, GameResult.quiz_id == Quiz.id).filter(GameResult.max_score > 0)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    rows = q.group_by(Quiz.category).having(
        func.count(GameResult.id) >= 8
    ).order_by(
        func.avg(GameResult.score * 100.0 / GameResult.max_score).desc()
    ).limit(limit).all()
    return {'labels': [r[0] for r in rows],
            'data': [pct(float(r[1])) for r in rows],
            'counts': [r[2] for r in rows]}


def _trend(since, category, period='30d'):
    """Trendová čára průměrného skóre v čase.
    
    Pro 'today': seskupení po hodinách, jinak po dnech.
    Pokud zvolené období nemá data, rozšíří se na všechna dostupná data.
    Downsample: 30d → každý 3. den, alltime → každý 9. den (méně teček v grafu).
    """
    effective = since or (datetime.utcnow() - timedelta(days=90))
    hourly = (period == 'today')

    def _query(dt_from):
        if hourly:
            group_col = func.date_format(GameResult.date, '%H:00')
        else:
            group_col = func.date(GameResult.date)
        q = db.session.query(
            group_col,
            func.avg(GameResult.score * 100.0 / GameResult.max_score)
        ).join(Quiz, GameResult.quiz_id == Quiz.id).filter(
            GameResult.max_score > 0, GameResult.date >= dt_from)
        if category:
            q = q.filter(Quiz.category == category)
        return {str(r[0]): round(float(r[1]), 1)
                for r in q.group_by(group_col).order_by(group_col).all()}

    data = _query(effective)
    # If the selected period has no data, widen to all available data.
    if not data and since is not None:
        data = _query(datetime(2000, 1, 1))

    # Build a complete x-axis so the graph always has all slots filled.
    now = datetime.utcnow()
    if hourly:
        slots = [f'{h:02d}:00' for h in range(24)]
    elif period == '7d':
        slots = [str((now - timedelta(days=6 - i)).date()) for i in range(7)]
    elif period == '30d':
        slots = [str((now - timedelta(days=29 - i)).date()) for i in range(30)]
    else:
        # alltime: span from 90 days ago (or earliest data point) to today
        if data:
            earliest = min(datetime.strptime(k, '%Y-%m-%d') for k in data.keys())
            start = min(earliest, now - timedelta(days=90))
        else:
            start = now - timedelta(days=90)
        days = (now - start).days + 1
        slots = [str((start + timedelta(days=i)).date()) for i in range(days)]

    labels = slots
    values = [data.get(s, 0) for s in slots]

    # Downsample 30d / alltime to reduce dot clutter
    step = 3 if period == '30d' else 9 if period not in ('today', '7d') else 0
    if step and len(labels) > step:
        new_labels, new_values = [], []
        for i in range(0, len(labels), step):
            chunk = values[i:i + step]
            non_zero = [v for v in chunk if v]
            avg = round(sum(non_zero) / len(non_zero), 1) if non_zero else 0
            new_labels.append(labels[i])
            new_values.append(avg)
        labels, values = new_labels, new_values

    return {'labels': labels, 'data': values}


def _hardest_global(since, category, limit=10):
    """Nejtěžší otázky globálně – seřazené podle % špatných odpovědí.
    
    JOIN: Question → UserAnswer → GameResult → Quiz.
    HAVING: min 3 pokusy (aby statistika měla smysl).
    Používá CASE expression pro počítání špatných odpovědí.
    """
    q = db.session.query(
        Question.text, Quiz.name, Quiz.category,
        func.count(UserAnswer.id).label('total'),
        func.sum(case((UserAnswer.is_correct == False, 1), else_=0)).label('wrong')
    ).join(UserAnswer, UserAnswer.question_id == Question.id
    ).join(GameResult, UserAnswer.game_id == GameResult.id
    ).join(Quiz, Question.quiz_id == Quiz.id)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    rows = q.group_by(Question.id, Question.text, Quiz.name, Quiz.category).having(
        func.count(UserAnswer.id) >= 3
    ).order_by(
        (func.sum(case((UserAnswer.is_correct == False, 1), else_=0)) * 100.0 / func.count(UserAnswer.id)).desc()
    ).limit(limit).all()
    return [{'text': r[0], 'quiz': r[1], 'category': r[2], 'attempts': r[3],
             'wrong_rate': pct(r[4] / r[3] * 100) if r[3] else 0} for r in rows]


# ── Per-user data builders ──────────────────────────────────────────────────

def _user_scatter(uid, since, category):
    """Scatter plot: přesnost (Y) vs rychlost (X) – každý bod = jeden pokus.

    X = průměrný čas na otázku (time_spent / max_score).
    Přesný čas na otázku není dostupný; toto je nejlepší aproximace.
    """
    q = GameResult.query.join(Quiz, GameResult.quiz_id == Quiz.id).filter(
        GameResult.user_id == uid, GameResult.max_score > 0)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    return [{'x': round(gr.time_spent / gr.max_score, 1),
             'y': pct(gr.score / gr.max_score * 100),
             'label': gr.quiz.name} for gr in q.all()]


def _user_streaks(uid):
    """Statistiky sérií: celkem správných, celkem odpovědí, nejdelší perfektní série."""
    results = GameResult.query.filter_by(user_id=uid).order_by(GameResult.date).all()
    total_correct = db.session.query(func.count(UserAnswer.id)).join(
        GameResult, UserAnswer.game_id == GameResult.id
    ).filter(GameResult.user_id == uid, UserAnswer.is_correct == True).scalar() or 0
    total_answered = db.session.query(func.count(UserAnswer.id)).join(
        GameResult, UserAnswer.game_id == GameResult.id
    ).filter(GameResult.user_id == uid).scalar() or 0

    longest = current = 0
    for gr in results:
        if gr.max_score > 0 and gr.score == gr.max_score:
            current += 1
            longest = max(longest, current)
        else:
            current = 0

    return {'total_correct': total_correct, 'total_answered': total_answered,
            'longest_perfect_streak': longest, 'total_games': len(results)}


def _user_mastery(uid, since, category):
    """Sloupcový graf: průměrné skóre uživatele v každé kategorii (min 2 pokusy)."""
    q = db.session.query(
        Quiz.category,
        func.avg(GameResult.score * 100.0 / GameResult.max_score),
        func.count(GameResult.id)
    ).join(Quiz, GameResult.quiz_id == Quiz.id).filter(
        GameResult.user_id == uid, GameResult.max_score > 0)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    rows = q.group_by(Quiz.category).having(func.count(GameResult.id) >= 2).order_by(
        func.avg(GameResult.score * 100.0 / GameResult.max_score).desc()).all()
    return {'labels': [r[0] for r in rows],
            'data': [pct(float(r[1])) for r in rows],
            'attempts': [r[2] for r in rows]}


def _user_comparison(uid, since, category, period='30d'):
    """Trendová čára uživatele překrytá globálním průměrem.
    
    Dva datasety se stejnými časovými sloty (labels):
      - user_data: průměrné skóre uživatele
      - global_data: průměrné skóre všech hráčů
    """
    effective = since or (datetime.utcnow() - timedelta(days=90))
    hourly = (period == 'today')

    def _q(dt_from, user_filter=None):
        if hourly:
            group_col = func.date_format(GameResult.date, '%H:00')
        else:
            group_col = func.date(GameResult.date)
        q = db.session.query(
            group_col,
            func.avg(GameResult.score * 100.0 / GameResult.max_score)
        ).join(Quiz, GameResult.quiz_id == Quiz.id).filter(
            GameResult.max_score > 0, GameResult.date >= dt_from)
        if category:
            q = q.filter(Quiz.category == category)
        if user_filter is not None:
            q = q.filter(GameResult.user_id == user_filter)
        return {str(r[0]): round(float(r[1]), 1)
                for r in q.group_by(group_col).order_by(group_col).all()}

    u, g = _q(effective, uid), _q(effective)
    # If the selected period has no data, widen to all available data.
    if not u and not g and since is not None:
        fallback = datetime(2000, 1, 1)
        u, g = _q(fallback, uid), _q(fallback)

    # Build a complete x-axis.
    now = datetime.utcnow()
    if hourly:
        slots = [f'{h:02d}:00' for h in range(24)]
    elif period == '7d':
        slots = [str((now - timedelta(days=6 - i)).date()) for i in range(7)]
    elif period == '30d':
        slots = [str((now - timedelta(days=29 - i)).date()) for i in range(30)]
    else:
        # alltime: span from 90 days ago (or earliest data point) to today
        all_keys = set(u) | set(g)
        if all_keys:
            earliest = min(datetime.strptime(k, '%Y-%m-%d') for k in all_keys)
            start = min(earliest, now - timedelta(days=90))
        else:
            start = now - timedelta(days=90)
        days = (now - start).days + 1
        slots = [str((start + timedelta(days=i)).date()) for i in range(days)]

    labels = slots
    user_vals = [u.get(s, 0) for s in slots]
    global_vals = [g.get(s, 0) for s in slots]

    # Downsample 30d / alltime to reduce dot clutter
    step = 3 if period == '30d' else 9 if period not in ('today', '7d') else 0
    if step and len(labels) > step:
        new_labels, new_user, new_global = [], [], []
        for i in range(0, len(labels), step):
            u_chunk = [v for v in user_vals[i:i + step] if v]
            g_chunk = [v for v in global_vals[i:i + step] if v]
            new_labels.append(labels[i])
            new_user.append(round(sum(u_chunk) / len(u_chunk), 1) if u_chunk else 0)
            new_global.append(round(sum(g_chunk) / len(g_chunk), 1) if g_chunk else 0)
        labels, user_vals, global_vals = new_labels, new_user, new_global

    return {'labels': labels,
            'user_data': user_vals,
            'global_data': global_vals}


def _user_hardest(uid, since, category, limit=10):
    """Nejtěžší otázky pro konkrétního uživatele (kde nejvíc chyboval)."""
    q = db.session.query(
        Question.text, Quiz.name, Quiz.category,
        func.count(UserAnswer.id).label('total'),
        func.sum(case((UserAnswer.is_correct == False, 1), else_=0)).label('wrong')
    ).join(UserAnswer, UserAnswer.question_id == Question.id
    ).join(GameResult, UserAnswer.game_id == GameResult.id
    ).join(Quiz, Question.quiz_id == Quiz.id
    ).filter(GameResult.user_id == uid)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    rows = q.group_by(Question.id, Question.text, Quiz.name, Quiz.category).having(
        func.sum(case((UserAnswer.is_correct == False, 1), else_=0)) > 0
    ).order_by(
        (func.sum(case((UserAnswer.is_correct == False, 1), else_=0)) * 100.0 / func.count(UserAnswer.id)).desc()
    ).limit(limit).all()
    return [{'text': r[0], 'quiz': r[1], 'category': r[2], 'attempts': r[3],
             'wrong_rate': pct(r[4] / r[3] * 100) if r[3] else 0} for r in rows]


def _user_personal_bests(uid):
    """Osobní rekordy uživatele v každé kategorii (nejlepší skóre + nejrychlejší)."""
    rows = db.session.query(
        Quiz.category, GameResult.score, GameResult.max_score,
        GameResult.time_spent, Quiz.name, GameResult.date
    ).join(Quiz, GameResult.quiz_id == Quiz.id).filter(
        GameResult.user_id == uid, GameResult.max_score > 0).all()

    bests = {}
    for cat, score, mx, time_s, qname, dt in rows:
        score_pct = score / mx * 100
        if cat not in bests:
            bests[cat] = {'category': cat,
                          'best_pct': score_pct, 'best_quiz': qname, 'best_date': dt,
                          'fastest': time_s, 'fast_quiz': qname, 'fast_date': dt}
        else:
            b = bests[cat]
            if score_pct > b['best_pct'] or (score_pct == b['best_pct'] and dt and b['best_date'] and dt < b['best_date']):
                b.update(best_pct=score_pct, best_quiz=qname, best_date=dt)
            if time_s < b['fastest'] or (time_s == b['fastest'] and dt and b['fast_date'] and dt < b['fast_date']):
                b.update(fastest=time_s, fast_quiz=qname, fast_date=dt)

    for v in bests.values():
        v['best_pct'] = pct(v['best_pct'])
        v['best_date'] = v['best_date'].strftime('%d.%m.%Y') if v['best_date'] else ''
        v['fast_date'] = v['fast_date'].strftime('%d.%m.%Y') if v['fast_date'] else ''
    return sorted(bests.values(), key=lambda x: -x['best_pct'])


# ── Routes ──────────────────────────────────────────────────────────────────
# Každá HTML routa předá data do templates/stats.html nebo user_stats.html.
# Šablony uloží data do window.statsData (JavaScript objekt) →
# stats.js je potom načte a vykreslí grafy pomocí Chart.js.

@stats_bp.route('/')
def global_stats():
    """Global community statistics dashboard.
    
    Volá všechny _builder funkce a předá výsledky do stats.html.
    Stats.html uloží data do window.statsData → stats.js je vykreslí.
    """
    period, category, since = _parse_filters()
    cats = _categories()
    return render_template('stats.html',
                           period=period, category=category, categories=cats,
                           counters=_counters(since, category),
                           feed=_recent_feed(since, category),
                           hot_topics=_hot_topics(since, category),
                           distribution=_distribution(since, category),
                           cat_bars=_category_bars(since, category),
                           trend=_trend(since, category, period),
                           hardest=_hardest_global(since, category))


@stats_bp.route('/api/global')
def api_global():
    """JSON pro AJAX filtrování (globální) – voláno při změně period/category bez refreshe."""
    period, category, since = _parse_filters()
    return jsonify(counters=_counters(since, category),
                   feed=_recent_feed(since, category),
                   hot_topics=_hot_topics(since, category),
                   distribution=_distribution(since, category),
                   cat_bars=_category_bars(since, category),
                   trend=_trend(since, category, period),
                   hardest=_hardest_global(since, category))


@stats_bp.route('/user/<int:user_id>')
def user_stats(user_id):
    """Per-user statistics deep-dive."""
    user = User.query.get_or_404(user_id)
    period, category, since = _parse_filters()
    cats = _categories()
    return render_template('user_stats.html',
                           target_user=user,
                           period=period, category=category, categories=cats,
                           streaks=_user_streaks(user_id),
                           scatter=_user_scatter(user_id, since, category),
                           mastery=_user_mastery(user_id, since, category),
                           comparison=_user_comparison(user_id, since, category, period),
                           hardest=_user_hardest(user_id, since, category),
                           personal_bests=_user_personal_bests(user_id))


@stats_bp.route('/api/user/<int:user_id>')
def api_user(user_id):
    """JSON pro AJAX filtrování (per-user) – voláno při změně period/category."""
    User.query.get_or_404(user_id)
    period, category, since = _parse_filters()
    return jsonify(scatter=_user_scatter(user_id, since, category),
                   mastery=_user_mastery(user_id, since, category),
                   comparison=_user_comparison(user_id, since, category, period),
                   hardest=_user_hardest(user_id, since, category))


@stats_bp.route('/export/csv')
@login_required
def export_csv():
    """Export globálních výsledků jako CSV soubor.
    
    BOM (\ufeff) na začátku zajistí správné zobrazení češtiny v Excelu.
    """
    period, category, since = _parse_filters()
    q = _base_q(since, category).join(User, GameResult.user_id == User.id).order_by(GameResult.date.desc())

    buf = io.StringIO()
    buf.write('\ufeff')  # BOM for Excel
    w = csv.writer(buf)
    w.writerow(['Uživatel', 'Kvíz', 'Kategorie', 'Skóre', 'Max', '%', 'Čas (s)', 'Datum'])
    for gr in q.all():
        w.writerow([gr.user.name, gr.quiz.name, gr.quiz.category, gr.score, gr.max_score,
                     round(gr.score / gr.max_score * 100, 1) if gr.max_score > 0 else 0,
                     gr.time_spent, gr.date.strftime('%Y-%m-%d %H:%M:%S') if gr.date else ''])
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': 'attachment; filename=Brainiac_statistiky.csv'})


@stats_bp.route('/export/user/<int:user_id>/csv')
@login_required
def export_user_csv(user_id):
    """Export historie her uživatele jako CSV (jen vlastní nebo admin)."""
    user = User.query.get_or_404(user_id)
    if current_user.id != user_id and not current_user.is_admin():
        abort(403)

    period, category, since = _parse_filters()
    q = GameResult.query.join(Quiz, GameResult.quiz_id == Quiz.id).filter(
        GameResult.user_id == user_id)
    if since:
        q = q.filter(GameResult.date >= since)
    if category:
        q = q.filter(Quiz.category == category)
    q = q.order_by(GameResult.date.desc())

    buf = io.StringIO()
    buf.write('\ufeff')
    w = csv.writer(buf)
    w.writerow(['Kvíz', 'Kategorie', 'Skóre', 'Max', '%', 'Čas (s)', 'Datum'])
    for gr in q.all():
        w.writerow([gr.quiz.name, gr.quiz.category, gr.score, gr.max_score,
                     round(gr.score / gr.max_score * 100, 1) if gr.max_score > 0 else 0,
                     gr.time_spent, gr.date.strftime('%Y-%m-%d %H:%M:%S') if gr.date else ''])
    buf.seek(0)
    return Response(buf.getvalue(), mimetype='text/csv',
                    headers={'Content-Disposition': f'attachment; filename=Brainiac_{user.name}_statistiky.csv'})
