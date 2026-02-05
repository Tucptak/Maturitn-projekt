"""
API endpointy pro desktop aplikaci.
"""
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_user, current_user, login_required
from database import db
from models import User, Quiz, Question, Answer, GameResult, UserAnswer

api_bp = Blueprint('api', __name__, url_prefix='/api')

# Úložiště tokenů pro SSO (token -> {user_id, expires})
_sso_tokens = {}


def generate_sso_token(user_id):
    """Vygeneruje jednorázový SSO token pro uživatele."""
    token = secrets.token_urlsafe(48)
    _sso_tokens[token] = {
        'user_id': user_id,
        'expires': datetime.utcnow() + timedelta(minutes=2)
    }
    return token


def validate_sso_token(token):
    """Ověří SSO token a vrátí user_id. Token je jednorázový."""
    token_data = _sso_tokens.pop(token, None)
    if not token_data:
        return None
    if datetime.utcnow() > token_data['expires']:
        return None
    return token_data['user_id']


@api_bp.route('/auth/token', methods=['POST'])
def api_token_login():
    """Přihlášení pomocí SSO tokenu (z webu do desktopu)."""
    data = request.get_json()
    if not data or 'token' not in data:
        return jsonify({'error': 'Chybí token'}), 400
    
    token = data['token']
    user_id = validate_sso_token(token)
    
    if user_id is None:
        return jsonify({'error': 'Neplatný nebo expirovaný token'}), 401
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'Uživatel nenalezen'}), 404
    
    login_user(user)
    return jsonify({
        'success': True,
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'role': user.role
        }
    })


@api_bp.route('/login', methods=['POST'])
def api_login():
    """API přihlášení pro desktop aplikaci."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Chybí data'}), 400
    
    email = data.get('email', '').strip()
    password = data.get('password', '')
    
    if not email or not password:
        return jsonify({'error': 'Vyplňte email a heslo'}), 400
    
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            }
        })
    
    return jsonify({'error': 'Neplatný email nebo heslo'}), 401


@api_bp.route('/quizzes', methods=['GET'])
def api_quizzes():
    """Získání seznamu kvízů."""
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    
    query = Quiz.query
    
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    quizzes = query.order_by(Quiz.created_at.desc()).all()
    
    return jsonify([{
        'id': q.id,
        'name': q.name,
        'category': q.category,
        'difficulty': q.difficulty,
        'time_limit': q.time_limit,
        'question_count': q.get_question_count(),
        'author': q.author.name
    } for q in quizzes])


@api_bp.route('/quiz/<int:quiz_id>/questions', methods=['GET'])
@login_required
def api_quiz_questions(quiz_id):
    """Získání otázek kvízu pro API."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    questions_data = []
    for question in quiz.questions:
        answers_data = [
            {'id': a.id, 'text': a.text}
            for a in question.answers
        ]
        questions_data.append({
            'id': question.id,
            'text': question.text,
            'answers': answers_data
        })
    
    return jsonify({
        'quiz_id': quiz.id,
        'quiz_name': quiz.name,
        'time_limit': quiz.time_limit,
        'questions': questions_data
    })


@api_bp.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def api_submit_quiz(quiz_id):
    """API endpoint pro odeslání výsledků kvízu."""
    quiz = Quiz.query.get_or_404(quiz_id)
    data = request.get_json()
    
    if not data or 'answers' not in data:
        return jsonify({'error': 'Neplatná data'}), 400
    
    answers = data['answers']
    time_spent = data.get('time_spent', 0)
    
    # Výpočet skóre
    score = 0
    max_score = len(quiz.questions)
    
    # Vytvoření záznamu o hře
    game_result = GameResult(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=0,
        max_score=max_score,
        time_spent=time_spent
    )
    db.session.add(game_result)
    db.session.flush()
    
    # Zpracování odpovědí
    results = []
    for answer_data in answers:
        question_id = answer_data.get('question_id')
        answer_id = answer_data.get('answer_id')
        
        question = Question.query.get(question_id)
        if not question or question.quiz_id != quiz_id:
            continue
        
        is_correct = False
        correct_answer = None
        selected_answer = None
        
        for ans in question.answers:
            if ans.is_correct:
                correct_answer = ans
            if ans.id == answer_id:
                selected_answer = ans
                if ans.is_correct:
                    is_correct = True
                    score += 1
        
        user_answer = UserAnswer(
            game_id=game_result.id,
            question_id=question_id,
            answer_id=answer_id,
            is_correct=is_correct
        )
        db.session.add(user_answer)
        
        results.append({
            'question_id': question_id,
            'question_text': question.text,
            'selected_answer_id': answer_id,
            'selected_answer_text': selected_answer.text if selected_answer else None,
            'correct_answer_id': correct_answer.id if correct_answer else None,
            'correct_answer_text': correct_answer.text if correct_answer else None,
            'is_correct': is_correct
        })
    
    game_result.score = score
    db.session.commit()
    
    return jsonify({
        'success': True,
        'score': score,
        'max_score': max_score,
        'percentage': round((score / max_score * 100) if max_score > 0 else 0, 1),
        'time_spent': time_spent,
        'results': results
    })


@api_bp.route('/categories', methods=['GET'])
def api_categories():
    """Získání seznamu kategorií."""
    categories = db.session.query(Quiz.category).distinct().all()
    return jsonify([c[0] for c in categories])


@api_bp.route('/user/stats', methods=['GET'])
@login_required
def api_user_stats():
    """Statistiky přihlášeného uživatele."""
    stats = current_user.get_stats()
    return jsonify(stats)