// ============================================================
// 第一章：LLM 与 Transformer 基础
// ============================================================
module.exports = {
  title: "第一章：LLM 与 Transformer 基础",
  difficulty: "A/B",
  knowledge: [
    {
      term: "Transformer 架构",
      desc: "2017年Google在论文《Attention Is All You Need》中提出的神经网络架构。由编码器（Encoder）和解码器（Decoder）组成，核心是自注意力机制（Self-Attention）。取代了此前主导NLP领域的RNN/LSTM，因为能并行计算且擅长捕捉长距离依赖。",
      explain: "想象你在看一部电影。RNN像从头到尾看一遍才能理解剧情，Transformer像同时看所有片段并理解它们之间的关系。前者慢且容易忘掉开头，后者快且全局理解。",
      parse: [
        { q: "为什么Transformer比RNN更适合处理长文本？", answer: "因为RNN是串行处理，信息需要一步步传递，长距离信息会衰减（梯度消失）。Transformer的自注意力机制可以直接计算任意两个位置的关系，不受距离限制。此外，Transformer可以并行计算所有位置，训练速度远快于RNN。", },
        { q: "Transformer的编码器和解码器分别有什么作用？", answer: "编码器负责理解输入文本的含义，将文本转换为高维向量表示。解码器根据编码器的输出和已生成的内容，逐个生成输出token。GPT系列只用解码器（Decoder-Only），T5/BART用编码器-解码器完整结构。", },
        { q: "为什么现在的大模型几乎都是Decoder-Only架构？", answer: "三个原因：1.自回归生成天然适合Decoder-Only结构；2.训练效率更高，所有token都参与loss计算（Encoder-Decoder只在输出部分计算loss）；3.工程实现更简单，推理时只需一个模型。", },
      ],
    },
    {
      term: "Self-Attention（自注意力机制）",
      desc: "Transformer的核心计算。对输入序列中的每个位置，计算它与所有其他位置的相关性分数（注意力权重），然后加权聚合其他位置的信息。公式：Attention(Q,K,V) = softmax(QK^T / √d_k) × V。Q是查询向量，K是键向量，V是值向量，d_k是维度。",
      explain: "你在图书馆找资料。Q（Query）是你脑中的问题，K（Key）是每本书的标题/摘要，V（Value）是书的正文内容。QK^T计算你的问题和每本书的匹配度，softmax归一化后按匹配度加权提取信息。",
      code: `import torch
import torch.nn.functional as F

def self_attention(Q, K, V, d_k):
    # Q,K,V shape: (batch, seq_len, d_model)
    scores = torch.matmul(Q, K.transpose(-2, -1)) / (d_k ** 0.5)
    weights = F.softmax(scores, dim=-1)  # 注意力权重
    output = torch.matmul(weights, V)     # 加权聚合
    return output, weights`,
      parse: [
        { q: "为什么要除以√d_k？", answer: "防止点积值过大导致softmax梯度消失。当d_k很大时，QK^T的值会很大，softmax输出趋向于one-hot分布（接近0或1），梯度接近于0，模型无法学习。除以√d_k将方差控制在1左右。", },
        { q: "注意力权重矩阵的形状是什么？物理意义是什么？", answer: "形状是(seq_len, seq_len)的方阵。第i行第j列表示第i个token对第j个token的关注程度。权重越大表示越相关。比如'它'这个词行中，'苹果'列的权重最大，说明模型理解'它'指代的是'苹果'。", },
      ],
    },
    {
      term: "Multi-Head Attention（多头注意力）",
      desc: "将Q/K/V分成h个头并行计算注意力，每个头学习不同的关注模式，最后拼接结果。公式：MultiHead(Q,K,V) = Concat(head_1,...,head_h) × W^O，其中head_i = Attention(QW_i^Q, KW_i^K, VW_i^V)。",
      explain: "读一句话时，你的大脑同时关注不同维度：语法关系（主谓宾）、语义关系（同义反义）、位置关系（前后文）。多头注意力就是让模型同时从多个角度理解文本。",
      parse: [
        { q: "多头注意力中，不同的头分别学到了什么？", answer: "研究发现：有的头关注局部语法（相邻词的关系），有的头关注长距离依赖（代词指代），有的头关注特定模式（动宾搭配）。多头组合让模型理解更全面。", },
      ],
    },
    {
      term: "位置编码（Positional Encoding）",
      desc: "Transformer本身不感知顺序，需要额外注入位置信息。原始方法：用正弦/余弦函数生成位置向量。RoPE（旋转位置编码）：通过旋转矩阵将位置信息编码进Q和V，支持相对位置，是目前主流（LLaMA/Qwen等都用RoPE）。ALiBi：通过注意力偏置注入位置信息。",
      explain: "给排队的人发号码牌。没有号码牌时，模型只知道有哪些人，不知道谁在前谁在后。位置编码就是号码牌，让模型知道'猫追狗'和'狗追猫'的区别。",
      parse: [
        { q: "RoPE（旋转位置编码）的优势是什么？", answer: "1.支持相对位置编码（不需要绝对位置信息）；2.具有外推能力（训练时用短序列，推理时可以处理更长序列）；3.计算高效，只需旋转操作。", },
        { q: "绝对位置编码和相对位置编码的区别？", answer: "绝对位置编码：给每个位置一个固定的向量（位置1、位置2...）。相对位置编码：只关注两个token之间的距离。相对位置编码更灵活，因为'我-喜欢'的关系不管在句首还是句尾都一样。", },
      ],
    },
    {
      term: "KV Cache",
      desc: "自回归推理时的优化技术。生成第n个token时，前n-1个token的Key和Value不需要重新计算，可以缓存复用。将推理复杂度从O(n²)降到O(n)。代价是显存占用随序列长度线性增长。",
      explain: "做笔记的比喻：你不需要每次都从头翻笔记本，只需要在最后一页写新内容，之前的笔记随时可以翻看。KV Cache就是那个笔记本。",
      code: `# 推理伪代码（简化）
def generate_with_kv_cache(model, prompt, max_tokens):
    # 第一次前向传播：计算所有token的KV
    kv_cache = model.forward(prompt)  # 缓存KV

    tokens = []
    for _ in range(max_tokens):
        # 后续只计算新token的KV，复用缓存
        new_token = model.forward_step(
            last_token, kv_cache=kv_cache
        )
        kv_cache.update(new_token.kv)  # 追加缓存
        tokens.append(new_token)
        if new_token == EOS:
            break
    return tokens`,
      parse: [
        { q: "KV Cache的显存占用怎么计算？", answer: "每个token需要存储K和V各一个向量，大小为2×d_model×2字节（FP16）。128K上下文、d_model=4096时，单个请求的KV Cache约2GB。这也是为什么长上下文推理需要大量显存。", },
        { q: "有KV Cache时，batch推理怎么处理不同长度的序列？", answer: "需要Padding对齐短序列，浪费显存。vLLM的PagedAttention技术解决了这个问题——像操作系统管理内存页一样管理KV Cache，按需分配，避免浪费。", },
      ],
    },
    {
      term: "Tokenizer（分词器）",
      desc: "将文本切分成token序列的工具。主流方法：BPE（Byte-Pair Encoding，GPT用）、SentencePiece（LLaMA用）、WordPiece（BERT用）。token可以是字、词、子词。中文通常1个字=2-3个token，英文1个单词=1-2个token。",
      explain: "英文分词像乐高积木：'unhappiness'拆成'un'+'happiness'。中文分词像切菜：'人工智能'可能切成'人工'+'智能'或'人'+'工'+'智'+'能'。不同的切法影响理解能力和推理成本。",
      parse: [
        { q: "为什么大模型不直接用字/词作为token，而用子词（subword）？", answer: "1.字粒度太细，序列太长（成本高）；2.词粒度太粗，词表太大（内存大），且无法处理新词/错字。子词是平衡点：常见词保留完整（如'the'），罕见词拆成子词（如'transformer'='trans'+'form'+'er'），兼顾效率和覆盖。", },
        { q: "Token数量对成本有什么影响？", answer: "API按token计费，输入和输出分开计价。中文内容的token数通常是字数的2-3倍，成本比英文高。Prompt设计时要精简token，避免无意义的重复内容。", },
      ],
    },
    {
      term: "上下文窗口（Context Window）",
      desc: "模型一次能处理的最大token数量。GPT-4 Turbo: 128K，Claude 3.5: 200K，Gemini 1.5: 1M。超过窗口的内容会被截断。窗口越大，KV Cache越大，推理越慢越贵。",
      explain: "上下文窗口就像你的工作台大小。小桌子只能同时看几份文件，大桌子能摊开一整本书。超大窗口（1M token）相当于一面墙那么大的桌子——能放下，但找东西更慢了。",
      parse: [
        { q: "如何处理超出上下文窗口的长文档？", answer: "四种方案：1.文本截断（保留最新内容）；2.文本摘要（用LLM压缩历史）；3.滑动窗口（只保留最近N轮对话）；4.RAG检索（将文档存入向量库，按需检索相关片段）。实际项目通常组合使用。", },
      ],
    },
    {
      term: "涌现能力（Emergent Abilities）",
      desc: "模型参数量达到一定规模后突然出现的能力，小模型完全不具备。如few-shot学习、思维链推理、代码生成等。GPT-3（175B）突然展现出few-shot能力，而更小的模型完全没有。学界对涌现是否真实存在仍有争论——可能是评估指标不连续导致的假象。",
      parse: [
        { q: "涌现能力对实际应用有什么意义？", answer: "选择模型时要考虑任务复杂度。简单任务（翻译、摘要）小模型就够用。复杂任务（推理、编程）需要大模型才能触发涌现能力。这直接影响成本和效果的权衡。", },
      ],
    },
    {
      term: "幻觉（Hallucination）",
      desc: "模型生成看似合理但实际错误或无中生有的内容。根本原因：模型基于统计概率生成文本，不真正理解事实。分类：事实性幻觉（与现实不符）、忠实性幻觉（与输入不符）。缓解方法：RAG引入外部知识、Chain-of-Thought推理、Self-Consistency一致性检查、人工反馈。",
      explain: "幻觉就像一个博学但不诚实的人——他什么都能说出一套道理，但部分内容是他'编'的。因为他的知识来自'听别人说'（训练数据），不是亲身验证。",
      parse: [
        { q: "如何在生产环境中检测和减少幻觉？", answer: "1.RAG引入可溯源的外部知识，限制模型只基于检索内容回答；2.要求模型输出引用来源，方便验证；3.设置置信度阈值，低置信度时回复'不确定'；4.用另一个模型做Fact-Check；5.关键信息（数字、日期、人名）用工具验证。", },
      ],
    },
    {
      term: "Temperature / Top-P / Top-K",
      desc: "控制生成随机性的三个参数。Temperature：缩放logits，0=确定性，>1=更随机。Top-P（核采样）：只从累积概率前P%的token中采样。Top-K：只从概率最高的K个token中采样。实际使用中通常只调Temperature或Top-P，不同时调。",
      explain: "Temperature像调味料——0是白开水（固定），1是正常，2是重口味（创意但可能离谱）。Top-P像自助餐——只从你喜欢的前80%菜品中选。Top-K像排行榜——只从前10名中选。",
      parse: [
        { q: "写代码和写创意文章时，Temperature应该怎么设置？", answer: "写代码：Temperature设低（0-0.3），因为代码需要精确，容错率低。写创意文章：Temperature设高（0.7-1.0），需要多样性和创意。事实性问答：接近0。聊天对话：0.5-0.7平衡准确和自然。", },
      ],
    },
    {
      term: "模型量化（Quantization）",
      desc: "将模型权重从高精度（FP32/FP16）压缩为低精度（INT8/INT4/NF4）的技术。降低显存占用和推理成本，但可能损失精度。常见方法：GPTQ（训练后量化）、AWQ（激活感知量化）、GGUF（llama.cpp格式）、bitsandbytes（动态量化）。",
      explain: "量化就像照片压缩——原图10MB（FP32），压缩成1MB（INT8）后大部分情况下看不出区别，但仔细看细节会丢失。INT4压缩更狠，只有0.5MB，细节丢失更多但依然能用。",
      parse: [
        { q: "INT8量化和INT4量化的区别？显存节省多少？", answer: "INT8：每个权重8位，显存约为FP16的一半，精度损失很小。INT4：每个权重4位，显存约为FP16的四分之一，精度损失更大但仍可用。7B模型：FP16约14GB，INT8约7GB，INT4约3.5GB。", },
        { q: "量化对推理速度有什么影响？", answer: "INT8推理速度通常比FP16快1.5-2倍（因为计算量减半，且显存带宽是瓶颈）。INT4更快但需要特定硬件支持。但量化后精度下降，需要在速度和质量间权衡。", },
      ],
    },
    {
      term: "LoRA / QLoRA",
      desc: "LoRA（Low-Rank Adaptation）：冻结原始模型参数，只训练两个低秩矩阵A和B（秩r通常8-64），参数量仅为全量的0.1%-1%。QLoRA：在LoRA基础上将基础模型量化为4-bit（NF4），进一步降低显存。7B模型QLoRA只需约6GB显存。",
      explain: "LoRA像给模型'贴标签'——原始模型不动，只在旁边加小模块学新知识。QLoRA是用缩微版的书来贴标签——书变小了（4-bit量化），便签还是高精度。省空间但效果接近。",
      parse: [
        { q: "LoRA的秩r怎么选择？", answer: "r越大，学习能力越强，但参数越多。经验值：简单任务r=8-16，复杂任务r=32-64，极少用r>128。实验表明r=16-32在大多数任务上效果已经很好。r过大反而可能过拟合。", },
      ],
    },
    {
      term: "Layer Normalization",
      desc: "对每个样本的特征维度做归一化，稳定训练过程。Pre-LN（先归一化再做注意力）比Post-LN（先做注意力再归一化）训练更稳定，是目前主流。RMSNorm是简化版的LayerNorm，去掉了均值计算，速度更快，LLaMA/Qwen等都用RMSNorm。",
      explain: "LayerNorm像把每个学生的成绩标准化——不管原始分是多少，标准化后平均分为0、标准差为1。这样不同层的数据范围一致，训练更稳定。RMSNorm是简化版，只管'波动大小'不管'平均值'。",
      parse: [
        { q: "Pre-LN和Post-LN的区别？为什么主流模型用Pre-LN？", answer: "Pre-LN：先LayerNorm再Attention/FFN，残差连接在归一化之后。Post-LN：先Attention/FFN再LayerNorm。Pre-LN训练更稳定（梯度更均匀），不需要warmup就能训练。Post-LN理论上效果可能更好但训练不稳定。", },
      ],
    },
    {
      term: "激活函数（SwiGLU / GELU）",
      desc: "Transformer中FFN层使用的非线性函数。GELU（BERT/GPT-2用）：平滑的ReLU变体。SwiGLU（LLaMA/Qwen用）：Swish激活+门控线性单元，效果更好但参数更多（FFN中间维度需要调整为8/3倍以保持总参数量不变）。",
      explain: "激活函数给神经网络加入'非线性'——没有它，多层线性变换叠加起来还是线性变换，无法学习复杂模式。GELU像'柔性开关'，SwiGLU像'智能调光器'——更精细地控制信息流。",
      parse: [
        { q: "为什么LLaMA选择SwiGLU而不是GELU？", answer: "实验表明SwiGLU在相同参数量下效果更好。SwiGLU的门控机制可以更精细地控制信息流动——决定哪些特征'通过'、哪些'被过滤'。但SwiGLU的FFN有三个权重矩阵（上投影、门控、下投影），比GELU的两个矩阵参数多，所以中间维度从4d降到8d/3以保持总量不变。", },
      ],
    },
    {
      term: "注意力优化：FlashAttention / MQA / GQA",
      desc: "FlashAttention：IO感知的注意力算法，减少HBM读写次数，训练和推理速度提升2-4倍，不改变数学结果。MQA（Multi-Query Attention）：所有注意力头共享K和V，显存减少约1/h。GQA（Grouped-Query Attention）：分组共享K和V，是MQA和MHA的折中。LLaMA 2/3使用GQA。",
      explain: "FlashAttention像整理书桌——不改变你要看的书，但把常用书放在手边（SRAM），不常用的放书架（HBM），减少来回走动的时间。GQA像小组作业——每组共享一套参考资料（KV），而不是每人一套。",
      parse: [
        { q: "GQA为什么是MQA和MHA的折中？效果怎么样？", answer: "MHA：每个头独立的Q/K/V（最灵活但显存大）。MQA：所有头共享K/V（显存最小但可能损失质量）。GQA：每g个头共享一组K/V（如8个头分4组）。GQA在显存节省和质量间取得平衡，LLaMA 2 70B使用GQA后推理速度提升约30%，质量几乎无损。", },
      ],
    },
  ],
  parse_extra: [
    { q: "解释Transformer中残差连接（Residual Connection）的作用。", answer: "残差连接：output = LayerNorm(x + Sublayer(x))。作用：1.解决深层网络的梯度消失问题（梯度可以直接通过跳跃连接回传）；2.让网络学习'增量变化'（只需学与输入的差异），更容易优化。没有残差连接，超过10层的Transformer很难训练。" },
    { q: "FFN（前馈网络）层在Transformer中起什么作用？", answer: "FFN层：FFN(x) = W2 × activation(W1 × x + b1) + b2。作用：1.引入非线性变换，增强模型表达能力；2.可以看作'记忆存储'——研究表明FFN层存储了大量事实知识（如'巴黎是法国的首都'）。FFN的中间维度通常是d_model的4倍（或SwiGLU的8/3倍）。" },
    { q: "Decoder-Only模型在训练时如何实现并行？推理时为什么不能并行？", answer: "训练时用Teacher Forcing：将完整输入序列一次性送入模型，通过因果注意力掩码（下三角矩阵）确保每个位置只能看到前面的内容，所有位置的loss同时计算，所以可以并行。推理时需要逐个生成token，每个token依赖前一个token的输出，所以必须串行。" },
    { q: "什么是Causal Attention Mask？为什么Decoder-Only需要它？", answer: "因果注意力掩码是一个下三角矩阵，将注意力权重中'未来位置'设为负无穷（softmax后为0），确保每个token只能关注它自己和之前的token。没有它，模型在训练时能'偷看'未来的token，推理时却不能，导致训练和推理不一致。" },
  ],
  exercises: {
    choice: [
      { q: "Transformer的核心创新是什么？", options: ["卷积神经网络", "循环神经网络", "自注意力机制（Self-Attention）", "池化操作"], answer: 2 },
      { q: "自注意力中为什么要除以√d_k？", options: ["加速计算", "防止梯度消失", "减少参数量", "增加非线性"], answer: 1 },
      { q: "RoPE（旋转位置编码）的主要优势是什么？", options: ["计算速度快", "支持相对位置且有外推能力", "占用内存小", "实现简单"], answer: 1 },
      { q: "KV Cache的作用是什么？", options: ["压缩模型参数", "缓存已计算的KV避免重复计算", "存储训练数据", "加密模型权重"], answer: 1 },
      { q: "GQA（Grouped-Query Attention）相比MQA的优势是什么？", options: ["速度更快", "显存更小", "质量和显存的折中更好", "实现更简单"], answer: 2 },
      { q: "FlashAttention优化的是什么？", options: ["注意力的数学计算", "GPU的IO读写效率", "模型参数量", "训练数据质量"], answer: 1 },
      { q: "LoRA的核心思想是什么？", options: ["删除部分参数", "冻结原参数，只训练低秩适配矩阵", "量化为1-bit", "增加更多层"], answer: 1 },
      { q: "模型量化INT8相比FP16，显存占用如何变化？", options: ["不变", "减少约一半", "减少约四分之一", "增加一倍"], answer: 1 },
      { q: "以下哪个不是控制生成随机性的参数？", options: ["Temperature", "Top-P", "Batch Size", "Top-K"], answer: 2 },
      { q: "Pre-LN和Post-LN中，哪个训练更稳定？", options: ["Post-LN", "Pre-LN", "两者一样", "取决于模型大小"], answer: 1 },
    ],
    fill: [
      { q: "Transformer论文标题是《______》，发表于______年。", answer: ["Attention Is All You Need", "2017"] },
      { q: "自注意力公式：Attention(Q,K,V) = softmax(______ / √______) × V。", answer: ["QK^T", "d_k"] },
      { q: "多头注意力将Q/K/V分成______个头并行计算，最后______结果。", answer: ["h/多个", "拼接/Concat"] },
      { q: "KV Cache的代价是______占用随序列长度线性增长。", answer: ["显存"] },
      { q: "Tokenizer将文本切分成______，主流方法包括BPE和______。", answer: ["token", "SentencePiece"] },
      { q: "模型量化将权重从高精度压缩为______精度，常见有INT8和______。", answer: ["低", "INT4/NF4"] },
      { q: "LoRA冻结原始参数，只训练两个______矩阵。秩r通常设为______。", answer: ["低秩", "8-64"] },
      { q: "SwiGLU是______激活函数和______线性单元的组合。", answer: ["Swish", "门控/GLU"] },
      { q: "______是IO感知的注意力算法，通过减少______读写次数提速。", answer: ["FlashAttention", "HBM/显存"] },
      { q: "大模型产生看似合理但实际错误的内容被称为______。", answer: ["幻觉/Hallucination"] },
    ],
    app: [
      { q: "解释为什么Transformer的自注意力机制能捕捉长距离依赖，但计算复杂度是O(n²)。有没有降低复杂度的方法？", key_points: ["自注意力直接计算任意两个位置的关系，不受距离限制", "但n个token两两计算需要n²次", "降低方法：FlashAttention（IO优化，不改变复杂度）、稀疏注意力（只计算部分位置）、线性注意力（用核函数近似softmax）"] },
      { q: "你的项目中使用DeepSeek作为LLM。如果用户输入超出了上下文窗口，你会怎么处理？给出至少4种方案并分析优劣。", key_points: ["1.截断：保留最新内容，简单但丢失历史", "2.摘要：LLM压缩历史，保留关键信息但有损", "3.滑动窗口：保留最近N轮，平衡成本和效果", "4.RAG检索：历史存入向量库，按需检索，最灵活", "5.组合方案：旧对话摘要+近期对话保留+RAG补充"] },
      { q: "对比LoRA和全量微调：各自的优缺点、适用场景、资源需求。你的项目为什么选择LoRA？", key_points: ["全量微调：效果最好，但需要大量显存（7B约56GB FP16）", "LoRA：只训练0.1%参数，显存降低10倍，效果接近", "QLoRA：进一步量化，7B只需6GB", "适用场景：数据少、资源有限用LoRA；数据多、追求极致用全量"] },
      { q: "从KV Cache的角度分析，为什么长上下文推理（如128K token）需要大量显存？如何优化？", key_points: ["每个token需存储K和V各一个向量", "128K×d_model×2×2字节（FP16）= 数GB", "优化：GQA减少KV头数、量化KV Cache（FP8/INT8）、PagedAttention按需分配、滑动窗口丢弃旧KV"] },
      { q: "如果你要部署一个7B参数的LLM到消费级GPU（24GB显存），需要做哪些优化？", key_points: ["1.量化：INT4量化后约3.5GB模型权重", "2.KV Cache管理：限制上下文长度或用PagedAttention", "3.批处理优化：vLLM的连续批处理", "4.推理框架：用vLLM或TensorRT-LLM加速", "5.考虑用GGUF格式在CPU上运行（如果GPU不够）"] },
    ]
  }
};
