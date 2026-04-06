/**
 * Brainiac - Logika hraní kvízu
 * 
 * Tento soubor řídí celý průběh hraní kvízu na stránce quiz_play.html:
 * 
 *   1. initQuiz()     – načte otázky z /quiz/<id>/questions (quiz.py:get_quiz_questions)
 *   2. showQuestion()  – zobrazí otázku a spustí časovač
 *   3. selectAnswer()  – uživatel klikne na odpověď, uloží se do userAnswers[]
 *   4. finishQuiz()    – odešle výsledky na /quiz/<id>/submit (quiz.py:submit_quiz)
 *   5. showResults()   – zobrazí přehled správných/špatných odpovědí
 *   6. exportResults() – stažení výsledků jako .txt soubor
 * 
 * Globální proměnné (definované v quiz_play.html šabloně):
 *   QUIZ_ID    – ID kvízu
 *   TIME_LIMIT – čas na otázku v sekundách
 *   CSRF_TOKEN – token pro CSRF ochranu (Flask-WTF)
 */

/**
 * Escapování HTML – ochrana proti XSS.
 * Používá se při vkládání textu otázek/odpovědí do innerHTML.
 * Vytvoří textový uzel (automaticky escapuje) a vrátí HTML.
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// Stav hry – drží se v paměti po dobu hraní jednoho kvízu
let quizData = null;           // JSON data z /quiz/<id>/questions
let currentQuestionIndex = 0;  // index aktuální otázky (0-based)
let userAnswers = [];          // pole odpovědí [{question_id, answer_id}]
let timerInterval = null;      // reference na setInterval pro časovač
let timeRemaining = 0;         // zbývající čas na aktuální otázku
let totalTimeSpent = 0;        // celkový čas hraní (součet všech otázek)
let questionStartTime = 0;     // Date.now() při zobrazení otázky
let lastResult = null;         // výsledky pro exportResults()

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
 * Inicializace kvízu – načte otázky ze serveru a zobrazí první.
 * Volá se automaticky při DOMContentLoaded (viz konec souboru).
 */
async function initQuiz() {
    try {
        const response = await fetch(`/quiz/${QUIZ_ID}/questions`);
        // Vrátí JSON z quiz.py:get_quiz_questions():
        // {quiz_id, quiz_name, time_limit, questions: [{id, text, answers: [{id, text}]}]}
        // Pozn.: answers neobsahují is_correct – správnost se kontroluje až při submit
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
 * Zobrazení otázky na daném indexu.
 * Pokud index >= počet otázek, zavolá finishQuiz().
 * Aktualizuje progress bar, text otázky a vygeneruje tlačítka odpovědí.
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
            <span class="answer-text">${escapeHtml(answer.text)}</span>
        `;
        btn.onclick = () => selectAnswer(answer.id);
        answersGridEl.appendChild(btn);
    });
    
    // Spuštění časovače
    startTimer();
    questionStartTime = Date.now();
}

/**
 * Spuštění časovače – odpočítává TIME_LIMIT sekund.
 * Při vypršení přeskočí na další otázku bez odpovědi (answer_id: null).
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
 * Aktualizace zobrazení časovače – barva se mění: normál → warning (≤10s) → danger (≤5s).
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
 * Výběr odpovědi – zastaví časovač, uloží odpověď a přejde na další otázku.
 * 300ms pauza dává uživateli vizuální zpětnou vazbu.
 */
function selectAnswer(answerId) {
    clearInterval(timerInterval);
    
    // Výpočet času
    const timeSpent = Math.round((Date.now() - questionStartTime) / 1000);
    totalTimeSpent += timeSpent;
    
    // Uložení odpovědi do pole → později se odešle jako JSON v finishQuiz()
    // Formát shodný s api.py:api_submit_quiz() a quiz.py:submit_quiz()
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
 * Dokončení kvízu – odešle všechny odpovědi na server přes POST.
 * Hlavička X-CSRFToken je nutná pro CSRF ochranu (Flask-WTF).
 * Server vrátí: skóre, přehled odpovědí, případně nové achievementy.
 */
async function finishQuiz() {
    clearInterval(timerInterval);
    
    // Skrytí otázek, zobrazení výsledků
    questionContainer.style.display = 'none';
    document.querySelector('.quiz-game-header').style.display = 'none';
    
    try {
        // Odešle všechny odpovědi na quiz.py:submit_quiz(quiz_id)
        // X-CSRFToken hlavička je nutná pro Flask-WTF CSRF ochranu
        // CSRF_TOKEN je definován v quiz_play.html šabloně jako {{ csrf_token() }}
        const response = await fetch(`/quiz/${QUIZ_ID}/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': CSRF_TOKEN
            },
            // userAnswers + totalTimeSpent se předávají serveru ke zpracování
            body: JSON.stringify({
                answers: userAnswers,
                time_spent: totalTimeSpent
            })
        });
        
        // result = JSON z quiz.py:submit_quiz():
        // {success, score, max_score, percentage, time_spent, results: [...], new_achievements: [...]}
        const result = await response.json();
        
        if (result.success) {
            showResults(result);
            // Pokud server vrátil nové achievementy → main.js:showAchievementQueue() je zobrazí
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
 * Zobrazení výsledků – přepne UI z otázky na přehled odpovědí.
 * Správné odpovědi se označí zeleně, špatné červeně se správnou odpovědí.
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
                <strong>${index + 1}. ${escapeHtml(item.question_text)}</strong>
            </div>
            <div class="result-answer">
                Vaše odpověď: ${escapeHtml(item.selected_answer_text) || 'Bez odpovědi'}
                ${item.is_correct ? '✓' : `<br>Správná odpověď: ${escapeHtml(item.correct_answer_text)}`}
            </div>
        `;
        resultsList.appendChild(div);
    });
}

/**
 * Export výsledků do textového souboru (.txt) – stahuje se přes Blob URL.
 * Název souboru se generuje z názvu kvízu (bez diakritiky) a data.
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

// Spuštění kvízu při načtení stránky (quiz_play.html)
document.addEventListener('DOMContentLoaded', initQuiz);