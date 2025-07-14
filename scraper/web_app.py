"""
Flask web interface for the scraper application.
"""

import os
import json
import threading
from datetime import datetime
from typing import Optional, List, Dict, Any
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
import sqlite3

from .database import DatabaseManager
from .models import Product
from .scraper import ProductScraper
from .utils import RateLimiter
from .config import load_config


class ScraperWebApp:
    """Flask web application for the scraper."""
    
    def __init__(self, database_path: str = "products.db"):
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)
        self.database_path = database_path
        self.db_manager = DatabaseManager(database_path)
        self.scraping_status = {
            'active': False,
            'progress': 0,
            'total': 0,
            'current_url': '',
            'errors': 0,
            'start_time': None
        }
        self.setup_routes()
    
    def setup_routes(self):
        """Set up Flask routes."""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page."""
            stats = self.get_dashboard_stats()
            return render_template('dashboard.html', stats=stats, scraping_status=self.scraping_status)
        
        @self.app.route('/products')
        def products():
            """Product listing page with pagination."""
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            search = request.args.get('search', '')
            category = request.args.get('category', '')
            brand = request.args.get('brand', '')
            
            products_data = self.get_products_paginated(
                page=page, 
                per_page=per_page, 
                search=search, 
                category=category, 
                brand=brand
            )
            
            categories = self.get_categories()
            brands = self.get_brands()
            
            return render_template('products.html', 
                                 products=products_data['products'],
                                 pagination=products_data['pagination'],
                                 categories=categories,
                                 brands=brands,
                                 current_search=search,
                                 current_category=category,
                                 current_brand=brand)
        
        @self.app.route('/product/<int:product_id>')
        def product_detail(product_id):
            """Product detail page."""
            product = self.get_product_by_id(product_id)
            if not product:
                flash('Product not found', 'error')
                return redirect(url_for('products'))
            return render_template('product_detail.html', product=product)
        
        @self.app.route('/scrape', methods=['GET', 'POST'])
        def scrape():
            """Scraping interface."""
            if request.method == 'POST':
                url = request.form.get('url', '').strip()
                max_pages = request.form.get('max_pages', 5, type=int)
                rate_limit = request.form.get('rate_limit', 1.0, type=float)
                
                if not url:
                    flash('Please enter a URL', 'error')
                    return redirect(url_for('scrape'))
                
                if self.scraping_status['active']:
                    flash('Scraping is already in progress', 'error')
                    return redirect(url_for('scrape'))
                
                # Start scraping in background thread
                thread = threading.Thread(target=self.start_scraping, args=(url, max_pages, rate_limit))
                thread.daemon = True
                thread.start()
                
                flash('Scraping started successfully', 'success')
                return redirect(url_for('dashboard'))
            
            return render_template('scrape.html')
        
        @self.app.route('/api/scraping-status')
        def scraping_status():
            """API endpoint for scraping status."""
            return jsonify(self.scraping_status)
        
        @self.app.route('/api/dashboard-stats')
        def dashboard_stats():
            """API endpoint for dashboard statistics."""
            return jsonify(self.get_dashboard_stats())
        
        @self.app.route('/export')
        def export():
            """Export products to CSV."""
            filename = f"products_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            if self.db_manager.export_to_csv(filename):
                flash(f'Products exported to {filename}', 'success')
            else:
                flash('Export failed', 'error')
            return redirect(url_for('products'))
        
        @self.app.route('/clear-database', methods=['POST'])
        def clear_database():
            """Clear all products from database."""
            if self.db_manager.clear_database():
                flash('Database cleared successfully', 'success')
            else:
                flash('Failed to clear database', 'error')
            return redirect(url_for('dashboard'))
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for the dashboard."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Total products
                cursor.execute("SELECT COUNT(*) FROM products")
                total_products = cursor.fetchone()[0]
                
                # Products by category
                cursor.execute("""
                    SELECT category, COUNT(*) as count 
                    FROM products 
                    WHERE category != '' 
                    GROUP BY category 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                categories = [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
                
                # Products by brand
                cursor.execute("""
                    SELECT brand, COUNT(*) as count 
                    FROM products 
                    WHERE brand != '' 
                    GROUP BY brand 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                brands = [{'name': row[0], 'count': row[1]} for row in cursor.fetchall()]
                
                # Recent products
                cursor.execute("""
                    SELECT name, price, scraped_at 
                    FROM products 
                    ORDER BY scraped_at DESC 
                    LIMIT 5
                """)
                recent_products = [
                    {'name': row[0], 'price': row[1], 'scraped_at': row[2]} 
                    for row in cursor.fetchall()
                ]
                
                # Average price
                cursor.execute("SELECT AVG(price) FROM products WHERE price IS NOT NULL")
                avg_price = cursor.fetchone()[0] or 0
                
                # Price range
                cursor.execute("SELECT MIN(price), MAX(price) FROM products WHERE price IS NOT NULL")
                price_range = cursor.fetchone()
                min_price = price_range[0] or 0
                max_price = price_range[1] or 0
                
                return {
                    'total_products': total_products,
                    'categories': categories,
                    'brands': brands,
                    'recent_products': recent_products,
                    'avg_price': round(avg_price, 2),
                    'min_price': min_price,
                    'max_price': max_price
                }
        except Exception as e:
            print(f"Error getting dashboard stats: {e}")
            return {
                'total_products': 0,
                'categories': [],
                'brands': [],
                'recent_products': [],
                'avg_price': 0,
                'min_price': 0,
                'max_price': 0
            }
    
    def get_products_paginated(self, page: int = 1, per_page: int = 20, 
                             search: str = '', category: str = '', brand: str = '') -> Dict[str, Any]:
        """Get paginated products with search and filters."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                where_conditions = []
                params = []
                
                if search:
                    where_conditions.append("(name LIKE ? OR description LIKE ?)")
                    params.extend([f'%{search}%', f'%{search}%'])
                
                if category:
                    where_conditions.append("category = ?")
                    params.append(category)
                
                if brand:
                    where_conditions.append("brand = ?")
                    params.append(brand)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # Get total count
                cursor.execute(f"SELECT COUNT(*) FROM products WHERE {where_clause}", params)
                total = cursor.fetchone()[0]
                
                # Get products for current page
                offset = (page - 1) * per_page
                cursor.execute(f"""
                    SELECT id, name, price, url, description, rating, reviews_count, 
                           availability, brand, category, scraped_at 
                    FROM products 
                    WHERE {where_clause}
                    ORDER BY scraped_at DESC 
                    LIMIT ? OFFSET ?
                """, params + [per_page, offset])
                
                products = []
                for row in cursor.fetchall():
                    products.append({
                        'id': row[0],
                        'name': row[1],
                        'price': row[2],
                        'url': row[3],
                        'description': row[4][:200] + '...' if row[4] and len(row[4]) > 200 else row[4],
                        'rating': row[5],
                        'reviews_count': row[6],
                        'availability': row[7],
                        'brand': row[8],
                        'category': row[9],
                        'scraped_at': row[10]
                    })
                
                # Pagination info
                total_pages = (total + per_page - 1) // per_page
                has_prev = page > 1
                has_next = page < total_pages
                
                return {
                    'products': products,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'total_pages': total_pages,
                        'has_prev': has_prev,
                        'has_next': has_next,
                        'prev_num': page - 1 if has_prev else None,
                        'next_num': page + 1 if has_next else None
                    }
                }
        except Exception as e:
            print(f"Error getting products: {e}")
            return {
                'products': [],
                'pagination': {
                    'page': 1,
                    'per_page': per_page,
                    'total': 0,
                    'total_pages': 0,
                    'has_prev': False,
                    'has_next': False,
                    'prev_num': None,
                    'next_num': None
                }
            }
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict[str, Any]]:
        """Get a single product by ID."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, name, price, url, description, rating, reviews_count, 
                           availability, brand, category, image_urls, scraped_at 
                    FROM products 
                    WHERE id = ?
                """, (product_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'price': row[2],
                        'url': row[3],
                        'description': row[4],
                        'rating': row[5],
                        'reviews_count': row[6],
                        'availability': row[7],
                        'brand': row[8],
                        'category': row[9],
                        'image_urls': row[10].split(',') if row[10] else [],
                        'scraped_at': row[11]
                    }
                return None
        except Exception as e:
            print(f"Error getting product {product_id}: {e}")
            return None
    
    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT category FROM products WHERE category != '' ORDER BY category")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    def get_brands(self) -> List[str]:
        """Get all unique brands."""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT brand FROM products WHERE brand != '' ORDER BY brand")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error getting brands: {e}")
            return []
    
    def start_scraping(self, url: str, max_pages: int, rate_limit: float):
        """Start scraping in background thread."""
        self.scraping_status.update({
            'active': True,
            'progress': 0,
            'total': 0,
            'current_url': url,
            'errors': 0,
            'start_time': datetime.now().isoformat()
        })
        
        try:
            # Initialize scraper
            rate_limiter = RateLimiter(rate_limit, 5)
            scraper = ProductScraper(url, rate_limiter=rate_limiter)
            
            # Extract product URLs
            product_urls = scraper.extract_product_urls(url, max_pages=max_pages)
            
            self.scraping_status['total'] = len(product_urls)
            
            # Scrape products
            for i, product_url in enumerate(product_urls):
                if not self.scraping_status['active']:  # Allow stopping
                    break
                
                self.scraping_status['current_url'] = product_url
                self.scraping_status['progress'] = i + 1
                
                try:
                    product = scraper.scrape_product(product_url)
                    if product:
                        self.db_manager.save_product(product)
                    else:
                        self.scraping_status['errors'] += 1
                except Exception as e:
                    print(f"Error scraping {product_url}: {e}")
                    self.scraping_status['errors'] += 1
            
        except Exception as e:
            print(f"Scraping error: {e}")
            self.scraping_status['errors'] += 1
        finally:
            self.scraping_status['active'] = False
    
    def run(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
        """Run the Flask application."""
        self.app.run(host=host, port=port, debug=debug)


def create_app(database_path: str = "products.db") -> Flask:
    """Create and configure the Flask application."""
    web_app = ScraperWebApp(database_path)
    return web_app.app


if __name__ == '__main__':
    web_app = ScraperWebApp()
    web_app.run(debug=True)