module.exports = {
  title: "第七章：API 调用与工程化",
  difficulty: "A/B",
  knowledge: [
    {
      term: "OpenAI API结构",
      desc: "OpenAI API是大模型调用的事实标准接口，主要包括Chat Completions API和Embeddings API。Chat Completions API通过POST /v1/chat/completions端点调用，请求体包含messages数组（含system/user/assistant角色）、model（模型名称）、temperature等参数，返回assistant角色的回复。Embeddings API通过POST /v1/embeddings端点将文本转换为向量表示，用于语义搜索、聚类、分类等任务。API采用RESTful设计，支持同步和流式（stream=True）两种模式。消息格式采用role-content结构，支持多轮对话（传入历史消息数组）。响应格式统一为JSON，包含choices数组、usage（token用量）和model字段。几乎所有国产大模型都兼容OpenAI API格式。",
      explain: "OpenAI API就像一个标准化的外卖平台接口——不管商家（模型）是谁，下单（请求）格式都一样：选菜品（model）、写备注（messages）、说口味偏好（temperature），商家按标准包装（JSON格式）送餐（返回响应）。",
      code: "from openai import OpenAI\n\nclient = OpenAI(api_key=\"sk-xxx\")\nresponse = client.chat.completions.create(\n    model=\"gpt-4o\",\n    messages=[\n        {\"role\": \"system\", \"content\": \"你是一个助手\"},\n        {\"role\": \"user\", \"content\": \"你好\"}\n    ],\n    temperature=0.7,\n    max_tokens=1000\n)\nprint(response.choices[0].message.content)",
      parse: [
        { q: "Chat Completions API的messages数组中system、user、assistant三种角色分别起什么作用？", answer: "system角色定义模型的行为准则和上下文，对模型有全局性影响，通常放在messages数组首位且只出现一次。user角色代表用户的输入，是模型需要回应的内容。assistant角色代表模型之前的回复，用于多轮对话中维持上下文。三者配合实现多轮对话：system设规则、user提问题、assistant的历史回复让模型记住之前说了什么。system消息虽然不显示给用户，但对模型行为影响最大。" }
      ],
    },
    {
      term: "国产大模型API",
      desc: "国产大模型API生态已相当成熟，主流平台包括：DeepSeek（性价比之王，DeepSeek-V3性能接近GPT-4，价格仅为其1/10，兼容OpenAI格式）、通义千问（阿里云，Qwen系列模型强大，与阿里云生态深度集成）、智谱AI（GLM系列，ChatGLM开源影响力大，API覆盖面广）、百川智能（Baichuan系列，在中文理解方面表现突出）、Moonshot/Kimi（长文本处理能力强，支持超长上下文）、文心一言（百度，与百度搜索生态集成）。选型建议：追求性价比选DeepSeek，长文本选Kimi，企业级选通义千问，学术研究选智谱。大多数国产API已兼容OpenAI格式，只需修改base_url和api_key即可切换。",
      explain: "国产大模型API市场就像手机品牌——DeepSeek是小米（高性价比），通义千问是华为（企业级生态），智谱是锤子（技术情怀），Kimi是OPPO（长文本如长续航），各有特色，选最适合自己的。",
      parse: [
        { q: "选择国产大模型API时应该从哪些维度进行评估？", answer: "评估维度包括：1）模型能力——在目标任务上的实际表现（数学推理、代码生成、中文理解等）；2）API价格——输入/输出token单价，是否有免费额度；3）API兼容性——是否兼容OpenAI格式（减少迁移成本）；4）速度和延迟——首token延迟和生成速度；5）稳定性——服务可用性、并发限制；6）上下文长度——支持的最大token数；7）功能支持——是否支持Function Calling、JSON Mode、Vision等；8）合规和数据安全——数据是否用于训练、合规认证。实际建议：先用几个模型的免费额度做对比测试，再做选择。" }
      ],
    },
    {
      term: "API参数详解",
      desc: "核心API参数及其作用：temperature（0-2），控制输出的随机性，0为最确定（适合分类、提取），2为最随机（适合创意生成），常用0.7；top_p（0-1），核采样参数，与temperature二选一使用，0.1表示只考虑概率最高的10%token；max_tokens，限制生成的最大token数，控制成本和输出长度；stop，停止生成的标记序列（如[\"\\n\\n\"]）；frequency_penalty（-2到2），惩罚重复token，正值减少重复；presence_penalty（-2到2），鼓励谈论新话题，正值增加多样性；response_format，指定输出格式（如{\"type\":\"json_object\"}）。参数调优建议：确定性任务（提取、分类）用temperature=0，创意任务用0.7-1.0，不要同时调temperature和top_p。",
      explain: "API参数就像调节收音机——temperature是频道清晰度（越低越清楚但单一），top_p是信号范围（越小接收的台越少），max_tokens是收听时长（到点自动关机），frequency_penalty是去重按钮（过滤重复台）。",
      parse: [
        { q: "temperature和top_p应该如何选择？为什么官方建议只调其中一个？", answer: "temperature通过缩放softmax概率分布来控制随机性——低温让概率更集中于高概率token，高温让分布更平坦。top_p通过截断概率累积和来控制候选范围——只保留概率和达到p的top token。两者都控制输出多样性但机制不同。官方建议只调一个是因为：两者同时调整会使行为难以预测——比如同时设低温和低top_p会导致过度约束，同时设高温和高top_p则效果互相抵消。实践中temperature更直观，推荐先调temperature，需要更精细控制时再用top_p。" }
      ],
    },
    {
      term: "流式输出（SSE）",
      desc: "流式输出（Streaming）通过Server-Sent Events（SSE）协议实现逐token返回结果，用户无需等待完整响应即可开始阅读。实现方式：API请求设置stream=True，响应不再是完整的JSON，而是以data:前缀的事件流，每个事件包含一个或多个token的增量内容。前端使用ReadableStream或EventSource解析SSE流。SSE协议基于HTTP，数据格式为每行以data:开头，以\\n\\n分隔，最后以data: [DONE]标记结束。流式输出的价值：大幅改善用户体验（TTFT首token延迟远小于完整响应时间）、实时性更好、前端可以逐步渲染。注意事项：流式模式下token用量在最后一个chunk中返回、错误处理需在流过程中进行、需要处理连接中断的情况。",
      explain: "普通API调用像等快递——包裹全部打包好才送达；流式输出像传送带——东西边生产边传送，你不用等全部做好就能开始用。用户体验的差别就像等待vs即时。",
      code: "// 前端流式读取\nconst response = await fetch('/chat/stream', {\n  method: 'POST',\n  headers: { 'Content-Type': 'application/json' },\n  body: JSON.stringify({ question: '你好' })\n});\n\nconst reader = response.body.getReader();\nconst decoder = new TextDecoder();\n\nwhile (true) {\n  const { done, value } = await reader.read();\n  if (done) break;\n  const text = decoder.decode(value);\n  // 解析SSE格式: data: {json}\\n\\n\n  appendToChat(text);\n}",
      parse: [
        { q: "SSE（Server-Sent Events）和WebSocket在实现流式输出时有什么区别？大模型API为什么多用SSE？", answer: "SSE是单向的（服务端→客户端），基于HTTP，实现简单，自动重连；WebSocket是双向的，需要独立的连接升级，实现更复杂。大模型API多用SSE的原因：1）场景匹配——大模型输出是单向的流式文本，不需要客户端到服务端的实时通信；2）兼容性好——基于HTTP无需特殊协议支持，通过代理和负载均衡器更稳定；3）实现简单——前端用EventSource或fetch+ReadableStream即可解析；4）自动重连——SSE内置重连机制，连接中断可自动恢复。WebSocket更适合聊天室、实时协作等双向通信场景。" }
      ],
    },
    {
      term: "API错误处理",
      desc: "大模型API调用需要处理多种错误场景：超时错误（模型生成慢导致请求超时，通常设置30-120秒超时）、限流错误（429 Too Many Requests，超出API速率限制）、服务器错误（5xx，服务端暂时不可用）、认证错误（401，API Key无效或过期）、参数错误（400，请求参数不合法）、上下文超长（超过模型max_context_length）。重试策略：使用指数退避（Exponential Backoff），首次失败等1秒，第二次等2秒，第三次等4秒，通常最多重试3-5次。对于429限流错误，应读取响应头中的Retry-After字段。封装建议：统一封装API调用层，内置重试、超时、错误日志、降级策略。",
      explain: "API错误处理就像客服应对各种突发情况——客户排队太久（429限流）就安排等待叫号（重试），电话断了（超时）就回拨（重试），客户信息有误（400参数错误）就要求重新提供，客服不在（5xx服务器错误）就稍后联系。",
      code: "import time\nimport random\n\ndef call_with_retry(func, max_retries=3):\n    for attempt in range(max_retries):\n        try:\n            return func()\n        except RateLimitError:\n            wait = 2 ** attempt + random.uniform(0, 1)\n            time.sleep(wait)\n        except TimeoutError:\n            if attempt == max_retries - 1:\n                raise\n            time.sleep(1)\n        except APIError as e:\n            if e.status_code >= 500:\n                time.sleep(2 ** attempt)\n            else:\n                raise\n    raise Exception(\"Max retries exceeded\")",
      parse: [
        { q: "指数退避重试策略的原理是什么？为什么要加入随机抖动（Jitter）？", answer: "指数退避的原理：每次重试的等待时间呈指数增长（如1s、2s、4s、8s），给服务端恢复的时间，避免频繁重试加重服务端负担。加入随机抖动的原因：如果多个客户端同时遇到限流，不加抖动它们会在相同时间点同时重试，形成\"重试风暴\"（Thundering Herd），反而加剧限流。加入0-1秒的随机偏移后，不同客户端的重试时间错开，降低同时请求的概率。这是分布式系统中处理瞬时故障的标准实践。" }
      ],
    },
    {
      term: "Token计费和成本控制",
      desc: "大模型API按token计费，1个token约0.75个英文单词或1.5-2个中文字。计费方式通常分为输入token价格和输出token价格（输出通常更贵）。成本控制策略：Prompt优化（精简Prompt减少输入token）、缓存机制（相同或相似请求返回缓存结果）、模型降级（非关键任务使用便宜的小模型）、限制max_tokens（控制输出长度）、批量处理（使用Batch API享受折扣）、流式中断（检测到无用生成时提前停止）。成本监控：记录每次API调用的token用量和费用、设置预算告警、定期分析调用模式优化高消耗场景。典型成本对比：GPT-4o约$2.5/$10 per 1M tokens（输入/输出），DeepSeek-V3约$0.27/$1.10，价格差距巨大。",
      explain: "Token计费就像手机流量——输入token是上传流量，输出token是下载流量（更贵）。省钱方法：少说废话（优化Prompt）、常用WiFi（缓存）、轻度使用时换便宜套餐（小模型）、设流量上限（max_tokens）。",
      parse: [
        { q: "在实际项目中有哪些有效的API成本控制策略？如何平衡成本和效果？", answer: "核心策略：1）模型分层——简单任务（分类、提取）用小模型如GPT-4o-mini，复杂任务才用大模型；2）缓存——对相同或相似请求使用语义缓存，命中率可达30-60%；3）Prompt精简——减少不必要的上下文和示例，用更少的token传递相同信息；4）输出限制——设置合理的max_tokens，避免生成过长无用内容；5）批量API——非实时任务使用Batch API可享50%折扣；6）异步处理——非紧急任务排队批量处理。平衡原则：先用低成本方案验证效果，确认需要时再升级模型，定期review成本构成找出优化点。" }
      ],
    },
    {
      term: "Prompt Caching（提示缓存）",
      desc: "Prompt Caching是优化API成本和延迟的重要技术，通过缓存已处理的Prompt前缀来避免重复计算。当多个请求共享相同的System Prompt或上下文时，缓存命中后这部分token的处理费用大幅降低（通常降低50-90%）。OpenAI的Prompt Caching自动对相同前缀的请求生效，缓存的前缀需要至少1024个token（GPT-4o）或256个token（GPT-4o-mini）。Anthropic的Prompt Caching需要显式设置cache_control标记缓存范围。缓存通常在5-10分钟内有效。最佳实践：将不变的内容（System Prompt、工具描述、Few-shot示例）放在messages数组前面，可变的用户输入放在最后，这样前面的内容更容易命中缓存。",
      explain: "Prompt Caching就像考试时把常用的公式写在草稿纸上（缓存），不用每次做新题都重新推导一遍公式。只有题目（用户输入）变了，公式（System Prompt）不用重算。",
      parse: [
        { q: "如何最大化Prompt Caching的命中率？对消息顺序有什么要求？", answer: "最大化命中率的关键是消息顺序——缓存基于前缀匹配，只有与之前请求相同前缀的部分才能命中缓存。因此：1）将不变的内容放在messages数组最前面——System Prompt、工具定义、Few-shot示例；2）将可变内容放在最后——用户输入、动态上下文；3）保持System Prompt和工具描述的稳定性，避免频繁修改；4）多个相关应用可以共享System Prompt以提高缓存复用率。注意：缓存有最小token要求（OpenAI为1024 token），太短的Prompt无法触发缓存。" }
      ],
    },
    {
      term: "Batch API批处理",
      desc: "Batch API是OpenAI提供的批量处理接口，适用于不需要实时响应的任务。将多个请求打包为一个batch文件提交，24小时内返回结果，价格比实时API便宜50%。适用场景：大规模文本分类、批量翻译、数据标注、离线内容生成等。使用流程：1）准备JSONL格式的请求文件（每行一个请求）；2）上传文件并创建batch任务；3）轮询batch状态等待完成；4）下载结果文件。限制：batch最多50000个请求或100MB、24小时内完成、不支持流式输出。国产大模型中DeepSeek也提供了类似的Batch模式。对于大规模数据处理任务，Batch API是降低成本的最有效方式之一。",
      explain: "Batch API就像快递的经济件——自己发实时API是同城闪送（贵但快），Batch API是集货发物流（便宜但要等）。不需要当天到的东西，走物流省钱。",
      parse: [
        { q: "Batch API和实时API的选择标准是什么？哪些场景适合用Batch API？", answer: "选择标准核心是时效性——如果用户在等待结果就用实时API，如果可以异步处理就用Batch API。适合Batch API的场景：1）数据预处理——离线对大量文本做分类、提取、翻译；2）内容生成——批量生成商品描述、文章摘要；3）数据标注——用LLM对训练数据做初步标注；4）评估测试——批量运行测试用例评估模型效果。不适合的场景：用户实时交互的聊天、需要即时反馈的搜索、流式输出场景。Batch API的50%折扣对大规模任务节省显著——处理100万条数据，成本可节省数万美元。" }
      ],
    },
    {
      term: "API Key管理",
      desc: "API Key是访问大模型服务的凭证，安全管理至关重要。最佳实践：环境变量存储（os.getenv读取，不硬编码在代码中）、密钥分离（开发/测试/生产使用不同Key）、权限最小化（按需分配读写和模型访问权限）、定期轮换（每30-90天更换Key）、密钥监控（记录每次调用的来源和频率，异常告警）。存储方案：开发环境用.env文件（加入.gitignore）、生产环境用密钥管理服务（AWS Secrets Manager、阿里云KMS、HashiCorp Vault）。常见安全风险：Key被提交到Git仓库、Key在日志中泄露、Key在前端代码中暴露、过度授权。发生泄露应立即吊销Key并排查使用记录。",
      explain: "API Key就像银行密码——不能写在纸条上贴显示器（硬编码）、不能告诉别人（泄露）、不同账户用不同密码（密钥分离）、定期换密码（轮换）、发现异常立即冻结（泄露处理）。",
      parse: [
        { q: "API Key泄露会有什么后果？如何建立完善的密钥管理机制？", answer: "泄露后果：他人盗用Key产生大量费用（账单爆炸）、数据被未授权访问、恶意调用导致业务受损、合规风险（密钥管理不当违反安全规范）。建立管理机制：1）存储——使用环境变量或密钥管理服务，禁止硬编码和提交到Git；2）分级——按环境（dev/staging/prod）和权限（只读/读写）分离Key；3）监控——实时监控调用量和来源，设置异常告警阈值；4）轮换——制定定期轮换计划，支持Key版本化实现无缝切换；5）应急——建立泄露应急流程，发现泄露后秒级吊销、排查影响、更换新Key。" }
      ],
    },
    {
      term: "异步调用",
      desc: "在实际应用中，经常需要并发调用多个API请求（如同时处理多个用户请求、批量处理任务）。Python中使用asyncio + aiohttp/httpx实现异步API调用，避免同步等待导致的阻塞。async/await语法让异步代码像同步代码一样清晰。并发控制：使用Semaphore限制同时进行的请求数（避免触发限流），通常设置为5-20。异步框架选择：httpx（支持异步的HTTP客户端）、aiohttp（高性能异步HTTP框架）。关键注意事项：OpenAI官方SDK已支持异步（AsyncOpenAI）、需要处理异步异常（try/except在async函数中）、合理设置超时时间、异步回调中的上下文管理。",
      explain: "同步调用像排队结账——一个一个来，前一个人没结完后一个只能等。异步调用像自助结账——多台机器同时使用，互不阻塞。10个请求同步要10倍时间，异步只需要1倍多一点。",
      code: "import asyncio\nfrom openai import AsyncOpenAI\n\nclient = AsyncOpenAI()\n\nasync def call_api(prompt):\n    response = await client.chat.completions.create(\n        model=\"gpt-4o-mini\",\n        messages=[{\"role\": \"user\", \"content\": prompt}]\n    )\n    return response.choices[0].message.content\n\nasync def batch_call(prompts):\n    semaphore = asyncio.Semaphore(10)  # 最多10并发\n    async def limited_call(p):\n        async with semaphore:\n            return await call_api(p)\n    tasks = [limited_call(p) for p in prompts]\n    return await asyncio.gather(*tasks)",
      parse: [
        { q: "为什么异步API调用需要使用Semaphore限制并发数？并发数应该如何设置？", answer: "需要Semaphore的原因：1）API提供商有并发和速率限制，不受限制的并发会导致429错误；2）过多并发会导致本地网络和内存资源紧张；3）无限制并发可能导致API费用瞬间飙升。并发数设置考虑因素：API的速率限制（如OpenAI Tier1限制RPM）、网络带宽、本地资源、任务类型。建议值：一般设置5-20，从较低值开始逐步提高直到接近限流阈值。最佳实践：Semaphore值设为API限制的80%，留出安全余量；结合指数退避处理偶尔的429错误。" }
      ],
    },
    {
      term: "API网关和代理",
      desc: "在企业级应用中，通常不直接调用大模型API，而是通过API网关进行统一管理。API网关的核心功能：负载均衡（多个API Key轮换分发请求）、鉴权管理（统一的认证授权，前端不需要知道具体API Key）、限流控制（防止超出预算的调用量）、请求路由（根据任务类型路由到不同模型）、日志记录（统一记录所有API调用便于审计和分析）、缓存（对相同请求返回缓存结果）。常见方案：开源的LiteLLM Proxy（支持多模型统一接口）、Kong/Nginx做反向代理、自研网关。企业级需求还包括：成本中心（按部门分摊API费用）、审计合规（记录谁调用了什么）、故障转移（主模型不可用时切换备用模型）。",
      explain: "API网关就像公司的总机前台——外部来电（用户请求）先到前台，前台负责转接（路由）、过滤（鉴权）、记录（日志）、限制呼入量（限流）、分配到不同部门（模型选择），而不是让每个部门直接对外。",
      parse: [
        { q: "为什么企业级AI应用需要API网关？LiteLLM Proxy有哪些核心功能？", answer: "需要API网关的原因：1）安全——不直接暴露API Key，统一鉴权和审计；2）成本控制——统一限流和预算管理；3）灵活性——可以无缝切换不同模型提供商而不改业务代码；4）可靠性——负载均衡和故障转移保障可用性；5）可观测性——统一日志和监控。LiteLLM Proxy的核心功能：将100+种LLM API统一为OpenAI格式、支持负载均衡和故障转移、内置限流和预算管理、支持虚拟API Key（用户使用虚拟Key，网关映射到真实Key）、详细的调用日志和费用追踪。" }
      ],
    },
    {
      term: "模型选型策略",
      desc: "根据任务特点选择合适的模型是工程化的重要环节。选型维度：任务复杂度（简单分类→小模型，复杂推理→大模型）、延迟要求（实时交互→快速模型，离线处理→效果优先）、成本预算（高预算→GPT-4o，低预算→GPT-4o-mini/DeepSeek）、输入长度（长文本→支持大上下文的模型）、语言需求（中文任务→国产模型，英文→OpenAI）、特殊能力（视觉→多模态模型，代码→代码模型）。实用的模型梯队策略：旗舰层（GPT-4o/Claude 3.5处理最复杂任务）、标准层（GPT-4o-mini/DeepSeek-V3处理日常任务）、经济层（GPT-3.5-turbo/Qwen-turbo处理简单任务）。通过任务分类器自动路由到合适的模型，最大化性价比。",
      explain: "模型选型就像选交通工具——上班通勤选地铁（经济层：便宜高效），商务出行选出租车（标准层：舒适便捷），重要场合选专车（旗舰层：最高品质）。不是每次都坐专车，按需选择最合理。",
      parse: [
        { q: "如何设计一个智能的模型路由系统？根据什么规则将请求分配给不同模型？", answer: "路由系统设计：1）任务分类器——用规则或小模型判断请求类型（简单问答/复杂推理/代码生成/创意写作）；2）路由规则——简单任务（问候、分类、提取）→经济层模型、中等任务（总结、翻译）→标准层模型、复杂任务（数学推理、多步分析）→旗舰层模型；3）动态调整——监控各层模型的成功率和用户满意度，自动调整路由阈值；4）兜底机制——低层模型置信度不足时自动升级到高层模型。实现方式：可以用关键词规则、Embedding相似度或小分类器做路由决策。这种分层策略通常能节省40-60%的API成本。" }
      ],
    },
    {
      term: "Function Calling和工具使用",
      desc: "Function Calling是让大模型调用外部工具和API的核心机制。通过在API请求中定义functions（或tools）参数，描述可用函数的名称、描述和参数Schema，模型会根据用户意图决定是否调用函数以及传入什么参数。模型返回的不是直接回答，而是结构化的函数调用请求（函数名+参数），开发者执行函数后将结果返回给模型，模型再生成最终回答。这形成了一个循环：用户请求→模型决策→函数调用→结果返回→模型回答。Function Calling的价值：让模型能够访问实时数据（天气、股价）、执行精确计算（计算器）、操作外部系统（发邮件、查数据库），弥补了纯文本模型的局限。",
      explain: "Function Calling就像给助手一个工具箱——助手看到用户问题后，决定用哪个工具（选择函数），填写使用说明（生成参数），你来执行工具并把结果告诉助手，助手基于工具结果给出最终回答。",
      parse: [
        { q: "Function Calling的工作流程是什么？如何设计高效的工具定义？", answer: "工作流程：1）定义工具——在API请求中声明可用函数的名称、描述、参数JSON Schema；2）模型决策——模型分析用户意图，决定是否调用函数、调用哪个函数、传入什么参数；3）执行函数——开发者在本地执行函数获取结果；4）结果返回——将函数执行结果作为新消息传回模型；5）生成回答——模型基于函数结果生成最终回复。工具定义要点：函数名语义清晰、描述准确说明使用场景、参数Schema完整（类型、必填、枚举值）、提供默认值和约束。参数数量控制在10个以内，工具总数不超过20个。" }
      ],
    },
  ],
  parse_extra: [
    {
      q: "如何设计一个高可用的大模型API调用架构？需要考虑哪些故障场景？",
      answer: "高可用架构设计：1）多模型冗余——主模型（GPT-4o）故障时自动切换到备用模型（Claude/DeepSeek）；2）多Key轮换——多个API Key轮换使用，单Key被限流不影响整体；3）重试机制——指数退避重试处理瞬时故障；4）超时控制——设置合理的超时时间，超时后降级或重试；5）熔断机制——错误率超过阈值时暂时停止调用，避免雪崩；6）缓存层——对相同请求返回缓存结果，减少对外部依赖；7）降级方案——API完全不可用时返回预设回答或人工接管。关键故障场景：API服务商全面宕机、特定模型不可用、网络抖动、限流升级、请求超长。"
    },
    {
      q: "在生产环境中如何监控大模型API的调用质量？有哪些关键指标需要关注？",
      answer: "监控指标分为四类：1）性能指标——TTFT（首token延迟）、TPS（每秒生成token数）、端到端延迟P50/P95/P99；2）可靠性指标——成功率、错误率（按错误类型分）、限流率、超时率；3）成本指标——每次调用的token用量、日/月费用、各模型费用占比；4）质量指标——输出格式合规率、用户满意度评分、人工抽检准确率。监控工具：Prometheus+Grafana做指标可视化、LangSmith做LLM专属可观测性、自建日志分析系统。告警规则：错误率>5%告警、P99延迟>10s告警、日费用超预算80%告警。定期生成质量报告指导优化。"
    },
    {
      q: "大模型API的数据安全和隐私合规有哪些需要特别注意的问题？",
      answer: "数据安全要点：1）数据传输——必须使用HTTPS加密传输，避免明文发送敏感数据；2）数据存储——确认API提供商是否将请求数据用于模型训练（大多数提供商的API数据默认不用于训练，但需要确认）；3）数据脱敏——发送前对敏感信息（姓名、电话、身份证）做脱敏处理；4）合规要求——不同行业有不同数据合规标准（医疗HIPAA、金融PCI-DSS、个人信息保护法）；5）数据驻留——确认API服务的数据中心位置是否满足数据主权要求；6）日志安全——API调用日志中可能包含用户敏感信息，需加密存储和访问控制；7）第三方风险——使用中间代理或网关时需评估其安全性。"
    },
  ],
  exercises: {
    choice: [
      {
        q: "OpenAI Chat Completions API的消息格式中，哪个角色用于定义模型的行为准则？",
        options: ["user", "assistant", "system", "function"],
        answer: 2,
      },
      {
        q: "以下哪个参数控制生成文本的随机性？",
        options: ["max_tokens", "temperature", "top_p", "stop"],
        answer: 1,
      },
      {
        q: "流式输出（Streaming）基于什么协议实现？",
        options: ["WebSocket", "HTTP/2", "SSE (Server-Sent Events)", "TCP长连接"],
        answer: 2,
      },
      {
        q: "API调用遇到429错误时，应该采取什么策略？",
        options: ["立即重试", "指数退避重试", "放弃调用", "切换到同步模式"],
        answer: 1,
      },
      {
        q: "Batch API相比实时API，价格通常优惠多少？",
        options: ["10%", "25%", "50%", "90%"],
        answer: 2,
      },
      {
        q: "Prompt Caching缓存生效的最小前缀长度（OpenAI GPT-4o）是多少token？",
        options: ["128", "512", "1024", "4096"],
        answer: 2,
      },
      {
        q: "以下哪个不是API Key管理的最佳实践？",
        options: ["使用环境变量存储", "定期轮换", "硬编码在代码中", "权限最小化"],
        answer: 2,
      },
      {
        q: "异步API调用中，Semaphore的作用是？",
        options: ["加速请求发送", "限制并发请求数量", "加密请求数据", "缓存请求结果"],
        answer: 1,
      },
      {
        q: "Function Calling中，开发者需要负责的是？",
        options: ["生成函数调用参数", "实际执行函数并返回结果", "决定是否调用函数", "编写函数描述"],
        answer: 1,
      },
      {
        q: "以下哪种场景最适合使用Batch API？",
        options: ["实时聊天", "用户搜索", "离线数据分类", "代码实时调试"],
        answer: 2,
      },
    ],
    fill: [
      {
        q: "OpenAI API中，______参数用于限制生成的最大token数量。",
        answer: ["max_tokens", "maxTokens", "max_tokens"],
      },
      {
        q: "流式输出的SSE协议中，数据以______前缀发送，以[DONE]标记结束。",
        answer: ["data:", "data: "],
      },
      {
        q: "API调用重试通常使用指数______策略。",
        answer: ["退避", "后退"],
      },
      {
        q: "API网关的核心功能包括负载均衡、鉴权、______和日志记录。",
        answer: ["限流", "流量控制"],
      },
      {
        q: "Prompt Caching将不变的内容放在messages数组______以提高缓存命中率。",
        answer: ["前面", "开头", "最前面"],
      },
      {
        q: "Function Calling中，工具的参数使用______Schema格式定义。",
        answer: ["JSON", "json"],
      },
      {
        q: "Python中使用______库实现异步API调用。",
        answer: ["asyncio", "httpx", "aiohttp", "AsyncOpenAI"],
      },
      {
        q: "大模型API的计费通常分为______token价格和输出token价格。",
        answer: ["输入", "请求"],
      },
      {
        q: "模型选型的梯队策略通常分为旗舰层、标准层和______层。",
        answer: ["经济", "基础"],
      },
      {
        q: "API Key发生泄露后应立即______该Key。",
        answer: ["吊销", "禁用", "撤销"],
      },
    ],
    app: [
      {
        q: "你正在开发一个AI客服系统，日均API调用量10万次。请设计完整的API调用架构，包括模型选型、成本控制、错误处理和监控方案。",
        key_points: [
          "模型分层：简单问题用GPT-4o-mini，复杂问题路由到GPT-4o/DeepSeek",
          "成本控制：Prompt缓存+语义缓存减少重复调用，Batch API处理离线任务",
          "并发控制：AsyncOpenAI + Semaphore限制并发，指数退避处理限流",
          "API Key管理：多Key轮换，环境变量存储，定期轮换",
          "监控：Prometheus记录延迟、成功率、token用量，Grafana可视化，告警通知",
        ],
      },
      {
        q: "你需要将一个同步的单线程AI应用改造为支持高并发的异步架构。当前问题是：100个用户同时请求时响应时间过长。请设计改造方案。",
        key_points: [
          "将同步OpenAI调用改为AsyncOpenAI异步调用",
          "使用asyncio.Semaphore控制并发数（建议10-20）",
          "引入API网关做负载均衡和多Key轮换",
          "添加请求队列和优先级处理",
          "实现结果缓存减少重复调用",
        ],
      },
      {
        q: "你的公司需要接入多个大模型提供商（OpenAI、DeepSeek、通义千问），要求统一接口、智能路由和成本优化。请设计技术方案。",
        key_points: [
          "使用LiteLLM Proxy或自建网关统一API接口",
          "设计智能路由规则：按任务类型、成本预算、延迟要求选择模型",
          "实现故障转移：主模型不可用自动切换备用模型",
          "成本优化：预算管理、调用统计、定期模型效果对比",
          "安全和合规：统一鉴权、日志审计、数据脱敏",
        ],
      },
    ],
  },
};
