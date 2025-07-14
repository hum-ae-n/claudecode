"""
Command-line interface for the web scraper.
"""

import argparse
import sys
import logging
from typing import Optional, List
from pathlib import Path
import time
from tqdm import tqdm

from .scraper import ProductScraper
from .database import DatabaseManager
from .models import Product
from .utils import RateLimiter


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format=format_str,
        handlers=handlers
    )


class ScraperCLI:
    """Command-line interface for the web scraper."""
    
    def __init__(self):
        self.parser = self._create_parser()
        self.db_manager = None
        self.scraper = None
        self.logger = logging.getLogger(__name__)
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create argument parser."""
        parser = argparse.ArgumentParser(
            description='E-commerce web scraper with rate limiting and retry logic',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog='''
Examples:
  # Scrape products from a category page
  python -m scraper.cli scrape https://example.com/category/electronics
  
  # Scrape with custom rate limiting
  python -m scraper.cli scrape https://example.com/category/electronics --rate 0.5 --burst 3
  
  # Scrape specific product URLs
  python -m scraper.cli scrape-urls urls.txt
  
  # Export scraped data to CSV
  python -m scraper.cli export products.csv
  
  # Show database statistics
  python -m scraper.cli stats
            '''
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        
        parser.add_argument(
            '--log-file',
            help='Log file path'
        )
        
        parser.add_argument(
            '--database', '-d',
            default='products.db',
            help='SQLite database file (default: products.db)'
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Scrape command
        scrape_parser = subparsers.add_parser(
            'scrape',
            help='Scrape products from a category page'
        )
        scrape_parser.add_argument(
            'url',
            help='Category URL to scrape'
        )
        scrape_parser.add_argument(
            '--rate', '-r',
            type=float,
            default=1.0,
            help='Requests per second (default: 1.0)'
        )
        scrape_parser.add_argument(
            '--burst', '-b',
            type=int,
            default=5,
            help='Burst size for rate limiting (default: 5)'
        )
        scrape_parser.add_argument(
            '--max-pages',
            type=int,
            default=10,
            help='Maximum pages to scrape (default: 10)'
        )
        scrape_parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Request timeout in seconds (default: 30)'
        )
        scrape_parser.add_argument(
            '--pattern',
            help='URL pattern to match product URLs (regex)'
        )
        scrape_parser.add_argument(
            '--headers',
            help='Custom headers as JSON string'
        )
        
        # Scrape URLs command
        scrape_urls_parser = subparsers.add_parser(
            'scrape-urls',
            help='Scrape products from a list of URLs'
        )
        scrape_urls_parser.add_argument(
            'file',
            help='File containing product URLs (one per line)'
        )
        scrape_urls_parser.add_argument(
            '--rate', '-r',
            type=float,
            default=1.0,
            help='Requests per second (default: 1.0)'
        )
        scrape_urls_parser.add_argument(
            '--burst', '-b',
            type=int,
            default=5,
            help='Burst size for rate limiting (default: 5)'
        )
        scrape_urls_parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Request timeout in seconds (default: 30)'
        )
        
        # Export command
        export_parser = subparsers.add_parser(
            'export',
            help='Export scraped data to CSV'
        )
        export_parser.add_argument(
            'filename',
            help='Output CSV filename'
        )
        export_parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of products to export'
        )
        export_parser.add_argument(
            '--category',
            help='Filter by category'
        )
        export_parser.add_argument(
            '--brand',
            help='Filter by brand'
        )
        
        # Stats command
        stats_parser = subparsers.add_parser(
            'stats',
            help='Show database statistics'
        )
        
        # Clear command
        clear_parser = subparsers.add_parser(
            'clear',
            help='Clear all data from database'
        )
        clear_parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompt'
        )
        
        return parser
    
    def run(self, args: Optional[List[str]] = None) -> int:
        """Run the CLI application."""
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return 1
        
        # Set up logging
        setup_logging(parsed_args.verbose, parsed_args.log_file)
        
        # Initialize database
        self.db_manager = DatabaseManager(parsed_args.database)
        
        try:
            if parsed_args.command == 'scrape':
                return self._handle_scrape(parsed_args)
            elif parsed_args.command == 'scrape-urls':
                return self._handle_scrape_urls(parsed_args)
            elif parsed_args.command == 'export':
                return self._handle_export(parsed_args)
            elif parsed_args.command == 'stats':
                return self._handle_stats(parsed_args)
            elif parsed_args.command == 'clear':
                return self._handle_clear(parsed_args)
            else:
                self.parser.print_help()
                return 1
                
        except KeyboardInterrupt:
            self.logger.info("Scraping interrupted by user")
            return 1
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return 1
    
    def _handle_scrape(self, args) -> int:
        """Handle scrape command."""
        # Parse custom headers
        custom_headers = None
        if args.headers:
            import json
            try:
                custom_headers = json.loads(args.headers)
            except json.JSONDecodeError:
                self.logger.error("Invalid JSON in headers argument")
                return 1
        
        # Initialize scraper
        rate_limiter = RateLimiter(args.rate, args.burst)
        self.scraper = ProductScraper(
            args.url,
            rate_limiter=rate_limiter,
            custom_headers=custom_headers,
            timeout=args.timeout
        )
        
        # Extract product URLs
        print(f"Extracting product URLs from: {args.url}")
        product_urls = self.scraper.extract_product_urls(
            args.url,
            url_pattern=args.pattern,
            max_pages=args.max_pages
        )
        
        if not product_urls:
            print("No product URLs found")
            return 1
        
        print(f"Found {len(product_urls)} product URLs")
        
        # Scrape products with progress bar
        success_count = 0
        error_count = 0
        
        with tqdm(total=len(product_urls), desc="Scraping products") as pbar:
            for url in product_urls:
                try:
                    product = self.scraper.scrape_product(url)
                    if product:
                        if self.db_manager.save_product(product):
                            success_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    self.logger.error(f"Error scraping {url}: {e}")
                    error_count += 1
                
                pbar.update(1)
                pbar.set_postfix({
                    'Success': success_count,
                    'Errors': error_count
                })
        
        print(f"\nScraping completed:")
        print(f"  Successfully scraped: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total in database: {self.db_manager.get_product_count()}")
        
        return 0
    
    def _handle_scrape_urls(self, args) -> int:
        """Handle scrape-urls command."""
        # Read URLs from file
        try:
            with open(args.file, 'r') as f:
                urls = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.logger.error(f"File not found: {args.file}")
            return 1
        
        if not urls:
            print("No URLs found in file")
            return 1
        
        # Initialize scraper
        rate_limiter = RateLimiter(args.rate, args.burst)
        
        # Use first URL to determine base URL
        from urllib.parse import urlparse
        parsed_url = urlparse(urls[0])
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        self.scraper = ProductScraper(
            base_url,
            rate_limiter=rate_limiter,
            timeout=args.timeout
        )
        
        print(f"Scraping {len(urls)} product URLs")
        
        # Scrape products with progress bar
        success_count = 0
        error_count = 0
        
        with tqdm(total=len(urls), desc="Scraping products") as pbar:
            for url in urls:
                try:
                    product = self.scraper.scrape_product(url)
                    if product:
                        if self.db_manager.save_product(product):
                            success_count += 1
                        else:
                            error_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    self.logger.error(f"Error scraping {url}: {e}")
                    error_count += 1
                
                pbar.update(1)
                pbar.set_postfix({
                    'Success': success_count,
                    'Errors': error_count
                })
        
        print(f"\nScraping completed:")
        print(f"  Successfully scraped: {success_count}")
        print(f"  Errors: {error_count}")
        print(f"  Total in database: {self.db_manager.get_product_count()}")
        
        return 0
    
    def _handle_export(self, args) -> int:
        """Handle export command."""
        print(f"Exporting products to: {args.filename}")
        
        if self.db_manager.export_to_csv(args.filename):
            print("Export completed successfully")
            return 0
        else:
            print("Export failed")
            return 1
    
    def _handle_stats(self, args) -> int:
        """Handle stats command."""
        total_products = self.db_manager.get_product_count()
        
        print(f"Database Statistics:")
        print(f"  Total products: {total_products}")
        
        # Get sample products by category and brand
        if total_products > 0:
            products = self.db_manager.get_products(limit=1000)
            
            categories = {}
            brands = {}
            
            for product in products:
                if product.category:
                    categories[product.category] = categories.get(product.category, 0) + 1
                if product.brand:
                    brands[product.brand] = brands.get(product.brand, 0) + 1
            
            if categories:
                print(f"  Top categories:")
                for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"    {cat}: {count}")
            
            if brands:
                print(f"  Top brands:")
                for brand, count in sorted(brands.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"    {brand}: {count}")
        
        return 0
    
    def _handle_clear(self, args) -> int:
        """Handle clear command."""
        if not args.confirm:
            response = input("Are you sure you want to clear all data? (y/N): ")
            if response.lower() != 'y':
                print("Cancelled")
                return 0
        
        if self.db_manager.clear_database():
            print("Database cleared successfully")
            return 0
        else:
            print("Failed to clear database")
            return 1


def main():
    """Main entry point."""
    cli = ScraperCLI()
    sys.exit(cli.run())


if __name__ == '__main__':
    main()