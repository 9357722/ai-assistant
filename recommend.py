
# recommend.py —— 商品推荐模块
from utils import ai_chat
def recommend_phone(budget, prefer_huawei):
    """根据预算和品牌偏好推荐手机"""
    if budget >= 6000 and prefer_huawei:
        return "推荐：华为 Mate 60 Pro"
    elif budget >= 6000 and not prefer_huawei:
        return "推荐：iPhone 15 Pro"
    elif 3000 <= budget < 6000:
        return "推荐：红米 K90 或 荣耀 100"
    else:
        return "推荐：红米 Note 13 或 荣耀 X50"


def compare_products(query):
    """商品对比（模拟版，后续可接入真实 API）"""
    # 这里是占位逻辑，后续可以升级
    return f"正在为您对比：{query}...（功能完善中）"


# 只有直接运行 recommend.py 时才测试
if __name__ == "__main__":
    print("测试 recommend_phone：")
    print(recommend_phone(7000, True))
    print(recommend_phone(4000, False))
    print(recommend_phone(2000, False))

    print("\n测试 compare_products：")
    print(compare_products("iPhone 15 vs 华为 Mate 60"))

def generate_product_comparison(client, query):
    """调用 AI 生成两个商品的参数对比表格"""
    prompt = f"""### 角色 ###
你是专业商品对比分析师。

### 任务 ###
根据常识和合理推测，对比以下两个商品的核心参数。

### 对比对象 ###
{query}

### 输出要求 ###
1. 生成包含「对比维度」、「商品A」、「商品B」、「差异简评」四列的 Markdown 表格
2. 选取 4-6 个关键维度（价格、性能、续航、特色功能等）
3. 表格下方给出 2-3 句话选购建议"""

    result = ai_chat(client, query, prompt)
    return result