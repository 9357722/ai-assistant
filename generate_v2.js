const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType,
  ShadingType, PageNumber, PageBreak, LevelFormat, TableOfContents
} = require("docx");

// ========== 加载所有章节 ==========
const chapterFiles = [
  'ch1_llm', 'ch2_rag', 'ch3_agent', 'ch4_langchain', 'ch5_finetune',
  'ch6_prompt', 'ch7_api', 'ch8_deploy', 'ch9_multi_agent', 'ch10_project', 'ch11_career'
];
const chapters = chapterFiles.map(f => require('./handbook_data/' + f));

// ========== 辅助函数 ==========
const h1 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  pageBreakBefore: true,
  spacing: { before: 360, after: 200 },
  children: [new TextRun({ text, bold: true, font: "Microsoft YaHei", size: 36, color: "2E75B6" })]
});

const h2 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  spacing: { before: 240, after: 160 },
  children: [new TextRun({ text, bold: true, font: "Microsoft YaHei", size: 28, color: "404040" })]
});

const h3 = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  spacing: { before: 180, after: 120 },
  children: [new TextRun({ text, bold: true, font: "Microsoft YaHei", size: 24, color: "555555" })]
});

const p = (text, opts = {}) => new Paragraph({
  spacing: { after: 80, line: 360 },
  ...opts,
  children: [new TextRun({ text: String(text), font: "Microsoft YaHei", size: 22, ...opts })]
});

const pBold = (label, text) => new Paragraph({
  spacing: { after: 80, line: 360 },
  children: [
    new TextRun({ text: label, bold: true, font: "Microsoft YaHei", size: 22 }),
    new TextRun({ text: String(text), font: "Microsoft YaHei", size: 22 })
  ]
});

const bullet = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  spacing: { after: 60, line: 340 },
  children: [new TextRun({ text: String(text), font: "Microsoft YaHei", size: 22 })]
});

const numItem = (text, ref = "numbers") => new Paragraph({
  numbering: { reference: ref, level: 0 },
  spacing: { after: 60, line: 340 },
  children: [new TextRun({ text: String(text), font: "Microsoft YaHei", size: 22 })]
});

const codeBlock = (text) => new Paragraph({
  spacing: { after: 120, line: 300 },
  shading: { fill: "F5F5F5", type: ShadingType.CLEAR },
  indent: { left: 360 },
  children: [new TextRun({ text: String(text), font: "Consolas", size: 18 })]
});

const separator = () => new Paragraph({
  spacing: { before: 80, after: 80 },
  border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "DDDDDD", space: 1 } },
  children: []
});

const emptyLine = () => new Paragraph({ spacing: { after: 60 }, children: [] });

// ========== 生成章节内容 ==========
function buildChapter(ch) {
  const children = [];

  // === 知识点梳理 ===
  children.push(h2("一、知识点梳理"));

  for (const item of ch.knowledge) {
    // 概念名
    children.push(pBold("", item.term));

    // 解释
    children.push(p(item.desc));

    // 通俗举例（如果有）
    if (item.explain) {
      children.push(pBold("举例理解：", ""));
      children.push(p(item.explain));
    }

    // 代码示例（如果有）
    if (item.code) {
      children.push(pBold("代码示例：", ""));
      children.push(codeBlock(item.code));
    }

    // 解析题（每个知识点自带的）
    if (item.parse && item.parse.length > 0) {
      children.push(pBold("配套解析：", ""));
      for (let i = 0; i < item.parse.length; i++) {
        children.push(pBold(`Q${i + 1}: `, item.parse[i].q));
        children.push(p(`A: ${item.parse[i].answer}`));
      }
    }

    children.push(separator());
  }

  // 额外解析题
  if (ch.parse_extra && ch.parse_extra.length > 0) {
    children.push(h2("二、综合解析题"));
    for (let i = 0; i < ch.parse_extra.length; i++) {
      children.push(pBold(`解析题${i + 1}: `, ch.parse_extra[i].q));
      children.push(p(`参考答案：${ch.parse_extra[i].answer}`));
      children.push(emptyLine());
    }
  }

  // === 练习题 ===
  children.push(h2(ch.parse_extra ? "三、练习题" : "二、练习题"));

  // 选择题
  children.push(h3(`${ch.parse_extra ? "3.1" : "2.1"} 选择题（${ch.exercises.choice.length}题）`));
  const labels = ["A", "B", "C", "D"];
  for (let i = 0; i < ch.exercises.choice.length; i++) {
    const q = ch.exercises.choice[i];
    children.push(p(`${i + 1}. ${q.q}`));
    for (let j = 0; j < q.options.length; j++) {
      children.push(bullet(`${labels[j]}. ${q.options[j]}`));
    }
    children.push(emptyLine());
  }

  // 填空题
  children.push(h3(`${ch.parse_extra ? "3.2" : "2.2"} 填空题（${ch.exercises.fill.length}题）`));
  for (let i = 0; i < ch.exercises.fill.length; i++) {
    children.push(p(`${i + 1}. ${ch.exercises.fill[i].q}`));
  }
  children.push(emptyLine());

  // 应用题
  children.push(h3(`${ch.parse_extra ? "3.3" : "2.3"} 应用题（${ch.exercises.app.length}题）`));
  for (let i = 0; i < ch.exercises.app.length; i++) {
    children.push(p(`${i + 1}. ${ch.exercises.app[i].q}`));
  }

  // === 答案与解析 ===
  children.push(h2(ch.parse_extra ? "四、答案与解析" : "三、答案与解析"));

  // 选择题答案
  children.push(p("【选择题答案】", { bold: true }));
  for (let i = 0; i < ch.exercises.choice.length; i++) {
    const q = ch.exercises.choice[i];
    children.push(p(`${i + 1}. ${labels[q.answer]} — ${q.options[q.answer]}`));
  }
  children.push(emptyLine());

  // 填空题答案
  children.push(p("【填空题答案】", { bold: true }));
  for (let i = 0; i < ch.exercises.fill.length; i++) {
    const q = ch.exercises.fill[i];
    children.push(p(`${i + 1}. ${q.answer.join(" / ")}`));
  }
  children.push(emptyLine());

  // 应用题参考答案
  children.push(p("【应用题参考答案】", { bold: true }));
  for (let i = 0; i < ch.exercises.app.length; i++) {
    const q = ch.exercises.app[i];
    children.push(pBold(`${i + 1}. `, q.q));
    if (q.key_points) {
      q.key_points.forEach(kp => children.push(bullet(kp)));
    }
    children.push(emptyLine());
  }

  return children;
}

// ========== 构建完整文档 ==========
async function generate() {
  const allChildren = [];

  // 封面
  allChildren.push(
    new Paragraph({ spacing: { before: 3000 }, children: [] }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: "AI Agent 应用开发工程师", font: "Microsoft YaHei", size: 52, bold: true, color: "2E75B6" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 200 },
      children: [new TextRun({ text: "面试知识手册 v2", font: "Microsoft YaHei", size: 44, bold: true, color: "2E75B6" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 600 },
      children: [new TextRun({ text: "知识点 + 解析题 + 练习题 + 答案解析 | 11章135个知识点", font: "Microsoft YaHei", size: 22, color: "666666" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { after: 100 },
      children: [new TextRun({ text: "涵盖：LLM | RAG | Agent | LangChain | 微调 | Prompt | API | 部署 | 多Agent | 项目 | 求职", font: "Microsoft YaHei", size: 18, color: "999999" })]
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER, spacing: { before: 400 },
      children: [new TextRun({ text: "2026年6月 编制", font: "Microsoft YaHei", size: 20, color: "999999" })]
    }),
    new Paragraph({ children: [new PageBreak()] })
  );

  // 目录
  allChildren.push(
    h1("目 录"),
    new TableOfContents("", { hyperlink: true, headingStyleRange: "1-2" }),
    new Paragraph({ children: [new PageBreak()] })
  );

  // 各章节
  for (let i = 0; i < chapters.length; i++) {
    allChildren.push(h1(chapters[i].title));
    allChildren.push(...buildChapter(chapters[i]));
  }

  // 附录：高频面试问题速查
  allChildren.push(h1("附录：高频面试问题速查"));
  const faq = [
    "介绍一下你的项目？用了什么技术栈？",
    "为什么选择LangChain而不是自己写？",
    "RAG的完整流程是什么？怎么优化检索精度？",
    "Agent和普通LLM对话有什么区别？",
    "你项目中的搜索引擎是怎么实现的？",
    "遇到过什么技术难题？怎么解决的？",
    "为什么用ChromaDB而不是Milvus？",
    "LoRA和全量微调的区别？",
    "流式输出的实现原理？",
    "Docker在你项目中的作用？",
    "异步编程有什么好处？项目中哪里用了async/await？",
    "怎么处理LLM的幻觉问题？",
    "如果让你重新设计这个项目，你会怎么改进？",
    "你对AI Agent的未来怎么看？",
    "Multi-Agent系统中如何处理Agent间的冲突？",
    "Prompt注入攻击怎么防御？",
    "如何评估RAG系统的检索质量？",
    "Function Calling的工作原理是什么？",
    "KV Cache如何优化推理性能？",
    "如何在生产环境中监控Agent的行为？",
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
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 24, bold: true, font: "Microsoft YaHei", color: "555555" },
          paragraph: { spacing: { before: 180, after: 120 }, outlineLevel: 2 } },
      ]
    },
    numbering: {
      config: [
        { reference: "bullets", levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        ]},
        { reference: "numbers", levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
        ]},
        { reference: "faq_numbers", levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 720, hanging: 360 } } } },
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
            children: [new TextRun({ text: "AI Agent 面试知识手册 v2", font: "Microsoft YaHei", size: 16, color: "999999" })]
          })]
        })
      },
      footers: {
        default: new Footer({
          children: [new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({ text: "第 ", font: "Microsoft YaHei", size: 16 }),
              new TextRun({ children: [PageNumber.CURRENT], font: "Microsoft YaHei", size: 16 }),
              new TextRun({ text: " 页", font: "Microsoft YaHei", size: 16 })
            ]
          })]
        })
      },
      children: allChildren
    }]
  });

  const buffer = await Packer.toBuffer(doc);
  const outPath = "D:\\python\\AI_Projects\\AI_Agent面试知识手册_v2.docx";
  fs.writeFileSync(outPath, buffer);
  console.log("文档已生成: " + outPath);
  console.log("文件大小: " + (buffer.length / 1024).toFixed(1) + " KB");
}

generate().catch(e => { console.error("生成失败:", e.message); process.exit(1); });
