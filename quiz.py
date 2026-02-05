"""
Routy pro správu a hraní kvízů.
"""
import subprocess
import sys
import os
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from database import db
from models import Quiz, Question, Answer, GameResult, UserAnswer

quiz_bp = Blueprint('quiz', __name__)


@quiz_bp.route('/quizzes')
def list_quizzes():
    """Seznam všech kvízů."""
    category = request.args.get('category', '')
    difficulty = request.args.get('difficulty', '')
    
    query = Quiz.query
    
    if category:
        query = query.filter_by(category=category)
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    
    quizzes = query.order_by(Quiz.created_at.desc()).all()
    
    # Získání unikátních kategorií
    categories = db.session.query(Quiz.category).distinct().all()
    categories = [c[0] for c in categories]
    
    return render_template('quizzes.html', 
                         quizzes=quizzes, 
                         categories=categories,
                         selected_category=category,
                         selected_difficulty=difficulty)


@quiz_bp.route('/quiz/<int:quiz_id>')
def quiz_detail(quiz_id):
    """Detail kvízu."""
    quiz = Quiz.query.get_or_404(quiz_id)
    return render_template('quiz_detail.html', quiz=quiz)


@quiz_bp.route('/quiz/<int:quiz_id>/play')
@login_required
def play_quiz(quiz_id):
    """Spustí desktopovou aplikaci pro hraní kvízu s automatickým přihlášením."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if not quiz.questions:
        flash('Tento kvíz nemá žádné otázky.', 'warning')
        return redirect(url_for('quiz.quiz_detail', quiz_id=quiz_id))
    
    try:
        # Vygenerování SSO tokenu pro automatické přihlášení v desktopové aplikaci
        from api import generate_sso_token
        token = generate_sso_token(current_user.id)
        
        desktop_app_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'desktop_app.py')
        subprocess.Popen([
            sys.executable, desktop_app_path,
            '--quiz-id', str(quiz_id),
            '--token', token
        ])
        flash('Desktopová aplikace se spouští... Budete automaticky přihlášeni.', 'success')
    except Exception as e:
        flash(f'Nepodařilo se spustit desktopovou aplikaci: {str(e)}', 'error')
    
    return redirect(url_for('quiz.quiz_detail', quiz_id=quiz_id))


@quiz_bp.route('/quiz/<int:quiz_id>/questions', methods=['GET'])
@login_required
def get_quiz_questions(quiz_id):
    """API endpoint pro získání otázek kvízu."""
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


@quiz_bp.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    """Odeslání výsledků kvízu."""
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
    db.session.flush()  # Pro získání ID
    
    # Zpracování odpovědí
    results = []
    for answer_data in answers:
        question_id = answer_data.get('question_id')
        answer_id = answer_data.get('answer_id')
        
        question = Question.query.get(question_id)
        if not question or question.quiz_id != quiz_id:
            continue
        
        # Kontrola správnosti
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
        
        # Uložení odpovědi uživatele
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
    
    # Aktualizace skóre
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


@quiz_bp.route('/quiz/create', methods=['GET', 'POST'])
@login_required
def create_quiz():
    """Vytvoření nového kvízu."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        difficulty = request.form.get('difficulty', 'medium')
        time_limit = request.form.get('time_limit', 30, type=int)
        
        # Validace
        if not name or len(name) < 3:
            flash('Název kvízu musí mít alespoň 3 znaky.', 'error')
            return render_template('quiz_create.html')
        
        if not category:
            flash('Zadejte kategorii kvízu.', 'error')
            return render_template('quiz_create.html')
        
        # Vytvoření kvízu
        quiz = Quiz(
            name=name,
            category=category,
            difficulty=difficulty,
            time_limit=time_limit,
            author_id=current_user.id
        )
        db.session.add(quiz)
        db.session.commit()
        
        flash('Kvíz byl vytvořen! Nyní přidejte otázky.', 'success')
        return redirect(url_for('quiz.edit_quiz', quiz_id=quiz.id))
    
    return render_template('quiz_create.html')


@quiz_bp.route('/quiz/<int:quiz_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_quiz(quiz_id):
    """Úprava kvízu."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        flash('Nemáte oprávnění upravovat tento kvíz.', 'error')
        return redirect(url_for('quiz.list_quizzes'))
    
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', '').strip()
        difficulty = request.form.get('difficulty', 'medium')
        time_limit = request.form.get('time_limit', 30, type=int)
        
        if name and len(name) >= 3:
            quiz.name = name
        if category:
            quiz.category = category
        quiz.difficulty = difficulty
        quiz.time_limit = time_limit
        
        db.session.commit()
        flash('Kvíz byl aktualizován.', 'success')
    
    return render_template('quiz_edit.html', quiz=quiz)


@quiz_bp.route('/quiz/<int:quiz_id>/add-question', methods=['POST'])
@login_required
def add_question(quiz_id):
    """Přidání otázky do kvízu."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Nemáte oprávnění'}), 403
    
    data = request.get_json()
    question_text = data.get('text', '').strip()
    answers_data = data.get('answers', [])
    
    if not question_text:
        return jsonify({'error': 'Text otázky je povinný'}), 400
    
    if len(answers_data) != 4:
        return jsonify({'error': 'Otázka musí mít přesně 4 odpovědi'}), 400
    
    # Kontrola, že alespoň jedna odpověď je správná
    has_correct = any(a.get('is_correct', False) for a in answers_data)
    if not has_correct:
        return jsonify({'error': 'Alespoň jedna odpověď musí být správná'}), 400
    
    # Vytvoření otázky
    question = Question(quiz_id=quiz_id, text=question_text)
    db.session.add(question)
    db.session.flush()
    
    # Vytvoření odpovědí
    for ans in answers_data:
        answer = Answer(
            question_id=question.id,
            text=ans.get('text', '').strip(),
            is_correct=ans.get('is_correct', False)
        )
        db.session.add(answer)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'question_id': question.id,
        'message': 'Otázka byla přidána'
    })


@quiz_bp.route('/question/<int:question_id>', methods=['DELETE'])
@login_required
def delete_question(question_id):
    """Smazání otázky."""
    question = Question.query.get_or_404(question_id)
    quiz = question.quiz
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Nemáte oprávnění'}), 403
    
    db.session.delete(question)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Otázka byla smazána'})


@quiz_bp.route('/question/<int:question_id>', methods=['PUT'])
@login_required
def edit_question(question_id):
    """Úprava otázky."""
    question = Question.query.get_or_404(question_id)
    quiz = question.quiz
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        return jsonify({'error': 'Nemáte oprávnění'}), 403
    
    data = request.get_json()
    question_text = data.get('text', '').strip()
    answers_data = data.get('answers', [])
    
    if not question_text:
        return jsonify({'error': 'Text otázky je povinný'}), 400
    
    if len(answers_data) != 4:
        return jsonify({'error': 'Otázka musí mít přesně 4 odpovědi'}), 400
    
    has_correct = any(a.get('is_correct', False) for a in answers_data)
    if not has_correct:
        return jsonify({'error': 'Alespoň jedna odpověď musí být správná'}), 400
    
    # Aktualizace textu otázky
    question.text = question_text
    
    # Smazání starých odpovědí a vytvoření nových
    Answer.query.filter_by(question_id=question.id).delete()
    
    for ans in answers_data:
        answer = Answer(
            question_id=question.id,
            text=ans.get('text', '').strip(),
            is_correct=ans.get('is_correct', False)
        )
        db.session.add(answer)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Otázka byla upravena'
    })


@quiz_bp.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
def delete_quiz(quiz_id):
    """Smazání kvízu."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Kontrola oprávnění
    if quiz.author_id != current_user.id and not current_user.is_admin():
        flash('Nemáte oprávnění smazat tento kvíz.', 'error')
        return redirect(url_for('quiz.list_quizzes'))
    
    db.session.delete(quiz)
    db.session.commit()
    
    flash('Kvíz byl smazán.', 'success')
    return redirect(url_for('quiz.list_quizzes'))


@quiz_bp.route('/leaderboard')
def leaderboard():
    """Žebříček nejlepších hráčů."""
    # Top hráči podle průměrného skóre
    from sqlalchemy import func
    
    top_players = db.session.query(
        GameResult.user_id,
        func.avg(GameResult.score * 100.0 / GameResult.max_score).label('avg_score'),
        func.count(GameResult.id).label('games_played')
    ).group_by(GameResult.user_id).having(
        func.count(GameResult.id) >= 1
    ).order_by(func.avg(GameResult.score * 100.0 / GameResult.max_score).desc()).limit(20).all()
    
    # Přidání uživatelských dat
    from models import User
    leaderboard_data = []
    for i, (user_id, avg_score, games_played) in enumerate(top_players, 1):
        user = User.query.get(user_id)
        if user:
            leaderboard_data.append({
                'rank': i,
                'user': user,
                'avg_score': round(avg_score, 1),
                'games_played': games_played
            })
    
    return render_template('leaderboard.html', leaderboard=leaderboard_data)


@quiz_bp.route('/my-quizzes')
@login_required
def my_quizzes():
    """Moje kvízy."""
    quizzes = Quiz.query.filter_by(author_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    return render_template('my_quizzes.html', quizzes=quizzes)
