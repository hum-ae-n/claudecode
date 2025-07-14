"""
Main web scraper class for extracting product data from e-commerce sites.
"""

import re
import logging
from typing import List, Optional, Dict, Any, Callable
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import Product
from .utils import RateLimiter, retry_on_failure, CircuitBreaker, random_user_agent, get_proxy_config
from .config import get_site_config


class ProductScraper:
    """Main scraper class for extracting product data."""
    
    def __init__(self, 
                 base_url: str,
                 rate_limiter: Optional[RateLimiter] = None,
                 custom_headers: Optional[Dict[str, str]] = None,
                 timeout: int = 30):
        """Initialize the scraper.
        
        Args:
            base_url: Base URL of the e-commerce site
            rate_limiter: Rate limiter instance
            custom_headers: Custom HTTP headers
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.rate_limiter = rate_limiter or RateLimiter()
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.circuit_breaker = CircuitBreaker()
        
        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set headers
        self.session.headers.update({
            'User-Agent': random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        if custom_headers:
            self.session.headers.update(custom_headers)
        
        # Set proxy if available
        proxy_config = get_proxy_config()
        if proxy_config:
            self.session.proxies.update(proxy_config)
    
    @retry_on_failure(max_retries=3, exceptions=(requests.RequestException,))
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if failed
        """
        self.rate_limiter.wait_if_needed()
        
        try:
            response = self.circuit_breaker.call(
                self.session.get, url, timeout=self.timeout
            )
            response.raise_for_status()
            
            # Check if content is HTML
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type:
                self.logger.warning(f"Non-HTML content received from {url}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            self.logger.debug(f"Successfully fetched {url}")
            return soup
            
        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_product_urls(self, 
                           category_url: str,
                           url_pattern: Optional[str] = None,
                           max_pages: int = 10) -> List[str]:
        """Extract product URLs from category pages.
        
        Args:
            category_url: URL of the category page
            url_pattern: Regex pattern to match product URLs
            max_pages: Maximum number of pages to scrape
            
        Returns:
            List of product URLs
        """
        product_urls = []
        current_url = category_url
        
        for page in range(max_pages):
            self.logger.info(f"Scraping page {page + 1}: {current_url}")
            soup = self._fetch_page(current_url)
            
            if not soup:
                break
            
            # Extract product URLs from current page
            page_urls = self._extract_urls_from_page(soup, url_pattern)
            product_urls.extend(page_urls)
            
            # Find next page URL
            next_url = self._find_next_page_url(soup, current_url)
            if not next_url:
                break
            
            current_url = next_url
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in product_urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        self.logger.info(f"Found {len(unique_urls)} unique product URLs")
        return unique_urls
    
    def _extract_urls_from_page(self, soup: BeautifulSoup, 
                               url_pattern: Optional[str] = None) -> List[str]:
        """Extract product URLs from a single page."""
        urls = []
        
        # Common selectors for product links
        selectors = [
            'a[href*="/product/"]',
            'a[href*="/item/"]',
            'a[href*="/p/"]',
            'a[href*="/catalogue/"]',  # books.toscrape.com
            '.product-link',
            '.product-item a',
            '.product-card a',
            '[data-product-id] a',
            'h3 a',  # books.toscrape.com book titles
        ]
        
        for selector in selectors:
            links = soup.select(selector)
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(self.base_url, href)
                    if url_pattern:
                        if re.search(url_pattern, full_url):
                            urls.append(full_url)
                    else:
                        urls.append(full_url)
        
        return urls
    
    def _find_next_page_url(self, soup: BeautifulSoup, current_url: str) -> Optional[str]:
        """Find the URL of the next page."""
        next_selectors = [
            'a[rel="next"]',
            'a:contains("Next")',
            'a:contains(">")',
            '.pagination .next a',
            '.pager-next a',
        ]
        
        for selector in next_selectors:
            try:
                next_link = soup.select_one(selector)
                if next_link and next_link.get('href'):
                    return urljoin(current_url, next_link.get('href'))
            except:
                continue
        
        return None
    
    def scrape_product(self, product_url: str) -> Optional[Product]:
        """Scrape a single product page.
        
        Args:
            product_url: URL of the product page
            
        Returns:
            Product instance or None if failed
        """
        soup = self._fetch_page(product_url)
        if not soup:
            return None
        
        try:
            # Get site-specific configuration
            site_config = get_site_config(product_url)
            
            # Extract product data using multiple strategies
            name = self._extract_product_name(soup, site_config)
            price = self._extract_product_price(soup, site_config)
            description = self._extract_product_description(soup, site_config)
            rating = self._extract_product_rating(soup, site_config)
            reviews_count = self._extract_reviews_count(soup, site_config)
            availability = self._extract_availability(soup, site_config)
            brand = self._extract_brand(soup, site_config)
            category = self._extract_category(soup, site_config)
            image_urls = self._extract_image_urls(soup, product_url, site_config)
            
            if not name:
                self.logger.warning(f"Could not extract product name from {product_url}")
                return None
            
            product = Product(
                name=name,
                price=price,
                url=product_url,
                description=description,
                rating=rating,
                reviews_count=reviews_count,
                availability=availability,
                brand=brand,
                category=category,
                image_urls=image_urls
            )
            
            self.logger.info(f"Successfully scraped product: {name}")
            return product
            
        except Exception as e:
            self.logger.error(f"Error scraping product {product_url}: {e}")
            return None
    
    def _extract_product_name(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> str:
        """Extract product name from page."""
        selectors = [
            'h1[data-product-name]',
            'h1.product-title',
            'h1.product-name',
            '.product-title h1',
            '.product-name h1',
            'h1',
            '[data-testid="product-name"]',
            '.pdp-title',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('name'):
            selectors.insert(0, site_config['name'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 3:
                    return text
        
        return ""
    
    def _extract_product_price(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Extract product price from page."""
        selectors = [
            '[data-testid="price"]',
            '.price-current',
            '.price-now',
            '.product-price',
            '.price',
            '.current-price',
            '.sale-price',
            '[data-price]',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('price'):
            selectors.insert(0, site_config['price'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Try data attribute first
                price_attr = element.get('data-price')
                if price_attr:
                    try:
                        return float(price_attr)
                    except:
                        pass
                
                # Extract from text
                text = element.get_text(strip=True)
                # Remove currency symbols and extract numbers
                price_match = re.search(r'[\d,]+\.?\d*', text.replace(',', '').replace('£', '').replace('$', ''))
                if price_match:
                    try:
                        return float(price_match.group())
                    except:
                        pass
        
        return None
    
    def _extract_product_description(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> str:
        """Extract product description from page."""
        selectors = [
            '[data-testid="product-description"]',
            '.product-description',
            '.product-details',
            '.product-info',
            '.description',
            '.product-overview',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('description'):
            selectors.insert(0, site_config['description'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text and len(text) > 10:
                    return text[:1000]  # Limit description length
        
        return ""
    
    def _extract_product_rating(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Extract product rating from page."""
        selectors = [
            '[data-testid="rating"]',
            '.rating-value',
            '.star-rating',
            '.rating',
            '.review-rating',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('rating'):
            selectors.insert(0, site_config['rating'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                # Try data attribute
                rating_attr = element.get('data-rating')
                if rating_attr:
                    try:
                        return float(rating_attr)
                    except:
                        pass
                
                # Extract from text or class names
                text = element.get_text(strip=True)
                class_names = ' '.join(element.get('class', []))
                
                # Check for star rating class patterns (e.g., 'star-rating Three')
                star_match = re.search(r'(One|Two|Three|Four|Five)', class_names)
                if star_match:
                    star_map = {'One': 1, 'Two': 2, 'Three': 3, 'Four': 4, 'Five': 5}
                    return float(star_map.get(star_match.group(1), 0))
                
                # Extract from text
                rating_match = re.search(r'(\d+\.?\d*)', text)
                if rating_match:
                    try:
                        rating = float(rating_match.group(1))
                        if 0 <= rating <= 5:
                            return rating
                    except:
                        pass
        
        return None
    
    def _extract_reviews_count(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> Optional[int]:
        """Extract number of reviews from page."""
        selectors = [
            '[data-testid="reviews-count"]',
            '.reviews-count',
            '.review-count',
            '.rating-count',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('reviews_count'):
            selectors.insert(0, site_config['reviews_count'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                count_match = re.search(r'(\d+)', text.replace(',', ''))
                if count_match:
                    try:
                        return int(count_match.group(1))
                    except:
                        pass
        
        return None
    
    def _extract_availability(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> str:
        """Extract product availability from page."""
        selectors = [
            '[data-testid="availability"]',
            '.availability',
            '.stock-status',
            '.product-availability',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('availability'):
            selectors.insert(0, site_config['availability'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        return ""
    
    def _extract_brand(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> str:
        """Extract product brand from page."""
        selectors = [
            '[data-testid="brand"]',
            '.brand',
            '.product-brand',
            '.manufacturer',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('brand'):
            selectors.insert(0, site_config['brand'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        return ""
    
    def _extract_category(self, soup: BeautifulSoup, site_config: Optional[Dict[str, str]] = None) -> str:
        """Extract product category from page."""
        selectors = [
            '[data-testid="category"]',
            '.breadcrumb',
            '.category',
            '.product-category',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('category'):
            selectors.insert(0, site_config['category'])
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        
        return ""
    
    def _extract_image_urls(self, soup: BeautifulSoup, base_url: str, site_config: Optional[Dict[str, str]] = None) -> List[str]:
        """Extract product image URLs from page."""
        image_urls = []
        
        selectors = [
            '.product-image img',
            '.product-photos img',
            '.product-gallery img',
            '[data-testid="product-image"] img',
        ]
        
        # Use site-specific selector if available
        if site_config and site_config.get('images'):
            selectors.insert(0, site_config['images'])
        
        for selector in selectors:
            images = soup.select(selector)
            for img in images:
                src = img.get('src') or img.get('data-src')
                if src:
                    full_url = urljoin(base_url, src)
                    if full_url not in image_urls:
                        image_urls.append(full_url)
        
        return image_urls[:10]  # Limit to 10 images