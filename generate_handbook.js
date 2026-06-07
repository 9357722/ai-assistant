const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat, TableOfContents,
  TabStopType, TabStopPosition
} = require("docx");

// ========== 辅助函数 ==========
const heading = (level, text) => new Paragraph({
  heading: level,
  spacing: { before: level === HeadingLevel.HEADING_1 ? 360 : 240, after: 120 },
  children: [new TextRun({ text, bold: true, font: "Microsoft YaHei" })]
});

const para = (text, opts = {}) => new Paragraph({
  spacing: { after: 80, line: 360 },
  ...opts,
  children: Array.isArray(text) ? text : [new TextRun({ text, font: "Microsoft YaHei", size: 22, ...opts })]
});

const boldPara = (label, text) => new Paragraph({
  spacing: { after: 80, line: 360 },
  children: [
    new TextRun({ text: label, bold: true, font: "Microsoft YaHei", size: 22 }),
    new TextRun({ text, font: "Microsoft YaHei", size: 22 })
  ]
});

const bullet = (text, ref = "bullets", level = 0) => new Paragraph({
  numbering: { reference: ref, level },
  spacing: { after: 60, line: 340 },
  children: [new TextRun({ text, font: "Microsoft YaHei", size: 22 })]
});

const numItem = (text, ref = "numbers", level = 0) => new Paragraph({
  numbering: { reference: ref, level },
  spacing: { after: 60, line: 340 },
  children: [new TextRun({ text, font: "Microsoft YaHei", size: 22 })]
});

const separator = () => new Paragraph({
  spacing: { before: 120, after: 120 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC", space: 1 } },
  children: []
});

const pageBreak = () => new Paragraph({ children: [new PageBreak()] });

// ========== 章节内容定义 ==========
const chapters = [
  // ===== 第一章：LLM 基础 =====
  {
    title: "第一章：大语言模型（LLM）基础知识",
    knowledge: [
      { term: "Transformer", desc: "2017年Google提出的神经网络架构，基于自注意力机制（Self-Attention），是当前所有大语言模型的基础架构。核心优势是能并行处理序列数据，解决了RNN的长距离依赖问题。", example: "想象你在读一句话：'小明把苹果放在桌子上，因为它太重了。' Transformer的注意力机制能让模型自动关注到'它'指的是'苹果'而不是'桌子'，就像人眼会自动聚焦到关键信息一样。" },
      { term: "Self-Attention（自注意力）", desc: "Transformer的核心机制。对于输入序列中的每个位置，计算它与所有其他位置的相关性（注意力权重），然后加权求和得到新的表示。计算公式：Attention(Q,K,V) = softmax(QK^T/√d)V", example: "类比：你在图书馆找书。Query是你脑中的需求，Key是每本书的标签，Value是书的内容。QK^T计算需求与每本书的匹配度，softmax归一化后加权求和，得到最符合你需求的知识。" },
      { term: "Multi-Head Attention（多头注意力）", desc: "将注意力机制分成多个'头'并行计算，每个头关注不同维度的信息（如语法关系、语义关系、位置关系），最后拼接结果。这就像多角度分析问题。", example: "分析'我喜欢在星巴克喝咖啡'：Head1可能关注'我-喜欢'的主谓关系，Head2关注'星巴克-咖啡'的场所-物品关系，Head3关注'喝-咖啡'的动作-对象关系。多头综合后，模型理解更全面。" },
      { term: "Position Encoding（位置编码）", desc: "Transformer本身不感知顺序，需要额外注入位置信息。原始方法用正弦/余弦函数，RoPE（旋转位置编码）是目前主流，通过旋转矩阵将位置信息编码进向量。", example: "就像给排队的人发号码牌。没有号码牌时，模型只知道有哪些人，不知道谁在前谁在后。位置编码就是号码牌，让模型知道'猫追狗'和'狗追猫'的区别。" },
      { term: "Decoder-Only / Encoder-Decoder", desc: "Decoder-Only（如GPT、LLaMA）：只用解码器，从左到右逐个生成token，适合生成任务。Encoder-Decoder（如T5）：编码器理解输入，解码器生成输出，适合翻译等任务。目前大模型主流是Decoder-Only。", example: "Decoder-Only像即兴演讲——看着前面说的，一个字一个字往后编。Encoder-Decoder像同声传译——先完整理解一段话，再翻译输出。GPT选择了更灵活的即兴演讲模式。" },
      { term: "KV Cache", desc: "推理时的优化技术。生成每个新token时，前面所有token的Key和Value不需要重新计算，可以缓存复用。这将推理复杂度从O(n²)降到O(n)。", example: "就像做笔记：你不需要每次都从头翻笔记本，只需要在最后一页写新内容，之前的笔记随时可以翻看。KV Cache就是那个笔记本，保存了之前所有计算结果。" },
      { term: "Tokenizer（分词器）", desc: "将文本切分成token的工具。主流方法有BPE（Byte-Pair Encoding）、SentencePiece等。token可以是字、词、子词。中文通常一个字2-3个token，英文一个单词1-2个token。", example: "'人工智能'可能被分成['人工','智能']两个token，也可能被分成['人','工','智','能']四个token。不同的分词方式直接影响模型的理解能力和推理成本。" },
      { term: "涌现能力（Emergent Abilities）", desc: "模型参数量达到一定规模后突然出现的新能力，如推理、编程、数学等。小模型完全不具备，大模型突然学会。目前科学界对涌现是否真实存在仍有争论。", example: "就像水加热到100度突然沸腾——不是逐渐变热就逐渐冒泡，而是到了临界点突然发生。GPT-3（175B参数）突然展现出few-shot学习能力，而更小的模型完全没有。" },
      { term: "幻觉（Hallucination）", desc: "模型生成看似合理但实际错误或无中生有的内容。根本原因是模型基于统计概率生成文本，不真正理解事实。分为事实性幻觉和忠实性幻觉。", example: "你问AI'刘德华获得过几次奥斯卡？'，AI可能回答'刘德华在2015年凭借《无间道》获得奥斯卡最佳男主角'——听起来很合理，但完全是编造的。这就是幻觉。" },
      { term: "Temperature / Top-P / Top-K", desc: "Temperature：控制随机性，0=确定性输出，>1=更随机。Top-P：只从累积概率前P%的token中采样。Top-K：只从概率最高的K个token中采样。三者共同控制输出的多样性。", example: "Temperature像调味料——0是白开水（固定），1是正常口味，2是重口味（创意十足但可能离谱）。Top-P像自助餐——只从你喜欢的前80%菜品中选。Top-K像排行榜——只从前10名中选。" },
      { term: "Context Window（上下文窗口）", desc: "模型一次能处理的最大token数量。GPT-4支持128K，Claude支持200K。超过窗口的内容会被截断。上下文越长，推理成本越高（KV Cache越大）。", example: "就像你的工作台大小。小桌子只能同时看几份文件，大桌子能摊开一整本书。上下文窗口就是模型的'工作台'，决定了它一次能处理多少信息。" },
    ],
    exercises: {
      choice: [
        { q: "Transformer的核心注意力机制中，Q、K、V分别代表什么？", options: ["Query-Question-Value", "Query-Key-Value", "Quality-Key-Vector", "Query-Knowledge-Value"], answer: 1 },
        { q: "为什么当前主流大模型采用Decoder-Only架构？", options: ["训练成本更低", "推理速度更快", "更适合自回归生成任务", "参数量更小"], answer: 2 },
        { q: "KV Cache的作用是什么？", options: ["压缩模型参数", "缓存已计算的Key和Value避免重复计算", "存储训练数据", "加密模型权重"], answer: 1 },
        { q: "以下哪个不是控制生成随机性的参数？", options: ["Temperature", "Top-P", "Batch Size", "Top-K"], answer: 2 },
        { q: "RoPE（旋转位置编码）的主要优势是什么？", options: ["计算速度快", "支持相对位置编码，具有外推能力", "占用内存小", "实现简单"], answer: 1 },
      ],
      fill: [
        { q: "Transformer架构由Google在______年提出，论文标题为'______'。", answer: ["2017", "Attention Is All You Need"] },
        { q: "自注意力的计算公式为：Attention(Q,K,V) = ______(QK^T/______)V。", answer: ["softmax", "√d"] },
        { q: "大模型产生看似合理但实际错误的内容被称为______。", answer: ["幻觉/Hallucination"] },
        { q: "Tokenizer将文本切分成______，主流方法包括______和SentencePiece。", answer: ["token", "BPE/Byte-Pair Encoding"] },
      ],
      app: [
        { q: "请解释为什么Transformer比RNN更适合处理长文本，并从计算复杂度和并行性两个角度分析。", key_points: ["RNN是串行处理，长距离依赖信息会衰减", "Transformer的自注意力可以直接关注任意距离的token", "RNN时间复杂度O(n*d²)，Transformer可以并行计算", "但Transformer的自注意力空间复杂度是O(n²)"] },
        { q: "你的项目中使用了DeepSeek作为LLM，如果用户输入超出了上下文窗口，你会怎么处理？请给出至少3种方案。", key_points: ["文本截断：保留最新的对话历史", "文本摘要：用LLM压缩早期对话", "滑动窗口：只保留最近N轮对话", "RAG检索：将历史对话存入向量库，按需检索"] },
      ]
    }
  },
  // ===== 第二章：RAG 检索增强生成 =====
  {
    title: "第二章：RAG（检索增强生成）",
    knowledge: [
      { term: "RAG（Retrieval-Augmented Generation）", desc: "检索增强生成。核心思想：先从外部知识库检索相关信息，再将检索结果作为上下文喂给LLM生成回答。解决了LLM知识过时、幻觉、无法访问私有数据三大问题。", example: "RAG就像开卷考试：学生（LLM）本身有知识（参数），但考试时可以翻书（检索知识库）。翻到相关内容后，结合自己的理解写出答案。比闭卷考试（纯LLM）准确得多。" },
      { term: "Embedding（向量嵌入）", desc: "将文本转换为高维向量的技术。语义相似的文本，向量距离更近。常用模型：OpenAI text-embedding-3-small、BGE系列、E5等。向量维度通常768-1536维。", example: "'苹果手机'和'iPhone'虽然字面完全不同，但Embedding后它们的向量会非常接近（余弦相似度>0.9），而'苹果手机'和'苹果水果'的向量则会较远。这就是语义理解的魔力。" },
      { term: "向量数据库", desc: "专门存储和检索高维向量的数据库。支持近似最近邻搜索（ANN），能在百万级向量中毫秒级找到最相似的结果。主流：ChromaDB（轻量）、Milvus（生产级）、Pinecone（托管服务）、FAISS（Meta开源）。", example: "传统数据库像按名字查通讯录（精确匹配），向量数据库像在照片库中找'最像某张脸的照片'（相似度搜索）。你描述'轻薄的笔记本电脑'，它能找到'MacBook Air'——虽然字面完全不同。" },
      { term: "Chunk（文本分块）", desc: "将长文档切分成适合检索的小段。分块策略直接影响检索质量。常见方法：固定长度分块、按段落分块、递归字符分块、语义分块。", example: "把一本500页的教科书复印成500张单页，你问'什么是牛顿第二定律'时，只需找到相关那几页，而不是翻完整本书。Chunk就是把大文档切成可检索的小片段。" },
      { term: "Reranker（重排序器）", desc: "对初步检索结果进行二次精排的模型。向量检索是粗排（速度快但精度有限），Reranker是精排（速度慢但精度高）。常用：Cohere Rerank、BGE Reranker、Cross-Encoder。", example: "向量检索像简历初筛——快速过滤掉明显不相关的。Reranker像面试官——仔细对比剩下的候选人，给出最终排名。两阶段结合才能找到最匹配的结果。" },
      { term: "Hybrid Search（混合检索）", desc: "结合向量检索（语义匹配）和关键词检索（精确匹配）的方法。向量检索擅长理解意图，关键词检索擅长精确匹配专有名词。两者互补，用RRF（Reciprocal Rank Fusion）融合分数。", example: "搜'iPhone 15 Pro Max价格'：向量检索能找到'苹果最新旗舰手机多少钱'（语义匹配），关键词检索能找到包含'iPhone 15 Pro Max'的精确结果。混合检索两者兼顾。" },
      { term: "多路召回", desc: "从多个维度同时检索：文本召回（BM25/全文索引）、向量召回（Embedding相似度）、类目召回（限定分类范围）、知识图谱召回（结构化关系）。多路结果融合后去重排序。", example: "就像找餐厅：朋友推荐（向量召回）、大众点评评分（文本召回）、只看川菜馆（类目召回）、米其林榜单（知识图谱召回）。综合所有渠道的推荐，才能找到最满意的餐厅。" },
      { term: "Query改写（Query Rewriting）", desc: "用户原始查询往往模糊、有错字、不完整。Query改写用LLM对查询进行纠错、扩展、分解，提高检索命中率。", example: "用户搜'苹菓手机多少钱'→纠错→'苹果手机多少钱'→扩展→'iPhone价格'→分解→['苹果手机型号','iPhone各型号价格']。改写后的查询能命中更多相关文档。" },
    ],
    exercises: {
      choice: [
        { q: "RAG主要解决了LLM的哪些问题？", options: ["只解决知识过时问题", "知识过时、幻觉、无法访问私有数据", "只解决推理速度问题", "只解决模型大小问题"], answer: 1 },
        { q: "向量数据库中，'苹果手机'和以下哪个词的Embedding向量最接近？", options: ["苹果水果", "iPhone", "手机壳", "苹果公司"], answer: 1 },
        { q: "Reranker的作用是什么？", options: ["替代向量检索", "对初步检索结果进行精排", "生成Embedding向量", "切分文档"], answer: 1 },
        { q: "Hybrid Search结合了哪两种检索方式？", options: ["向量检索和图数据库检索", "向量检索和关键词检索", "SQL检索和NoSQL检索", "全文检索和模糊检索"], answer: 1 },
        { q: "文本Chunk过大会导致什么问题？", options: ["检索速度变慢", "检索精度下降，噪声多", "模型无法处理", "Embedding维度不够"], answer: 1 },
      ],
      fill: [
        { q: "RAG的全称是______。", answer: ["Retrieval-Augmented Generation"] },
        { q: "将文本转换为高维向量的技术叫做______。", answer: ["Embedding/向量嵌入"] },
        { q: "______是专门存储和检索高维向量的数据库，支持______搜索。", answer: ["向量数据库", "近似最近邻/ANN"] },
        { q: "混合检索通常使用______算法来融合多路结果的分数。", answer: ["RRF/Reciprocal Rank Fusion"] },
      ],
      app: [
        { q: "你的项目中使用了ChromaDB做RAG，请描述完整的RAG流程：从用户提问到生成回答，每一步做了什么？", key_points: ["1.用户提问→Query改写（纠错/扩展）", "2.将Query转为Embedding向量", "3.在ChromaDB中做相似度搜索，召回Top-K相关文档", "4.将检索结果拼入Prompt上下文", "5.调用DeepSeek LLM生成最终回答", "6.流式输出给前端"] },
        { q: "如果RAG检索结果不准确，你会从哪些方面优化？请至少给出5个优化方向。", key_points: ["1.优化分块策略（按语义分块而非固定长度）", "2.使用更好的Embedding模型", "3.加入Reranker精排", "4.实现Hybrid Search（向量+关键词）", "5.Query改写（纠错、扩展、分解）", "6.调整Top-K和相似度阈值", "7.优化Chunk元数据（加标题、来源等）"] },
      ]
    }
  },
  // ===== 第三章：Agent 智能体 =====
  {
    title: "第三章：Agent（智能体）",
    knowledge: [
      { term: "Agent（智能体）", desc: "能自主感知环境、做出决策、执行行动的AI系统。与纯LLM对话的区别：LLM只能被动回答问题，Agent能主动调用工具、规划任务、记忆上下文。核心循环：感知→思考→行动→观察。", example: "LLM像一个百科全书——你问它答。Agent像一个私人助理——你说'帮我订明天去上海的机票'，它会自己查航班、比价格、选座位、完成预订。关键区别是'自主行动能力'。" },
      { term: "ReAct（Reasoning + Acting）", desc: "Agent的核心推理框架。交替进行推理（Thought）和行动（Action），每次行动后观察结果（Observation），再进行下一步推理。形成 Thought→Action→Observation 循环。", example: "用户问'北京明天天气怎么样，需要带伞吗？'\nThought: 我需要查北京明天的天气\nAction: 调用天气查询工具\nObservation: 明天北京多云转小雨，降水概率80%\nThought: 降水概率高，建议带伞\nAnswer: 明天北京有小雨，建议带伞。" },
      { term: "Function Calling（函数调用）", desc: "LLM根据用户意图，自动选择合适的函数/工具并生成调用参数的能力。OpenAI首先推出，现在主流模型都支持。模型输出结构化的函数名和参数，由系统执行并返回结果。", example: "用户说'帮我查一下北京到上海的航班'。LLM输出：\n```json\n{\"function\": \"search_flights\", \"args\": {\"from\": \"北京\", \"to\": \"上海\"}}```\n系统执行函数，返回航班列表，LLM再整理成自然语言回答。" },
      { term: "Tool（工具）", desc: "Agent能调用的外部能力。可以是API、数据库查询、搜索引擎、计算器、代码执行器等。每个工具需要定义名称、描述、参数schema。LLM根据工具描述决定何时使用哪个工具。", example: "一个客服Agent可能有这些工具：\n- search_product: 搜索商品\n- check_order: 查询订单状态\n- refund: 申请退款\n- transfer_human: 转接人工\n用户说'我要退款'，Agent自动选择refund工具。" },
      { term: "Memory（记忆系统）", desc: "Agent的记忆能力。短期记忆：当前对话上下文（在Context Window内）。长期记忆：跨会话的持久化存储（向量数据库/关系数据库）。工作记忆：当前任务的中间状态。", example: "就像人的记忆：短期记忆是你正在读的这句话（几秒~几分钟），长期记忆是你记得小学同学的名字（几年~终生），工作记忆是你做心算时暂存的中间结果。Agent需要三种记忆配合。" },
      { term: "Planning（规划）", desc: "Agent将复杂任务分解为可执行子任务的能力。常见方法：Chain-of-Thought（思维链）、Tree-of-Thought（思维树）、Plan-and-Solve（先规划后执行）。", example: "用户说'帮我策划一个生日派对'。Agent规划：\n1.确定预算和人数\n2.选择场地\n3.制定菜单\n4.购买装饰品\n5.发送邀请\n每个子任务再细化执行。这就是Planning的价值。" },
      { term: "Multi-Agent（多智能体）", desc: "多个Agent协作完成复杂任务。架构模式：串行（A→B→C）、并行（A∥B∥C）、层级（Manager分配任务给Worker）、辩论（多个Agent讨论得出结论）。", example: "写一篇深度报道：\n- Researcher Agent：搜集资料\n- Writer Agent：撰写初稿\n- Editor Agent：审核修改\n- Critic Agent：提出质疑\n每个Agent专注自己的角色，协作产出高质量内容。" },
      { term: "Agent四大设计模式", desc: "1.Reflection（反思）：Agent检查自己的输出并改进。2.Tool Use（工具使用）：调用外部工具获取信息。3.Planning（规划）：分解复杂任务。4.Multi-Agent（多智能体）：多个Agent协作。", example: "写代码任务中的四种模式：\nReflection：写完代码后自己review，发现bug并修复\nTool Use：调用搜索引擎查API文档\nPlanning：先设计架构再写代码\nMulti-Agent：一个写代码，一个写测试，一个review" },
    ],
    exercises: {
      choice: [
        { q: "Agent与纯LLM对话的核心区别是什么？", options: ["Agent参数更多", "Agent能主动调用工具和执行行动", "Agent速度更快", "Agent更便宜"], answer: 1 },
        { q: "ReAct框架的核心循环是什么？", options: ["输入→处理→输出", "感知→决策→执行", "Thought→Action→Observation", "Plan→Execute→Review"], answer: 2 },
        { q: "以下哪项不属于Agent的记忆类型？", options: ["短期记忆（对话上下文）", "长期记忆（持久化存储）", "工作记忆（中间状态）", "训练记忆（模型参数）"], answer: 3 },
        { q: "Function Calling中，LLM的主要职责是什么？", options: ["执行函数", "生成函数名和参数", "返回结果给用户", "存储函数定义"], answer: 1 },
        { q: "Multi-Agent架构中，'辩论模式'的特点是什么？", options: ["Agent串行执行任务", "多个Agent讨论得出结论", "Manager分配任务给Worker", "Agent独立完成各自任务"], answer: 1 },
      ],
      fill: [
        { q: "Agent的核心循环是：______→思考→______→观察。", answer: ["感知", "行动"] },
        { q: "ReAct的三个组成部分是______、______和______。", answer: ["Reasoning/推理", "Acting/行动", "Observation/观察"] },
        { q: "Agent的四大设计模式是：______、Tool Use、______和Multi-Agent。", answer: ["Reflection/反思", "Planning/规划"] },
        { q: "______记忆是当前对话上下文，______记忆是跨会话的持久化存储。", answer: ["短期", "长期"] },
      ],
      app: [
        { q: "你的项目中实现了Agent工具调用（商品搜索、计算器、联网搜索），请描述从用户提问到Agent回答的完整流程，包括工具选择和结果整合。", key_points: ["1.用户提问进入Agent", "2.LLM分析意图，决定是否需要调用工具", "3.如果需要，LLM输出function call（工具名+参数）", "4.系统执行工具，返回结果", "5.LLM结合工具结果和上下文生成回答", "6.支持多轮工具调用（一个回答可能调用多个工具）"] },
        { q: "如果要将你的项目从单Agent升级为Multi-Agent架构，你会设计哪些Agent角色？每个角色的职责是什么？", key_points: ["1.导购Agent：负责商品推荐和比价", "2.客服Agent：处理售后问题和投诉", "3.搜索Agent：负责搜索引擎优化", "4.分析Agent：分析用户行为和偏好", "5.Manager Agent：协调各Agent，分配任务"] },
      ]
    }
  },
  // ===== 第四章：LangChain / LangGraph =====
  {
    title: "第四章：LangChain 与 LangGraph",
    knowledge: [
      { term: "LangChain", desc: "LLM应用开发框架。核心组件：Model（模型接入）、Prompt（提示模板）、Chain（链式调用）、Memory（记忆管理）、Tool（工具集成）、Agent（智能体）。简化了LLM应用的开发流程。", example: "LangChain就像乐高积木——每块积木是一个功能模块（模型、工具、记忆），你可以自由拼装成不同的应用。比如拼一个客服机器人：模型+记忆+工具=有记忆、能查数据库的客服。" },
      { term: "LCEL（LangChain Expression Language）", desc: "LangChain的声明式调用语言，用管道符|串联组件。支持自动异步、批量处理、流式输出。如：prompt | llm | output_parser", example: "就像Unix管道命令：cat file | grep error | sort | uniq\nLCEL同理：format_prompt | call_llm | parse_output\n每个组件处理完传给下一个，清晰直观。" },
      { term: "LangGraph", desc: "基于图结构的Agent编排框架。将Agent的工作流建模为有向图：节点=处理步骤，边=状态转移。支持循环、条件分支、人工介入。比LangChain Agent更灵活可控。", example: "LangChain Agent像流水线——只能线性前进。LangGraph像流程图——可以循环（不满意就重来）、分支（根据条件走不同路径）、暂停（等人工确认）。更适合复杂业务逻辑。" },
      { term: "State（状态）", desc: "LangGraph中图的共享数据结构。每个节点可以读取和修改状态。状态在节点间传递，记录了Agent的所有上下文信息（对话历史、工具结果、中间变量等）。", example: "状态就像一个共享白板：Agent A在上面写'已搜索到3个结果'，Agent B看到后在下面写'已筛选出1个最优'，Agent C继续写'已生成推荐语'。所有Agent通过白板协作。" },
      { term: "MemorySaver", desc: "LangGraph的内存记忆存储。将对话状态保存在内存中，支持按thread_id隔离不同会话。适合开发和测试，生产环境建议用数据库持久化。", example: "MemorySaver就像给每个用户发一个独立的记事本。用户A的对话记在A的本子上，用户B的记在B的本子上。重启服务器后，记事本清空（内存丢失）。" },
      { term: "Prompt Template", desc: "提示词模板。用变量占位符{variable}定义可复用的提示词。支持系统提示、用户输入、上下文注入、Few-shot示例等。好的Prompt Template是LLM应用质量的关键。", example: "模板：'你是{role}，请用{style}回答以下问题：{question}，参考知识：{context}'\n填入：role=电商客服，style=亲切友好，question=退货流程，context=退货政策文档\n生成最终Prompt发给LLM。" },
    ],
    exercises: {
      choice: [
        { q: "LangChain的核心组件不包括以下哪项？", options: ["Chain", "Memory", "Database", "Agent"], answer: 2 },
        { q: "LCEL使用什么符号串联组件？", options: ["->", "|", "+", "&"], answer: 1 },
        { q: "LangGraph相比LangChain Agent的主要优势是什么？", options: ["速度更快", "支持图结构编排，可循环和分支", "占用内存更小", "不需要API Key"], answer: 1 },
        { q: "MemorySaver的数据存储在哪里？", options: ["磁盘文件", "数据库", "内存", "Redis"], answer: 2 },
      ],
      fill: [
        { q: "LangChain的核心组件包括Model、Prompt、Chain、______、Tool和______。", answer: ["Memory", "Agent"] },
        { q: "LCEL的全称是______。", answer: ["LangChain Expression Language"] },
        { q: "LangGraph中，图的节点代表______，边代表______。", answer: ["处理步骤", "状态转移"] },
      ],
      app: [
        { q: "你的项目使用了LangGraph MemorySaver实现多轮对话记忆，请解释记忆的工作原理，以及如果要持久化记忆（重启不丢失），你会怎么改？", key_points: ["1.MemorySaver将状态存在内存中，按thread_id隔离", "2.每轮对话更新状态（追加消息、更新变量）", "3.重启后内存清空，记忆丢失", "4.持久化方案：换用Redis/MySQL存储状态", "5.LangGraph支持自定义Saver接口"] },
      ]
    }
  },
  // ===== 第五章：微调 =====
  {
    title: "第五章：模型微调（Fine-tuning）",
    knowledge: [
      { term: "全量微调（Full Fine-tuning）", desc: "更新模型所有参数。效果最好但成本最高——7B模型需要约56GB显存（FP16）。适合数据量大、计算资源充足的场景。", example: "全量微调就像让一个大学生重新上一遍专业课——所有知识都要更新。效果最好，但需要大量时间和资源。" },
      { term: "LoRA（Low-Rank Adaptation）", desc: "低秩适配。冻结原始模型参数，只训练两个小矩阵A和B（秩r通常8-64）。参数量仅为全量的0.1%-1%，显存降低10倍以上。效果接近全量微调。", example: "LoRA像给模型'贴标签'而不是'换大脑'。原始模型不动，只在旁边加一个小模块学习新知识。就像你在书上贴便签笔记——书的内容不变，但你的理解增加了。" },
      { term: "QLoRA", desc: "在LoRA基础上，将基础模型量化为4-bit（NF4），进一步降低显存需求。7B模型只需约6GB显存即可微调。代价是训练速度略慢。", example: "LoRA是贴便签，QLoRA是用缩微版的书来贴便签——书变小了（4-bit量化），便签还是原来大小（LoRA参数保持高精度）。省空间但效果差不多。" },
      { term: "SFT（Supervised Fine-Tuning）", desc: "有监督微调。使用'指令-回答'对来训练模型。让模型学会遵循指令格式回答问题。是大模型训练流程的第二步（预训练→SFT→RLHF）。", example: "SFT就像给实习生做培训：\n指令：'请用3句话总结这篇文章'\n标准答案：'本文主要讲了...'\n通过大量这样的练习，模型学会了'按照指令格式回答'。" },
      { term: "RLHF", desc: "基于人类反馈的强化学习。步骤：1.收集人类对模型回答的排序偏好 2.训练奖励模型（Reward Model） 3.用PPO算法优化模型，使其输出更符合人类偏好。", example: "训练宠物狗：\n1.狗做了几个动作（模型生成多个回答）\n2.你选择最好的那个（人类标注偏好）\n3.给奖励（训练奖励模型）\n4.狗学会哪种行为有奖励（PPO优化模型）\n重复多次，狗越来越听话。" },
      { term: "DPO（Direct Preference Optimization）", desc: "直接偏好优化。跳过训练奖励模型的步骤，直接从偏好数据优化模型。比RLHF更简单稳定，但效果可能略差。是当前流行的对齐方法。", example: "RLHF是：看答案→打分→学打分标准→根据标准改进\nDPO是：看两个答案→直接学'这个比那个好'→改进\nDPO省去了中间的打分步骤，更直接。" },
    ],
    exercises: {
      choice: [
        { q: "LoRA的核心思想是什么？", options: ["删除模型部分参数", "冻结原始参数，只训练低秩适配矩阵", "将模型压缩为1-bit", "增加更多Transformer层"], answer: 1 },
        { q: "QLoRA相比LoRA的优势是什么？", options: ["效果更好", "显存需求更低（4-bit量化）", "训练速度更快", "不需要GPU"], answer: 1 },
        { q: "大模型训练的标准三步流程是什么？", options: ["预训练→推理→部署", "预训练→SFT→RLHF", "采集数据→训练→测试", "SFT→LoRA→量化"], answer: 1 },
        { q: "DPO相比RLHF的主要优势是什么？", options: ["效果更好", "不需要人类标注", "实现更简单，跳过奖励模型训练", "可以处理更长文本"], answer: 2 },
      ],
      fill: [
        { q: "LoRA的全称是______，核心是用______矩阵来近似参数更新。", answer: ["Low-Rank Adaptation", "低秩"] },
        { q: "SFT的全称是______，使用______对来训练模型。", answer: ["Supervised Fine-Tuning", "指令-回答"] },
        { q: "RLHF中，人类反馈被用来训练______模型，然后用______算法优化LLM。", answer: ["奖励/Reward", "PPO"] },
      ],
      app: [
        { q: "你的项目记录中提到了模型微调LoRA（Qwen2.5-0.5B-Instruct）。请说明你为什么选择LoRA而不是全量微调？微调的数据是什么格式？", key_points: ["1.资源限制：全量微调需要大量显存", "2.LoRA只训练0.1%参数，效果接近全量", "3.数据格式：instruction-input-output三元组", "4.或messages格式：system+user+assistant"] },
      ]
    }
  },
  // ===== 第六章：工程实践 =====
  {
    title: "第六章：工程实践与部署",
    knowledge: [
      { term: "流式输出（Streaming）", desc: "LLM生成token后立即返回给前端，而不是等全部生成完再返回。技术实现：SSE（Server-Sent Events）或WebSocket。用户体验：打字机效果，减少等待感。", example: "非流式：你问问题→等30秒→一次性看到完整回答\n流式：你问问题→立刻开始看到文字→逐字出现→2秒后已经有部分内容可以阅读\n就像对话vs等快递——流式更像实时对话。" },
      { term: "Prompt Caching（提示缓存）", desc: "缓存相同的Prompt前缀部分，避免重复计算。Anthropic和OpenAI都支持。对于长System Prompt或Few-shot示例，缓存命中后成本降低90%。", example: "每次上课都要念一遍课堂规则（System Prompt）。Prompt Caching就像把规则打印出来贴在黑板上——不用每次念，直接指给学生看。省时省力。" },
      { term: "Token计费", desc: "LLM API按token数量收费。输入token和输出token分开计费，输出通常更贵。1个中文字符≈2-3个token，1个英文单词≈1个token。需要监控和控制token使用量。", example: "就像手机流量：输入token是下载（便宜），输出token是上传（贵）。你需要监控流量，避免月底超支。Token计费就是监控AI的'流量'使用。" },
      { term: "限流（Rate Limiting）", desc: "控制API请求频率，防止过载和滥用。常见策略：令牌桶（Token Bucket）、滑动窗口、固定窗口。你的项目中实现了基于IP的登录限流。", example: "限流像餐厅叫号机——一次只能服务10桌，第11桌必须排队。防止厨房（API服务器）被订单淹没而崩溃。" },
      { term: "Docker容器化", desc: "将应用及其依赖打包成标准容器。Dockerfile定义构建步骤，docker-compose编排多个服务。优势：环境一致性、快速部署、易于扩展。", example: "Docker像集装箱——不管里面装的是什么货物（Python/Node/Java），集装箱的尺寸和吊装方式都是标准的。任何港口（服务器）都能处理。" },
      { term: "异步编程（async/await）", desc: "Python的异步编程模型。async def定义协程，await等待异步操作。在IO密集型任务（如API调用、数据库查询）中，异步比同步快数倍。", example: "同步像在餐厅点餐——必须等上一桌的菜上齐了才能点下一桌。\n异步像快餐店——点完餐拿号码牌，同时给下一桌点餐，菜好了叫号取餐。\nAI应用大量IO等待，异步能显著提升并发能力。" },
    ],
    exercises: {
      choice: [
        { q: "流式输出通常使用什么技术实现？", options: ["HTTP长轮询", "SSE（Server-Sent Events）", "FTP", "SMTP"], answer: 1 },
        { q: "以下哪项不是Docker的核心优势？", options: ["环境一致性", "快速部署", "降低API成本", "易于扩展"], answer: 2 },
        { q: "async/await主要适用于什么场景？", options: ["CPU密集型计算", "IO密集型任务", "内存管理", "图形渲染"], answer: 1 },
      ],
      fill: [
        { q: "LLM API通常按______数量计费，______token通常比______token更贵。", answer: ["token", "输出", "输入"] },
        { q: "Docker使用______文件定义构建步骤，使用______编排多个服务。", answer: ["Dockerfile", "docker-compose"] },
      ],
      app: [
        { q: "你的项目使用了FastAPI + aiomysql实现异步全链路。请解释为什么选择异步而不是同步？在哪些地方用了异步？如果改成同步会有什么问题？", key_points: ["1.FastAPI原生支持async", "2.aiomysql异步数据库操作", "3.DeepSeek API调用是IO操作，异步不阻塞", "4.如果同步：一个请求等待API时，其他请求全部阻塞", "5.并发能力从数百降到个位数"] },
      ]
    }
  },
  // ===== 第七章：项目实战 =====
  {
    title: "第七章：项目实战与面试话术",
    knowledge: [
      { term: "项目介绍话术", desc: "面试时用STAR法则介绍项目：Situation（背景）→ Task（任务）→ Action（行动）→ Result（结果）。重点突出技术选型理由、遇到的挑战、如何解决。", example: "话术模板：'我做了一个AI智能电商导购平台。背景是电商比价需求，我用FastAPI+LangChain+DeepSeek构建了完整的AI导购系统。核心亮点是四棒搜索引擎和Agent工具调用。过程中解决了N+1查询、CORS跨域、向量检索精度等问题。最终实现了用户注册→商品浏览→AI比价→下单的完整闭环。'" },
      { term: "四棒搜索引擎", desc: "你的项目核心亮点。第1棒：意图解析（LLM纠错+语义扩展）。第2棒：多路召回（文本+向量+类目）。第3棒：精排打分（规则打分）。第4棒：重排调整（品牌打散+去重+兜底）。", example: "面试话术：'搜索引擎是四棒架构。用户搜三千左右的手机，第一棒LLM理解意图提取价格区间，第二棒从MySQL和ChromaDB多路召回候选，第三棒按价格匹配度+销量评分排序，第四棒做品牌打散避免全是同一品牌。'" },
      { term: "技术选型理由", desc: "面试必问：为什么用X而不是Y？回答模板：'选择X是因为...，相比Y的优势是...，在当前场景下更适合因为...'", example: "为什么用ChromaDB而不是Milvus？\n'选择ChromaDB是因为：1.项目是demo阶段，数据量小（44个商品），ChromaDB轻量够用 2.与LangChain集成方便 3.如果商品量过万，可以无缝切换到Milvus做生产级部署'" },
      { term: "遇到的挑战", desc: "面试高频问题：项目中遇到的最大挑战是什么？要说出具体的技术问题和解决方案，不要说空话。", example: "示例：'最大挑战是搜索精度。最初用SQL LIKE搜索，用户搜苹果手机找不到iPhone。解决方案是四棒搜索引擎：用LLM做Query改写（苹果→iPhone），用ChromaDB做向量检索（语义匹配），加品牌别名映射表。最终搜索准确率从30%提升到90%。'" },
    ],
    exercises: {
      choice: [
        { q: "面试介绍项目时，推荐使用什么方法？", options: ["按时间顺序讲", "STAR法则", "只讲技术细节", "只讲结果"], answer: 1 },
        { q: "面试官问'为什么用X而不是Y'时，最好的回答方式是什么？", options: ["X是最好的", "因为教程用的X", "分析X和Y的优劣，说明当前场景为什么选X", "不知道，老师让用的"], answer: 2 },
      ],
      fill: [
        { q: "STAR法则的四个要素是______、______、______和______。", answer: ["Situation/背景", "Task/任务", "Action/行动", "Result/结果"] },
      ],
      app: [
        { q: "请用STAR法则，准备一段2分钟的项目介绍话术，介绍你的AI智能电商导购平台。重点突出：技术选型理由、核心亮点（四棒搜索引擎、Agent工具调用）、遇到的挑战和解决方案。", key_points: ["Situation：电商比价场景，用户需要跨平台比价", "Task：构建AI驱动的导购系统", "Action：FastAPI+LangChain+DeepSeek，四棒搜索，Agent工具", "Result：完整闭环，搜索准确率提升，解决了多个技术难题"] },
        { q: "面试官问：'你的项目和京东/淘宝的搜索有什么差距？你怎么回答？'", key_points: ["1.坦诚差距：数据量级完全不同（44 vs 亿级）", "2.但架构思路一致：意图解析→多路召回→精排→重排", "3.已具备核心能力：向量检索、LLM Query改写", "4.生产环境可以替换为ES+Milvus", "5.重点是理解原理，不是照搬规模"] },
      ]
    }
  }
];

// ========== 生成文档 ==========
async function generate() {
  const allChildren = [];

  // 封面
  allChildren.push(
    new Paragraph({ spacing: { before: 3000 }, children: [] }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [new TextRun({ text: "AI Agent 应用开发工程师", font: "Microsoft YaHei", size: 52, bold: true, color: "2E75B6" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 200 },
      children: [new TextRun({ text: "面试知识手册", font: "Microsoft YaHei", size: 44, bold: true, color: "2E75B6" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { after: 600 },
      children: [new TextRun({ text: "知识点 + 举例 + 练习题 + 答案解析", font: "Microsoft YaHei", size: 24, color: "666666" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: "涵盖：LLM基础 | RAG | Agent | LangChain | 微调 | 工程实践 | 项目实战", font: "Microsoft YaHei", size: 20, color: "999999" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 400 },
      children: [new TextRun({ text: "2026年6月 编制", font: "Microsoft YaHei", size: 20, color: "999999" })]
    }),
    pageBreak()
  );

  // 目录
  allChildren.push(
    heading(HeadingLevel.HEADING_1, "目 录"),
    new TableOfContents("", { hyperlink: true, headingStyleRange: "1-2" }),
    pageBreak()
  );

  // 各章节
  for (const ch of chapters) {
    allChildren.push(heading(HeadingLevel.HEADING_1, ch.title));

    // === 知识点梳理 ===
    allChildren.push(heading(HeadingLevel.HEADING_2, "一、知识点梳理"));
    for (const item of ch.knowledge) {
      allChildren.push(
        boldPara(item.term, ""),
        para(item.desc),
        boldPara("举例理解：", ""),
        para(item.example),
        separator()
      );
    }

    // === 练习题 ===
    allChildren.push(heading(HeadingLevel.HEADING_2, "二、练习题"));

    // 选择题
    allChildren.push(heading(HeadingLevel.HEADING_2, "2.1 选择题"));
    ch.exercises.choice.forEach((q, i) => {
      allChildren.push(para(`${i + 1}. ${q.q}`));
      const labels = ["A", "B", "C", "D"];
      q.options.forEach((opt, j) => {
        allChildren.push(bullet(`${labels[j]}. ${opt}`));
      });
      allChildren.push(para(""));
    });

    // 填空题
    allChildren.push(heading(HeadingLevel.HEADING_2, "2.2 填空题"));
    ch.exercises.fill.forEach((q, i) => {
      allChildren.push(para(`${i + 1}. ${q.q}`));
    });
    allChildren.push(para(""));

    // 应用题
    allChildren.push(heading(HeadingLevel.HEADING_2, "2.3 应用题"));
    ch.exercises.app.forEach((q, i) => {
      allChildren.push(para(`${i + 1}. ${q.q}`));
    });

    // === 答案与解析 ===
    allChildren.push(heading(HeadingLevel.HEADING_2, "三、答案与解析"));

    // 选择题答案
    allChildren.push(para("【选择题答案】", { bold: true }));
    ch.exercises.choice.forEach((q, i) => {
      const labels = ["A", "B", "C", "D"];
      allChildren.push(para(`${i + 1}. ${labels[q.answer]} — ${q.options[q.answer]}`));
    });
    allChildren.push(para(""));

    // 填空题答案
    allChildren.push(para("【填空题答案】", { bold: true }));
    ch.exercises.fill.forEach((q, i) => {
      allChildren.push(para(`${i + 1}. ${q.answer.join(" / ")}`));
    });
    allChildren.push(para(""));

    // 应用题解析
    allChildren.push(para("【应用题参考答案】", { bold: true }));
    ch.exercises.app.forEach((q, i) => {
      allChildren.push(para(`${i + 1}. ${q.q}`));
      q.key_points.forEach(p => {
        allChildren.push(bullet(p));
      });
      allChildren.push(para(""));
    });

    allChildren.push(pageBreak());
  }

  // 附录：面试高频问题速查
  allChildren.push(
    heading(HeadingLevel.HEADING_1, "附录：面试高频问题速查"),
    para("以下为高频面试问题，建议提前准备话术："),
    para("")
  );

  const faq = [
    "介绍一下你的项目？用了什么技术栈？",
    "为什么选择LangChain而不是自己写？",
    "RAG的完整流程是什么？怎么优化检索精度？",
    "Agent和普通LLM对话有什么区别？",
    "你项目中的搜索引擎是怎么实现的？",
    "遇到过什么技术难题？怎么解决的？",
    "为什么用ChromaDB而不是Milvus/Pinecone？",
    "LoRA和全量微调的区别？你为什么选LoRA？",
    "流式输出的实现原理？SSE和WebSocket的区别？",
    "Docker在你项目中的作用？docker-compose做了什么？",
    "异步编程有什么好处？你在项目中哪里用了async/await？",
    "怎么处理LLM的幻觉问题？",
    "如果让你重新设计这个项目，你会怎么改进？",
    "你对AI Agent的未来怎么看？",
  ];
  faq.forEach((q, i) => allChildren.push(numItem(`${i + 1}. ${q}`, "faq_numbers")));

  // 构建文档
  const doc = new Document({
    styles: {
      default: { document: { run: { font: "Microsoft YaHei", size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 36, bold: true, font: "Microsoft YaHei", color: "2E75B6" },
          paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 28, bold: true, font: "Microsoft YaHei", color: "404040" },
          paragraph: { spacing: { before: 240, after: 160 }, outlineLevel: 1 } },
      ]
    },
    numbering: {
      config: [
        { reference: "bullets", levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1440, hanging: 360 } } } },
        ]},
        { reference: "numbers", levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        ]},
        { reference: "faq_numbers", levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        ]},
      ]
    },
    sections: [{
      properties: {
        page: {
          size: { width: 11906, height: 16838 },
          margin: { top: 1440, right: 1200, bottom: 1440, left: 1200 }
        }
      },
      headers: {
        default: new Header({
          children: [new Paragraph({
            alignment: AlignmentType.RIGHT,
            children: [new TextRun({ text: "AI Agent 面试知识手册", font: "Microsoft YaHei", size: 16, color: "999999" })]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [new TextRun({ text: "第 ", font: "Microsoft YaHei", size: 16 }), new TextRun({ children: [PageNumber.CURRENT], font: "Microsoft YaHei", size: 16 }), new TextRun({ text: " 页", font: "Microsoft YaHei", size: 16 })]
          })]
        })
      },
      children: allChildren
    }]
  });

  const buffer = await Packer.toBuffer(doc);
  const outPath = "D:\\python\\AI_Projects\\AI_Agent面试知识手册.docx";
  fs.writeFileSync(outPath, buffer);
  console.log(`文档已生成: ${outPath}`);
  console.log(`文件大小: ${(buffer.length / 1024).toFixed(1)} KB`);
}

generate().catch(console.error);
