"""
Databázové připojení a inicializace.

Tento modul vytváří SQLAlchemy instanci (db) a poskytuje funkci init_db(),
která se volá z main.py při startu aplikace. Všechny ostatní moduly
(models.py, auth.py, quiz.py, …) importují 'db' odsud.

Připojení k MySQL se sestavuje z proměnných prostředí (.env soubor):
  DB_HOST, DB_USER, DB_PASSWORD, DB_NAME
Driver: PyMySQL (čistý Python MySQL klient, nevyžaduje C knihovny).
"""
import os
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

# Načte proměnné z .env souboru do os.environ
load_dotenv()

# Globální SQLAlchemy instance sdílená celou aplikací.
# Jednotlivé modely (models.py) dědí z db.Model.
db = SQLAlchemy()


def get_database_uri():
    """Sestaví URI pro připojení k MySQL databázi.
    
    Formát: mysql+pymysql://user:password@host/dbname?charset=utf8mb4
    charset=utf8mb4 zajišťuje plnou podporu Unicode (včetně emoji).
    """
    host = os.getenv('DB_HOST', 'localhost')
    user = os.getenv('DB_USER', 'root')
    password = os.getenv('DB_PASSWORD', '')
    name = os.getenv('DB_NAME', 'quiz_app')
    
    return f"mysql+pymysql://{user}:{password}@{host}/{name}?charset=utf8mb4"


def init_db(app):
    """Inicializuje databázi s Flask aplikací.
    
    Volá se jednou z main.py. Nastaví URI a propojí SQLAlchemy s Flask.
    db.create_all() automaticky vytvoří všechny tabulky definované v models.py,
    pokud ještě neexistují (nemodifikuje existující tabulky).
    """
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
