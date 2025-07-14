# Web Scraper with Flask Interface

A comprehensive Python web scraper for extracting product data from e-commerce websites with advanced features including rate limiting, retry logic, SQLite storage, a command-line interface, and a modern Flask web interface with real-time progress tracking.

## Features

### 🕷️ **Web Scraping Engine**
- **Modular Design**: Clean separation of concerns with dedicated modules for scraping, database management, and CLI
- **Rate Limiting**: Configurable rate limiting to respect website resources
- **Retry Logic**: Exponential backoff with jitter for handling failed requests
- **Circuit Breaker**: Automatic failure detection and recovery
- **SQLite Storage**: Efficient local database storage with indexing
- **Site-specific Selectors**: Pre-configured selectors for popular e-commerce sites (Amazon, eBay, Etsy, books.toscrape.com)
- **Error Handling**: Robust error handling with detailed logging

### 🌐 **Flask Web Interface**
- **Dashboard**: Real-time statistics and scraping overview with progress tracking
- **Product Listing**: Browse, search, and filter scraped products with pagination
- **Scraping Interface**: Start new scraping sessions with safety controls
- **Product Details**: Full product information display with images
- **Export**: Download products as CSV with one-click export

### ⚠️ **Safety Features**
- **IP Banning Warnings**: Prominent alerts about scraping risks and best practices
- **Rate Limiting Controls**: Configurable requests per second (0.5-5.0)
- **Page Limits**: Prevent overwhelming target servers with maximum page settings
- **Responsible Scraping**: Built-in guidance for ethical web scraping

### 🔧 **Technical Features**
- **Command-line Interface**: Comprehensive CLI with multiple commands
- **Real-time Progress**: Live updates during scraping operations
- **Background Processing**: Non-blocking scraping with threading support
- **Virtual Environment**: Proper dependency isolation
- **Responsive Design**: Modern Bootstrap UI that works on all devices

## Installation

1. **Clone the repository**:
```bash
git clone https://github.com/hum-ae-n/claudecode.git
cd claudecode
```

2. **Create and activate virtual environment**:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

## Quick Start

### Flask Web Interface

1. **Start the web application**:
```bash
# Activate virtual environment
source .venv/bin/activate

# Run the Flask app
python run_web_app.py
```

2. **Access the interface**:
   - Local: `http://127.0.0.1:5000`
   - GitHub Codespaces: Use the forwarded port URL

3. **Use the web interface**:
   - 📊 **Dashboard** - View statistics and scraping progress
   - 📦 **Products** - Browse and search scraped products
   - 🚀 **Scrape** - Start new scraping with IP banning warnings
   - 📥 **Export** - Download products as CSV

### Command Line Interface

```bash
# Scrape products from books.toscrape.com
python -m scraper.cli scrape https://books.toscrape.com/ --max-pages 5 --rate 1.0

# Scrape with custom rate limiting
python -m scraper.cli scrape https://example.com/category/electronics --rate 0.5 --burst 3

# Scrape from URL list
python -m scraper.cli scrape-urls product_urls.txt

# Export data to CSV
python -m scraper.cli export products.csv

# View database statistics
python -m scraper.cli stats
```

## Usage

### Command Line Interface

The scraper provides several commands:

#### Scrape Command
```bash
python -m scraper.cli scrape [URL] [OPTIONS]
```

Options:
- `--rate, -r`: Requests per second (default: 1.0)
- `--burst, -b`: Burst size for rate limiting (default: 5)
- `--max-pages`: Maximum pages to scrape (default: 10)
- `--timeout`: Request timeout in seconds (default: 30)
- `--pattern`: URL pattern to match product URLs (regex)
- `--headers`: Custom headers as JSON string

#### Scrape URLs Command
```bash
python -m scraper.cli scrape-urls [FILE] [OPTIONS]
```

Scrape products from a file containing URLs (one per line).

#### Export Command
```bash
python -m scraper.cli export [FILENAME] [OPTIONS]
```

Options:
- `--limit`: Maximum number of products to export
- `--category`: Filter by category
- `--brand`: Filter by brand

#### Stats Command
```bash
python -m scraper.cli stats
```

Show database statistics including total products, top categories, and brands.

#### Clear Command
```bash
python -m scraper.cli clear [--confirm]
```

Clear all data from the database.

### Configuration

#### Environment Variables

You can configure the scraper using environment variables:

```bash
export SCRAPER_REQUESTS_PER_SECOND=0.5
export SCRAPER_BURST_SIZE=3
export SCRAPER_TIMEOUT=60
export SCRAPER_MAX_RETRIES=5
export SCRAPER_DATABASE_PATH=./my_products.db
export SCRAPER_PROXY_URL=http://proxy.example.com:8080
export SCRAPER_CUSTOM_HEADERS='{"User-Agent": "MyBot/1.0"}'
```

#### Configuration File

Create a `config.json` file:

```json
{
  "requests_per_second": 0.5,
  "burst_size": 3,
  "timeout": 60,
  "max_retries": 5,
  "database_path": "./products.db",
  "custom_headers": {
    "User-Agent": "MyBot/1.0"
  },
  "proxy_config": {
    "http": "http://proxy.example.com:8080",
    "https": "http://proxy.example.com:8080"
  }
}
```

### Programmatic Usage

```python
from scraper.scraper import ProductScraper
from scraper.database import DatabaseManager
from scraper.utils import RateLimiter

# Initialize components
rate_limiter = RateLimiter(requests_per_second=1.0, burst_size=5)
scraper = ProductScraper("https://example.com", rate_limiter=rate_limiter)
db = DatabaseManager("products.db")

# Extract product URLs
product_urls = scraper.extract_product_urls(
    "https://example.com/category/electronics",
    max_pages=5
)

# Scrape products
for url in product_urls:
    product = scraper.scrape_product(url)
    if product:
        db.save_product(product)

# Export data
db.export_to_csv("products.csv")
```

## Architecture

### Core Components

1. **models.py**: Data models for product information
2. **scraper.py**: Main scraping logic with rate limiting and retry mechanisms
3. **database.py**: SQLite database management
4. **utils.py**: Rate limiting, retry logic, and circuit breaker utilities
5. **cli.py**: Command-line interface
6. **config.py**: Configuration management

### Data Model

The `Product` class captures comprehensive product information:

- Name, price, description
- Rating and review count
- Availability status
- Brand and category
- Image URLs
- Metadata and timestamps

### Rate Limiting

The scraper implements token bucket rate limiting:
- Configurable requests per second
- Burst capacity for initial requests
- Automatic throttling when limits are exceeded

### Retry Logic

Exponential backoff with jitter:
- Configurable maximum retry attempts
- Exponential backoff factor
- Random jitter to prevent thundering herd
- Specific exception handling

### Circuit Breaker

Automatic failure detection:
- Configurable failure threshold
- Open/closed/half-open states
- Automatic recovery attempts

## Supported Sites

The scraper includes pre-configured selectors for:
- **Books to Scrape** (`books.toscrape.com`) - Demo site perfect for testing
- **Amazon** (`amazon.com`) - Product listings and details
- **eBay** (`ebay.com`) - Auction and buy-it-now items
- **Etsy** (`etsy.com`) - Handmade and vintage items

Additional sites can be supported by adding selectors to the configuration in `scraper/config.py`.

## Error Handling

The scraper includes comprehensive error handling:
- Request timeouts and connection errors
- HTTP status code errors
- Parsing errors
- Database errors
- Rate limiting violations

## Logging

Detailed logging with configurable levels:
- Debug: Detailed request/response information
- Info: General operation status
- Warning: Recoverable errors
- Error: Critical failures

## Legal and Ethical Considerations

⚠️ **Important**: This tool is for educational and research purposes only.

- **Respect robots.txt**: Always check site policies before scraping
- **Use reasonable rate limits**: Don't overwhelm servers (recommended: 1 request/second)
- **Obtain permission**: Get explicit consent when possible
- **Check terms of service**: Ensure compliance with site rules
- **Consider APIs**: Use official APIs when available
- **Be mindful of laws**: Respect copyright and data protection regulations

The Flask interface includes prominent warnings about these considerations.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is provided for educational purposes. Users are responsible for ensuring compliance with applicable laws and website terms of service.

---

**Built with ❤️ using Claude Code**
