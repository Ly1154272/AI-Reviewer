# AI Reviewer 使用指南

## 概述

AI Reviewer 是一个智能代码审查系统，结合 RAG（检索增强生成）技术和 AI 能力，支持：

- 基于 Git 代码仓库的自动化代码审查
- 支持全量和增量审查模式
- 接收外部代码扫描工具（P3C、SpotBugs 等）的结果进行误报分析
- 根据自然语言规范文档进行代码审查
- 生成统一的审查报告

## 安装

### 环境要求

- Python 3.10+
- Git

### 安装步骤

> **注意**：以下命令使用 `python` 和 `pip`。如果在您的系统上找不到命令，请尝试使用 `python3` 和 `pip3`。

```bash
# 克隆项目（如果需要）
git clone <your-repo-url>
cd AI-Reviewer

# 创建虚拟环境（推荐）
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# 安装依赖
pip install -e .
```

### 环境变量

在运行前，需要设置以下环境变量：

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `OPENAI_API_KEY` | OpenAI API Key | 是（除非使用其他 AI 提供商） |
| `GIT_TOKEN` | Git 访问令牌 | 是 |
| `AI_PROVIDER` | AI 提供商 (openai/claude/azure) | 否 |
| `AI_MODEL` | AI 模型 | 否 |

## 快速开始

### 1. 构建规范文档索引

首次使用前，需要将规范文档向量化并建立索引：

```bash
python ai_reviewer.py build-index \
  --rule-doc ./examples/docs/coding_standards.md \
  --rule-doc ./examples/docs/security_guidelines.md
```

这将在 `./vector_store` 目录创建向量索引。

### 2. 运行代码审查

基本用法：

```bash
python ai_reviewer.py review \
  --git-url https://github.com/your-org/your-repo \
  --git-token your-github-token \
  --mode incremental
```

完整参数示例：

```bash
python ai_reviewer.py review \
  --git-url https://github.com/your-org/your-repo \
  --git-token your-github-token \
  --branch main \
  --mode incremental \
  --scan-result pmd.xml,spotbugs.xml \
  --rule-doc ./examples/docs/coding_standards.md \
  --rule-doc ./examples/docs/security_guidelines.md \
  --output review_report.json \
  --format json \
  --ai-provider openai \
  --ai-model gpt-4
```

### 3. 查看报告

审查完成后，会生成报告文件。默认输出格式为 JSON：

```bash
# 查看报告内容
cat review_report.json
```

或使用 HTML 格式：

```bash
python ai_reviewer.py review \
  ... \
  --format html \
  --output review_report.html
```

## 命令详解

### review 命令

运行代码审查。

```bash
python ai_reviewer.py review [OPTIONS]
```

**参数选项：**

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--git-url` | `-u` | Git 仓库 URL | 必需 |
| `--git-token` | `-t` | Git 访问令牌 | 环境变量 |
| `--branch` | `-b` | 审查分支 | main |
| `--mode` | `-m` | 审查模式 (full/incremental) | incremental |
| `--scan-result` | `-s` | 扫描结果文件（可多次使用） | 无 |
| `--rule-doc` | `-r` | 规范文档文件或文件夹（可多次使用，支持 .md/.docx/.pdf/.txt） | 无 |
| `--output` | `-o` | 输出报告路径 | review_report.json |
| `--format` | `-f` | 报告格式 (json/html/markdown) | json |
| `--ai-provider` | - | AI 提供商 (openai/claude/azure) | openai |
| `--ai-model` | - | AI 模型 | gpt-4 |
| `--ai-api-key` | - | AI API Key | 环境变量 |
| `--no-rag` | - | 禁用 RAG | false |
| `--vector-store` | - | 向量存储目录 | ./vector_store |

### build-index 命令

构建 RAG 索引。

```bash
python ai_reviewer.py build-index [OPTIONS]
```

**参数选项：**

| 参数 | 简写 | 说明 | 默认值 |
|------|------|------|--------|
| `--rule-doc` | `-r` | 规范文档文件或文件夹（必需，可多次使用，支持 .md/.docx/.pdf/.txt） | 无 |
| `--vector-store` | - | 向量存储目录 | ./vector_store |
| `--embedding-model` | - | Embedding 模型 | text-embedding-ada-002 |

## 配置说明

### 配置文件

除了命令行参数，也可以使用 YAML 配置文件：

```yaml
# config.yaml
git:
  url: "https://github.com/your-org/your-repo"
  token: "your-token"
  branch: "main"
  review_mode: "incremental"

scanner:
  scan_results:
    - "pmd.xml"
    - "spotbugs.xml"

rag:
  enabled: true
  vector_store_dir: "./vector_store"
  embedding_model: "text-embedding-ada-002"

ai:
  provider: "openai"
  model: "gpt-4"

report:
  output_format: "json"
  output_path: "./review_report.json"

rule_docs:
  - "./docs/coding_standards.md"
```

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `GIT_URL` | Git 仓库 URL | - |
| `GIT_TOKEN` | Git 访问令牌 | - |
| `GIT_BRANCH` | 审查分支 | main |
| `REVIEW_MODE` | 审查模式 | incremental |
| `SCAN_RESULTS` | 扫描结果文件（逗号分隔） | - |
| `RAG_ENABLED` | 是否启用 RAG | true |
| `VECTOR_STORE_DIR` | 向量存储目录 | ./vector_store |
| `EMBEDDING_MODEL` | Embedding 模型 | text-embedding-ada-002 |
| `AI_PROVIDER` | AI 提供商 | openai |
| `AI_MODEL` | AI 模型 | gpt-4 |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `ANTHROPIC_API_KEY` | Claude API Key | - |
| `REPORT_FORMAT` | 报告格式 | json |
| `REPORT_OUTPUT` | 报告输出路径 | review_report.json |
| `RULE_DOCS` | 规范文档（逗号分隔） | - |

## 审查模式

### 增量审查 (Incremental)

只审查自上次提交以来变更的代码。适用于 PR/MR 审查场景。

```bash
python ai_reviewer.py review \
  --git-url https://github.com/xxx/yyy \
  --mode incremental
```

### 全量审查 (Full)

审查仓库中的所有代码。适用于定时全量扫描。

```bash
python ai_reviewer.py review \
  --git-url https://github.com/xxx/yyy \
  --mode full \
  --branch main
```

## 集成 CI/CD

### GitHub Actions

参考 `examples/.github/workflows/ai-review.yml`：

```yaml
name: AI Code Review

on:
  pull_request:
    branches: [main, develop]

jobs:
  ai-review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -e .
      
      - name: Run AI Review
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python ai_reviewer.py review \
            --git-url "https://github.com/${{ github.repository }}" \
            --git-token "${{ secrets.GITHUB_TOKEN }}" \
            --branch "${{ github.base_ref }}" \
            --rule-doc "./docs/standards.md" \
            --output review_report.json
```

### GitLab CI

```yaml
ai-review:
  stage: test
  image: python:3.10
  before_script:
    - pip install -e .
  script:
    - python ai_reviewer.py review
      --git-url $CI_REPOSITORY_URL
      --git-token $GIT_TOKEN
      --rule-doc ./docs/standards.md
  artifacts:
    paths:
      - review_report.json
```

## 规范文档格式

支持多种文档格式：

| 格式 | 扩展名 | 说明 |
|------|--------|------|
| Markdown | .md | 推荐格式 |
| Word | .docx | 支持 .docx 格式 |
| PDF | .pdf | 支持 PDF 格式 |
| 纯文本 | .txt | 纯文本格式 |

规范文档支持自然语言编写。例如：

```markdown
# 编码规范

## 命名规范

### 类名
- 必须以 Service、Controller、Repository 结尾
- 使用 UpperCamelCase

### 方法名
- 使用 camelCase
- 应该是动词或动词短语

## 代码风格

### 注释
- 公开方法必须有 Javadoc 注释
- 使用注释解释为什么，而不是做什么
```

**使用示例：**

```bash
# 支持混合使用多种格式
python ai_reviewer.py build-index \
  --rule-doc ./docs/coding_standards.md \
  --rule-doc ./docs/security_guidelines.docx \
  --rule-doc ./docs/company_rules.pdf \
  --rule-doc ./docs/notes.txt

# 支持传入文件夹（自动扫描所有支持的文档格式）
python ai_reviewer.py build-index \
  --rule-doc ./docs

# 混用文件和文件夹
python ai_reviewer.py build-index \
  --rule-doc ./docs/coding_standards.md \
  --rule-doc ./docs/company_rules
```

## 输出报告示例

### JSON 格式

```json
{
  "id": "report-abc123",
  "repository": "https://github.com/xxx/yyy",
  "branch": "main",
  "mode": "incremental",
  "summary": {
    "total_issues": 15,
    "critical": 2,
    "warning": 8,
    "info": 5,
    "false_positives": 3,
    "ai_analyzed": 10
  },
  "issues": [
    {
      "id": "issue-001",
      "source": "p3c",
      "rule_id": "NAMING-001",
      "file": "UserService.java",
      "line": 42,
      "severity": "WARNING",
      "message": "类名应该以 Service 结尾",
      "ai_analysis": {
        "is_false_positive": false,
        "confidence": 0.95,
        "suggestion": "将类名改为 UserService"
      }
    }
  ]
}
```

## 故障排除

### API Key 错误

```
Error: AI API key is required
```

解决：设置环境变量或使用 `--ai-api-key` 参数。

### Git 克隆失败

```
Error: Repository not found
```

解决：检查 Git URL 和 Token 权限是否正确。

### RAG 索引问题

```
Warning: RAG index not found
```

解决：运行 `build-index` 命令重新构建索引。

### 依赖安装问题

```
ImportError: No module named 'xxx'
```

解决：确保已正确安装依赖：`pip install -e .`

## 常见问题

### Q: 支持哪些代码扫描工具？

A: 目前支持 P3C (PMD)、SpotBugs、Checkstyle、SonarQube、ESLint。

### Q: 可以使用其他 AI 提供商吗？

A: 可以，支持 OpenAI、Claude、Azure OpenAI。

### Q: RAG 可以禁用吗？

A: 可以，使用 `--no-rag` 参数禁用。

### Q: 如何更新规范文档索引？

A: 重新运行 `build-index` 命令即可更新索引。

## 目录结构

```
AI-Reviewer/
├── pyproject.toml              # 项目配置
├── ai_reviewer.py              # CLI 入口
├── config/
│   └── config.example.yaml     # 配置示例
├── examples/
│   ├── docs/                  # 规范文档示例
│   └── .github/workflows/      # CI/CD 示例
└── src/
    ├── core/models.py         # 数据模型
    ├── git/client.py         # Git 集成
    ├── scanner/parser.py     # 扫描结果解析
    ├── rag/manager.py        # RAG 模块
    ├── ai/reviewer.py        # AI 审查
    ├── report/generator.py   # 报告生成
    └── cli/main.py           # CLI
```
