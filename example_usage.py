#!/usr/bin/env python3
"""
Example usage of the e-commerce web scraper.

This script demonstrates how to use the scraper programmatically.
"""

import logging
from scraper.scraper import ProductScraper
from scraper.database import DatabaseManager
from scraper.utils import RateLimiter
from scraper.config import load_config

def main():
    """Example usage of the scraper."""
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load configuration
    config = load_config()
    
    # Initialize components
    rate_limiter = RateLimiter(
        requests_per_second=config.requests_per_second,
        burst_size=config.burst_size
    )
    
    # Example: Scrape a hypothetical electronics category
    base_url = "https://example-ecommerce.com"
    category_url = f"{base_url}/category/electronics"
    
    scraper = ProductScraper(
        base_url=base_url,
        rate_limiter=rate_limiter,
        timeout=config.timeout
    )
    
    db = DatabaseManager(config.database_path)
    
    print("Starting product scraping example...")
    
    # Extract product URLs from category page
    print(f"Extracting product URLs from: {category_url}")
    try:
        product_urls = scraper.extract_product_urls(
            category_url,
            max_pages=config.max_pages
        )
        print(f"Found {len(product_urls)} product URLs")
    except Exception as e:
        print(f"Error extracting URLs: {e}")
        return
    
    # Scrape a few products as example
    max_products = min(5, len(product_urls))  # Limit to 5 products for example
    
    print(f"Scraping {max_products} products...")
    success_count = 0
    
    for i, url in enumerate(product_urls[:max_products]):
        print(f"Scraping product {i+1}/{max_products}: {url}")
        
        try:
            product = scraper.scrape_product(url)
            if product:
                if db.save_product(product):
                    success_count += 1
                    print(f"  ✓ Saved: {product.name}")
                else:
                    print(f"  ✗ Failed to save product")
            else:
                print(f"  ✗ Failed to scrape product")
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    print(f"\nScraping completed:")
    print(f"  Successfully scraped: {success_count}")
    print(f"  Total products in database: {db.get_product_count()}")
    
    # Export data to CSV
    print("\nExporting data to CSV...")
    if db.export_to_csv("example_products.csv"):
        print("  ✓ Data exported to example_products.csv")
    else:
        print("  ✗ Failed to export data")
    
    # Show some statistics
    print("\nDatabase statistics:")
    products = db.get_products(limit=10)
    for product in products:
        print(f"  - {product.name} (${product.price})")

if __name__ == "__main__":
    main()