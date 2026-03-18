#!/usr/bin/env python3
"""
ArXiv Embodied AI Summarizer - Main Application
Refactored modular version with YAML configuration
"""

import argparse
import sys
from typing import List, Dict, Any

from core.arxiv_client import ArXivClient
from core.translator import TranslationService
from core.pdf_processor import PDFProcessor
from core.analyzer import PaperAnalyzer
from core.output_manager import OutputManager


class ArXivSummarizer:
    """Main application class for ArXiv paper summarization."""

    def __init__(self):
        """Initialize summarizer with all components."""
        self.arxiv_client = ArXivClient()
        self.translator = TranslationService()
        self.pdf_processor = PDFProcessor()
        self.analyzer = PaperAnalyzer()
        self.output_manager = OutputManager()

    def run(self, days_back: int = None, max_results: int = None,
            output_dir: str = None, download_only: bool = False) -> str:
        """Run the complete summarization pipeline.

        Args:
            days_back: Number of days back to search
            max_results: Maximum number of papers
            output_dir: Output directory (auto-generated if None)
            download_only: Only download PDFs without processing

        Returns:
            Path to output directory
        """
        print("🚀 Starting ArXiv Embodied AI Summarizer")

        # Create output directory
        if output_dir is None:
            output_dir = self.output_manager.create_output_directory()
        else:
            output_dir = self.output_manager.create_output_directory(output_dir)

        # Step 1: Fetch papers from ArXiv
        print("\n📥 Fetching papers from ArXiv...")
        papers = self.arxiv_client.fetch_papers(days_back, max_results)

        if not papers:
            print("❌ No papers found")
            return output_dir

        print(f"✅ Found {len(papers)} papers")

        # Step 2: Download PDFs
        print("\n📄 Downloading PDFs...")
        papers_dir = self.output_manager.get_papers_dir(output_dir)
        pdf_paths = []

        for paper in papers:
            pdf_path = self.pdf_processor.download_pdf(paper, papers_dir)
            if pdf_path:
                pdf_paths.append(pdf_path)
                paper['local_pdf_path'] = pdf_path

        print(f"✅ Downloaded {len(pdf_paths)} PDFs")

        if download_only:
            print("📁 Download-only mode completed")
            return output_dir

        # Step 3: Analyze papers
        print("\n🔍 Analyzing papers...")
        analyses = []
        senior_researchers_list = []

        for paper in papers:
            # Analyze paper content
            analysis = self.analyzer.analyze_paper(paper)
            analyses.append(analysis)

            # Identify senior researchers
            senior_researchers = self.analyzer.identify_senior_researchers(paper.get('authors', []))
            senior_researchers_list.append(senior_researchers)

            if senior_researchers:
                researchers_str = ', '.join([name for name, _ in senior_researchers])
                print(f"  🌟 Senior researchers found in '{paper['title'][:50]}...': {researchers_str}")

        # Step 4: Extract images
        print("\n🖼️  Extracting images...")
        images_dir = self.output_manager.get_images_dir(output_dir)

        for paper in papers:
            if 'local_pdf_path' in paper:
                try:
                    extracted_images = self.pdf_processor.extract_images(
                        paper['local_pdf_path'], paper['id'], images_dir
                    )
                    paper['extracted_images'] = extracted_images
                    if extracted_images:
                        print(f"  ✅ Extracted {len(extracted_images)} images from {paper['id']}")
                except Exception as e:
                    print(f"  ❌ Failed to extract images from {paper['id']}: {e}")

        # Step 5: Translate summaries first
        from core.config import config
        if config.get('translation.enabled', True):
            print("\n🌐 Translating content...")
            self._translate_summaries(papers, analyses, output_dir)

        # Step 6: Generate summary (after translations are available)
        print("\n📝 Generating summary...")
        summary_path = self.output_manager.generate_summary(
            papers, analyses, senior_researchers_list, output_dir
        )

        print(f"\n🎉 Completed! Output saved to: {output_dir}")
        print(f"📋 Summary available at: {summary_path}")

        return output_dir

    def _translate_summaries(self, papers: List[Dict[str, Any]],
                           analyses: List[Dict[str, str]], output_dir: str):
        """Translate paper summaries to Chinese."""
        translations_dir = self.output_manager.get_translations_dir(output_dir)

        for paper, analysis in zip(papers, analyses):
            try:
                # Translate title and summary
                title_zh = self.translator.translate(paper.get('title', ''))
                summary_zh = self.translator.translate(paper.get('summary', ''))

                # Save translation
                translation_content = f"标题: {title_zh}\n\n摘要: {summary_zh}\n"

                translation_file = f"{translations_dir}/{paper['id']}_translation.txt"
                with open(translation_file, 'w', encoding='utf-8') as f:
                    f.write(translation_content)

                print(f"  ✅ Translated {paper['id']}")

            except Exception as e:
                print(f"  ❌ Failed to translate {paper['id']}: {e}")


def main():
    """Command line interface."""
    # Import config here to avoid import issues
    from core.config import config

    parser = argparse.ArgumentParser(
        description="ArXiv Embodied AI Summarizer - Fetch and analyze latest papers"
    )

    parser.add_argument(
        '--days-back', '-d',
        type=int,
        default=None,
        help=f"Number of days back to search (default: {config.get('arxiv.default_days_back', 1)})"
    )

    parser.add_argument(
        '--max-results', '-m',
        type=int,
        default=None,
        help=f"Maximum number of papers (default: {config.get('arxiv.default_max_results', 50)})"
    )

    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        default=None,
        help="Output directory (auto-generated if not specified)"
    )

    parser.add_argument(
        '--download-only',
        action='store_true',
        help="Only download PDFs without processing"
    )

    parser.add_argument(
        '--config',
        type=str,
        default=None,
        help="Path to configuration file"
    )

    args = parser.parse_args()

    try:
        # Initialize configuration if custom path provided
        if args.config:
            from core.config import Config, config as default_config
            config = Config(args.config)
        else:
            from core.config import config

        # Initialize and run summarizer
        summarizer = ArXivSummarizer()
        output_dir = summarizer.run(
            days_back=args.days_back,
            max_results=args.max_results,
            output_dir=args.output_dir,
            download_only=args.download_only
        )

        print(f"\n📁 Results saved to: {output_dir}")

    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()