"""
Configuration management for the web scraper.
"""

import os
import json
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ScraperConfig:
    """Configuration settings for the scraper."""
    
    # Rate limiting settings
    requests_per_second: float = 1.0
    burst_size: int = 5
    
    # Request settings
    timeout: int = 30
    max_retries: int = 3
    backoff_factor: float = 2.0
    
    # Circuit breaker settings
    failure_threshold: int = 5
    recovery_timeout: int = 60
    
    # Database settings
    database_path: str = "products.db"
    
    # Scraping settings
    max_pages: int = 10
    max_images_per_product: int = 10
    description_max_length: int = 1000
    
    # Custom headers
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Proxy settings
    proxy_config: Optional[Dict[str, str]] = None
    
    # Site-specific selectors
    product_selectors: Dict[str, Dict[str, str]] = field(default_factory=dict)
    
    @classmethod
    def from_file(cls, config_path: str) -> 'ScraperConfig':
        """Load configuration from JSON file."""
        if not os.path.exists(config_path):
            return cls()
        
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            return cls(**config_data)
        except Exception as e:
            print(f"Error loading config from {config_path}: {e}")
            return cls()
    
    def save_to_file(self, config_path: str) -> bool:
        """Save configuration to JSON file."""
        try:
            config_data = {
                'requests_per_second': self.requests_per_second,
                'burst_size': self.burst_size,
                'timeout': self.timeout,
                'max_retries': self.max_retries,
                'backoff_factor': self.backoff_factor,
                'failure_threshold': self.failure_threshold,
                'recovery_timeout': self.recovery_timeout,
                'database_path': self.database_path,
                'max_pages': self.max_pages,
                'max_images_per_product': self.max_images_per_product,
                'description_max_length': self.description_max_length,
                'custom_headers': self.custom_headers,
                'proxy_config': self.proxy_config,
                'product_selectors': self.product_selectors
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving config to {config_path}: {e}")
            return False
    
    @classmethod
    def from_env(cls) -> 'ScraperConfig':
        """Load configuration from environment variables."""
        config = cls()
        
        # Override with environment variables if they exist
        config.requests_per_second = float(os.getenv('SCRAPER_REQUESTS_PER_SECOND', config.requests_per_second))
        config.burst_size = int(os.getenv('SCRAPER_BURST_SIZE', config.burst_size))
        config.timeout = int(os.getenv('SCRAPER_TIMEOUT', config.timeout))
        config.max_retries = int(os.getenv('SCRAPER_MAX_RETRIES', config.max_retries))
        config.backoff_factor = float(os.getenv('SCRAPER_BACKOFF_FACTOR', config.backoff_factor))
        config.failure_threshold = int(os.getenv('SCRAPER_FAILURE_THRESHOLD', config.failure_threshold))
        config.recovery_timeout = int(os.getenv('SCRAPER_RECOVERY_TIMEOUT', config.recovery_timeout))
        config.database_path = os.getenv('SCRAPER_DATABASE_PATH', config.database_path)
        config.max_pages = int(os.getenv('SCRAPER_MAX_PAGES', config.max_pages))
        
        # Parse proxy config from env
        proxy_url = os.getenv('SCRAPER_PROXY_URL')
        if proxy_url:
            config.proxy_config = {
                'http': proxy_url,
                'https': proxy_url
            }
        
        # Parse custom headers from env
        custom_headers = os.getenv('SCRAPER_CUSTOM_HEADERS')
        if custom_headers:
            try:
                config.custom_headers = json.loads(custom_headers)
            except json.JSONDecodeError:
                print("Warning: Invalid JSON in SCRAPER_CUSTOM_HEADERS")
        
        return config


# Site-specific selector configurations
SITE_CONFIGS = {
    'amazon.com': {
        'name': '#productTitle',
        'price': '.a-price-whole',
        'description': '#feature-bullets ul',
        'rating': '.a-icon-alt',
        'reviews_count': '#acrCustomerReviewText',
        'availability': '#availability span',
        'brand': '#bylineInfo',
        'category': '.a-breadcrumb',
        'images': '#altImages img'
    },
    'ebay.com': {
        'name': '#it-ttl',
        'price': '.notranslate',
        'description': '#desc_div',
        'rating': '.reviews .star-rating',
        'reviews_count': '.reviews .review-count',
        'availability': '#qtySubTxt',
        'brand': '#x-ebay-brand',
        'category': '.breadcrumb',
        'images': '#PicturePanel img'
    },
    'etsy.com': {
        'name': '[data-testid="product-title"]',
        'price': '[data-testid="price"]',
        'description': '[data-testid="product-description"]',
        'rating': '[data-testid="rating"]',
        'reviews_count': '[data-testid="reviews-count"]',
        'availability': '[data-testid="availability"]',
        'brand': '[data-testid="shop-name"]',
        'category': '.breadcrumb',
        'images': '[data-testid="product-image"] img'
    }
}


def get_site_config(url: str) -> Optional[Dict[str, str]]:
    """Get site-specific configuration for selectors."""
    from urllib.parse import urlparse
    
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    
    # Remove www. prefix
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return SITE_CONFIGS.get(domain)


def load_config(config_path: Optional[str] = None) -> ScraperConfig:
    """Load configuration from file or environment variables."""
    if config_path and os.path.exists(config_path):
        return ScraperConfig.from_file(config_path)
    else:
        return ScraperConfig.from_env()