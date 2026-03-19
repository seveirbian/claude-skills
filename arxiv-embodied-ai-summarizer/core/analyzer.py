"""Paper analysis module."""

import re
from typing import Dict, List, Tuple, Any

from .config import config


class PaperAnalyzer:
    """Analyzes papers to extract key information and identify senior researchers."""

    def __init__(self):
        """Initialize analyzer with configuration."""
        self.analysis_config = config.get_analysis_config()
        self.paper_config = self.analysis_config.get('paper', {})
        self.keywords = self.analysis_config.get('keywords', {})
        self.senior_researchers = config.get_senior_researchers()
        self.top_tier_researchers = config.get_top_tier_researchers()

    def analyze_paper(self, paper: Dict[str, Any]) -> Dict[str, str]:
        """Analyze a paper and extract key information.

        Args:
            paper: Paper metadata dict

        Returns:
            Dict with extracted problem, method, highlights
        """
        summary = paper.get('summary', '')
        title = paper.get('title', '')

        analysis = {}

        if self.paper_config.get('extract_problem', True):
            analysis['problem'] = self._extract_problem(summary, title)

        if self.paper_config.get('extract_method', True):
            analysis['method'] = self._extract_method(summary, title)

        if self.paper_config.get('extract_highlights', True):
            analysis['highlights'] = self._extract_highlights(summary, title)

        return analysis

    def identify_senior_researchers(self, authors: List[str]) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """Identify senior researchers from author list with tier classification.

        Args:
            authors: List of author names

        Returns:
            Tuple of (top_tier_authors, senior_authors) - each as list of (author, affiliation) tuples
        """
        top_tier_authors = []
        senior_authors = []

        for author in authors:
            # Check top tier first
            for top_name, affiliation in self.top_tier_researchers.items():
                if self._name_match(author, top_name):
                    top_tier_authors.append((top_name, affiliation))
                    break
            else:
                # If not in top tier, check senior researchers
                for senior_name, affiliation in self.senior_researchers.items():
                    if self._name_match(author, senior_name):
                        senior_authors.append((senior_name, affiliation))
                        break

        return top_tier_authors, senior_authors

    def _name_match(self, author: str, senior_name: str) -> bool:
        """Check if author name matches senior researcher name."""
        # Simple matching: check if last name and first name initial match
        author_parts = author.strip().split()
        senior_parts = senior_name.strip().split()

        if len(author_parts) >= 2 and len(senior_parts) >= 2:
            # Check last name
            if author_parts[-1].lower() != senior_parts[-1].lower():
                return False
            # Check first name initial
            if author_parts[0][0].lower() == senior_parts[0][0].lower():
                return True

        return False

    def _extract_problem(self, summary: str, title: str) -> str:
        """Extract problem/challenge description from paper."""
        text = f"{title}. {summary}"
        problem_indicators = self.keywords.get('problem_indicators', [])

        # Find sentences containing problem indicators
        sentences = re.split(r'[.!?]+', text)
        problem_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in problem_indicators):
                problem_sentences.append(sentence)

        if problem_sentences:
            return '. '.join(problem_sentences[:2])  # Return first 2 relevant sentences
        else:
            # Fallback: return first sentence of summary
            first_sentence = sentences[1] if len(sentences) > 1 else summary[:200]
            return first_sentence.strip()

    def _extract_method(self, summary: str, title: str) -> str:
        """Extract method/approach description from paper."""
        text = f"{title}. {summary}"
        method_indicators = self.keywords.get('method_indicators', [])

        sentences = re.split(r'[.!?]+', text)
        method_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in method_indicators):
                method_sentences.append(sentence)

        if method_sentences:
            return '. '.join(method_sentences[:2])
        else:
            # Fallback: look for technical terms
            technical_sentences = []
            for sentence in sentences:
                if any(term in sentence.lower() for term in ['neural', 'network', 'learning', 'algorithm']):
                    technical_sentences.append(sentence.strip())

            if technical_sentences:
                return '. '.join(technical_sentences[:1])
            else:
                return "方法待详细分析"

    def _extract_highlights(self, summary: str, title: str) -> str:
        """Extract key highlights/contributions from paper."""
        text = f"{title}. {summary}"
        highlight_indicators = self.keywords.get('highlight_indicators', [])

        sentences = re.split(r'[.!?]+', text)
        highlight_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            sentence_lower = sentence.lower()
            if any(indicator in sentence_lower for indicator in highlight_indicators):
                highlight_sentences.append(sentence)

        if highlight_sentences:
            return '. '.join(highlight_sentences[:2])
        else:
            # Look for quantitative results
            result_sentences = []
            for sentence in sentences:
                if re.search(r'\d+(\.\d+)?%|\d+x|state-of-the-art|outperform|improve', sentence.lower()):
                    result_sentences.append(sentence.strip())

            if result_sentences:
                return '. '.join(result_sentences[:1])
            else:
                return "主要贡献待详细分析"