"""
Automatizované testy pro projekt Brainiac.
Spuštění: pytest test_brainiac.py -v
"""
import pytest
from flask import Flask
from database import db
from models import User, Quiz, Question, Answer, GameResult, pct


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope='function')
def app():
    """Vytvoří testovací Flask aplikaci s in-memory SQLite databází."""
    test_app = Flask(__name__)
    test_app.config['TESTING'] = True
    test_app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    test_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    test_app.config['SECRET_KEY'] = 'test-secret'
    test_app.config['WTF_CSRF_ENABLED'] = False

    db.init_app(test_app)

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Vrátí testovacího klienta."""
    return app.test_client()


@pytest.fixture
def sample_user(app):
    """Vytvoří testovacího uživatele v databázi."""
    user = User(name='TestUser', email='test@example.com', role='user')
    user.set_password('heslo123')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def sample_quiz(app, sample_user):
    """Vytvoří testovací kvíz se 3 otázkami."""
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
        db.session.flush()
        for j, letter in enumerate(['A', 'B', 'C', 'D']):
            a = Answer(question_id=q.id, text=f'Odpověď {letter}', is_correct=(j == 0))
            db.session.add(a)

    db.session.commit()
    return quiz


# ── Test 1: Ověření hesla uživatele ────────────────────────────────────────

def test_password_verification(sample_user):
    """Test hashování a ověření hesla – správné projde, špatné ne, uloženo jako hash."""
    assert sample_user.check_password('heslo123') is True
    assert sample_user.check_password('spatne_heslo') is False
    assert sample_user.password != 'heslo123'


# ── Test 2: Statistiky uživatele ───────────────────────────────────────────

def test_user_stats(app, sample_user, sample_quiz):
    """Test výpočtu statistik – nulové bez her, správné po odehrání."""
    assert sample_user.get_stats()['total_games'] == 0

    g1 = GameResult(user_id=sample_user.id, quiz_id=sample_quiz.id,
                    score=8, max_score=10, time_spent=45)
    g2 = GameResult(user_id=sample_user.id, quiz_id=sample_quiz.id,
                    score=6, max_score=10, time_spent=60)
    db.session.add_all([g1, g2])
    db.session.commit()

    stats = sample_user.get_stats()
    assert stats['total_games'] == 2
    assert stats['average_score'] == 70
    assert stats['best_score'] == 80


# ── Test 3: Pomocná funkce pct() ───────────────────────────────────────────

def test_pct_formatting():
    """Test funkce pct() – celá čísla vrátí int, necelá float s 1 desetinným místem."""
    assert pct(100.0) == 100 and isinstance(pct(100.0), int)
    assert pct(73.456) == 73.5 and isinstance(pct(73.456), float)
    assert pct(0) == 0 and isinstance(pct(0), int)
    assert pct(66.66) == 66.7


# ── Test 4: Struktura kvízu ────────────────────────────────────────────────

def test_quiz_structure(sample_quiz, sample_user):
    """Test modelu kvízu – počet otázek, 4 odpovědi, 1 správná, propojení s autorem."""
    assert sample_quiz.get_question_count() == 3
    assert sample_quiz.author.id == sample_user.id
    for question in sample_quiz.questions:
        assert len(question.answers) == 4
        assert len([a for a in question.answers if a.is_correct]) == 1


# ── Test 5: Role uživatele ─────────────────────────────────────────────────

def test_user_role(sample_user):
    """Test ověření role – běžný uživatel není admin, po změně role ano."""
    assert sample_user.is_admin() is False
    sample_user.role = 'admin'
    assert sample_user.is_admin() is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
