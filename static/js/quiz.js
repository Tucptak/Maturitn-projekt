/**
 * Braniac - Logika hraní kvízu
 */

// Stav hry
let quizData = null;
let currentQuestionIndex = 0;
let userAnswers = [];
let timerInterval = null;
let timeRemaining = 0;
let totalTimeSpent = 0;
let questionStartTime = 0;
let lastResult = null;

// DOM elementy
const timerEl = document.getElementById('timer');
const progressFill = document.getElementById('progressFill');
const currentQuestionEl = document.getElementById('currentQuestion');
const totalQuestionsEl = document.getElementById('totalQuestions');
const questionNumEl = document.getElementById('questionNum');
const questionTextEl = document.getElementById('questionText');
const answersGridEl = document.getElementById('answersGrid');
const questionContainer = document.getElementById('questionContainer');
const quizResults = document.getElementById('quizResults');

/**
 * Inicializace kvízu
 */
async function initQuiz() {
    try {
        const response = await fetch(`/quiz/${QUIZ_ID}/questions`);
        quizData = await response.json();
        
        if (!quizData.questions || quizData.questions.length === 0) {
            alert('Tento kvíz nemá žádné otázky.');
            window.location.href = `/quiz/${QUIZ_ID}`;
            return;
        }
        
        totalQuestionsEl.textContent = quizData.questions.length;
        showQuestion(0);
    } catch (error) {
        console.error('Chyba při načítání kvízu:', error);
        alert('Nepodařilo se načíst kvíz. Zkuste to znovu.');
    }
}

/**
 * Zobrazení otázky
 */
function showQuestion(index) {
    if (index >= quizData.questions.length) {
        finishQuiz();
        return;
    }
    
    currentQuestionIndex = index;
    const question = quizData.questions[index];
    
    // Aktualizace UI
    currentQuestionEl.textContent = index + 1;
    questionNumEl.textContent = index + 1;
    questionTextEl.textContent = question.text;
    
    // Progress bar
    const progress = ((index + 1) / quizData.questions.length) * 100;
    progressFill.style.width = `${progress}%`;
    
    // Vykreslení odpovědí
    answersGridEl.innerHTML = '';
    const labels = ['A', 'B', 'C', 'D'];
    
    question.answers.forEach((answer, i) => {
        const btn = document.createElement('button');
        btn.className = 'answer-btn';
        btn.innerHTML = `
            <span class="answer-label">${labels[i]}</span>
            <span class="answer-text">${answer.text}</span>
        `;
        btn.onclick = () => selectAnswer(answer.id);
        answersGridEl.appendChild(btn);
    });
    
    // Spuštění časovače
    startTimer();
    questionStartTime = Date.now();
}

/**
 * Spuštění časovače
 */
function startTimer() {
    clearInterval(timerInterval);
    timeRemaining = TIME_LIMIT;
    updateTimerDisplay();
    
    timerInterval = setInterval(() => {
        timeRemaining--;
        updateTimerDisplay();
        
        if (timeRemaining <= 0) {
            clearInterval(timerInterval);
            // Automaticky přeskočit na další otázku bez odpovědi
            userAnswers.push({
                question_id: quizData.questions[currentQuestionIndex].id,
                answer_id: null
            });
            totalTimeSpent += TIME_LIMIT;
            showQuestion(currentQuestionIndex + 1);
        }
    }, 1000);
}

/**
 * Aktualizace zobrazení časovače
 */
function updateTimerDisplay() {
    timerEl.textContent = timeRemaining;
    
    timerEl.classList.remove('warning', 'danger');
    if (timeRemaining <= 5) {
        timerEl.classList.add('danger');
    } else if (timeRemaining <= 10) {
        timerEl.classList.add('warning');
    }
}

/**
 * Výběr odpovědi
 */
function selectAnswer(answerId) {
    clearInterval(timerInterval);
    
    // Výpočet času
    const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
    totalTimeSpent += timeSpent;
    
    // Uložení odpovědi
    userAnswers.push({
        question_id: quizData.questions[currentQuestionIndex].id,
        answer_id: answerId
    });
    
    // Vizuální feedback
    const buttons = answersGridEl.querySelectorAll('.answer-btn');
    buttons.forEach(btn => {
        btn.disabled = true;
    });
    
    // Krátká pauza před další otázkou
    setTimeout(() => {
        showQuestion(currentQuestionIndex + 1);
    }, 300);
}

/**
 * Dokončení kvízu
 */
async function finishQuiz() {
    clearInterval(timerInterval);
    
    // Skrytí otázek, zobrazení výsledků
    questionContainer.style.display = 'none';
    document.querySelector('.quiz-game-header').style.display = 'none';
    
    try {
        const response = await fetch(`/quiz/${QUIZ_ID}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                answers: userAnswers,
                time_spent: totalTimeSpent
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showResults(result);
            // Zobrazení achievement pop-upů, pokud byly získány
            if (result.new_achievements && result.new_achievements.length > 0 && typeof showAchievementQueue === 'function') {
                showAchievementQueue(result.new_achievements);
            }
        } else {
            alert('Chyba při odesílání výsledků.');
        }
    } catch (error) {
        console.error('Chyba:', error);
        alert('Nepodařilo se odeslat výsledky.');
    }
}

/**
 * Zobrazení výsledků
 */
function showResults(result) {
    lastResult = result;
    quizResults.style.display = 'block';
    
    document.getElementById('resultScore').textContent = `${result.percentage}%`;
    document.getElementById('resultCorrect').textContent = result.score;
    document.getElementById('resultTotal').textContent = result.max_score;
    document.getElementById('resultTime').textContent = result.time_spent;
    
    // Seznam odpovědí
    const resultsList = document.getElementById('resultsList');
    resultsList.innerHTML = '<h3>Přehled odpovědí</h3>';
    
    result.results.forEach((item, index) => {
        const div = document.createElement('div');
        div.className = `result-item ${item.is_correct ? 'correct' : 'incorrect'}`;
        div.innerHTML = `
            <div class="result-question">
                <strong>${index + 1}. ${item.question_text}</strong>
            </div>
            <div class="result-answer">
                Vaše odpověď: ${item.selected_answer_text || 'Bez odpovědi'}
                ${item.is_correct ? '✓' : `<br>Správná odpověď: ${item.correct_answer_text}`}
            </div>
        `;
        resultsList.appendChild(div);
    });
}

/**
 * Export výsledků do textového souboru
 */
function exportResults() {
    if (!lastResult || !quizData) return;

    const now = new Date();
    const dateStr = now.toLocaleDateString('cs-CZ');
    const timeStr = now.toLocaleTimeString('cs-CZ');

    let text = `Výsledky kvízu: ${quizData.quiz_name}\n`;
    text += `Datum: ${dateStr} ${timeStr}\n`;
    text += `${'='.repeat(40)}\n\n`;
    text += `Skóre: ${lastResult.score} / ${lastResult.max_score} (${lastResult.percentage}%)\n`;
    text += `ÄŒas: ${lastResult.time_spent} sekund\n\n`;
    text += `${'='.repeat(40)}\n`;
    text += `Přehled odpovědí:\n\n`;

    lastResult.results.forEach((item, index) => {
        text += `${index + 1}. ${item.question_text}\n`;
        text += `   Vaše odpověď: ${item.selected_answer_text || 'Bez odpovědi'}\n`;
        if (item.is_correct) {
            text += `   ✓ Správně\n`;
        } else {
            text += `   ✗ Špatně — Správná odpověď: ${item.correct_answer_text}\n`;
        }
        text += `\n`;
    });

    const safeName = quizData.quiz_name
        .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
        .replace(/[^a-zA-Z0-9]/g, '_')
        .replace(/_+/g, '_')
        .toLowerCase();
    const fileDate = now.toISOString().slice(0, 10);
    const fileName = `vysledky_${safeName}_${fileDate}.txt`;

    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Spuštění kvízu při načtení stránky
document.addEventListener('DOMContentLoaded', initQuiz);