"""Output management module."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

from .config import config


class OutputManager:
    """Manages output directory structure and file generation."""

    def __init__(self):
        """Initialize output manager with configuration."""
        self.output_config = config.get_output_config()

    def create_output_directory(self, base_name: str = None) -> str:
        """Create timestamped output directory.

        Args:
            base_name: Optional base name for directory

        Returns:
            Path to created directory
        """
        if base_name is None:
            pattern = self.output_config.get('directory_pattern', 'arxiv_embodied_ai_{timestamp}')
            timestamp_format = self.output_config.get('timestamp_format', '%Y%m%d_%H%M')
            timestamp = datetime.now().strftime(timestamp_format)
            base_name = pattern.format(timestamp=timestamp)

        output_dir = Path(base_name)
        output_dir.mkdir(exist_ok=True)

        # Create subdirectories
        subdirs = self.output_config.get('subdirectories', {})
        for key, dirname in subdirs.items():
            (output_dir / dirname).mkdir(exist_ok=True)

        print(f"Created output directory: {output_dir}")
        return str(output_dir)

    def generate_summary(self, papers: List[Dict[str, Any]], analyses: List[Dict[str, str]],
                        top_tier_researchers: List[List], senior_researchers: List[List],
                        output_dir: str) -> str:
        """Generate markdown summary of papers with tiered researcher classification.

        Args:
            papers: List of paper metadata
            analyses: List of paper analyses
            top_tier_researchers: List of top tier researcher findings
            senior_researchers: List of senior researcher findings
            output_dir: Output directory

        Returns:
            Path to generated summary file
        """
        summary_format = self.output_config.get('formats.summary', 'markdown')
        if summary_format != 'markdown':
            print(f"Warning: Only markdown format supported, got {summary_format}")

        timestamp = datetime.now().strftime("%Y年%m月%d日")

        # Generate summary content
        summary_lines = [
            f"# ArXiv具身智能论文日报 - {timestamp}",
            "",
            f"本报告汇总了{len(papers)}篇具身智能相关的最新论文。",
            ""
        ]

        # Add researcher highlights with tier classification
        all_top_tier = []
        all_senior = []
        for top_tier in top_tier_researchers:
            all_top_tier.extend(top_tier)
        for seniors in senior_researchers:
            all_senior.extend(seniors)

        if all_top_tier or all_senior:
            summary_lines.extend([
                "## 🏆 知名研究者论文",
                ""
            ])

            # Top tier researchers first
            if all_top_tier:
                summary_lines.extend([
                    "### 🌟 顶尖研究者",
                    ""
                ])

                # Group by affiliation
                by_affiliation = {}
                for name, affiliation in all_top_tier:
                    if affiliation not in by_affiliation:
                        by_affiliation[affiliation] = []
                    by_affiliation[affiliation].append(name)

                for affiliation, researchers in by_affiliation.items():
                    researchers_str = ', '.join([f"**{name}**" for name in researchers])
                    summary_lines.append(f"- 🌟 **{affiliation}**: {researchers_str}")

                summary_lines.append("")

            # Senior researchers second
            if all_senior:
                summary_lines.extend([
                    "### ⭐️ 重要研究者",
                    ""
                ])

                # Group by affiliation
                by_affiliation = {}
                for name, affiliation in all_senior:
                    if affiliation not in by_affiliation:
                        by_affiliation[affiliation] = []
                    by_affiliation[affiliation].append(name)

                for affiliation, researchers in by_affiliation.items():
                    researchers_str = ', '.join(researchers)
                    summary_lines.append(f"- ⭐️ **{affiliation}**: {researchers_str}")

                summary_lines.append("")

        # Sort papers by researcher importance
        paper_data = list(zip(papers, analyses, top_tier_researchers, senior_researchers))

        # Sort function: top tier first, then senior, then others
        def paper_importance(item):
            _, _, top_tier, senior = item
            if top_tier:  # Has top tier researchers
                return 0
            elif senior:  # Has senior researchers
                return 1
            else:  # No notable researchers
                return 2

        sorted_paper_data = sorted(paper_data, key=paper_importance)

        # Add paper summaries
        summary_lines.extend([
            "## 📚 论文详情",
            ""
        ])

        include_images = self.output_config.get('formats.include_images', True)

        for i, (paper, analysis, top_tier, senior) in enumerate(sorted_paper_data, 1):
            # Paper header
            title = paper.get('title', 'Untitled')
            arxiv_id = paper.get('id', 'unknown')
            all_authors = paper.get('authors', [])
            authors = self._highlight_famous_researchers(all_authors, top_tier, senior)  # Highlight famous researchers with tiers

            summary_lines.extend([
                f"### {i}. {title}",
                "",
                f"**ArXiv ID**: {arxiv_id}",
                f"**作者**: {authors}",
                "",
                f"**链接**: [PDF]({paper.get('pdf_url', '')}) | [Abstract]({paper.get('abs_url', '')})",
                ""
            ])

            # Add original abstract
            abstract = paper.get('summary', '')
            if abstract:
                summary_lines.extend([
                    "#### 📄 原文摘要",
                    "",
                    abstract,
                    ""
                ])

            # Add translated abstract
            translation_file = Path(output_dir) / "translations" / f"{arxiv_id}_translation.txt"
            if translation_file.exists():
                try:
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        translation_content = f.read().strip()

                    # Extract Chinese abstract from translation file
                    if "摘要:" in translation_content:
                        chinese_abstract = translation_content.split("摘要:")[1].strip()
                        summary_lines.extend([
                            "#### 🌐 中文摘要",
                            "",
                            chinese_abstract,
                            ""
                        ])
                except Exception as e:
                    print(f"Failed to read translation for {arxiv_id}: {e}")

            # Add core architecture section with images
            if include_images:
                images_dir = Path(output_dir) / "images" / arxiv_id
                if images_dir.exists():
                    image_files = list(images_dir.glob("*.png"))
                    if image_files:
                        # Sort images by size (larger images likely more important)
                        image_info = []
                        for img_path in image_files:
                            try:
                                file_size = img_path.stat().st_size
                                image_info.append((img_path, file_size))
                            except:
                                image_info.append((img_path, 0))

                        # Sort by file size descending and take top 3
                        image_info.sort(key=lambda x: x[1], reverse=True)
                        top_images = [img[0] for img in image_info[:3]]

                        summary_lines.extend([
                            "#### 🏗️ 核心架构",
                            "",
                            "以下为论文中体现核心架构的关键图表：",
                            ""
                        ])

                        for idx, img_path in enumerate(top_images, 1):
                            rel_path = img_path.relative_to(Path(output_dir))
                            img_name = img_path.stem.replace(f"{arxiv_id}_", "").replace("_", " ").title()
                            summary_lines.extend([
                                f"**图 {idx}: {img_name}**",
                                "",
                                f"![{img_name}]({rel_path})",
                                ""
                            ])

            summary_lines.extend([
                "---",
                ""
            ])

        # Write overall summary file
        summary_content = '\n'.join(summary_lines)
        summary_file = Path(output_dir) / "summary.md"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary_content)

        print(f"Generated summary: {summary_file}")

        # Generate individual paper summaries
        self._generate_individual_summaries(sorted_paper_data, output_dir)

        return str(summary_file)

    def get_papers_dir(self, output_dir: str) -> str:
        """Get papers subdirectory path."""
        subdir = self.output_config.get('subdirectories.papers', 'papers')
        return str(Path(output_dir) / subdir)

    def get_images_dir(self, output_dir: str) -> str:
        """Get images subdirectory path."""
        subdir = self.output_config.get('subdirectories.images', 'images')
        return str(Path(output_dir) / subdir)

    def get_summaries_dir(self, output_dir: str) -> str:
        """Get summaries subdirectory path."""
        subdir = self.output_config.get('subdirectories.summaries', 'summaries')
        return str(Path(output_dir) / subdir)

    def get_translations_dir(self, output_dir: str) -> str:
        """Get translations subdirectory path."""
        subdir = self.output_config.get('subdirectories.translations', 'translations')
        return str(Path(output_dir) / subdir)

    def _highlight_famous_researchers(self, all_authors: List[str],
                                     top_tier_found: List[Tuple[str, str]],
                                     senior_found: List[Tuple[str, str]]) -> str:
        """Highlight famous researchers in the author list with tier indicators.

        Args:
            all_authors: List of all authors
            top_tier_found: List of found top tier researchers
            senior_found: List of found senior researchers

        Returns:
            Formatted author string with highlighted famous researchers
        """
        # Create lookup dictionaries for faster matching
        top_tier_dict = {name: affiliation for name, affiliation in top_tier_found}
        senior_dict = {name: affiliation for name, affiliation in senior_found}

        all_researchers = {**config.get('top_tier_researchers', {}), **config.get('senior_researchers', {})}

        highlighted_authors = []
        for author in all_authors:
            # Check if this author is a famous researcher
            found_in_top_tier = None
            found_in_senior = None

            # Look for exact matches in found researchers
            for name in top_tier_dict:
                if self._name_match_simple(author, name):
                    found_in_top_tier = (name, top_tier_dict[name])
                    break

            if not found_in_top_tier:
                for name in senior_dict:
                    if self._name_match_simple(author, name):
                        found_in_senior = (name, senior_dict[name])
                        break

            # Highlight based on tier
            if found_in_top_tier:
                name, affiliation = found_in_top_tier
                highlighted_authors.append(f"🌟 **{name}** ({affiliation})")
            elif found_in_senior:
                name, affiliation = found_in_senior
                highlighted_authors.append(f"⭐️ **{name}** ({affiliation})")
            else:
                highlighted_authors.append(author)

        return ', '.join(highlighted_authors)

    def _name_match_simple(self, author: str, target_name: str) -> bool:
        """Simple name matching for highlighting."""
        author_parts = author.strip().split()
        target_parts = target_name.strip().split()

        if len(author_parts) >= 2 and len(target_parts) >= 2:
            # Check last name and first name initial
            if (author_parts[-1].lower() == target_parts[-1].lower() and
                author_parts[0][0].lower() == target_parts[0][0].lower()):
                return True

        return False

    def _generate_individual_summaries(self, sorted_paper_data: List[Tuple], output_dir: str):
        """Generate individual summary file for each paper.

        Args:
            sorted_paper_data: List of (paper, analysis, top_tier, senior) tuples
            output_dir: Output directory
        """
        summaries_dir = self.get_summaries_dir(output_dir)

        for paper, analysis, top_tier, senior in sorted_paper_data:
            arxiv_id = paper.get('id', 'unknown')
            title = paper.get('title', 'Untitled')
            all_authors = paper.get('authors', [])
            authors = self._highlight_famous_researchers(all_authors, top_tier, senior)

            # Create individual summary content
            summary_lines = [
                f"# {title}",
                "",
                f"**ArXiv ID**: {arxiv_id}",
                f"**作者**: {authors}",
                "",
                f"**链接**: [PDF]({paper.get('pdf_url', '')}) | [Abstract]({paper.get('abs_url', '')})",
                ""
            ]

            # Add original abstract
            abstract = paper.get('summary', '')
            if abstract:
                summary_lines.extend([
                    "## 📄 原文摘要",
                    "",
                    abstract,
                    ""
                ])

            # Add Chinese translation
            translation_file = Path(output_dir) / "translations" / f"{arxiv_id}_translation.txt"
            if translation_file.exists():
                try:
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        translation_content = f.read().strip()

                    if "摘要:" in translation_content:
                        chinese_abstract = translation_content.split("摘要:")[1].strip()
                        summary_lines.extend([
                            "## 🌐 中文摘要",
                            "",
                            chinese_abstract,
                            ""
                        ])
                except Exception as e:
                    print(f"Warning: Failed to read translation for {arxiv_id}: {e}")

            # Add images section
            include_images = self.output_config.get('formats.include_images', True)
            if include_images:
                images_dir = Path(output_dir) / "images" / arxiv_id
                if images_dir.exists():
                    image_files = list(images_dir.glob("*.png"))
                    if image_files:
                        # Sort images by size (larger images likely more important)
                        image_info = []
                        for img_path in image_files:
                            try:
                                file_size = img_path.stat().st_size
                                image_info.append((img_path, file_size))
                            except:
                                image_info.append((img_path, 0))

                        # Sort by file size descending and take top 3
                        image_info.sort(key=lambda x: x[1], reverse=True)
                        top_images = [img[0] for img in image_info[:3]]

                        summary_lines.extend([
                            "## 🏗️ 核心架构",
                            "",
                            "以下为论文中体现核心架构的关键图表：",
                            ""
                        ])

                        for idx, img_path in enumerate(top_images, 1):
                            rel_path = img_path.relative_to(Path(output_dir))
                            img_name = img_path.stem.replace(f"{arxiv_id}_", "").replace("_", " ").title()
                            summary_lines.extend([
                                f"**图 {idx}: {img_name}**",
                                "",
                                f"![{img_name}]({rel_path})",
                                ""
                            ])

            # Write individual summary file
            filename_pattern = self.output_config.get('file_naming.summary_pattern', '{arxiv_id}_summary.md')
            filename = filename_pattern.format(arxiv_id=arxiv_id)
            individual_summary_path = Path(summaries_dir) / filename

            individual_content = '\n'.join(summary_lines)
            with open(individual_summary_path, 'w', encoding='utf-8') as f:
                f.write(individual_content)

            print(f"Generated individual summary: {individual_summary_path}")