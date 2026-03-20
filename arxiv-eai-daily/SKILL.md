---
name: arxiv-eai-daily
description: 抓取并分析ArXiv最新具身AI/机器人学习论文，使用Claude AI生成中文深度总结报告。当用户想了解具身AI、机器人学习的最新论文进展，或者说"看看今天的arxiv"、"有什么新论文"时使用。
argument-hint: "[--days-back N] [--max-results N] [--download-only]"
allowed-tools: Bash
---

# ArXiv EAI Daily

从ArXiv自动抓取具身AI（Embodied AI）和机器人学习领域最新论文，使用Claude AI进行深度分析，生成中文总结报告。

## 执行

```bash
cd "${CLAUDE_SKILL_DIR}" && uv run python main.py $ARGUMENTS
```

## 常用参数

- `--days-back N`：抓取最近N天的论文（默认1天）
- `--max-results N`：最多分析N篇论文（默认50篇）
- `--download-only`：仅下载PDF，不进行分析

## 完成后告知用户

1. 输出目录的完整路径
2. 共分析了多少篇论文
3. 摘要文件在哪里可以查看
