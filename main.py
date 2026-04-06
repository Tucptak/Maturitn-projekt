"""
Hlavní soubor Flask aplikace - Brainiac.

Toto je vstupní bod celé webové aplikace. Zde se:
  1. Vytváří Flask instance a nastavuje SECRET_KEY (pro session cookies)
  2. Aktivuje CSRF ochrana (Flask-WTF) na všechny POST formuláře
  3. Inicializuje databáze (database.py → MySQL)
  4. Seedují výchozí achievementy do DB (achievements.py)
  5. Nastavuje Flask-Login pro správu přihlášení
  6. Registrují všechny blueprinty (moduly aplikace):
     - auth_bp   → /login, /register, /profile, …     (auth.py)
     - quiz_bp   → /quizzes, /quiz/<id>, …              (quiz.py)
     - admin_bp  → /admin/…                              (admin.py)
     - api_bp    → /api/… (CSRF výjimka – desktop app)  (api.py)
     - stats_bp  → /stats/…                              (stats.py)
  7. Definuje hlavní stránku (/) a chybové stránky (404, 500)

Spuštění: python main.py → Flask dev server na http://localhost:5000
"""
import os
from flask import Flask, render_template, request
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

# Načtení environment proměnných z .env souboru (DB heslo, SECRET_KEY, …)
load_dotenv()

# Inicializace Flask aplikace
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# CSRF ochrana – automaticky vyžaduje token u každého POST požadavku.
# Tokeny se vkládají do formulářů pomocí {{ csrf_token() }} v šablonách
# a do JS fetch požadavků přes hlavičku X-CSRFToken (viz quiz.js).
csrf = CSRFProtect(app)

# Inicializace databáze – propojí SQLAlchemy s Flask a vytvoří tabulky
from database import init_db, db
init_db(app)

# Seed achievementů – naplní tabulku 'achievements' výchozími daty,
# pokud je prázdná (viz ACHIEVEMENT_DEFINITIONS v achievements.py)
with app.app_context():
    from achievements import seed_achievements
    seed_achievements()

# Flask-Login – správa přihlašovacích sessions.
# login_view = kam přesměrovat nepřihlášené uživatele.
from auth import auth_bp, login_manager
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Pro přístup k této stránce se musíte přihlásit.'
login_manager.login_message_category = 'warning'

# Registrace blueprintů – každý modul má svůj Blueprint s vlastními routami
app.register_blueprint(auth_bp)

from quiz import quiz_bp
app.register_blueprint(quiz_bp)

from admin import admin_bp
app.register_blueprint(admin_bp)

# API blueprint je vyňat z CSRF ochrany, protože desktopová aplikace
# (desktop_app.py) posílá JSON požadavky bez CSRF tokenu.
from api import api_bp
app.register_blueprint(api_bp)
csrf.exempt(api_bp)

from stats import stats_bp
app.register_blueprint(stats_bp)


@app.route('/')
def index():
    """Hlavní stránka – zobrazuje nejnovější a nejpopulárnější kvízy."""
    from models import Quiz, GameResult
    from flask_login import current_user
    
    # Nejnovější kvízy – posledních 6 podle data vytvoření
    recent_quizzes = Quiz.query.order_by(Quiz.created_at.desc()).limit(6).all()
    
    # Populární kvízy – 6 nejhranějších (GROUP BY quiz_id, seřazeno podle počtu her)
    from sqlalchemy import func
    popular_quiz_ids = db.session.query(
        GameResult.quiz_id,
        func.count(GameResult.id).label('play_count')
    ).group_by(GameResult.quiz_id).order_by(
        func.count(GameResult.id).desc()
    ).limit(6).all()
    
    popular_quizzes = []
    for quiz_id, play_count in popular_quiz_ids:
        quiz = Quiz.query.get(quiz_id)
        if quiz:
            popular_quizzes.append({'quiz': quiz, 'play_count': play_count})
    
    # Šablona: templates/index.html
    return render_template('index.html', 
                         recent_quizzes=recent_quizzes,
                         popular_quizzes=popular_quizzes)


@app.errorhandler(404)
def not_found(e):
    """Stránka nenalezena."""
    return render_template('errors/404.html'), 404


@app.errorhandler(500)
def server_error(e):
    """Interní chyba serveru."""
    return render_template('errors/500.html'), 500


if __name__ == "__main__":
    app.run(debug=True)