"""
Databázové modely pro quiz aplikaci.
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from database import db


class User(UserMixin, db.Model):
    """Model uživatele."""
    __tablename__ = 'users1'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user')  # 'user' nebo 'admin'
    avatar = db.Column(db.String(255), default='default.png')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Vztahy
    quizzes = db.relationship('Quiz', backref='author', lazy=True)
    game_results = db.relationship('GameResult', backref='user', lazy=True)
    
    def set_password(self, password):
        """Hashuje a uloží heslo."""
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        """Ověří heslo proti hashi."""
        return check_password_hash(self.password, password)
    
    def is_admin(self):
        """Zkontroluje, zda je uživatel admin."""
        return self.role == 'admin'
    
    def get_stats(self):
        """Vrátí statistiky uživatele."""
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
            'average_score': round(sum(scores) / len(scores), 1),
            'best_score': round(max(scores), 1),
            'total_quizzes_created': len(self.quizzes)
        }


class Quiz(db.Model):
    """Model kvízu."""
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)  # 'easy', 'medium', 'hard'
    time_limit = db.Column(db.Integer, default=30)  # sekund na otázku
    author_id = db.Column(db.Integer, db.ForeignKey('users1.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Vztahy
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    game_results = db.relationship('GameResult', backref='quiz', lazy=True, cascade='all, delete-orphan')
    
    def get_question_count(self):
        """Vrátí počet otázek v kvízu."""
        return len(self.questions)


class Question(db.Model):
    """Model otázky."""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default='multiple_choice')
    
    # Vztahy
    answers = db.relationship('Answer', backref='question', lazy=True, cascade='all, delete-orphan')


class Answer(db.Model):
    """Model odpovědi."""
    __tablename__ = 'answers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)


class GameResult(db.Model):
    """Model výsledku hry."""
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
    """Model odpovědi uživatele."""
    __tablename__ = 'user_answers'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game_results.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'), nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answers.id'), nullable=True)
    answer_text = db.Column(db.Text, nullable=True)
    is_correct = db.Column(db.Boolean, default=False)
