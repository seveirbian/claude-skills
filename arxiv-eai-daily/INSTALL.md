# ArXiv EAI Daily - 安装指南

## 项目结构

```
arxiv-eai-daily/
├── SKILL.md            # Claude Code Skill配置
├── INSTALL.md          # 安装指南（本文件）
├── main.py             # 主程序入口
├── config.yaml         # 配置文件
├── pyproject.toml      # 项目依赖定义
├── requirements.txt    # pip依赖列表
├── uv.lock             # uv锁定文件
└── core/               # 核心模块
    ├── __init__.py
    ├── arxiv_client.py     # ArXiv API抓取
    ├── pdf_processor.py    # PDF下载与图像提取
    ├── translator.py       # 摘要翻译
    ├── analyzer.py         # 论文分析
    ├── claude_analyzer.py  # Claude AI深度分析
    ├── output_manager.py   # 输出管理
    └── config.py           # 配置加载
```

## 系统要求

- **Python**: 3.8 或更高版本
- **uv**: 推荐用于环境管理（[安装uv](https://docs.astral.sh/uv/getting-started/installation/)）
- **ANTHROPIC_API_KEY**: Claude AI分析功能需要（未设置时自动降级跳过）
- **网络连接**: 用于访问ArXiv和翻译服务
- **存储空间**: 至少1GB（用于PDF和图像缓存）

## 安装

### 使用 uv（推荐）

```bash
cd ~/.claude/skills/arxiv-eai-daily
uv sync
```

### 使用 pip

```bash
cd ~/.claude/skills/arxiv-eai-daily
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml` 自定义行为：

```yaml
# 搜索配置
arxiv:
  default_days_back: 1      # 抓取最近几天的论文
  default_max_results: 50   # 最多抓取论文数

# Claude AI分析配置
claude:
  model: "claude-opus-4-6"  # 分析使用的模型
  enabled: true             # 自动检测API Key，未设置时降级

# 翻译配置
translation:
  enabled: true
  target_language: "zh-CN"
```

## 使用方法

### 通过 Claude Code Skill（推荐）

在Claude Code中直接使用 `/arxiv-eai-daily`

### 命令行直接运行

```bash
cd ~/.claude/skills/arxiv-eai-daily

# 抓取今日论文（默认最多50篇）
uv run python main.py

# 抓取最近3天的论文
uv run python main.py --days-back 3

# 最多分析20篇
uv run python main.py --max-results 20

# 仅下载PDF，不分析
uv run python main.py --download-only
```

## 输出说明

每次运行会在当前目录生成带时间戳的输出文件夹：

```
arxiv_eai_daily_YYYYMMDD_HHMM/
├── summary.md          # 所有论文汇总报告（主要查看文件）
├── papers/             # 下载的PDF文件
├── images/             # 从PDF提取的架构图
├── summaries/          # 各论文单独的分析报告
└── analyses/           # Claude AI深度分析缓存
```

## 故障排除

### Claude分析不工作
确保设置了API Key：
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### PDF下载失败
检查ArXiv访问：
```bash
curl -I http://export.arxiv.org/api/query
```

### 翻译服务不可用
翻译使用Google/Microsoft/MyMemory多个备用服务，网络问题会自动降级，不影响核心功能。

### PyMuPDF安装失败
```bash
# macOS
brew install mupdf-tools

# Ubuntu/Debian
sudo apt-get install libmupdf-dev
```
