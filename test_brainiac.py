"""
Automatizované testy pro projekt Brainiac.
Spuštění: pytest test_brainiac.py -v

Testovací strategie:
  - Používá SQLite in-memory databázi (ne MySQL) pro izolaci testů.
  - Každý test dostane čistou DB díky scope='function' u app fixture.
  - Fixtures vytvářejí testovací data (User, Quiz, Question, Answer).

Testované oblasti:
  Test 1: hashování hesel (User.set_password / check_password z models.py)
  Test 2: statistiky uživatele (User.get_stats z models.py)
  Test 3: pomocná funkce pct() (formátování procent z models.py)
  Test 4: struktura kvízu (relace Quiz → Question → Answer)
  Test 5: role uživatele (User.is_admin() z models.py)
"""
import pytest
from flask import Flask
from database import db
from models import User, Quiz, Question, Answer, GameResult, pct


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def app():
    """Vytvoří testovací Flask aplikaci s in-memory SQLite databází.
    
    scope='function' = nová DB pro každý test (izolace).
    SQLite in-memory je rychlejší než MySQL a nevyžaduje server.
    WTF_CSRF_ENABLED=False vypne CSRF ochranu (nepotřebujeme v testech).
    """
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # DB jen v paměti
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.config['SECRET_KEY'] = 'test-secret'
    test_app.config['WTF_CSRF_ENABLED'] = False

    db.init_app(test_app)  # propojí SQLAlchemy s test_app (stejně jako v main.py)

    with test_app.app_context():
        db.create_all()      # vytvoří tabulky podle modelů v models.py
        yield test_app       # předá app testu
        db.session.remove()  # zavře session
        db.drop_all()        # smaže tabulky (cleanup)


@pytest.fixture
def client(app):
    """Vrátí testovacího klienta."""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Vytvoří testovacího uživatele v databázi.
    
    Závisí na 'app' fixture (potřebuje app_context pro DB operace).
    set_password() hashuje heslo přes Werkzeug (stejně jako auth.py:register).
    """
    user = User(name='TestUser', email='test@example.com', role='user')
    user.set_password('heslo123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_quiz(app, sample_user):
    """Vytvoří testovací kvíz se 3 otázkami (každá má 4 odpovědi, 1 správná).
    
    Závisí na 'sample_user' (kvíz potřebuje author_id).
    flush() po quiz/question získá ID bez commitu → použije se pro foreign key.
    """
    quiz = Quiz(
        name='Testovací kvíz',
        category='Testování',
        difficulty='medium',
        time_limit=30,
        author_id=sample_user.id
    )
    db.session.add(quiz)
    db.session.flush()

    for i in range(3):
        q = Question(quiz_id=quiz.id, text=f'Otázka č. {i + 1}?')
        db.session.add(q)
        db.session.flush()  # flush() přiřadí q.id bez commitu → potřebujeme pro Answer.question_id
        for j, letter in enumerate(['A', 'B', 'C', 'D']):
            # j==0 → první odpověď (A) je vždy správná
            a = Answer(question_id=q.id, text=f'Odpověď {letter}', is_correct=(j == 0))
            db.session.add(a)

    db.session.commit()
    return quiz


# ── Test 1: Ověření hesla uživatele ────────────────────────────────────────

def test_password_verification(sample_user):
    """Test hashování a ověření hesla – volá User.check_password() z models.py.
    
    Ověřuje: správné heslo → True, špatné heslo → False,
    a heslo v DB je hash (ne plaintext).
    """
    assert sample_user.check_password('heslo123') is True
    assert sample_user.check_password('spatne_heslo') is False
    assert sample_user.password != 'heslo123'


# ── Test 2: Statistiky uživatele ───────────────────────────────────────────

def test_user_stats(app, sample_user, sample_quiz):
    """Test výpočtu statistik – volá User.get_stats() z models.py.
    
    Nejdřív ověřuje nulové statistiky (0 her), pak přidá 2 GameResult záznamy
    a ověřuje: total_games=2, average_score=70% ((80+60)/2), best_score=80%.
    """
    assert sample_user.get_stats()['total_games'] == 0

    # Vytvoří 2 výsledky: 8/10 (80%) a 6/10 (60%)
    g1 = GameResult(user_id=sample_user.id, quiz_id=sample_quiz.id,
                    score=8, max_score=10, time_spent=45)
    g2 = GameResult(user_id=sample_user.id, quiz_id=sample_quiz.id,
                    score=6, max_score=10, time_spent=60)
    db.session.add_all([g1, g2])
    db.session.commit()

    # get_stats() z models.py spočítá: total_games, average_score, best_score
    stats = sample_user.get_stats()
    assert stats['total_games'] == 2
    assert stats['average_score'] == 70
    assert stats['best_score'] == 80


# ── Test 3: Pomocná funkce pct() ───────────────────────────────────────────

def test_pct_formatting():
    """Test funkce pct() z models.py – formátuje procenta pro zobrazení.
    
    pct(100.0) → 100 (int, ne 100.0)
    pct(73.456) → 73.5 (float, zaokrouhleno na 1 des. místo)
    Používá se v šablonách a stats.py pro čistý výstup.
    """
    assert pct(100.0) == 100 and isinstance(pct(100.0), int)
    assert pct(73.456) == 73.5 and isinstance(pct(73.456), float)
    assert pct(0) == 0 and isinstance(pct(0), int)
    assert pct(66.66) == 66.7


# ── Test 4: Struktura kvízu ────────────────────────────────────────────────

def test_quiz_structure(sample_quiz, sample_user):
    """Test modelu kvízu – ověřuje relace Quiz → Question → Answer.
    
    Quiz.get_question_count() vrací len(questions) z models.py.
    Každá otázka musí mít přesně 4 odpovědi, z toho 1 správná.
    Quiz.author odkazuje na User přes author_id (foreign key).
    """
    assert sample_quiz.get_question_count() == 3
    assert sample_quiz.author.id == sample_user.id
    for question in sample_quiz.questions:
        assert len(question.answers) == 4
        assert len([a for a in question.answers if a.is_correct]) == 1


# ── Test 5: Role uživatele ─────────────────────────────────────────────────

def test_user_role(sample_user):
    """Test ověření role – volá User.is_admin() z models.py.
    
    Výchozí role='user' → is_admin()=False.
    Po změně role='admin' → is_admin()=True.
    V produkci roli mění admin přes admin.py:toggle_role().
    """
    assert sample_user.is_admin() is False
    sample_user.role = 'admin'
    assert sample_user.is_admin() is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
