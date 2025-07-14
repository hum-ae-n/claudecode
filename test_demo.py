#!/usr/bin/env python3
"""
Demo script to show the scraper working without hitting real sites.
"""

import logging
from scraper.scraper import ProductScraper
from scraper.database import DatabaseManager
from scraper.models import Product
from scraper.utils import RateLimiter
from datetime import datetime

def demo_scraper():
    """Demo the scraper with mock data."""
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize database
    db = DatabaseManager("demo_products.db")
    
    # Create some demo products
    demo_products = [
        Product(
            name="iPhone 15 Pro",
            price=999.99,
            url="https://example.com/iphone-15-pro",
            description="Latest iPhone with titanium design",
            rating=4.5,
            reviews_count=1234,
            availability="In Stock",
            brand="Apple",
            category="Electronics/Phones",
            image_urls=["https://example.com/iphone1.jpg", "https://example.com/iphone2.jpg"]
        ),
        Product(
            name="Samsung Galaxy S24",
            price=899.99,
            url="https://example.com/galaxy-s24",
            description="Flagship Android phone with AI features",
            rating=4.3,
            reviews_count=856,
            availability="In Stock",
            brand="Samsung",
            category="Electronics/Phones",
            image_urls=["https://example.com/galaxy1.jpg"]
        ),
        Product(
            name="MacBook Pro 14-inch",
            price=1999.99,
            url="https://example.com/macbook-pro-14",
            description="Professional laptop with M3 chip",
            rating=4.8,
            reviews_count=567,
            availability="In Stock",
            brand="Apple",
            category="Electronics/Computers",
            image_urls=["https://example.com/macbook1.jpg", "https://example.com/macbook2.jpg"]
        )
    ]
    
    print("🚀 Demo: Adding sample products to database...")
    
    # Save demo products
    for product in demo_products:
        if db.save_product(product):
            print(f"✅ Saved: {product.name} - ${product.price}")
        else:
            print(f"❌ Failed to save: {product.name}")
    
    print(f"\n📊 Database now contains {db.get_product_count()} products")
    
    # Show some statistics
    print("\n📈 Product Statistics:")
    products = db.get_products()
    
    categories = {}
    brands = {}
    total_value = 0
    
    for product in products:
        if product.category:
            categories[product.category] = categories.get(product.category, 0) + 1
        if product.brand:
            brands[product.brand] = brands.get(product.brand, 0) + 1
        if product.price:
            total_value += product.price
    
    print(f"  • Total value: ${total_value:,.2f}")
    print(f"  • Categories: {list(categories.keys())}")
    print(f"  • Brands: {list(brands.keys())}")
    
    # Export to CSV
    print("\n📄 Exporting to CSV...")
    if db.export_to_csv("demo_products.csv"):
        print("✅ Exported to demo_products.csv")
    else:
        print("❌ Export failed")
    
    # Test rate limiter
    print("\n⏱️  Testing rate limiter...")
    rate_limiter = RateLimiter(requests_per_second=2.0, burst_size=3)
    
    import time
    start_time = time.time()
    
    for i in range(5):
        rate_limiter.wait_if_needed()
        print(f"  Request {i+1} at {time.time() - start_time:.2f}s")
    
    print(f"\n🎉 Demo completed! Check demo_products.csv for exported data.")

if __name__ == "__main__":
    demo_scraper()