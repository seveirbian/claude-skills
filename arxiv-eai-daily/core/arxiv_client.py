"""ArXiv API client for fetching papers."""

import requests
import feedparser
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from urllib.parse import quote

from .config import config


class ArXivClient:
    """Client for interacting with ArXiv API."""

    def __init__(self):
        """Initialize ArXiv client with configuration."""
        self.arxiv_config = config.get_arxiv_config()
        self.base_url = self.arxiv_config.get('base_url', 'http://export.arxiv.org/api/query')
        self.rate_limit_delay = self.arxiv_config.get('rate_limit_delay', 1.0)

    def build_query(self, days_back: int = None, max_results: int = None) -> str:
        """Build ArXiv search query based on configuration."""
        if days_back is None:
            days_back = self.arxiv_config.get('default_days_back', 1)
        if max_results is None:
            max_results = self.arxiv_config.get('default_max_results', 50)

        # Build category query
        categories = self.arxiv_config.get('search_categories', [])
        cat_query = ' OR '.join([f'cat:{cat}' for cat in categories])

        # Build terms query
        terms = self.arxiv_config.get('search_terms', [])
        # Use titles and abstracts for term search
        term_queries = []
        for term in terms:
            term_queries.append(f'ti:"{term}" OR abs:"{term}"')
        terms_query = ' OR '.join(term_queries)

        # Combine queries
        if terms_query:
            query = f'({cat_query}) AND ({terms_query})'
        else:
            query = cat_query

        # Add date filter
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        date_filter = f'submittedDate:[{start_date.strftime("%Y%m%d")}0000 TO {end_date.strftime("%Y%m%d")}2359]'

        final_query = f'({query}) AND {date_filter}'

        return f'{self.base_url}?search_query={quote(final_query)}&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending'

    def fetch_papers(self, days_back: int = None, max_results: int = None) -> List[Dict[str, Any]]:
        """Fetch papers from ArXiv."""
        query_url = self.build_query(days_back, max_results)

        try:
            print(f"Fetching papers from ArXiv...")
            print(f"Query URL: {query_url}")

            # Add rate limiting
            time.sleep(self.rate_limit_delay)

            # Parse feed
            feed = feedparser.parse(query_url)

            if feed.bozo:
                print(f"Warning: Feed parsing issues: {feed.bozo_exception}")

            papers = []
            for entry in feed.entries:
                paper = self._parse_entry(entry)
                papers.append(paper)

            print(f"Found {len(papers)} papers")
            return papers

        except Exception as e:
            print(f"Error fetching papers: {e}")
            return []

    def _parse_entry(self, entry) -> Dict[str, Any]:
        """Parse a single ArXiv entry."""
        # Extract arXiv ID from the link
        arxiv_id = entry.id.split('/')[-1]

        # Parse authors
        authors = []
        if hasattr(entry, 'authors'):
            for author in entry.authors:
                if hasattr(author, 'name'):
                    authors.append(author.name)
        elif hasattr(entry, 'author'):
            authors.append(entry.author)

        # Parse categories
        categories = []
        if hasattr(entry, 'tags'):
            for tag in entry.tags:
                if hasattr(tag, 'term'):
                    categories.append(tag.term)

        # Extract PDF URL
        pdf_url = None
        if hasattr(entry, 'links'):
            for link in entry.links:
                if hasattr(link, 'type') and link.type == 'application/pdf':
                    pdf_url = link.href
                    break

        if not pdf_url:
            pdf_url = f"http://arxiv.org/pdf/{arxiv_id}.pdf"

        return {
            'id': arxiv_id,
            'title': entry.title.replace('\n', ' ').strip() if hasattr(entry, 'title') else '',
            'authors': authors,
            'summary': entry.summary.replace('\n', ' ').strip() if hasattr(entry, 'summary') else '',
            'categories': categories,
            'published': entry.published if hasattr(entry, 'published') else '',
            'updated': entry.updated if hasattr(entry, 'updated') else '',
            'pdf_url': pdf_url,
            'abs_url': entry.link if hasattr(entry, 'link') else f"http://arxiv.org/abs/{arxiv_id}"
        }