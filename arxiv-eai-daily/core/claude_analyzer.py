"""Claude AI-powered paper analysis module."""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

from .config import config


class ClaudeAnalyzer:
    """Uses Claude API for deep paper analysis and Chinese translation."""

    def __init__(self):
        """Initialize Claude analyzer."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.enabled = bool(api_key)
        self.client = None

        if self.enabled:
            try:
                import anthropic
                self.client = anthropic.Anthropic(api_key=api_key)
            except ImportError:
                print("⚠️  anthropic package not installed. Run: uv add anthropic")
                self.enabled = False

        self.claude_config = config.get('claude', {})
        self.model = self.claude_config.get('model', 'claude-opus-4-6')
        self.max_tokens = self.claude_config.get('max_tokens', 2048)

    def analyze_paper(self, paper: Dict[str, Any]) -> Optional[Dict]:
        """Deep analysis of a paper using Claude API.

        Args:
            paper: Paper metadata dict with title, summary, authors, etc.

        Returns:
            Dict with structured Chinese analysis, or None if unavailable.
        """
        if not self.enabled or self.client is None:
            return None

        title = paper.get('title', '')
        abstract = paper.get('summary', '')
        authors = ', '.join(paper.get('authors', [])[:5])
        if len(paper.get('authors', [])) > 5:
            authors += ' et al.'

        prompt = f"""请对以下具身AI/机器人学习论文进行深度专业分析，严格按JSON格式输出：

论文标题：{title}
作者：{authors}
摘要：{abstract}

请返回如下JSON（只输出JSON，不要有其他文字）：
{{
  "title_zh": "准确的中文标题翻译",
  "abstract_zh": "完整的中文摘要翻译（保留技术术语的英文原文，如 VLM、RL、sim-to-real 等）",
  "core_problem": "该论文解决的核心问题（1-2句话，中文）",
  "method": "主要技术方法和系统架构（2-3句话，中文）",
  "contribution": "主要学术贡献和创新点（2-3句话，中文）",
  "experiment_highlights": "关键实验结果和性能指标（1-2句话，中文，如无实验数据可留空字符串）",
  "keywords_zh": ["关键词1", "关键词2", "关键词3"],
  "significance": "在具身AI/机器人学习领域的重要性（1句话，中文）",
  "relevance_score": 基于具身AI相关度的0-10评分（整数，10=直接相关，5=部分相关，0=不相关）
}}"""

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )

            content = message.content[0].text
            # Extract JSON from response
            start = content.find('{')
            end = content.rfind('}') + 1
            if start >= 0 and end > start:
                result = json.loads(content[start:end])
                return result

        except Exception as e:
            print(f"  ⚠️  Claude analysis failed for {paper.get('id', 'unknown')}: {e}")

        return None

    def analyze_papers_batch(self, papers: list, analyses_dir: str) -> Dict[str, Dict]:
        """Analyze multiple papers and save results to disk.

        Args:
            papers: List of paper metadata dicts
            analyses_dir: Directory to save analysis JSON files

        Returns:
            Dict mapping arxiv_id to Claude analysis result
        """
        if not self.enabled:
            print("  ℹ️  Claude API not available (ANTHROPIC_API_KEY not set). Skipping AI analysis.")
            return {}

        Path(analyses_dir).mkdir(parents=True, exist_ok=True)
        results = {}

        for paper in papers:
            arxiv_id = paper.get('id', 'unknown')
            analysis_file = Path(analyses_dir) / f"{arxiv_id}_analysis.json"

            # Load cached analysis if exists
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        results[arxiv_id] = json.load(f)
                    print(f"  ✅ Loaded cached Claude analysis for {arxiv_id}")
                    continue
                except Exception:
                    pass

            print(f"  🤖 Analyzing {arxiv_id} with Claude ({self.model})...")
            result = self.analyze_paper(paper)

            if result:
                results[arxiv_id] = result
                with open(analysis_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                score = result.get('relevance_score', '?')
                print(f"  ✅ Claude analysis complete for {arxiv_id} (relevance: {score}/10)")
            else:
                print(f"  ⚠️  Claude analysis unavailable for {arxiv_id}")

        return results
