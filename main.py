"""
Hlavní soubor Flask aplikace - Brainiac.
"""
import os
from flask import Flask, render_template
from dotenv import load_dotenv

# Načtení environment proměnných
load_dotenv()

# Inicializace Flask aplikace
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

# Inicializace databáze
from database import init_db, db
init_db(app)

# Seed achievementů
with app.app_context():
    from achievements import seed_achievements
    seed_achievements()

# Inicializace přihlašování
from auth import auth_bp, login_manager
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Pro přístup k této stránce se musíte přihlásit.'
login_manager.login_message_category = 'warning'

# Registrace blueprintů
app.register_blueprint(auth_bp)

from quiz import quiz_bp
app.register_blueprint(quiz_bp)

from admin import admin_bp
app.register_blueprint(admin_bp)

from api import api_bp
app.register_blueprint(api_bp)

from stats import stats_bp
app.register_blueprint(stats_bp)


@app.route('/')
def index():
    """Hlavní stránka."""
    from models import Quiz, GameResult
    from flask_login import current_user
    
    # Nejnovější kvízy
    recent_quizzes = Quiz.query.order_by(Quiz.created_at.desc()).limit(6).all()
    
    # Populární kvízy (nejvíce hraných)
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