module.exports = {
  title: "第九章：多 Agent 系统",
  difficulty: "B/C",
  knowledge: [
    {
      term: "多Agent系统定义和动机",
      desc: "多Agent系统（Multi-Agent System, MAS）是指由多个自主Agent协同工作以完成复杂任务的系统架构。其核心动机源于单Agent的局限性：当任务涉及多个专业领域时，单个Agent难以同时精通所有领域；当任务需要多步骤协作时，单Agent容易因上下文过长而表现退化；当任务需要对抗性验证时，单Agent无法自我质疑。多Agent系统通过将复杂任务分解给专业化Agent，每个Agent专注于自己擅长的领域，通过协作完成整体目标。典型场景包括软件开发（产品经理Agent、程序员Agent、测试Agent协作）、学术研究（搜索Agent、分析Agent、写作Agent配合）。",
      explain: "多Agent系统就像一个项目团队：项目经理负责协调，程序员负责开发，设计师负责UI，测试员负责质量，每个人专注自己的专长，协作完成一个单人难以胜任的复杂项目。",
      code: `# 多Agent系统概念示例\nclass MultiAgentSystem:\n    def __init__(self):\n        self.agents = {\n            "planner": PlannerAgent(),   # 任务规划\n            "researcher": ResearchAgent(), # 信息搜集\n            "writer": WriterAgent(),       # 内容生成\n            "reviewer": ReviewerAgent()    # 质量审核\n        }\n    \n    async def execute(self, task: str):\n        plan = await self.agents["planner"].plan(task)\n        research = await self.agents["researcher"].search(plan)\n        draft = await self.agents["writer"].write(research)\n        result = await self.agents["reviewer"].review(draft)\n        return result`,
      parse: [
        { q: "多Agent系统相比单Agent系统的核心优势是什么？", answer: "多Agent系统的核心优势体现在四个方面：第一，专业化分工，每个Agent专注于特定领域，能提供更高质量的输出；第二，上下文管理更优，每个Agent只需处理与其职责相关的上下文，避免单Agent上下文过长导致的性能退化；第三，可扩展性强，新增能力只需添加新Agent而非重构整个系统；第四，容错能力更强，单个Agent失败不影响其他Agent工作，系统整体更稳健。" },
        { q: "什么时候应该选择多Agent架构而不是单Agent架构？", answer: "选择多Agent架构的判断标准包括：任务是否涉及多个明确的专业领域、任务是否需要对抗性验证（如代码需要审核）、任务步骤是否超过单Agent上下文窗口的合理范围、是否需要并行处理子任务提高效率。如果任务简单且领域单一，单Agent加工具调用已足够，引入多Agent反而增加通信开销和系统复杂度。建议从单Agent开始，当复杂度超出单Agent能力时再拆分为多Agent。" }
      ],
    },
    {
      term: "通信机制",
      desc: "多Agent间的通信机制是系统设计的基础，主要有三种模式。消息传递模式是最直接的方式，Agent通过发送和接收结构化消息进行交互，类似微服务间的API调用，适合松耦合的异步协作。共享状态模式通过一个公共的状态空间（如数据库、键值存储）让Agent读写共享信息，适合需要全局可见性的场景。事件驱动模式中Agent通过发布和订阅事件进行通信，一个Agent完成任务后发布事件，订阅该事件的Agent自动响应，适合流水线式的协作。三种模式可以混合使用，选择取决于Agent间的耦合程度和实时性要求。",
      explain: "消息传递像发微信（点对点沟通），共享状态像白板（所有人看到同一块白板上的信息），事件驱动像广播电台（发布消息，感兴趣的人自动收听）。",
      code: `# 消息传递模式\nasync def agent_communicate(sender, receiver, message):\n    msg = {\n        "from": sender.name,\n        "to": receiver.name,\n        "content": message,\n        "timestamp": datetime.now()\n    }\n    await receiver.receive(msg)\n\n# 共享状态模式\nshared_state = {"task": "", "research": "", "draft": ""}\nasync def update_state(agent_name, key, value):\n    shared_state[key] = value\n    notify_all_agents(f"{agent_name} 更新了 {key}")\n\n# 事件驱动模式\nclass EventBus:\n    def __init__(self):\n        self.subscribers = defaultdict(list)\n    def subscribe(self, event, handler):\n        self.subscribers[event].append(handler)\n    async def publish(self, event, data):\n        for handler in self.subscribers[event]:\n            await handler(data)`,
      parse: [
        { q: "消息传递模式和共享状态模式各自的适用场景是什么？", answer: "消息传递模式适合Agent间需要明确的请求-响应交互场景，如一个Agent向另一个Agent发送查询并等待结果，优点是通信明确、易于追踪调试。共享状态模式适合多个Agent需要访问同一份全局信息的场景，如多个Agent协作处理一份文档的不同部分，优点是信息同步简单。缺点是消息传递在复杂交互时消息量爆炸，共享状态在高并发时存在一致性问题，需根据具体场景选择。" },
        { q: "事件驱动模式如何实现Agent间的松耦合协作？", answer: "事件驱动模式通过EventBus中间件解耦Agent间的直接依赖。Agent只需发布事件到总线或订阅感兴趣的事件，不需要知道事件的消费者是谁。例如研究Agent完成搜索后发布'research_complete'事件，写作Agent订阅该事件自动触发写作。新增审核Agent只需订阅'draft_complete'事件即可，无需修改已有Agent代码。这种模式实现了发布者和消费者的完全解耦，极大提升了系统的可扩展性和可维护性。" }
      ],
    },
    {
      term: "协作模式",
      desc: "多Agent的协作模式定义了Agent之间如何组织和配合完成任务，主要有五种经典模式。串行模式中Agent按顺序依次工作，前一个的输出是后一个的输入，适合有明确阶段划分的任务。并行模式中多个Agent同时工作处理不同子任务，最后汇总结果，适合可独立分解的任务。层级模式中有一个主控Agent负责任务分解和结果汇总，下属Agent执行具体任务，适合复杂的项目管理场景。辩论模式中多个Agent对同一问题给出不同观点并互相质疑，最终达成共识，适合需要多角度分析的决策场景。投票模式中多个Agent独立给出答案，通过投票决定最终结果，适合需要集体智慧的场景。",
      explain: "串行像接力赛（一棒接一棒），并行像分组作业（各组同时做不同部分），层级像公司组织架构（老板分配任务给员工），辩论像学术答辩（互相质疑达成共识），投票像选举（一人一票多数决）。",
      code: `# 串行模式\nasync def serial_pipeline(task, agents):\n    result = task\n    for agent in agents:\n        result = await agent.process(result)\n    return result\n\n# 辩论模式\nasync def debate(topic, agents, rounds=3):\n    opinions = []\n    for agent in agents:\n        opinions.append(await agent.opine(topic))\n    \n    for round in range(rounds):\n        new_opinions = []\n        for i, agent in enumerate(agents):\n            others = opinions[:i] + opinions[i+1:]\n            new_opinions.append(\n                await agent.argue(topic, others))\n        opinions = new_opinions\n    \n    return await summarize(opinions)`,
      parse: [
        { q: "辩论模式在什么场景下优于串行模式？", answer: "辩论模式适用于需要深度思考和多角度分析的决策场景，如战略规划、风险评估、技术方案选型等。在这些场景中，单一视角容易遗漏关键因素，而辩论模式通过让多个Agent互相质疑和补充，能发现单Agent看不到的盲点。串行模式更适合流程化、阶段清晰的任务（如先搜索再写作再审核），不需要多角度辩论。核心区别在于：串行追求流程效率，辩论追求决策质量。" },
        { q: "并行模式中如何处理子任务间存在依赖关系的情况？", answer: "当子任务间存在依赖关系时，纯并行模式无法直接应用，需要使用DAG（有向无环图）调度策略：第一，分析子任务间的依赖关系，构建任务依赖图；第二，将无依赖的任务放入并行批次同时执行；第三，等待当前批次完成后，将依赖满足的下一批任务放入新批次执行；第四，重复直到所有任务完成。这种策略结合了并行的效率和依赖关系的正确性，是实际项目中最常用的协作调度方式。" }
      ],
    },
    {
      term: "角色设计",
      desc: "多Agent系统中的角色设计是决定系统效果的关键环节，需要从三个维度精心定义。任务分解是将复杂目标拆分为多个独立子任务，每个子任务对应一个Agent角色，分解粒度需要平衡：过粗则Agent职责不清，过细则通信开销过大。能力边界定义每个Agent能做什么和不能做什么，包括可用的工具集、知识范围和决策权限，清晰的能力边界避免Agent越权操作。职责定义明确每个角色的输入期望、输出标准和质量要求，使Agent的行为可预测和可评估。好的角色设计应遵循单一职责原则，每个Agent只做一件事但做到最好。",
      explain: "角色设计就像电影选角：导演（主控Agent）需要清楚每个演员（子Agent）擅长什么角色、能演什么戏、对每场戏有什么具体要求。",
      code: `# 角色定义示例\nresearcher_role = {\n    "name": "研究员",\n    "goal": "搜集和整理与任务相关的可靠信息",\n    "backstory": "你是一个资深研究员，擅长从多个来源搜集信息并交叉验证",\n    "tools": ["web_search", "database_query", "pdf_reader"],\n    "constraints": [\n        "只负责信息搜集，不做最终判断",\n        "每个结论至少需要两个独立来源支撑",\n        "输出必须标注信息来源"\n    ],\n    "output_format": "结构化的研究报告，包含来源标注"\n}`,
      parse: [
        { q: "为什么多Agent系统中的角色设计应遵循单一职责原则？", answer: "单一职责原则确保每个Agent专注于一个明确的任务领域，带来三个核心好处：第一，Prompt可以高度针对化，提供该领域的专业知识和约束，输出质量更高；第二，测试和调试更简单，每个Agent的输入输出明确，容易定位问题；第三，复用性强，同一个研究员Agent可以在不同项目中复用。违反单一职责会导致Prompt变得冗长复杂，LLM难以同时兼顾多个目标，输出质量下降。" },
        { q: "如何确定子任务的合理粒度？", answer: "合理粒度的判断标准有四个：第一，每个子任务应能由一个Agent独立完成，不需要频繁与其他Agent交互获取中间结果；第二，每个子任务的输入输出应能清晰定义，便于验证和调试；第三，粒度不应过细导致Agent数量过多、通信开销超过计算开销；第四，粒度不应过粗导致单个Agent的职责模糊、Prompt过长。实践中建议从粗粒度开始，根据实际效果逐步细化，每个Agent的Prompt控制在2000Token以内为佳。" }
      ],
    },
    {
      term: "Multi-Agent框架概览",
      desc: "当前主流的Multi-Agent开发框架有三个：AutoGen、CrewAI和MetaGPT。AutoGen由微软研究院开发，核心理念是ConversableAgent，通过Agent间的对话来完成任务，支持灵活的GroupChat多人对话机制，适合研究探索场景。CrewAI提供了最高层次的抽象，用Agent、Task、Crew、Process四个概念即可构建多Agent系统，学习曲线最平缓，适合快速原型开发。MetaGPT模拟软件公司的组织架构，预定义了产品经理、架构师、工程师等角色，特别适合软件开发场景。选择框架时应考虑项目复杂度、定制化需求和团队技术栈。",
      explain: "三个框架就像三种不同的团队管理工具：AutoGen像微信群聊（灵活对话）、CrewAI像Trello看板（清晰分工）、MetaGPT像公司组织架构（预设角色齐全）。",
      code: `# CrewAI基础示例\nfrom crewai import Agent, Task, Crew\n\nresearcher = Agent(\n    role="研究员",\n    goal="搜集最新的AI技术趋势",\n    backstory="资深AI研究员",\n    verbose=True\n)\nwriter = Agent(\n    role="技术作家",\n    goal="撰写通俗易懂的技术文章",\n    backstory="科技媒体资深编辑"\n)\nresearch_task = Task(\n    description="搜集2024年AI Agent领域的最新进展",\n    agent=researcher\n)\nwrite_task = Task(\n    description="根据研究结果撰写一篇2000字的技术文章",\n    agent=writer\n)\ncrew = Crew(agents=[researcher, writer],\n            tasks=[research_task, write_task])\nresult = crew.kickoff()`,
      parse: [
        { q: "三个主流框架各自最适合什么类型的项目？", answer: "AutoGen最适合研究型和探索型项目，因为它的对话式交互灵活度最高，支持复杂的多轮讨论和人机协作模式，但学习曲线较陡。CrewAI最适合业务应用型项目，它的四元素抽象（Agent/Task/Crew/Process）简洁直观，可以快速搭建原型，适合MVP开发和业务场景落地。MetaGPT最适合软件开发项目，因为它预定义了软件公司的完整角色链（产品经理到工程师），开箱即用且输出质量高。" },
        { q: "选择Multi-Agent框架时应考虑哪些关键因素？", answer: "选择框架应从五个维度评估：第一，抽象层次，高层抽象（如CrewAI）开发快但灵活性低，低层抽象（如AutoGen）灵活但开发成本高；第二，社区生态，活跃的社区意味着更多的示例和更快的Bug修复；第三，与现有技术栈的兼容性，是否支持当前使用的LLM、工具链等；第四，可观测性，是否内置调试和监控能力；第五，生产就绪度，是否支持流式输出、错误处理、并发控制等生产环境必需的能力。" }
      ],
    },
    {
      term: "CrewAI详解",
      desc: "CrewAI框架基于四个核心概念构建多Agent系统。Agent是具有特定角色、目标和工具的自主实体，通过role定义专业领域、goal定义目标、backstory提供背景知识来塑造Agent的行为风格。Task是Agent需要完成的具体任务，通过description描述任务要求、agent指定执行者、expected_output定义输出标准。Crew是多个Agent和Task的集合，代表一个完整的团队，负责管理Agent间的协作流程。Process定义协作的执行策略，sequential模式按顺序执行、hierarchical模式由管理Agent协调。CrewAI的高层抽象使得构建多Agent系统非常简洁，适合快速开发。",
      explain: "CrewAI就像拍电影：Agent是演员（有角色和技能），Task是剧本中的每场戏（有具体要求），Crew是整个剧组（所有演员和戏的集合），Process是拍摄计划（按什么顺序拍）。",
      code: `# CrewAI完整示例\nfrom crewai import Agent, Task, Crew, Process\n\nanalyst = Agent(\n    role="数据分析师",\n    goal="从数据中发现有价值的洞察",\n    backstory="10年数据分析经验",\n    tools=[data_query_tool, chart_tool],\n    llm=ChatOpenAI(model="gpt-4o")\n)\n\nreport_task = Task(\n    description="分析本季度销售数据并生成报告",\n    expected_output="包含关键指标和趋势分析的报告",\n    agent=analyst,\n    output_file="report.md"\n)\n\ncrew = Crew(\n    agents=[analyst],\n    tasks=[report_task],\n    process=Process.sequential,\n    verbose=True\n)\nresult = crew.kickoff()`,
      parse: [
        { q: "CrewAI中Process.sequential和Process.hierarchical的区别是什么？", answer: "sequential模式按Task定义的顺序依次执行，前一个Task的输出自动传递给下一个Task作为上下文，适合有明确先后依赖的流水线任务。hierarchical模式引入一个Manager Agent，由它动态决定任务分配和执行顺序，Manager可以将子任务委派给不同的Agent，适合任务间关系复杂、需要动态调度的场景。hierarchical更灵活但额外消耗Token用于Manager的决策过程。" },
        { q: "CrewAI中如何设计一个高质量的Task description？", answer: "高质量的Task description应包含四个要素：第一，明确的任务目标，说清楚要做什么；第二，具体的输入信息，提供Task执行所需的数据和背景；第三，输出要求，明确期望的格式、长度和内容标准；第四，质量约束，说明需要注意的边界条件和限制。例如不要只写'分析数据'，而要写'分析本季度销售数据，找出环比增长超过20%的产品类别，输出Markdown格式报告，包含表格和图表建议'。" }
      ],
    },
    {
      term: "AutoGen详解",
      desc: "AutoGen是微软推出的Multi-Agent框架，核心理念是通过Agent间的对话来解决复杂问题。ConversableAgent是基础构建块，每个Agent都可以发送消息、接收消息和生成回复，支持配置系统消息、LLM参数和代码执行能力。GroupChat是AutoGen的多人对话机制，多个Agent在同一个对话空间中交流，由GroupChatManager控制发言顺序和对话流程。AutoGen的独特优势是支持人类参与，可以设置human_input_mode让用户随时介入对话。AutoGen还支持自定义发言顺序、最大对话轮次和终止条件等精细控制，适合需要复杂交互逻辑的研究和开发场景。",
      explain: "AutoGen就像一个多人视频会议：每个参会者（ConversableAgent）都有自己的专长，会议主持人（GroupChatManager）控制谁先发言、讨论多久，你（用户）也可以随时开麦发言。",
      code: `from autogen import ConversableAgent, GroupChat, GroupChatManager\n\nassistant = ConversableAgent(\n    name="助手",\n    system_message="你是一个有帮助的AI助手",\n    llm_config={"model": "gpt-4o"}\n)\ncritic = ConversableAgent(\n    name="评论家",\n    system_message="你负责审视和质疑助手的回答",\n    llm_config={"model": "gpt-4o"}\n)\nuser_proxy = ConversableAgent(\n    name="用户",\n    human_input_mode="ALWAYS"\n)\n\ngroup_chat = GroupChat(\n    agents=[user_proxy, assistant, critic],\n    messages=[],\n    max_round=10\n)\nmanager = GroupChatManager(groupchat=group_chat)`,
      parse: [
        { q: "AutoGen的human_input_mode有哪几种模式？各自适用场景是什么？", answer: "AutoGen有三种human_input_mode：ALWAYS模式每轮都请求用户输入，适合需要人类深度参与决策的场景；TERMINATE模式只在Agent请求终止时才询问用户，适合全自动运行但保留人类最终控制权的场景；NEVER模式完全不需要人类参与，适合批量自动化处理场景。选择时应根据人机协作的紧密程度决定，研究探索阶段常用ALWAYS，生产部署阶段常用TERMINATE或NEVER。" },
        { q: "GroupChat中GroupChatManager如何控制发言顺序？", answer: "GroupChatManager通过speaker_selection_method控制发言顺序，支持三种方式：auto模式让LLM自动判断下一个发言者，适合自由讨论场景；round_robin模式按Agent列表顺序轮流发言，适合确保每个Agent都有发言机会的场景；自定义函数模式允许开发者编写逻辑指定发言顺序，适合有特殊流程要求的场景。还可以设置allowed_or_disallowed_speaker_transitions来限制某些Agent间的发言跳转，实现更精细的流程控制。" }
      ],
    },
    {
      term: "Agent间冲突解决",
      desc: "多Agent系统中Agent间可能产生多种冲突：观点冲突（对同一问题有不同判断）、资源冲突（竞争使用同一工具或数据）、目标冲突（子目标与全局目标不一致）。解决策略包括：仲裁机制，由一个专门的仲裁Agent综合各方观点做出最终决策，适合观点冲突；优先级机制，为不同Agent或任务设置优先级，高优先级Agent优先使用资源，适合资源冲突；共识机制，通过多轮辩论和投票让Agent逐步收敛到统一观点，适合需要深度分析的决策场景；全局约束机制，由主控Agent设定全局规则和约束，确保各Agent的子目标与全局目标一致。选择策略应根据冲突类型和系统要求综合考虑。",
      explain: "冲突解决就像团队决策：观点不同请领导拍板（仲裁）、都想要会议室就按级别排（优先级）、开会讨论到大家都同意（共识）、领导定规矩大家遵守（全局约束）。",
      code: `# 仲裁Agent示例\nasync def resolve_conflict(agents, topic):\n    opinions = []\n    for agent in agents:\n        opinion = await agent.analyze(topic)\n        opinions.append({\n            "agent": agent.name,\n            "opinion": opinion,\n            "confidence": opinion.confidence\n        })\n    \n    # 仲裁Agent综合决策\n    arbiter = ArbiterAgent()\n    decision = await arbiter.decide(\n        topic=topic,\n        opinions=opinions,\n        criteria=["证据充分性", "逻辑一致性", "实用性"]\n    )\n    return decision`,
      parse: [
        { q: "为什么多Agent系统中观点冲突不一定是坏事？", answer: "适度的观点冲突是多Agent系统的核心价值之一。不同Agent从不同角度分析问题，冲突意味着发现了被单一视角忽略的信息或风险。例如在技术方案评估中，乐观的Agent看到方案的优势，悲观的Agent发现潜在风险，两者的冲突促使系统更全面地评估方案。关键是建立有效的冲突解决机制，将冲突转化为更高质量的决策，而不是让冲突导致系统瘫痪。这就是辩论模式的价值所在。" },
        { q: "如何设计一个有效的仲裁Agent？", answer: "有效的仲裁Agent设计要点：第一，系统Prompt应明确定义仲裁标准（如证据充分性、逻辑一致性、实用性），确保决策有据可依；第二，应要求各方Agent提供详细的推理过程和证据支持，而非只给出结论；第三，仲裁结果应附带理由说明，便于其他Agent理解和接受；第四，应设定置信度阈值，当各方观点高度一致时可跳过仲裁直接采信多数意见，只有分歧明显时才启动完整仲裁流程，节省Token消耗。" }
      ],
    },
    {
      term: "多Agent的评估和调试",
      desc: "多Agent系统的评估和调试比单Agent更复杂，因为问题可能出现在Agent本身、Agent间的通信或协作流程中。评估维度包括：端到端效果（最终输出是否满足需求）、过程质量（每个Agent的中间输出是否正确）、协作效率（通信轮次和Token消耗是否合理）。调试方法包括：对话日志分析，记录所有Agent间的完整对话记录，定位哪个Agent的输出偏离预期；流程可视化，将多Agent的交互流程图化展示，直观发现卡顿和死循环；隔离测试，单独测试每个Agent确保其独立工作正常，再测试协作流程。建议开发时先确保每个Agent独立正确，再验证协作效果。",
      explain: "调试多Agent系统就像排查电路故障：先检查每个电器（单Agent）是否正常，再检查电线连接（通信）是否正确，最后检查整体电路（协作流程）是否通畅。",
      code: `# 多Agent调试日志系统\nclass AgentDebugger:\n    def __init__(self):\n        self.conversation_log = []\n        self.metrics = {\n            "total_rounds": 0,\n            "tokens_used": 0,\n            "agent_latencies": {}\n        }\n    \n    def log_message(self, sender, receiver, content):\n        self.conversation_log.append({\n            "timestamp": datetime.now(),\n            "from": sender,\n            "to": receiver,\n            "content": content[:500],  # 截断长内容\n            "tokens": count_tokens(content)\n        })\n    \n    def detect_issues(self):\n        # 检测死循环\n        if self.metrics["total_rounds"] > 20:\n            return "警告：对话轮次过多，可能存在死循环"\n        # 检测Token异常\n        if self.metrics["tokens_used"] > 50000:\n            return "警告：Token消耗异常"`,
      parse: [
        { q: "多Agent系统调试时如何快速定位是Agent问题还是通信问题？", answer: "定位方法分两步：第一，隔离测试Agent，给每个Agent单独输入相同的任务，检查输出是否正确。如果单独测试时Agent表现正常，则问题在通信或协作流程；如果单独测试就有问题，则是Agent本身的Prompt或工具配置问题。第二，审查通信日志，检查Agent间传递的消息内容是否完整、格式是否正确、是否因上下文过长导致信息丢失。通过这两步可以快速区分Agent问题和通信问题。" },
        { q: "如何评估多Agent系统的协作效率？", answer: "协作效率的评估指标包括四个：第一，通信轮次，完成任务所需的Agent间消息交换次数，过多说明流程设计不合理；第二，总Token消耗，所有Agent消耗的Token总量，与单Agent方案对比评估是否值得引入多Agent；第三，端到端延迟，从任务输入到最终输出的总时间，评估并行化是否有效；第四，任务完成率和质量评分，与单Agent基线对比。如果多Agent在质量上没有明显提升但Token消耗翻倍，则需要重新评估架构设计。" }
      ],
    },
    {
      term: "多Agent应用场景",
      desc: "多Agent系统在多个领域有成熟的应用场景。代码开发场景中，产品经理Agent负责需求分析和PRD编写，架构师Agent负责技术方案设计，程序员Agent负责编码实现，测试Agent负责编写和执行测试用例，形成完整的软件开发流水线。内容创作场景中，选题Agent负责热点分析和选题建议，研究Agent负责资料搜集，写作Agent负责初稿撰写，编辑Agent负责润色和校对，协作生产高质量内容。数据分析场景中，数据清洗Agent负责预处理，分析Agent负责统计建模，可视化Agent负责图表生成，报告Agent负责撰写分析报告。每个场景都通过角色分工和流程设计发挥多Agent协作优势。",
      explain: "多Agent应用场景就像不同的行业团队：软件公司有产品经理、程序员、测试员；杂志社有选题编辑、记者、校对；研究所有数据采集员、分析师、报告撰写人，各自分工协作。",
      code: `# 代码开发多Agent场景\ncode_crew = Crew(\n    agents=[\n        Agent(role="产品经理", goal="定义清晰的需求",\n              tools=[market_research_tool]),\n        Agent(role="架构师", goal="设计合理的技术方案",\n              tools=[architecture_diagram_tool]),\n        Agent(role="程序员", goal="编写高质量代码",\n              tools=[code_execution_tool, file_write_tool]),\n        Agent(role="测试工程师", goal="确保代码质量",\n              tools=[test_runner_tool, code_review_tool])\n    ],\n    tasks=[requirement_task, design_task, \n           coding_task, testing_task],\n    process=Process.sequential\n)`,
      parse: [
        { q: "代码开发场景中为什么需要独立的测试Agent而不是让程序员Agent自己测试？", answer: "独立测试Agent的核心价值在于视角分离。程序员在测试自己写的代码时存在确认偏误，倾向于测试自己预期的使用方式而非真实的异常场景。独立的测试Agent不受实现细节影响，能从用户视角和边界条件角度设计测试用例，发现程序员自测容易忽略的边界情况、异常输入和集成问题。此外，测试Agent可以使用不同的LLM或不同的Prompt策略，进一步降低系统性盲点的风险。" },
        { q: "数据分析场景中多Agent相比单Agent的优势在哪里体现？", answer: "数据分析场景中多Agent优势体现在三个方面：第一，数据清洗Agent和分析Agent分离，避免数据质量问题污染分析过程，清洗Agent可以独立验证数据完整性；第二，可视化Agent专注于图表设计和呈现，不受分析思路干扰，能产出更美观和直观的图表；第三，报告Agent综合所有中间结果生成结构化报告，比单Agent一次性处理更不容易遗漏关键发现。每个Agent的Prompt更聚焦，输出质量更高。" }
      ],
    },
  ],
  parse_extra: [
    { q: "请设计一个用于竞品分析的多Agent系统，说明需要哪些Agent角色、各自的职责和协作流程。", answer: "竞品分析多Agent系统设计五个角色：选题Agent负责确定竞品范围和分析维度（如功能、定价、用户评价）；数据采集Agent使用搜索和爬虫工具搜集各竞品的公开信息；对比分析Agent从多个维度横向对比各竞品的优劣势；洞察Agent基于对比结果提炼市场机会和威胁；报告Agent整合所有分析结果生成结构化报告。协作流程采用DAG调度：选题完成后数据采集并行启动，对比分析依赖数据采集完成，洞察和报告依次执行。关键设计点是数据采集Agent需要输出标准化格式供下游Agent使用。" },
    { q: "在多Agent系统中如何处理Agent因LLM幻觉导致的错误信息传播？如何设计防护机制？", answer: "错误信息传播是多Agent系统的重大风险，防护机制分三层：第一层是源头控制，为Agent配置高置信度要求，当Agent不确定时输出'不确定'而非猜测，系统Prompt中明确要求标注信息来源和置信度；第二层是传播控制，下游Agent对接收到的信息进行独立验证，特别是关键数据和事实性声明；第三层是终端控制，最终输出Agent对所有中间结果做一致性检查，发现矛盾时触发重新验证流程。此外可以在关键节点加入人工审核环节。" },
    { q: "如何评估多Agent系统的ROI（投入产出比），在什么情况下多Agent不值得引入？", answer: "评估多Agent ROI需量化三个维度：成本增加（多Agent的Token消耗通常是单Agent的N倍，N为Agent数量）、质量提升（多Agent输出相比单Agent的质量提升幅度）、开发维护成本（多Agent的调试和维护复杂度更高）。当满足以下条件时不值得引入多Agent：任务本身简单且领域单一，单Agent效果已足够好；质量提升幅度小于10%但Token消耗增加200%以上；团队缺乏多Agent调试经验，维护成本过高。建议先用单Agent建立基线，再评估多Agent是否能带来显著的质量或效率提升。" }
  ],
  exercises: {
    choice: [
      { q: "多Agent系统相比单Agent系统的核心优势不包括以下哪项？", options: ["专业化分工", "上下文管理更优", "Token消耗更低", "可扩展性强"], answer: 2 },
      { q: "以下哪种通信模式最适合流水线式的Agent协作？", options: ["消息传递模式", "共享状态模式", "事件驱动模式", "直接函数调用"], answer: 2 },
      { q: "CrewAI中定义Agent协作执行策略的核心概念是？", options: ["Agent", "Task", "Crew", "Process"], answer: 3 },
      { q: "AutoGen中控制Agent发言顺序的核心组件是？", options: ["ConversableAgent", "GroupChat", "GroupChatManager", "UserProxy"], answer: 2 },
      { q: "以下哪个不是多Agent系统的经典协作模式？", options: ["串行模式", "并行模式", "循环模式", "辩论模式"], answer: 2 },
      { q: "多Agent角色设计应遵循什么原则？", options: ["全功能原则", "单一职责原则", "最大权限原则", "最少Agent原则"], answer: 1 },
      { q: "多Agent系统中观点冲突的最佳处理方式是？", options: ["忽略冲突取第一个Agent的意见", "通过辩论机制达成共识", "随机选择一个Agent的意见", "重新开始整个流程"], answer: 1 },
      { q: "以下哪个框架最适合软件开发场景的多Agent协作？", options: ["AutoGen", "CrewAI", "MetaGPT", "LangChain"], answer: 2 },
    ],
    fill: [
      { q: "多Agent系统的三种通信模式是消息传递、共享状态和______。", answer: ["事件驱动"] },
      { q: "CrewAI的四个核心概念是Agent、Task、Crew和______。", answer: ["Process"] },
      { q: "AutoGen中多个Agent在同一个对话空间中交流的机制叫______。", answer: ["GroupChat", "群聊"] },
      { q: "多Agent的五种经典协作模式是串行、并行、层级、______和投票。", answer: ["辩论"] },
      { q: "多Agent调试时应先确保每个Agent______工作正常，再验证协作效果。", answer: ["独立", "单独"] },
      { q: "选择Multi-Agent框架时应评估抽象层次、社区生态、______、可观测性和生产就绪度。", answer: ["技术栈兼容性", "兼容性"] },
      { q: "多Agent系统中______模式适合需要多角度分析的决策场景。", answer: ["辩论"] },
      { q: "GroupChat中speaker_selection_method的三种方式是auto、round_robin和______。", answer: ["自定义函数", "custom_function", "自定义"] },
    ],
    app: [
      { q: "设计一个用于产品需求评审的多Agent系统，需要从用户体验、技术可行性和商业价值三个角度评估需求，请列出Agent角色、各自职责、协作流程和冲突解决机制。", key_points: ["三个评审Agent：UX评审Agent（评估用户体验）、Tech评审Agent（评估技术可行性）、Biz评审Agent（评估商业价值）", "仲裁Agent：综合三方意见做出最终评审结论", "协作流程：三个评审Agent并行评估，完成后仲裁Agent综合决策", "冲突解决：评分维度冲突由仲裁Agent根据权重决策，关键否决项任何一方有权否决", "输出格式：结构化评审报告包含各维度评分、风险点和改进建议"] },
      { q: "你正在构建一个新闻聚合和分析的多Agent系统，需要从多个新闻源搜集、去重、分类和摘要生成。请设计系统架构并说明如何保证信息的准确性和时效性。", key_points: ["数据采集Agent：从RSS、API等多个源并行搜集新闻", "去重Agent：基于语义相似度去除重复报道", "分类Agent：按主题分类（科技、财经、社会等）", "摘要Agent：为每篇新闻生成简明摘要", "事实核查Agent：交叉验证关键事实的准确性", "时效性保证：定时任务+增量更新机制"] },
      { q: "为一个电商平台设计多Agent客服系统，需要处理售前咨询、售后问题和投诉升级三类场景，请设计Agent角色分工和路由机制。", key_points: ["入口Agent：识别用户意图并路由到对应Agent", "售前Agent：处理商品咨询、推荐、比价等", "售后Agent：处理退换货、物流查询、发票等", "投诉Agent：处理用户投诉和升级请求", "路由机制：基于意图分类模型智能路由，支持人工转接", "记忆共享：共享用户画像和历史对话，避免用户重复描述问题"] },
    ],
  },
};
