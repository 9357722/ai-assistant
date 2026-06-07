"""
AI 大模型面试题库 Web 版 - 刷题模式
功能：选择题 + 应用题，每次10道，计分系统
"""

import os
import json
import random
import pdfplumber
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="AI 大模型面试题库 - 刷题模式")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])

# ============ 数据结构 ============
class InterviewQuestion:
    def __init__(self, id, question, answer, category, source_file, page_num, question_type="app"):
        self.id = id
        self.question = question
        self.answer = answer
        self.category = category
        self.source_file = source_file
        self.page_num = page_num
        self.question_type = question_type  # "choice" or "app"
        self.options = []  # 选择题选项
        self.correct_option = 0  # 正确选项索引
        self.is_favorite = False
        self.is_wrong = False
        self.attempt_count = 0
        self.correct_count = 0

    def to_dict(self):
        return {
            'id': self.id,
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'source_file': self.source_file,
            'page_num': self.page_num,
            'question_type': self.question_type,
            'options': self.options,
            'correct_option': self.correct_option,
            'is_favorite': self.is_favorite,
            'is_wrong': self.is_wrong,
            'attempt_count': self.attempt_count,
            'correct_count': self.correct_count
        }

# ============ 全局数据 ============
questions: List[InterviewQuestion] = []
categories = set()
favorites = set()
wrong_questions = set()

# ============ 加载题库 ============
def load_questions():
    global questions, categories
    data_dir = r"D:\新建文件夹 (2)\IQIYI Video\大模型学习资料包\6️⃣大模型面试题库"
    pdf_files = list(Path(data_dir).rglob("*.pdf"))
    print(f"找到 {len(pdf_files)} 个PDF文件")

    q_id = 0
    for pdf_file in pdf_files:
        try:
            category = get_category_from_filename(pdf_file.name)
            with pdfplumber.open(pdf_file) as pdf:
                current_question = None
                current_answer = []
                current_page = 1

                for page_num, page in enumerate(pdf.pages, 1):
                    text = page.extract_text()
                    if not text:
                        continue

                    for line in text.split('\n'):
                        line = line.strip()
                        if not line:
                            continue

                        if is_question_line(line):
                            if current_question and current_answer:
                                answer_text = '\n'.join(current_answer)
                                if len(answer_text) > 10:
                                    q_id += 1
                                    q = InterviewQuestion(
                                        id=q_id,
                                        question=current_question,
                                        answer=answer_text,
                                        category=category,
                                        source_file=pdf_file.name,
                                        page_num=current_page,
                                        question_type="app"
                                    )
                                    # 生成选择题版本
                                    if random.random() < 0.4:  # 40%概率生成选择题
                                        q.question_type = "choice"
                                        generate_choice_options(q)
                                    questions.append(q)
                                    categories.add(category)
                            current_question = line
                            current_answer = []
                            current_page = page_num
                        else:
                            current_answer.append(line)

                if current_question and current_answer:
                    answer_text = '\n'.join(current_answer)
                    if len(answer_text) > 10:
                        q_id += 1
                        q = InterviewQuestion(
                            id=q_id,
                            question=current_question,
                            answer=answer_text,
                            category=category,
                            source_file=pdf_file.name,
                            page_num=current_page,
                            question_type="app"
                        )
                        if random.random() < 0.4:
                            q.question_type = "choice"
                            generate_choice_options(q)
                        questions.append(q)
                        categories.add(category)
        except Exception as e:
            print(f"处理 {pdf_file.name} 时出错: {e}")

    print(f"共加载 {len(questions)} 道面试题")
    print(f"分类: {', '.join(sorted(categories))}")

def generate_choice_options(q):
    """生成选择题选项"""
    # 从答案中提取关键词作为正确选项
    keywords = [kw.strip() for kw in q.answer.split('\n') if kw.strip() and len(kw.strip()) > 3]
    if len(keywords) >= 1:
        correct = keywords[0][:50]  # 取第一行作为正确答案
        q.options = [correct]
        q.correct_option = 0

        # 生成错误选项（从其他题目答案中随机选取）
        wrong_answers = [a.answer.split('\n')[0][:50] for a in questions if a.id != q.id and a.answer]
        if len(wrong_answers) >= 3:
            wrong_options = random.sample(wrong_answers, 3)
            q.options.extend(wrong_options)
            # 打乱顺序
            random.shuffle(q.options)
            q.correct_option = q.options.index(correct)

def is_question_line(line):
    if line and line[0].isdigit() and ('?' in line or '？' in line or '是什么' in line or '什么是' in line):
        return True
    if '?' in line or '？' in line:
        return True
    return False

def get_category_from_filename(filename):
    filename = filename.lower()
    if 'rag' in filename:
        return 'RAG'
    elif 'agent' in filename:
        return 'Agent'
    elif '微调' in filename or 'finetune' in filename:
        return '微调'
    elif '训练' in filename or 'train' in filename:
        return '训练'
    elif '推理' in filename or 'inference' in filename:
        return '推理'
    elif '分布式' in filename:
        return '分布式'
    elif '基础' in filename:
        return '基础'
    elif '进阶' in filename:
        return '进阶'
    else:
        return '其他'

# ============ API 路由 ============

@app.get("/", response_class=HTMLResponse)
async def root():
    return get_html_page()

@app.get("/api/categories")
async def get_categories():
    result = []
    for cat in sorted(categories):
        count = len([q for q in questions if q.category == cat])
        result.append({"name": cat, "count": count})
    return {"categories": result}

@app.get("/api/quiz")
async def get_quiz(category: Optional[str] = None, count: int = 10):
    """获取刷题题目（选择题+应用题混合）"""
    filtered = questions
    if category:
        filtered = [q for q in questions if q.category == category]

    if len(filtered) < count:
        count = len(filtered)

    selected = random.sample(filtered, count)

    # 确保有选择题和应用题的混合
    choice_count = len([q for q in selected if q.question_type == "choice"])
    app_count = len([q for q in selected if q.question_type == "app"])

    result = []
    for i, q in enumerate(selected, 1):
        q_dict = q.to_dict()
        q_dict['index'] = i
        result.append(q_dict)

    return {
        "questions": result,
        "total": len(result),
        "choice_count": choice_count,
        "app_count": app_count
    }

@app.post("/api/check/{question_id}")
async def check_answer(question_id: int, answer: str, question_type: str):
    """检查答案"""
    for q in questions:
        if q.id == question_id:
            q.attempt_count += 1

            if question_type == "choice":
                # 选择题检查
                try:
                    selected_idx = int(answer)
                    is_correct = selected_idx == q.correct_option
                except ValueError:
                    is_correct = False
            else:
                # 应用题检查（关键词匹配）
                keywords = [kw.strip() for kw in q.answer.split('\n') if kw.strip() and len(kw.strip()) > 3]
                matched = sum(1 for kw in keywords if kw in answer)
                is_correct = matched >= len(keywords) * 0.3

            if is_correct:
                q.correct_count += 1
            else:
                q.is_wrong = True
                if q.id not in wrong_questions:
                    wrong_questions.add(q.id)

            return {
                "is_correct": is_correct,
                "correct_answer": q.answer,
                "correct_option": q.correct_option if question_type == "choice" else None,
                "explanation": q.answer
            }
    raise HTTPException(status_code=404, detail="题目不存在")

@app.post("/api/favorite/{question_id}")
async def toggle_favorite(question_id: int):
    for q in questions:
        if q.id == question_id:
            q.is_favorite = not q.is_favorite
            if q.is_favorite:
                favorites.add(question_id)
            else:
                favorites.discard(question_id)
            return {"is_favorite": q.is_favorite}
    raise HTTPException(status_code=404, detail="题目不存在")

@app.get("/api/favorites")
async def get_favorites():
    items = [q.to_dict() for q in questions if q.is_favorite]
    return {"items": items, "total": len(items)}

@app.get("/api/wrong")
async def get_wrong_questions():
    items = [q.to_dict() for q in questions if q.is_wrong]
    return {"items": items, "total": len(items)}

@app.get("/api/stats")
async def get_stats():
    total = len(questions)
    fav_count = len([q for q in questions if q.is_favorite])
    wrong_count = len([q for q in questions if q.is_wrong])
    attempted = len([q for q in questions if q.attempt_count > 0])
    correct = sum(q.correct_count for q in questions)

    cat_stats = []
    for cat in sorted(categories):
        count = len([q for q in questions if q.category == cat])
        cat_stats.append({"name": cat, "count": count})

    return {
        "total_questions": total,
        "favorites": fav_count,
        "wrong_questions": wrong_count,
        "attempted": attempted,
        "correct": correct,
        "categories": cat_stats
    }

# ============ HTML 页面 ============

def get_html_page():
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI 大模型面试题库 - 刷题模式</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --bg: #f8fafc;
            --card: #ffffff;
            --text: #1e293b;
            --text-secondary: #64748b;
            --border: #e2e8f0;
            --success: #22c55e;
            --danger: #ef4444;
            --warning: #f59e0b;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
        .container { max-width: 800px; margin: 0 auto; padding: 20px; }
        header { background: linear-gradient(135deg, var(--primary), var(--primary-dark)); color: white; padding: 30px; text-align: center; border-radius: 16px; margin-bottom: 30px; }
        header h1 { font-size: 28px; margin-bottom: 8px; }
        header p { opacity: 0.9; font-size: 14px; }
        .nav { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; justify-content: center; }
        .nav-btn { padding: 10px 20px; border: 2px solid var(--border); border-radius: 10px; background: var(--card); cursor: pointer; font-size: 14px; transition: all 0.2s; }
        .nav-btn:hover, .nav-btn.active { border-color: var(--primary); color: var(--primary); background: #eef2ff; }
        .category-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; margin-bottom: 30px; }
        .category-card { background: var(--card); border-radius: 10px; padding: 16px; text-align: center; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: all 0.2s; }
        .category-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.12); }
        .category-card .name { font-size: 14px; font-weight: 600; }
        .category-card .count { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
        .quiz-container { background: var(--card); border-radius: 16px; padding: 30px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
        .progress-bar { height: 8px; background: #e2e8f0; border-radius: 4px; margin-bottom: 20px; overflow: hidden; }
        .progress-fill { height: 100%; background: linear-gradient(90deg, var(--primary), var(--success)); transition: width 0.3s; }
        .question-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
        .question-number { font-size: 14px; color: var(--text-secondary); }
        .question-type { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; }
        .type-choice { background: #dbeafe; color: #2563eb; }
        .type-app { background: #fef3c7; color: #d97706; }
        .question-text { font-size: 18px; font-weight: 600; line-height: 1.6; margin-bottom: 24px; }
        .options { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
        .option { padding: 16px; border: 2px solid var(--border); border-radius: 12px; cursor: pointer; transition: all 0.2s; }
        .option:hover { border-color: var(--primary); background: #eef2ff; }
        .option.selected { border-color: var(--primary); background: #eef2ff; }
        .option.correct { border-color: var(--success); background: #dcfce7; }
        .option.wrong { border-color: var(--danger); background: #fee2e2; }
        .option-label { font-weight: 600; margin-right: 12px; }
        .app-answer { width: 100%; min-height: 120px; padding: 16px; border: 2px solid var(--border); border-radius: 12px; font-size: 14px; resize: vertical; outline: none; }
        .app-answer:focus { border-color: var(--primary); }
        .btn-group { display: flex; gap: 10px; margin-top: 20px; }
        .btn { padding: 12px 24px; border: none; border-radius: 10px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-outline { background: transparent; border: 2px solid var(--border); color: var(--text); }
        .btn-outline:hover { border-color: var(--primary); color: var(--primary); }
        .btn-success { background: var(--success); color: white; }
        .btn-danger { background: var(--danger); color: white; }
        .result-panel { padding: 20px; border-radius: 12px; margin-top: 20px; }
        .result-correct { background: #dcfce7; border: 1px solid #86efac; }
        .result-wrong { background: #fee2e2; border: 1px solid #fca5a5; }
        .result-title { font-weight: 600; margin-bottom: 8px; }
        .result-answer { font-size: 14px; line-height: 1.6; white-space: pre-wrap; }
        .score-card { text-align: center; padding: 40px; }
        .score-number { font-size: 64px; font-weight: 700; color: var(--primary); }
        .score-label { font-size: 16px; color: var(--text-secondary); margin-top: 8px; }
        .score-detail { display: flex; justify-content: center; gap: 30px; margin-top: 20px; }
        .score-item { text-align: center; }
        .score-item .num { font-size: 24px; font-weight: 600; }
        .score-item .label { font-size: 12px; color: var(--text-secondary); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 30px; }
        .stat-card { background: var(--card); border-radius: 12px; padding: 20px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
        .stat-card .number { font-size: 32px; font-weight: 700; color: var(--primary); }
        .stat-card .label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
        .empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); }
        .empty-state .icon { font-size: 48px; margin-bottom: 16px; }
        @media (max-width: 768px) { .container { padding: 12px; } header { padding: 20px; } header h1 { font-size: 22px; } }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI 大模型面试题库</h1>
            <p>刷题模式 | 选择题 + 应用题 | 每次10道</p>
        </header>

        <div class="nav">
            <button class="nav-btn active" onclick="showSection('home')">首页</button>
            <button class="nav-btn" onclick="showSection('start')">开始刷题</button>
            <button class="nav-btn" onclick="showSection('favorites')">收藏夹</button>
            <button class="nav-btn" onclick="showSection('wrong')">错题本</button>
        </div>

        <!-- 首页 -->
        <div id="section-home">
            <div class="stats-grid" id="stats-grid"></div>
            <h3 style="margin-bottom: 16px; text-align: center;">题库分类</h3>
            <div class="category-grid" id="category-grid"></div>
        </div>

        <!-- 选择分类 -->
        <div id="section-start" style="display:none;">
            <h3 style="margin-bottom: 16px; text-align: center;">选择分类开始刷题</h3>
            <div class="category-grid" id="start-categories"></div>
        </div>

        <!-- 刷题 -->
        <div id="section-quiz" style="display:none;">
            <div class="quiz-container">
                <div class="progress-bar"><div class="progress-fill" id="progress-fill"></div></div>
                <div id="quiz-content"></div>
            </div>
        </div>

        <!-- 成绩 -->
        <div id="section-score" style="display:none;">
            <div class="quiz-container">
                <div class="score-card" id="score-card"></div>
            </div>
        </div>

        <!-- 收藏夹 -->
        <div id="section-favorites" style="display:none;">
            <div id="favorites-list"></div>
        </div>

        <!-- 错题本 -->
        <div id="section-wrong" style="display:none;">
            <div id="wrong-list"></div>
        </div>
    </div>

    <script>
        let currentSection = 'home';
        let quizQuestions = [];
        let currentQuestionIndex = 0;
        let selectedOption = -1;
        let userAnswer = '';
        let score = 0;
        let answered = [];

        async function init() {
            await loadStats();
            await loadCategories();
        }

        async function loadStats() {
            const res = await fetch('/api/stats');
            const data = await res.json();
            document.getElementById('stats-grid').innerHTML = `
                <div class="stat-card"><div class="number">${data.total_questions}</div><div class="label">总题目</div></div>
                <div class="stat-card"><div class="number">${data.categories.length}</div><div class="label">分类</div></div>
                <div class="stat-card"><div class="number">${data.favorites}</div><div class="label">收藏</div></div>
                <div class="stat-card"><div class="number">${data.wrong_questions}</div><div class="label">错题</div></div>
            `;
        }

        async function loadCategories() {
            const res = await fetch('/api/categories');
            const data = await res.json();

            let html = '';
            data.categories.forEach(c => {
                html += `<div class="category-card" onclick="startQuiz('${c.name}')">
                    <div class="name">${c.name}</div><div class="count">${c.count}题</div>
                </div>`;
            });
            document.getElementById('category-grid').innerHTML = html;

            let startHtml = `<div class="category-card" onclick="startQuiz('')" style="border: 2px solid var(--primary);">
                <div class="name">随机刷题</div><div class="count">全部分类</div>
            </div>`;
            data.categories.forEach(c => {
                startHtml += `<div class="category-card" onclick="startQuiz('${c.name}')">
                    <div class="name">${c.name}</div><div class="count">${c.count}题</div>
                </div>`;
            });
            document.getElementById('start-categories').innerHTML = startHtml;
        }

        function showSection(section) {
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            if (event && event.target) event.target.classList.add('active');
            document.querySelectorAll('[id^="section-"]').forEach(s => s.style.display = 'none');
            document.getElementById(`section-${section}`).style.display = 'block';
            currentSection = section;

            if (section === 'home') loadStats();
            if (section === 'favorites') loadFavorites();
            if (section === 'wrong') loadWrong();
        }

        async function startQuiz(category) {
            const res = await fetch(`/api/quiz?category=${encodeURIComponent(category)}&count=10`);
            const data = await res.json();
            quizQuestions = data.questions;
            currentQuestionIndex = 0;
            score = 0;
            answered = new Array(10).fill(null);

            showSection('quiz');
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.nav-btn')[1].classList.add('active');
            renderQuestion();
        }

        function renderQuestion() {
            const q = quizQuestions[currentQuestionIndex];
            const progress = ((currentQuestionIndex + 1) / quizQuestions.length) * 100;
            document.getElementById('progress-fill').style.width = `${progress}%`;

            let html = `
                <div class="question-header">
                    <span class="question-number">第 ${currentQuestionIndex + 1} / ${quizQuestions.length} 题</span>
                    <span class="question-type ${q.question_type === 'choice' ? 'type-choice' : 'type-app'}">
                        ${q.question_type === 'choice' ? '选择题' : '应用题'}
                    </span>
                </div>
                <div class="question-text">${q.question}</div>
            `;

            if (q.question_type === 'choice') {
                html += '<div class="options">';
                const labels = ['A', 'B', 'C', 'D'];
                q.options.forEach((opt, i) => {
                    const isSelected = selectedOption === i;
                    const isAnswered = answered[currentQuestionIndex] !== null;
                    let className = 'option';
                    if (isAnswered) {
                        if (i === q.correct_option) className += ' correct';
                        else if (isSelected && i !== q.correct_option) className += ' wrong';
                    } else if (isSelected) {
                        className += ' selected';
                    }
                    html += `<div class="${className}" onclick="selectOption(${i})">
                        <span class="option-label">${labels[i]}</span>${opt}
                    </div>`;
                });
                html += '</div>';
            } else {
                const isAnswered = answered[currentQuestionIndex] !== null;
                html += `<textarea class="app-answer" id="app-answer" placeholder="输入你的答案..." ${isAnswered ? 'disabled' : ''}>${userAnswer}</textarea>`;
            }

            if (answered[currentQuestionIndex] !== null) {
                const isCorrect = answered[currentQuestionIndex];
                html += `<div class="result-panel ${isCorrect ? 'result-correct' : 'result-wrong'}">
                    <div class="result-title">${isCorrect ? '✓ 回答正确！' : '✗ 回答错误'}</div>
                    <div class="result-answer">${q.answer}</div>
                </div>`;
            }

            html += `<div class="btn-group">`;
            if (answered[currentQuestionIndex] === null) {
                if (q.question_type === 'choice') {
                    html += `<button class="btn btn-primary" onclick="submitAnswer()" ${selectedOption === -1 ? 'disabled' : ''}>提交答案</button>`;
                } else {
                    html += `<button class="btn btn-primary" onclick="submitAnswer()">提交答案</button>`;
                }
            } else {
                if (currentQuestionIndex < quizQuestions.length - 1) {
                    html += `<button class="btn btn-primary" onclick="nextQuestion()">下一题</button>`;
                } else {
                    html += `<button class="btn btn-success" onclick="showScore()">查看成绩</button>`;
                }
            }
            html += `</div>`;

            document.getElementById('quiz-content').innerHTML = html;
        }

        function selectOption(idx) {
            if (answered[currentQuestionIndex] !== null) return;
            selectedOption = idx;
            renderQuestion();
        }

        async function submitAnswer() {
            const q = quizQuestions[currentQuestionIndex];
            let answer;

            if (q.question_type === 'choice') {
                answer = selectedOption.toString();
            } else {
                answer = document.getElementById('app-answer').value;
                if (!answer.trim()) return;
            }

            const res = await fetch(`/api/check/${q.id}?answer=${encodeURIComponent(answer)}&question_type=${q.question_type}`, { method: 'POST' });
            const result = await res.json();

            answered[currentQuestionIndex] = result.is_correct;
            if (result.is_correct) score++;

            renderQuestion();
        }

        function nextQuestion() {
            currentQuestionIndex++;
            selectedOption = -1;
            userAnswer = '';
            renderQuestion();
        }

        function showScore() {
            showSection('score');
            const percentage = Math.round((score / quizQuestions.length) * 100);
            const correctCount = score;
            const wrongCount = quizQuestions.length - score;

            let emoji = '🎉';
            let message = '太棒了！';
            if (percentage < 60) { emoji = '😢'; message = '继续加油！'; }
            else if (percentage < 80) { emoji = '👍'; message = '不错！'; }

            document.getElementById('score-card').innerHTML = `
                <div style="font-size: 64px; margin-bottom: 16px;">${emoji}</div>
                <div class="score-number">${percentage}分</div>
                <div class="score-label">${message}</div>
                <div class="score-detail">
                    <div class="score-item"><div class="num" style="color: var(--success);">${correctCount}</div><div class="label">正确</div></div>
                    <div class="score-item"><div class="num" style="color: var(--danger);">${wrongCount}</div><div class="label">错误</div></div>
                </div>
                <div class="btn-group" style="justify-content: center; margin-top: 30px;">
                    <button class="btn btn-primary" onclick="showSection('start')">再来一轮</button>
                    <button class="btn btn-outline" onclick="showSection('home')">返回首页</button>
                </div>
            `;
        }

        async function loadFavorites() {
            const res = await fetch('/api/favorites');
            const data = await res.json();
            if (data.total === 0) { document.getElementById('favorites-list').innerHTML = '<div class="empty-state"><div class="icon">暂无收藏</div><p>刷题时点击收藏按钮</p></div>'; return; }
            let html = '<div class="quiz-container"><h3>收藏题目</h3><br>';
            data.items.forEach(q => {
                html += `<div style="padding: 12px; border-bottom: 1px solid var(--border); cursor: pointer;" onclick="alert('${q.answer.replace(/'/g, "\\'")}')">
                    <div style="font-weight: 500;">${q.question}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${q.category}</div>
                </div>`;
            });
            html += '</div>';
            document.getElementById('favorites-list').innerHTML = html;
        }

        async function loadWrong() {
            const res = await fetch('/api/wrong');
            const data = await res.json();
            if (data.total === 0) { document.getElementById('wrong-list').innerHTML = '<div class="empty-state"><div class="icon">暂无错题</div><p>刷题中答错的题会出现在这里</p></div>'; return; }
            let html = '<div class="quiz-container"><h3>错题本</h3><br>';
            data.items.forEach(q => {
                html += `<div style="padding: 12px; border-bottom: 1px solid var(--border);">
                    <div style="font-weight: 500;">${q.question}</div>
                    <div style="font-size: 12px; color: var(--text-secondary); margin-top: 4px;">${q.category}</div>
                    <div style="font-size: 13px; margin-top: 8px; color: var(--primary);">答案: ${q.answer.substring(0, 100)}...</div>
                </div>`;
            });
            html += '</div>';
            document.getElementById('wrong-list').innerHTML = html;
        }

        init();
    </script>
</body>
</html>'''

# ============ 启动 ============
if __name__ == "__main__":
    import uvicorn
    load_questions()
    uvicorn.run(app, host="0.0.0.0", port=8888)
