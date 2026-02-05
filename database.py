"""
Databázové připojení a inicializace.
"""
import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()


def get_database_uri():
    """Sestaví URI pro připojení k MySQL databázi."""
    host = os.getenv('DB_HOST', 'localhost')
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', '')
    name = os.getenv('DB_NAME', 'quiz_app')
    
    return f"mysql+pymysql://{user}:{password}@{host}/{name}?charset=utf8mb4"


def init_db(app):
    """Inicializuje databázi s Flask aplikací."""
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
