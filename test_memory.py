# test_memory.py —— 测试对话记忆功能

import openai
import os
from utils import ChatSession

# 从环境变量读取 API Key
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    print("错误：请设置环境变量 DEEPSEEK_API_KEY")
    exit(1)

# 初始化 DeepSeek 客户端
client = openai.OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)

# 创建一个带记忆的会话，设定 AI 的角色
session = ChatSession(system_prompt="你是一个编程助教，回答要简洁，用中文。")

# 第一轮对话
print("=== 第1轮 ===")
reply = session.ask(client, "我叫小明，我正在学 Python。")
print(f"AI: {reply}\n")

# 第二轮对话——AI 应该记住名字和上下文
print("=== 第2轮 ===")
reply = session.ask(client, "我叫什么名字？我在学什么？")
print(f"AI: {reply}\n")

# 第三轮对话
print("=== 第3轮 ===")
reply = session.ask(client, "给我出一道列表操作的练习题。")
print(f"AI: {reply}\n")

# 查看完整历史记录
print("=== 完整对话记录 ===")
for i, msg in enumerate(session.get_history()):
    role = msg['role']
    content = msg['content'][:50]
    print(f"{i+1}. [{role}]: {content}...")