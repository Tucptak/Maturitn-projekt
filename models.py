"""
Databázové modely pro quiz aplikaci.

Definuje 8 tabulek (modelů) a jejich vzájemné vztahy:

  User  ──1:N──  Quiz          (uživatel vytváří kvízy)
  User  ──1:N──  GameResult    (uživatel hraje hry)
  Quiz  ──1:N──  Question      (kvíz obsahuje otázky)
  Quiz  ──1:N──  GameResult    (ke kvízu patří výsledky)
  Question ─1:N─ Answer        (otázka má odpovědi)
  GameResult─1:N─UserAnswer    (výsledek hry má odpovědi)
  Achievement─1:N─UserAchievement (M:N mezi User a Achievement přes spojovací tabulku)

Kaskádové mazání: smazání kvízu automaticky smaže i jeho otázky,
odpovědi a výsledky her (cascade='all, delete-orphan').

Všechny modely importují db z database.py.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database import db


def pct(v):
    """Pomocná funkce pro formátování procent.
    
    Zaokrouhlí na 1 des. místo a odstraní zbytečnou '.0'.
    Příklad: 85.0 → 85, 72.3 → 72.3
    Používá se v quiz.py, stats.py, api.py pro zobrazení skóre.
    """
    r = round(v, 1)
    return int(r) if r == int(r) else r


class User(UserMixin, db.Model):
    """Model uživatele.
    
    UserMixin (z Flask-Login) přidává metody potřebné pro správu přihlášení:
    is_authenticated, is_active, get_id() – Flask-Login je volá automaticky.
    
    Tabulka: users1
    Vztahy: 1:N na Quiz (autor), 1:N na GameResult (odehraná hra)
    """
    __tablename__ = 'users1'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user' nebo 'admin'
    avatar = db.Column(db.String(255), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Vztahy (1:N) – backref vytváří zpětný odkaz:
    #   quiz.author → User objekt (používá se v šablonách: quiz.author.name)
    #   game_result.user → User objekt (používá se v stats.py: gr.user.name)
    quizzes = db.relationship('Quiz', backref='author', lazy=True)
    game_results = db.relationship('GameResult', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hashuje a uloží heslo (werkzeug pbkdf2, nikdy neukládáme plaintext)."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Ověří heslo proti hashi. Vrací True/False."""
        return check_password_hash(self.password, password)
    
    def is_admin(self):
        """Zkontroluje, zda je uživatel admin."""
        return self.role == 'admin'
    
    def get_stats(self):
        """Vrátí statistiky uživatele pro profil a mini-profil na leaderboardu.
        
        Voláno z:
          - auth.py:profile() → data se předá do templates/profile.html
          - quiz.py:mini_profile() → data se vrátí jako JSON pro main.js popover
          - api.py:api_user_stats() → data se vrátí jako JSON pro desktop app
          - test_brainiac.py:test_user_stats() → testuje správnost výpočtu
        """
        total_games = len(self.game_results)
        if total_games == 0:
            return {
                'total_games': 0,
                'average_score': 0,
                'best_score': 0,
                'total_quizzes_created': len(self.quizzes)
            }
        
        scores = [
            (r.score / r.max_score * 100) if r.max_score > 0 else 0
            for r in self.game_results
        ]
        return {
            'total_games': total_games,
            'average_score': pct(sum(scores) / len(scores)),
            'best_score': pct(max(scores)),
            'total_quizzes_created': len(self.quizzes)
        }


class Quiz(db.Model):
    """Model kvízu.
    
    Tabulka: quizzes
    Vztahy: 1:N na Question, 1:N na GameResult (oba s kaskádovým mazáním)
    Cizí klíč: author_id → users1.id (1:N – uživatel vytváří kvízy)
    """
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)  # 'easy', 'medium', 'hard'
    time_limit = db.Column(db.Integer, default=30)  # sekund na otázku
    author_id = db.Column(db.Integer, db.ForeignKey('users1.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Vztahy (1:N) – cascade='all, delete-orphan' = smazání kvízu smaže i otázky a výsledky
    #   quiz.questions → list Question objektů (používá se v quiz.py, api.py)
    #   quiz.game_results → list GameResult objektů (používá se v stats.py)
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    game_results = db.relationship('GameResult', backref='quiz', lazy=True, cascade='all, delete-orphan')
    
    def get_question_count(self):
        """Vrátí počet otázek v kvízu."""
        return len(self.questions)


class Question(db.Model):
    """Model otázky.
    
    Tabulka: questions
    Cizí klíč: quiz_id → quizzes.id
    Vztah: 1:N na Answer (kaskádové mazání)
    """
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='multiple_choice')
    
    # Vztahy
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')


class Answer(db.Model):
    """Model odpovědi.
    
    Tabulka: answers
    Cizí klíč: question_id → questions.id
    is_correct označuje správnou odpověď (právě 1 z 4 u každé otázky).
    """
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class GameResult(db.Model):
    """Model výsledku hry.
    
    Tabulka: game_results
    Cizí klíče: user_id → users1.id, quiz_id → quizzes.id
    Vztah: 1:N na UserAnswer (kaskádové mazání)
    Každý záznam = jeden pokus uživatele o kvíz.
    """
    __tablename__ = 'game_results'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users1.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    max_score = db.Column(db.Integer, default=0)
    time_spent = db.Column(db.Integer, default=0)  # v sekundách
    date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Vztahy
    user_answers = db.relationship('UserAnswer', backref='game_result', lazy=True, cascade='all, delete-orphan')


class UserAnswer(db.Model):
    """Model odpovědi uživatele.
    
    Tabulka: user_answers
    Cizí klíče: game_id → game_results.id, question_id → questions.id,
                answer_id → answers.id (nullable – uživatel nemusel odpovědět)
    Ukládá, co uživatel zvolil a zda to bylo správně.
    """
    __tablename__ = 'user_answers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game_results.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=True)
    answer_text = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)


class Achievement(db.Model):
    """Model definice úspěchu (achievement).
    
    Tabulka: achievements
    Obsahuje pravidla pro získání úspěchu (requirement_type + requirement_value).
    Typy: games_played, quizzes_created, perfect_score, score_average,
          fast_completion, correct_streak, total_answers.
    Tier: bronze / silver / gold.
    Seed dat z achievements.py (ACHIEVEMENT_DEFINITIONS) při startu aplikace.
    """
    __tablename__ = 'achievements'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    icon = db.Column(db.String(255), nullable=False, default='default.svg')
    tier = db.Column(db.String(20), nullable=False, default='bronze')
    category = db.Column(db.String(100), nullable=False, default='gameplay')
    requirement_type = db.Column(db.String(100), nullable=False)
    requirement_value = db.Column(db.Integer, nullable=False, default=1)
    
    user_achievements = db.relationship('UserAchievement', backref='achievement', lazy=True, cascade='all, delete-orphan')


class UserAchievement(db.Model):
    """Model získaného úspěchu uživatele (spojovací tabulka M:N).
    
    Tabulka: user_achievements
    Cizí klíče: user_id → users1.id, achievement_id → achievements.id
    UniqueConstraint zabraňuje duplicitnímu přidělení stejného achievementu.
    earned_at = datum, kdy uživatel achievement získal.
    """
    __tablename__ = 'user_achievements'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users1.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievements.id'), nullable=False)
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),
    )
