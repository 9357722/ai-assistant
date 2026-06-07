// ============================================================
// 第四章：LangChain 与 LangGraph
// ============================================================
module.exports = {
  title: "第四章：LangChain 与 LangGraph",
  difficulty: "A/B",
  knowledge: [
    {
      term: "LangChain 核心组件",
      desc: "LangChain是一个用于构建LLM应用的开源框架，六大核心组件：1.Model（模型）——封装各种LLM接口（OpenAI、Anthropic、本地模型），统一调用方式；2.Prompt（提示模板）——管理和复用Prompt，支持变量插入和格式化；3.Chain（链）——将多个组件串联为工作流，如Prompt→LLM→OutputParser；4.Memory（记忆）——管理对话历史和上下文；5.Tool（工具）——封装外部功能（搜索、计算、API），供Agent调用；6.Agent（智能体）——LLM自主决定使用哪些工具、以什么顺序执行。LangChain的核心价值是抽象和标准化——让开发者可以轻松切换底层模型和组件。",
      explain: "LangChain像一个乐高积木工厂。Model是不同颜色的积木块（GPT-4是红色、Claude是蓝色），Prompt是积木形状模板，Chain是拼装说明书，Memory是便签纸（记录拼到哪了），Tool是特殊功能积木（带轮子、带灯光），Agent是设计师（决定怎么拼）。你可以自由组合，快速搭建各种'建筑'（应用）。",
      parse: [
        { q: "LangChain的抽象层有什么优缺点？", answer: "优点：1.统一接口——切换模型只需改一行代码；2.丰富的生态——大量预构建的Loader、Tool、Chain；3.快速原型——几行代码就能搭建RAG或Agent；4.社区活跃——文档完善，遇到问题容易找到解决方案。缺点：1.抽象层增加复杂度——调试时需要跳过多层封装；2.性能开销——额外的抽象层有一定性能损耗；3.版本更新频繁——API经常变化，代码需要频繁维护；4.过度封装——简单场景用LangChain反而更复杂。建议：复杂项目用LangChain提升效率，简单项目直接调用SDK。" },
      ],
    },
    {
      term: "LCEL（LangChain Expression Language）",
      desc: "LCEL是LangChain的声明式组合语言，用管道操作符（|）将组件串联为可执行的Chain。语法：chain = prompt | llm | output_parser。核心特性：1.声明式——描述'做什么'而非'怎么做'；2.流式支持——自动支持stream/ainvoke/astream；3.并行执行——RunnableParallel可以并行运行多个分支；4.批处理——自动支持batch调用；5.重试和回退——RunnableWithFallbacks。LCEL替代了早期的LLMChain等类，是LangChain 0.1+推荐的Chain构建方式。",
      explain: "LCEL像Unix的管道命令。'cat file | grep error | sort | head -10'——每一步的输出是下一步的输入。LCEL也是这样：prompt（组装问题）| llm（AI回答）| parser（解析结果）——数据在管道中流动，每一步做一件事。",
      code: `# LCEL 基本用法
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser

prompt = ChatPromptTemplate.from_template(
    "用一句话解释什么是{concept}"
)
llm = ChatOpenAI(model="gpt-4")
parser = StrOutputParser()

# 用管道操作符组合
chain = prompt | llm | parser

# 调用
result = chain.invoke({"concept": "机器学习"})
# 输出: "机器学习是让计算机从数据中自动学习规律的技术。"

# 并行执行
from langchain_core.runnables import RunnableParallel
chain_parallel = RunnableParallel(
    definition=prompt | llm | parser,   # 分支1：解释概念
    example=prompt2 | llm | parser      # 分支2：举例说明
)`,
      parse: [
        { q: "LCEL相比传统的LLMChain有什么优势？", answer: "1.更灵活——管道操作符可以自由组合，传统LLMChain是固定的Prompt→LLM→Parser流程；2.自动支持流式——LCEL Chain天然支持stream()方法，LLMChain需要额外处理；3.并行执行——RunnableParallel可以并行运行多个分支，传统方式只能串行；4.更好的错误处理——每个步骤的错误可以独立捕获和处理；5.可组合性——小Chain可以嵌套组合成大Chain，像搭积木一样。LCEL是LangChain的设计哲学转变：从面向对象（类继承）到函数式（管道组合）。" },
      ],
    },
    {
      term: "Prompt Template（提示模板）",
      desc: "Prompt Template是将动态变量插入提示词中的模板系统。类型：1.ChatPromptTemplate——聊天模型的提示模板，支持System/Human/AI多种角色消息；2.PromptTemplate——纯文本模板，用{变量}占位符；3.FewShotPromptTemplate——包含示例的模板，自动格式化few-shot示例。核心功能：变量插入（{variable}）、格式验证（确保所有变量都有值）、模板复用（一处定义多处使用）。Prompt设计是LLM应用中最重要的环节——好的Prompt Template可以让输出质量提升50%以上。",
      explain: "Prompt Template像邮件模板。你不需要每次手写完整邮件，而是设计一个模板'亲爱的{name}，感谢您购买{product}...'，每次只需要填入姓名和产品名。这样既省时又保持格式统一，还能根据不同场景（售后、营销）设计不同模板。",
      code: `# Prompt Template 示例
from langchain_core.prompts import ChatPromptTemplate

# 系统消息 + 用户消息模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "你是一个{role}，请用{style}的风格回答问题。"),
    ("human", "{question}")
])

# 格式化输出
messages = prompt.format_messages(
    role="Python专家",
    style="简洁明了",
    question="什么是装饰器？"
)

# Few-shot 模板
from langchain_core.prompts import FewShotPromptTemplate
examples = [
    {"input": "高兴", "output": "happy"},
    {"input": "悲伤", "output": "sad"},
]
example_prompt = PromptTemplate.from_template("中文：{input} → 英文：{output}")
few_shot = FewShotPromptTemplate(
    examples=examples,
    example_prompt=example_prompt,
    prefix="将中文翻译为英文：",
    suffix="中文：{input} → 英文："
)`,
      parse: [
        { q: "如何设计高质量的Prompt Template？有哪些最佳实践？", answer: "1.角色设定——System消息中明确Agent的角色和行为规范（'你是XX领域的专家'）；2.任务描述——清晰说明要做什么、不做什么、输出格式；3.约束条件——指定输出格式（JSON/Markdown）、长度限制、语言要求；4.Few-shot示例——提供2-3个输入输出示例，让LLM理解期望；5.变量隔离——需要动态变化的部分用变量，固定部分写死在模板中；6.版本管理——不同场景用不同模板，像管理代码一样管理Prompt。避免：模糊的指令、过长的Prompt（浪费token）、缺少输出格式要求。" },
      ],
    },
    {
      term: "Chain 类型",
      desc: "LangChain中的Chain是将多个组件串联执行的工作流。主要类型：1.LLMChain——最基本的链：Prompt→LLM→Parser，适合单步生成任务；2.SequentialChain——多个Chain按顺序执行，前一个的输出作为后一个的输入（已被LCEL管道替代）；3.RouterChain——根据输入动态路由到不同的子Chain，适合多场景分发（如按语言路由到翻译链或摘要链）。在LCEL时代，这些Chain类型都可以用管道操作符（|）和RunnableBranch实现，更灵活更简洁。但理解传统Chain类型有助于理解LangChain的设计演进。",
      explain: "Chain类型像不同的流水线模式。LLMChain是一个工位（原料→加工→成品）。SequentialChain是流水线（原料→粗加工→精加工→包装→成品）。RouterChain是智能分拣（判断产品类型→送入不同的流水线）。LCEL则是通用管道——你可以自由拼接任意工位，不再受限于固定模式。",
      parse: [
        { q: "LCEL的管道组合如何替代传统的SequentialChain和RouterChain？", answer: "SequentialChain替代：A | B | C，管道操作符自然串联，每个组件的输出自动传给下一个。RouterChain替代：RunnableBranch——根据条件选择不同的分支执行。例如：RunnableBranch((条件1, chain1), (条件2, chain2), (默认, chain3))。LCEL的优势：不需要预先定义Chain类型，任何Runnable都可以自由组合；自动支持流式和异步；代码更简洁直观。传统Chain更多是概念参考，实际开发中推荐全部用LCEL。" },
      ],
    },
    {
      term: "Memory 类型",
      desc: "LangChain提供多种Memory组件管理对话历史：1.ConversationBufferMemory——保存完整对话历史，简单但token消耗大；2.ConversationBufferWindowMemory——滑动窗口，只保留最近K轮对话，平衡成本和上下文；3.ConversationSummaryMemory——用LLM将对话历史压缩为摘要，节省token但可能丢失细节；4.ConversationSummaryBufferMemory——保留最近几轮完整对话+早期对话的摘要，最佳平衡方案；5.VectorStoreMemory——将对话存入向量库，按语义相似度检索相关历史。选择标准：短对话用Buffer，长对话用Summary+Buffer组合，需要语义检索用VectorStore。",
      explain: "Memory类型像不同的记笔记方式。Buffer Memory像逐字记录——什么都记，完整但费本子。Window Memory像只记最近几页——之前的翻掉不管。Summary Memory像写摘要——把长对话压缩成要点。Summary+Buffer组合最实用——最近的详细记，远的写摘要。",
      code: `# ConversationSummaryBufferMemory 示例
from langchain.memory import ConversationSummaryBufferMemory
from langchain_openai import ChatOpenAI

memory = ConversationSummaryBufferMemory(
    llm=ChatOpenAI(model="gpt-4"),
    max_token_limit=500,    # 超过500 token时自动摘要
    return_messages=True
)

# 对话过程中自动管理记忆
memory.save_context(
    {"input": "我想学Python"},
    {"output": "好的！Python是一门很好的入门语言..."}
)
# 当对话历史超过500 token时，旧内容自动压缩为摘要`,
      parse: [
        { q: "ConversationSummaryBufferMemory的工作原理是什么？为什么说它是最佳平衡方案？", answer: "工作原理：维护两部分——滑动窗口（保留最近N条消息）和摘要（更早消息的LLM压缩版）。当窗口满时，最早的消息被移出窗口并入摘要。优势：1.最近的对话保持完整（不需要解压，精确可用）；2.早期对话通过摘要保留关键信息（不会完全丢失）；3.总token消耗可控（摘要远比原文短）。相比纯Buffer不会token爆表，相比纯Summary不会丢失近期细节。max_token_limit是控制窗口大小的关键参数。" },
      ],
    },
    {
      term: "LangGraph 定义与原理",
      desc: "LangGraph是LangChain团队开发的有状态、多步骤AI应用框架。核心概念：将应用建模为有向图（Graph），节点（Node）是处理函数，边（Edge）定义执行流向，状态（State）在节点间传递和更新。特点：1.有向图结构——支持条件分支、循环、并行，比线性Chain更灵活；2.持久化状态——State在执行过程中不断更新，支持中断和恢复；3.人机协作——支持Human-in-the-Loop，在任意节点暂停等待人工输入；4.检查点（Checkpointing）——自动保存执行状态，支持回滚和重放。LangGraph是构建复杂Agent和工作流的首选框架。",
      explain: "LangGraph像地铁线路图。每个站点（Node）是一个处理步骤（查询数据库、调用LLM、执行工具），铁轨（Edge）连接各站点决定行驶方向，车厢里的乘客信息（State）在各站更新。条件分支像换乘站——根据目的地选择不同线路。循环像环线——可以反复经过某些站点直到满足条件。",
      code: `# LangGraph 基本示例
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# 1.定义State
class AgentState(TypedDict):
    question: str
    answer: str
    need_search: bool

# 2.定义节点函数
def analyze(state: AgentState) -> AgentState:
    # LLM判断是否需要搜索
    question = state["question"]
    need_search = "最新" in question or "今天" in question
    return {"need_search": need_search}

def search(state: AgentState) -> AgentState:
    # 执行搜索
    return {"answer": f"搜索结果：关于'{state['question']}'..."}

def direct_answer(state: AgentState) -> AgentState:
    # 直接回答
    return {"answer": f"直接回答：关于'{state['question']}'..."}

# 3.构建图
graph = StateGraph(AgentState)
graph.add_node("analyze", analyze)
graph.add_node("search", search)
graph.add_node("direct_answer", direct_answer)

graph.add_edge(START, "analyze")
graph.add_conditional_edges("analyze",
    lambda s: "search" if s["need_search"] else "direct_answer")
graph.add_edge("search", END)
graph.add_edge("direct_answer", END)

# 4.编译运行
app = graph.compile()
result = app.invoke({"question": "今天上海的天气怎么样？"})`,
      parse: [
        { q: "LangGraph的State设计有哪些最佳实践？", answer: "1.使用TypedDict定义——类型清晰、IDE支持好；2.字段设计为可选更新——节点只返回需要更新的字段，通过Reducer合并；3.避免State过大——只存必要的中间状态，大文件用引用（存路径不存内容）；4.设计清晰的类型——用Literal类型限制枚举值、用Optional标记可空字段；5.版本兼容——State字段变更时考虑向后兼容。核心原则：State是节点间的'公共语言'，设计得好整个Graph就清晰流畅。" },
        { q: "LangGraph如何实现循环（Loop）？什么场景需要循环？", answer: "实现方式：在条件边中，让某个节点的输出可以回到之前的节点。例如：generate节点→evaluate节点→条件判断（质量好→END，质量不好→回到generate重新生成）。典型场景：1.Self-Reflection——生成→评估→修正循环；2.Agent重试——工具调用失败→改参数重试；3.多轮优化——初稿→审阅→修改→审阅→直到满意。需要设置最大循环次数（通过计数器或条件判断），防止无限循环。" },
      ],
    },
    {
      term: "State（状态管理）",
      desc: "State是LangGraph中最核心的概念，定义了在图中流动的数据结构。State的作用：1.在节点间传递数据——节点从State读取输入，将结果写回State；2.保存执行历史——State记录了整个执行过程的所有中间结果；3.支持条件分支——条件边通过读取State决定走向。State的更新机制：每个节点返回一个字典，只包含需要更新的字段，LangGraph自动合并到State中（默认行为是覆盖同名字段）。可以自定义Reducer函数控制合并方式（如operator.add实现列表追加）。",
      explain: "State像一份共享文档。每个节点（员工）从文档中读取自己需要的信息，处理完后把结果写回文档。文档内容随着处理逐步丰富，最终包含所有需要的信息。不同员工可能同时更新文档的不同部分，系统会自动合并他们的修改。",
      code: `# State 定义和 Reducer 示例
from typing import TypedDict, Annotated
import operator

class AgentState(TypedDict):
    # 基本字段：覆盖更新
    question: str
    answer: str

    # 使用Reducer：消息列表追加而非覆盖
    messages: Annotated[list, operator.add]

    # 使用Reducer：计数器累加
    retry_count: Annotated[int, operator.add]

# 节点返回的消息会被追加到messages列表
def generate(state: AgentState) -> AgentState:
    new_msg = {"role": "assistant", "content": "回答内容..."}
    return {"messages": [new_msg]}  # 追加到列表`,
      parse: [
        { q: "LangGraph中State的Reducer机制有什么作用？为什么需要它？", answer: "默认情况下，节点返回的字段会覆盖State中的同名字段。但有些场景需要'合并'而非'覆盖'：1.消息列表——每次追加新消息而非替换整个列表（用operator.add）；2.计数器——累加而非重置（用operator.add）；3.搜索结果——合并多次搜索的结果（用自定义函数）。不使用Reducer的话，每次节点返回都会覆盖之前的数据，导致历史丢失。Annotated[list, operator.add]告诉LangGraph：这个字段用add操作合并。这是LangGraph实现'增量更新'的关键机制。" },
      ],
    },
    {
      term: "LangGraph vs LangChain Agent 的区别",
      desc: "LangGraph和LangChain Agent都能构建Agent系统，但设计理念和能力不同。LangChain Agent：高层抽象，用AgentExecutor管理'思考-行动'循环，适合简单场景，代码量少但可控性差。LangGraph：底层框架，用有向图精确定义每个节点和边的逻辑，适合复杂场景，代码量多但可控性强。关键区别：1.控制粒度——LangGraph可以精确控制每一步的逻辑，LangChain Agent是黑盒循环；2.状态管理——LangGraph有完善的State管理，LangChain Agent依赖Memory组件；3.人机协作——LangGraph原生支持Human-in-the-Loop，LangChain Agent需要额外实现；4.持久化——LangGraph内置Checkpointing，LangChain Agent不支持中断恢复。",
      explain: "LangChain Agent像自动挡汽车——上手简单，踩油门就走（调用AgentExecutor.run()），但你不能精确控制换挡时机。LangGraph像手动挡+自定义ECU——你需要自己设计每个挡位的逻辑（定义节点和边），但可以精确控制一切。简单通勤选自动挡（LangChain Agent），赛车比赛选手动挡（LangGraph）。",
      parse: [
        { q: "什么时候应该用LangChain Agent，什么时候应该用LangGraph？", answer: "用LangChain Agent：1.简单的工具调用（1-5个工具，流程简单）；2.快速原型验证（几行代码搞定）；3.不需要中断恢复和人工干预。用LangGraph：1.复杂多步骤工作流（需要条件分支、循环）；2.需要Human-in-the-Loop（关键步骤人工确认）；3.生产环境需要可靠的错误处理和状态恢复；4.多Agent协作系统；5.需要可观测性和调试能力。判断标准：如果你觉得AgentExecutor控制不了你想要的行为，就该用LangGraph了。" },
      ],
    },
    {
      term: "MemorySaver",
      desc: "MemorySaver是LangGraph内置的内存检查点（Checkpoint）存储器。作用：在Graph执行的每一步自动保存State的快照，支持：1.中断恢复——Graph可以在任意节点暂停，稍后从断点继续；2.回滚重放——可以回到任意历史状态重新执行；3.分支执行——从某个历史状态创建新的执行分支。MemorySaver将State存储在内存中（Python字典），适合开发和测试。生产环境建议用SqliteSaver或PostgresSaver持久化存储。Thread是MemorySaver的隔离单元——不同Thread的状态互相独立。",
      explain: "MemorySaver像游戏的存档系统。每到一个节点就自动存档（保存State快照）。你可以随时读档回到之前的某个状态（回滚），也可以从某个存档开始走不同的路（分支）。开发时用内存存档（MemorySaver），上线后用硬盘存档（SqliteSaver）。",
      code: `# MemorySaver 使用示例
from langgraph.checkpoint.memory import MemorySaver

# 创建检查点存储
memory = MemorySaver()

# 编译Graph时传入checkpointer
app = graph.compile(checkpointer=memory)

# 使用thread_id隔离不同会话
config = {"configurable": {"thread_id": "user_123"}}

# 第一次执行（执行到某个节点可能中断）
result = app.invoke({"question": "查询订单"}, config=config)

# 查看当前State
state = app.get_state(config)

# 从断点继续执行
app.invoke(None, config=config)  # 继续执行

# 回滚到历史状态
history = list(app.get_state_history(config))
app.update_state(config, values=history[2].values)  # 回滚到第3个快照`,
      parse: [
        { q: "MemorySaver和SqliteSaver的区别？如何选择？", answer: "MemorySaver：数据存在内存（Python dict），速度快但进程退出后丢失，适合开发和测试。SqliteSaver：数据存在SQLite文件，持久化存储，进程重启后数据仍在，适合单机生产环境。PostgresSaver：数据存在PostgreSQL，支持并发和分布式，适合多实例部署的生产环境。选择：开发用MemorySaver（零配置），单机生产用SqliteSaver（简单可靠），多实例/高并发用PostgresSaver。切换只需改一行代码——checkpointer=SqliteSaver.from_conn_string('checkpoints.db')。" },
      ],
    },
    {
      term: "LangGraph 的条件分支和循环",
      desc: "条件分支和循环是LangGraph区别于线性Chain的核心能力。条件分支：通过add_conditional_edges实现，根据State中的值决定下一步执行哪个节点。语法：graph.add_conditional_edges(source_node, routing_function)，routing_function返回目标节点名称。循环：当条件边的目标节点在当前节点之前时形成循环。例如：generate→evaluate→(quality_ok?→END : →generate)。循环必须有退出条件（最大次数、质量阈值），否则Agent会死循环。LangGraph还支持子图（Subgraph）——一个节点可以是一个完整的子Graph，实现模块化。",
      explain: "条件分支像导航软件的路线规划——到达路口（节点）后，根据实时路况（State）选择不同路线（边）。循环像迷宫游戏——走一段路检查一次（evaluate），没找到出口就回到起点重来，但最多尝试3次（防死循环）。",
      code: `# 条件分支 + 循环示例
from langgraph.graph import StateGraph, START, END

graph = StateGraph(AgentState)

# 添加节点
graph.add_node("generate", generate_answer)
graph.add_node("evaluate", evaluate_answer)
graph.add_node("improve", improve_answer)

# 起点到生成
graph.add_edge(START, "generate")

# 生成到评估
graph.add_edge("generate", "evaluate")

# 评估后的条件分支
def route_after_eval(state: AgentState):
    if state.get("retry_count", 0) >= 3:
        return "end"           # 最多重试3次
    if state.get("quality", 0) >= 0.8:
        return "end"           # 质量达标
    return "improve"           # 需要改进

graph.add_conditional_edges("evaluate", route_after_eval, {
    "end": END,
    "improve": "improve"
})

# 改进后回到生成（形成循环）
graph.add_edge("improve", "generate")`,
      parse: [
        { q: "LangGraph中如何安全地实现循环，避免无限循环？", answer: "四种方法：1.最大次数限制——State中维护retry_count，每次循环+1，超过阈值强制退出；2.质量阈值——评估节点输出质量分数，达标即退出；3.超时机制——在config中设置执行超时时间；4.外部中断——通过interrupt机制在特定条件下暂停等待人工决策。最佳实践是组合使用：retry_count限制最多3次+质量分数阈值0.8+超时60秒。任何一条满足就退出循环。此外，要在日志中记录每次循环的原因和结果，方便调试。" },
      ],
    },
    {
      term: "自定义工具开发",
      desc: "为LangChain/LangGraph Agent开发自定义工具，扩展Agent的能力。两种方式：1.@tool装饰器——最简单，给函数加装饰器即可，自动从函数签名和docstring生成工具描述和参数schema；2.BaseTool类——继承基类，实现_run和_arun方法，适合需要复杂逻辑的工具。工具开发最佳实践：1.清晰的docstring——这是LLM决定是否使用工具的依据；2.类型注解——自动推断参数类型；3.错误处理——捕获异常返回友好错误信息而非崩溃；4.输入验证——在执行前验证参数合法性；5.返回格式——返回字符串（LLM可直接理解）而非原始对象。",
      explain: "自定义工具开发像教机器人新技能。@tool装饰器是'快捷教学法'——写个函数、加上说明（docstring），机器人就学会了。BaseTool是'正式培训法'——详细定义每一步怎么做，适合复杂的技能。关键是'说明书'（docstring）要写得好——机器人靠说明书决定什么时候用这个技能。",
      code: `# 自定义工具开发示例
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 方式1：@tool装饰器（简单工具）
@tool
def get_current_time() -> str:
    """获取当前时间。当用户询问现在几点时使用此工具。"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 方式2：带参数验证的工具
class SearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    max_results: int = Field(default=5, description="最大结果数", ge=1, le=20)

@tool(args_schema=SearchInput)
def search_products(query: str, max_results: int = 5) -> str:
    """搜索商品信息。当用户查询商品价格、库存时使用。"""
    # 搜索逻辑...
    results = db.search(query, limit=max_results)
    return "\\n".join([f"- {r['name']}: ¥{r['price']}" for r in results])`,
      parse: [
        { q: "如何确保自定义工具与LLM的Function Calling良好配合？", answer: "1.工具名称——简洁明了，用下划线命名（search_products而非sp），LLM更容易理解和选择；2.工具描述——最重要！写清楚功能、适用场景、不适用场景，这直接决定LLM是否正确使用；3.参数描述——每个参数都要有Field(description=...)，说明含义和格式；4.类型约束——用Pydantic做类型验证，enum限制可选值，ge/le限制数值范围；5.错误消息——验证失败时返回清晰的错误说明，帮助LLM修正参数；6.返回格式——返回结构化文本（列表或表格），LLM更容易理解。" },
      ],
    },
    {
      term: "Agent 执行流程",
      desc: "Agent的完整执行流程（以LangGraph Agent为例）：1.接收输入——用户消息进入State的question字段；2.意图分析——LLM分析用户意图，决定是直接回答还是调用工具；3.工具选择——如果需要工具，LLM根据工具描述选择合适的工具并生成参数；4.工具执行——系统执行工具调用，获取结果；5.结果整合——LLM将工具结果整合为自然语言回答；6.质量评估——（可选）评估回答质量，不满意则重试。整个流程在LangGraph中表现为有向图的节点遍历，State在每个节点更新。",
      explain: "Agent执行流程像餐厅的服务流程。客人点菜（用户输入）→服务员理解需求（意图分析）→告诉厨房做什么（工具选择）→厨房做菜（工具执行）→服务员端菜并介绍（结果整合）→客人品尝反馈（质量评估，不好吃就重做）。每一步都可能需要回到上一步调整。",
      parse: [
        { q: "在Agent执行流程中，如何处理工具调用失败的情况？", answer: "分层处理：1.参数错误——返回错误信息给LLM，让LLM修正参数重试（如'city参数不能为空'→LLM补充city='北京'）；2.工具不可用——返回错误给LLM，LLM选择替代工具或直接用自身知识回答；3.执行超时——返回超时错误，LLM决定是重试还是放弃；4.结果异常——结果为空或格式不对，LLM可尝试换个工具或换个问法。关键原则：错误信息一定要返回给LLM（而非静默失败），让LLM根据错误类型做出智能决策。最多重试2-3次，超过则告知用户。" },
      ],
    },
  ],
  parse_extra: [
    { q: "如何用LangGraph实现一个Human-in-the-Loop的审批工作流？", answer: "核心实现：1.在需要人工审批的节点前使用interrupt()——Graph执行到此处自动暂停，保存State到Checkpointer；2.系统通知审批人（邮件/消息），附上审批链接；3.审批人查看当前State（任务详情），做出审批/拒绝决策；4.通过update_state()将审批结果写入State；5.Graph从断点继续执行。关键API：graph.compile(checkpointer=memory, interrupt_before=['approval_node'])。配置interrupt_before或interrupt_after指定在哪些节点前后暂停。Thread机制确保不同审批请求的状态互相隔离。" },
    { q: "LangChain生态中，LangChain、LangGraph、LangSmith、LangServe分别是什么关系？", answer: "LangChain：核心框架，提供Model/Prompt/Tool等基础组件和LCEL组合语言。LangGraph：扩展框架，在LangChain基础上提供有向图、状态管理、检查点，构建复杂Agent。LangSmith：开发平台，提供调试、追踪、评估、监控功能（类似LLM的DevOps平台）。LangServe：部署工具，将LangChain Chain快速部署为REST API（一行代码）。四者关系：LangChain是地基，LangGraph是高级建筑框架，LangSmith是监控系统，LangServe是部署管道。实际项目中通常全部使用。" },
    { q: "如何评估和优化LangChain应用的性能？", answer: "性能瓶颈通常在三处：1.LLM调用延迟（最大瓶颈）——优化方法：流式输出减少感知延迟、缓存相同query的结果、用小模型处理简单任务；2.工具调用延迟——优化方法：并行调用无依赖的工具、异步执行（asyncio）、结果缓存；3.向量检索延迟——优化方法：HNSW索引、向量量化、减少Top-K。评估方法：LangSmith可以追踪每个组件的执行时间和token消耗，定位瓶颈。最佳实践：设置超时机制、用async/await避免阻塞、关键路径上避免多余的LLM调用。" },
  ],
  exercises: {
    choice: [
      { q: "LCEL中管道操作符（|）的作用是什么？", options: ["数学运算", "将前一个组件的输出作为后一个组件的输入", "创建并行分支", "定义条件分支"], answer: 1 },
      { q: "以下哪个不是LangChain的核心组件？", options: ["Model", "Prompt", "Compiler", "Memory"], answer: 2 },
      { q: "ConversationSummaryMemory相比ConversationBufferMemory的优势是什么？", options: ["信息更完整", "节省token消耗", "速度更快", "不需要LLM"], answer: 1 },
      { q: "LangGraph中State的作用是什么？", options: ["存储模型参数", "在节点间传递和保存数据", "管理用户权限", "配置网络连接"], answer: 1 },
      { q: "LangGraph的条件分支用什么方法实现？", options: ["add_edge", "add_conditional_edges", "add_node", "add_branch"], answer: 1 },
      { q: "MemorySaver的数据存储在哪里？", options: ["数据库", "文件系统", "内存（Python字典）", "Redis"], answer: 2 },
      { q: "LangChain Agent和LangGraph的核心区别是什么？", options: ["支持的LLM不同", "控制粒度不同：LangChain Agent是黑盒循环，LangGraph是精确图控制", "编程语言不同", "价格不同"], answer: 1 },
      { q: "@tool装饰器从函数的什么信息生成工具描述？", options: ["函数名", "函数名和docstring", "函数体代码", "返回值类型"], answer: 1 },
      { q: "LangGraph中如何实现Human-in-the-Loop？", options: ["使用sleep等待", "使用interrupt机制暂停Graph执行", "使用多线程", "使用回调函数"], answer: 1 },
      { q: "Prompt Template中FewShotPromptTemplate的作用是什么？", options: ["减少token消耗", "在提示中包含输入输出示例引导LLM", "限制输出长度", "设置模型参数"], answer: 1 },
    ],
    fill: [
      { q: "LangChain六大核心组件是Model、Prompt、Chain、______、Tool和______。", answer: ["Memory/记忆", "Agent/智能体"] },
      { q: "LCEL用______操作符将组件串联，替代了传统的______类。", answer: ["管道/|", "LLMChain"] },
      { q: "LangGraph的核心概念是有向图（Graph），由______、______和State组成。", answer: ["节点/Node", "边/Edge"] },
      { q: "MemorySaver是LangGraph的______存储器，生产环境建议用______持久化。", answer: ["内存检查点", "SqliteSaver/PostgresSaver"] },
      { q: "Conversation______Memory保存完整历史，Conversation______Memory只保留最近K轮。", answer: ["Buffer", "BufferWindow"] },
      { q: "Prompt Template中，______角色用于设定AI的行为规范，______角色用于用户输入。", answer: ["System/系统", "Human/用户"] },
      { q: "LangGraph中add_conditional_edges方法的参数包括源节点和______函数，该函数根据______决定目标节点。", answer: ["路由/routing", "State/状态"] },
      { q: "自定义工具开发有两种方式：______装饰器和继承______类。", answer: ["@tool", "BaseTool"] },
      { q: "LangGraph的检查点机制支持中断______、回滚______和分支执行。", answer: ["恢复", "重放"] },
      { q: "LangSmith是LangChain的______平台，提供调试、______和监控功能。", answer: ["开发", "评估"] },
    ],
    app: [
      { q: "用LangGraph设计一个客服Agent系统，需要支持订单查询、退换货申请和商品咨询，包含Human-in-the-Loop的退换货审批流程。画出Graph结构并说明各节点和边的逻辑。", key_points: ["节点设计：intent_router（意图识别）→order_query（订单查询）/return_process（退换货）/product_info（商品咨询）→approval（人工审批）→execute_return（执行退换货）→response（生成回复）", "条件分支：intent_router根据用户意图路由到不同处理节点", "Human-in-the-Loop：退换货金额>500元时在approval节点暂停等待人工审批", "State设计：包含user_input、intent、order_info、tool_results、response等字段", "错误处理：工具调用失败时的重试和降级策略"] },
      { q: "你的LangChain项目中，一个RAG Chain的响应延迟高达10秒，用户反馈太慢。分析可能的瓶颈并给出优化方案。", key_points: ["瓶颈分析：1.Embedding模型推理慢（首次加载+向量计算）；2.向量检索数据量大、索引未优化；3.LLM调用延迟（网络+生成时间）；4.Reranker重排序额外耗时", "优化方案：1.Embedding模型预加载+GPU加速；2.向量数据库使用HNSW索引+向量量化；3.LLM使用流式输出减少感知延迟；4.缓存热门query的检索结果；5.Reranker只对Top-20重排序而非Top-50；6.异步并行执行无依赖的步骤"] },
      { q: "用LCEL构建一个多语言翻译Chain，输入一种语言的文本，同时翻译为英语、日语和法语，最后汇总为一个JSON格式的结果。", key_points: ["使用PromptTemplate定义翻译模板，变量包含目标语言", "用RunnableParallel并行执行三种语言的翻译", "每个分支：prompt | llm | parser", "汇总节点将三个翻译结果组装为JSON", "LCEL代码结构：translate_chain = RunnableParallel(en=chain_en, ja=chain_ja, fr=chain_fr) | merge_to_json"] },
      { q: "设计一个基于LangGraph的代码Review Agent，包含代码分析、问题检测、修复建议和人工确认四个阶段，支持循环迭代直到代码质量达标。", key_points: ["State：包含code、issues、suggestions、review_score、iteration_count字段", "节点：analyze（分析代码结构和风格）→detect（检测问题：安全、性能、规范）→suggest（生成修复建议）→confirm（人工确认修复建议）→apply_fix（应用修复）→循环回到analyze", "条件分支：review_score>=90→END，iteration_count>=3→END（强制退出），否则→apply_fix→analyze（循环）", "Human-in-the-Loop：confirm节点暂停等待开发者确认修复建议", "工具：代码解析器、Lint工具、安全扫描工具"] },
    ]
  }
};
