#!/usr/bin/env python3
"""
Run the Flask web application for the scraper.
"""

import os
import sys
from scraper.web_app import ScraperWebApp

if __name__ == '__main__':
    # Set database path
    database_path = os.path.join(os.path.dirname(__file__), 'products.db')
    
    # Create and run the web app
    web_app = ScraperWebApp(database_path)
    
    print("Starting Flask web application...")
    print("Virtual environment: " + (os.environ.get('VIRTUAL_ENV', 'Not activated')))
    print("Access the dashboard at: http://0.0.0.0:5000")
    print("In GitHub Codespaces, use the forwarded port URL")
    print("Press Ctrl+C to stop the server")
    
    try:
        web_app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        sys.exit(0)