"""
AI 大模型面试题库程序
功能：
1. 读取 PDF 面试题库
2. 分类整理题目
3. 模拟面试（随机出题）
4. 查看答案
5. 收藏题目
6. 错题本
"""

import os
import json
import random
import pdfplumber
from pathlib import Path
from datetime import datetime

class InterviewQuestion:
    """面试题数据结构"""
    def __init__(self, question, answer, category, source_file, page_num):
        self.question = question
        self.answer = answer
        self.category = category
        self.source_file = source_file
        self.page_num = page_num
        self.is_favorite = False
        self.is_wrong = False
        self.attempt_count = 0
        self.correct_count = 0

    def to_dict(self):
        return {
            'question': self.question,
            'answer': self.answer,
            'category': self.category,
            'source_file': self.source_file,
            'page_num': self.page_num,
            'is_favorite': self.is_favorite,
            'is_wrong': self.is_wrong,
            'attempt_count': self.attempt_count,
            'correct_count': self.correct_count
        }

class InterviewSystem:
    """面试系统"""
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.questions = []
        self.categories = set()
        self.favorites = []
        self.wrong_questions = []
        self.current_question = None
        self.score = 0
        self.total_questions = 0
        self.load_questions()

    def load_questions(self):
        """加载所有PDF中的面试题"""
        print("正在加载面试题库...")

        # 遍历所有PDF文件
        pdf_files = list(self.data_dir.rglob("*.pdf"))
        print(f"找到 {len(pdf_files)} 个PDF文件")

        for pdf_file in pdf_files:
            try:
                self.extract_questions_from_pdf(pdf_file)
            except Exception as e:
                print(f"处理 {pdf_file.name} 时出错: {e}")

        print(f"共加载 {len(self.questions)} 道面试题")
        print(f"分类: {', '.join(sorted(self.categories))}")

    def extract_questions_from_pdf(self, pdf_path):
        """从PDF中提取面试题"""
        with pdfplumber.open(pdf_path) as pdf:
            current_question = None
            current_answer = []
            category = self.get_category_from_filename(pdf_path.name)

            for page_num, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if not text:
                    continue

                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue

                    # 检测题目（通常是数字开头的问题）
                    if self.is_question_line(line):
                        # 保存上一道题
                        if current_question and current_answer:
                            answer_text = '\n'.join(current_answer)
                            if len(answer_text) > 10:  # 过滤太短的答案
                                self.questions.append(InterviewQuestion(
                                    question=current_question,
                                    answer=answer_text,
                                    category=category,
                                    source_file=pdf_path.name,
                                    page_num=page_num
                                ))
                                self.categories.add(category)

                        current_question = line
                        current_answer = []
                    else:
                        current_answer.append(line)

            # 保存最后一道题
            if current_question and current_answer:
                answer_text = '\n'.join(current_answer)
                if len(answer_text) > 10:
                    self.questions.append(InterviewQuestion(
                        question=current_question,
                        answer=answer_text,
                        category=category,
                        source_file=pdf_path.name,
                        page_num=page_num
                    ))

    def is_question_line(self, line):
        """判断是否是题目行"""
        # 数字开头的问题
        if line and line[0].isdigit() and ('?' in line or '？' in line or '是什么' in line or '什么是' in line):
            return True
        # 带问号的行
        if '?' in line or '？' in line:
            return True
        return False

    def get_category_from_filename(self, filename):
        """从文件名获取分类"""
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

    def get_random_question(self, category=None):
        """获取随机题目"""
        if category:
            filtered = [q for q in self.questions if q.category == category]
        else:
            filtered = self.questions

        if not filtered:
            return None

        self.current_question = random.choice(filtered)
        self.total_questions += 1
        return self.current_question

    def check_answer(self, user_answer):
        """检查答案"""
        if not self.current_question:
            return False

        # 简单的答案匹配（实际应该用更智能的匹配）
        correct_answer = self.current_question.answer.lower()
        user_answer = user_answer.lower()

        # 关键词匹配
        keywords = [kw.strip() for kw in correct_answer.split() if len(kw.strip()) > 2]
        matched = sum(1 for kw in keywords if kw in user_answer)

        if matched >= len(keywords) * 0.3:  # 30%关键词匹配就算对
            self.current_question.correct_count += 1
            self.score += 1
            return True
        else:
            self.current_question.is_wrong = True
            if self.current_question not in self.wrong_questions:
                self.wrong_questions.append(self.current_question)
            return False

    def add_to_favorites(self, question):
        """添加到收藏"""
        question.is_favorite = True
        if question not in self.favorites:
            self.favorites.append(question)

    def remove_from_favorites(self, question):
        """从收藏中移除"""
        question.is_favorite = False
        if question in self.favorites:
            self.favorites.remove(question)

    def get_favorites(self):
        """获取收藏列表"""
        return self.favorites

    def get_wrong_questions(self):
        """获取错题本"""
        return self.wrong_questions

    def get_categories(self):
        """获取所有分类"""
        return sorted(list(self.categories))

    def get_questions_by_category(self, category):
        """按分类获取题目"""
        return [q for q in self.questions if q.category == category]

    def get_statistics(self):
        """获取统计信息"""
        return {
            'total_questions': len(self.questions),
            'total_attempted': self.total_questions,
            'correct_count': self.score,
            'accuracy': self.score / self.total_questions * 100 if self.total_questions > 0 else 0,
            'favorites_count': len(self.favorites),
            'wrong_count': len(self.wrong_questions),
            'categories': list(self.categories)
        }

    def save_progress(self, filepath):
        """保存进度"""
        data = {
            'questions': [q.to_dict() for q in self.questions],
            'favorites': [q.to_dict() for q in self.favorites],
            'wrong_questions': [q.to_dict() for q in self.wrong_questions],
            'score': self.score,
            'total_questions': self.total_questions
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_progress(self, filepath):
        """加载进度"""
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.score = data.get('score', 0)
                self.total_questions = data.get('total_questions', 0)
                # 恢复收藏和错题
                # ...（简化实现）

def main():
    """主函数"""
    print("=" * 60)
    print("AI 大模型面试题库系统")
    print("=" * 60)

    # 数据目录
    data_dir = r"D:\新建文件夹 (2)\IQIYI Video\大模型学习资料包\6️⃣大模型面试题库"

    # 初始化系统
    system = InterviewSystem(data_dir)

    while True:
        print("\n" + "=" * 60)
        print("主菜单")
        print("=" * 60)
        print("1. 开始模拟面试")
        print("2. 按分类查看题目")
        print("3. 查看收藏题目")
        print("4. 查看错题本")
        print("5. 查看统计信息")
        print("6. 退出")

        choice = input("\n请选择 (1-6): ").strip()

        if choice == '1':
            start_interview(system)
        elif choice == '2':
            browse_by_category(system)
        elif choice == '3':
            view_favorites(system)
        elif choice == '4':
            view_wrong_questions(system)
        elif choice == '5':
            view_statistics(system)
        elif choice == '6':
            print("\n感谢使用，再见！")
            break
        else:
            print("\n无效选择，请重试")

def start_interview(system):
    """开始模拟面试"""
    print("\n" + "=" * 60)
    print("模拟面试")
    print("=" * 60)

    categories = system.get_categories()
    print("\n可选分类:")
    for i, cat in enumerate(categories, 1):
        print(f"{i}. {cat}")
    print(f"{len(categories) + 1}. 随机分类")

    cat_choice = input("\n选择分类 (输入数字): ").strip()

    try:
        cat_idx = int(cat_choice) - 1
        if 0 <= cat_idx < len(categories):
            category = categories[cat_idx]
        else:
            category = None
    except ValueError:
        category = None

    print("\n开始面试！输入 'quit' 退出，'skip' 跳过，'fav' 收藏")

    question_count = 0
    while True:
        question = system.get_random_question(category)
        if not question:
            print("\n没有更多题目了！")
            break

        question_count += 1
        print(f"\n【第 {question_count} 题】")
        print(f"分类: {question.category}")
        print(f"来源: {question.source_file}")
        print(f"\n题目: {question.question}")

        user_input = input("\n你的答案 (或 quit/skip/fav): ").strip()

        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'skip':
            print("\n已跳过")
            continue
        elif user_input.lower() == 'fav':
            system.add_to_favorites(question)
            print("\n已收藏！")
            continue

        # 检查答案
        is_correct = system.check_answer(user_input)
        if is_correct:
            print("\n✓ 回答正确！")
        else:
            print("\n✗ 回答不正确")
            print(f"\n参考答案:\n{question.answer}")

        # 显示进度
        stats = system.get_statistics()
        print(f"\n当前得分: {stats['correct_count']}/{stats['total_attempted']} "
              f"({stats['accuracy']:.1f}%)")

def browse_by_category(system):
    """按分类查看题目"""
    categories = system.get_categories()

    while True:
        print("\n" + "=" * 60)
        print("按分类查看")
        print("=" * 60)

        for i, cat in enumerate(categories, 1):
            count = len(system.get_questions_by_category(cat))
            print(f"{i}. {cat} ({count}题)")
        print(f"{len(categories) + 1}. 返回主菜单")

        choice = input("\n选择分类 (输入数字): ").strip()

        try:
            cat_idx = int(choice) - 1
            if cat_idx == len(categories):
                break
            if 0 <= cat_idx < len(categories):
                category = categories[cat_idx]
                questions = system.get_questions_by_category(category)

                print(f"\n【{category}】共 {len(questions)} 题")
                for i, q in enumerate(questions[:10], 1):  # 只显示前10题
                    print(f"{i}. {q.question[:50]}...")

                if len(questions) > 10:
                    print(f"... 还有 {len(questions) - 10} 题")

                input("\n按 Enter 返回...")
        except ValueError:
            print("无效输入")

def view_favorites(system):
    """查看收藏题目"""
    favorites = system.get_favorites()

    if not favorites:
        print("\n暂无收藏题目")
        input("按 Enter 返回...")
        return

    print("\n" + "=" * 60)
    print(f"收藏题目 ({len(favorites)} 题)")
    print("=" * 60)

    for i, q in enumerate(favorites, 1):
        print(f"{i}. [{q.category}] {q.question[:50]}...")

    input("\n按 Enter 返回...")

def view_wrong_questions(system):
    """查看错题本"""
    wrong = system.get_wrong_questions()

    if not wrong:
        print("\n暂无错题")
        input("按 Enter 返回...")
        return

    print("\n" + "=" * 60)
    print(f"错题本 ({len(wrong)} 题)")
    print("=" * 60)

    for i, q in enumerate(wrong, 1):
        print(f"{i}. [{q.category}] {q.question[:50]}...")

    input("\n按 Enter 返回...")

def view_statistics(system):
    """查看统计信息"""
    stats = system.get_statistics()

    print("\n" + "=" * 60)
    print("统计信息")
    print("=" * 60)
    print(f"总题目数: {stats['total_questions']}")
    print(f"已答题数: {stats['total_attempted']}")
    print(f"正确数: {stats['correct_count']}")
    print(f"正确率: {stats['accuracy']:.1f}%")
    print(f"收藏数: {stats['favorites_count']}")
    print(f"错题数: {stats['wrong_count']}")
    print(f"\n分类统计:")
    for cat in stats['categories']:
        count = len(system.get_questions_by_category(cat))
        print(f"  - {cat}: {count} 题")

    input("\n按 Enter 返回...")

if __name__ == "__main__":
    main()
