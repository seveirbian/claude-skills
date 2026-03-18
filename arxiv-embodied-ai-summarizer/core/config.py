"""Configuration management for ArXiv Embodied AI Summarizer."""

import yaml
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """Configuration manager that loads and provides access to settings."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration.

        Args:
            config_path: Path to config file. If None, looks for config.yaml in current directory.
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config.yaml"

        self._config = self._load_config(config_path)

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML configuration: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.

        Args:
            key: Configuration key in dot notation (e.g., 'arxiv.base_url')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def get_senior_researchers(self) -> Dict[str, str]:
        """Get senior researchers mapping."""
        return self.get('senior_researchers', {})

    def get_arxiv_config(self) -> Dict[str, Any]:
        """Get ArXiv search configuration."""
        return self.get('arxiv', {})

    def get_translation_config(self) -> Dict[str, Any]:
        """Get translation configuration."""
        return self.get('translation', {})

    def get_pdf_config(self) -> Dict[str, Any]:
        """Get PDF processing configuration."""
        return self.get('pdf', {})

    def get_analysis_config(self) -> Dict[str, Any]:
        """Get analysis configuration."""
        return self.get('analysis', {})

    def get_output_config(self) -> Dict[str, Any]:
        """Get output configuration."""
        return self.get('output', {})


# Global configuration instance
config = Config()