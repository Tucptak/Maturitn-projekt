"""
Administrátorské routy.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from auth import admin_required
from database import db
from models import User, Quiz, GameResult, UserAnswer

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    """Administrátorský dashboard."""
    stats = {
        'total_users': User.query.count(),
        'total_quizzes': Quiz.query.count(),
        'total_games': GameResult.query.count(),
        'admin_count': User.query.filter_by(role='admin').count()
    }
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_quizzes = Quiz.query.order_by(Quiz.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_users=recent_users,
                         recent_quizzes=recent_quizzes)


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    """Seznam uživatelů."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/user/<int:user_id>/toggle-role', methods=['POST'])
@login_required
@admin_required
def toggle_role(user_id):
    """Přepnutí role uživatele."""
    if user_id == current_user.id:
        flash('Nemůžete změnit svou vlastní roli.', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == 1:
        flash('Nelze změnit roli hlavního administrátora.', 'error')
        return redirect(url_for('admin.users'))
    
    if user.role == 'admin':
        user.role = 'user'
        flash(f'Uživatel {user.name} byl změněn na běžného uživatele.', 'success')
    else:
        user.role = 'admin'
        flash(f'Uživatel {user.name} byl povýšen na administrátora.', 'success')
    
    db.session.commit()
    return redirect(url_for('admin.users'))


@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Smazání uživatele."""
    if user_id == current_user.id:
        flash('Nemůžete smazat sami sebe.', 'error')
        return redirect(url_for('admin.users'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == 1:
        flash('Nelze smazat hlavního administrátora.', 'error')
        return redirect(url_for('admin.users'))
    
    # Smazání souvisejících dat
    GameResult.query.filter_by(user_id=user_id).delete()
    Quiz.query.filter_by(author_id=user_id).delete()
    
    db.session.delete(user)
    db.session.commit()
    
    flash(f'Uživatel {user.name} byl smazán.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/quizzes')
@login_required
@admin_required
def quizzes():
    """Seznam všech kvízů pro admina."""
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    return render_template('admin/quizzes.html', quizzes=quizzes)


@admin_bp.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_quiz(quiz_id):
    """Smazání kvízu adminem."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    db.session.delete(quiz)
    db.session.commit()
    
    flash(f'Kvíz "{quiz.name}" byl smazán.', 'success')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/quiz/<int:quiz_id>/clear-results', methods=['POST'])
@login_required
@admin_required
def clear_quiz_results(quiz_id):
    """Smazání všech výsledků (záznamů, odpovědí) pro konkrétní kvíz."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    results = GameResult.query.filter_by(quiz_id=quiz_id).all()
    count = len(results)
    
    for result in results:
        db.session.delete(result)  # cascade smaže i UserAnswer
    
    db.session.commit()
    
    flash(f'Smazáno {count} záznamů pro kvíz "{quiz.name}".', 'success')
    return redirect(url_for('admin.quizzes'))


@admin_bp.route('/clear-all-results', methods=['POST'])
@login_required
@admin_required
def clear_all_results():
    """Smazání všech výsledků a odpovědí ze všech kvízů."""
    # Nejprve smazat všechny UserAnswer, pak všechny GameResult
    UserAnswer.query.delete()
    count = GameResult.query.delete()
    db.session.commit()
    
    flash(f'Smazáno {count} záznamů ze všech kvízů.', 'success')
    return redirect(url_for('admin.dashboard'))
