"""
Database management for storing scraped product data.
"""

import sqlite3
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from contextlib import contextmanager

from .models import Product


class DatabaseManager:
    """Manages SQLite database operations for product data."""
    
    def __init__(self, db_path: str = "products.db"):
        """Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database tables."""
        with self.get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price REAL,
                    url TEXT UNIQUE,
                    description TEXT,
                    rating REAL,
                    reviews_count INTEGER,
                    availability TEXT,
                    brand TEXT,
                    category TEXT,
                    image_urls TEXT,
                    metadata TEXT,
                    scraped_at TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_url ON products(url)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_brand ON products(brand)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_category ON products(category)
            ''')
            
            conn.commit()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def save_product(self, product: Product) -> bool:
        """Save a product to the database.
        
        Args:
            product: Product instance to save
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            with self.get_connection() as conn:
                product_data = product.to_dict()
                
                # Check if product already exists
                existing = conn.execute(
                    'SELECT id FROM products WHERE url = ?',
                    (product_data['url'],)
                ).fetchone()
                
                if existing:
                    # Update existing product
                    conn.execute('''
                        UPDATE products SET
                            name = ?, price = ?, description = ?, rating = ?,
                            reviews_count = ?, availability = ?, brand = ?,
                            category = ?, image_urls = ?, metadata = ?, scraped_at = ?
                        WHERE url = ?
                    ''', (
                        product_data['name'], product_data['price'],
                        product_data['description'], product_data['rating'],
                        product_data['reviews_count'], product_data['availability'],
                        product_data['brand'], product_data['category'],
                        product_data['image_urls'], product_data['metadata'],
                        product_data['scraped_at'], product_data['url']
                    ))
                else:
                    # Insert new product
                    conn.execute('''
                        INSERT INTO products (
                            name, price, url, description, rating, reviews_count,
                            availability, brand, category, image_urls, metadata, scraped_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        product_data['name'], product_data['price'],
                        product_data['url'], product_data['description'],
                        product_data['rating'], product_data['reviews_count'],
                        product_data['availability'], product_data['brand'],
                        product_data['category'], product_data['image_urls'],
                        product_data['metadata'], product_data['scraped_at']
                    ))
                
                conn.commit()
                self.logger.info(f"Saved product: {product.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error saving product {product.name}: {e}")
            return False
    
    def get_products(self, limit: Optional[int] = None, 
                    category: Optional[str] = None,
                    brand: Optional[str] = None) -> List[Product]:
        """Retrieve products from database.
        
        Args:
            limit: Maximum number of products to return
            category: Filter by category
            brand: Filter by brand
            
        Returns:
            List of Product instances
        """
        query = "SELECT * FROM products WHERE 1=1"
        params = []
        
        if category:
            query += " AND category = ?"
            params.append(category)
        
        if brand:
            query += " AND brand = ?"
            params.append(brand)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        try:
            with self.get_connection() as conn:
                rows = conn.execute(query, params).fetchall()
                return [Product.from_dict(dict(row)) for row in rows]
        except Exception as e:
            self.logger.error(f"Error retrieving products: {e}")
            return []
    
    def get_product_count(self) -> int:
        """Get total number of products in database."""
        try:
            with self.get_connection() as conn:
                result = conn.execute('SELECT COUNT(*) FROM products').fetchone()
                return result[0] if result else 0
        except Exception as e:
            self.logger.error(f"Error getting product count: {e}")
            return 0
    
    def clear_database(self) -> bool:
        """Clear all products from database."""
        try:
            with self.get_connection() as conn:
                conn.execute('DELETE FROM products')
                conn.commit()
                self.logger.info("Database cleared successfully")
                return True
        except Exception as e:
            self.logger.error(f"Error clearing database: {e}")
            return False
    
    def export_to_csv(self, filename: str) -> bool:
        """Export products to CSV file.
        
        Args:
            filename: Output CSV filename
            
        Returns:
            bool: True if exported successfully
        """
        try:
            import csv
            
            products = self.get_products()
            if not products:
                self.logger.warning("No products to export")
                return False
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['name', 'price', 'url', 'description', 'rating',
                             'reviews_count', 'availability', 'brand', 'category',
                             'image_urls', 'scraped_at']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for product in products:
                    data = product.to_dict()
                    writer.writerow({k: v for k, v in data.items() if k in fieldnames})
            
            self.logger.info(f"Exported {len(products)} products to {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return False