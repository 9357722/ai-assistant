import openai

client = openai.OpenAI(
    api_key="sk-ef1bcf1c1c0b4deebbaf4a83cbcc0dd0",
    base_url="https://api.deepseek.com"
)

# 结构化 Prompt 实战：做一个编程术语解释器
system_prompt = """
### 角色 ###
你是一位专为编程初学者服务的助教，擅长用生活中常见的比喻来解释晦涩的技术概念。

### 任务 ###
用户会输入一个编程术语，你需要用比喻的方式解释它。

### 约束 ###
- 解释必须包含一个生活化的比喻（比如把API比作服务员，把变量比作盒子）
- 总字数不超过150字
- 语气亲切幽默
- 不要输出任何除解释内容以外的废话
"""

user_question = "什么是异步编程？"

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_question}
    ]
)

print("用户问题：", user_question)
print("AI 解释：", response.choices[0].message.content)