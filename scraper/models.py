"""
Data models for product information.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class Product:
    """Product data model."""
    
    name: str
    price: Optional[float] = None
    url: str = ""
    description: str = ""
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    availability: str = ""
    brand: str = ""
    category: str = ""
    image_urls: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    scraped_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert product to dictionary for database storage."""
        return {
            'name': self.name,
            'price': self.price,
            'url': self.url,
            'description': self.description,
            'rating': self.rating,
            'reviews_count': self.reviews_count,
            'availability': self.availability,
            'brand': self.brand,
            'category': self.category,
            'image_urls': ','.join(self.image_urls),
            'metadata': str(self.metadata),
            'scraped_at': self.scraped_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Product':
        """Create product from dictionary."""
        image_urls = data.get('image_urls', '')
        image_urls = image_urls.split(',') if image_urls else []
        
        return cls(
            name=data['name'],
            price=data.get('price'),
            url=data.get('url', ''),
            description=data.get('description', ''),
            rating=data.get('rating'),
            reviews_count=data.get('reviews_count'),
            availability=data.get('availability', ''),
            brand=data.get('brand', ''),
            category=data.get('category', ''),
            image_urls=image_urls,
            metadata=eval(data.get('metadata', '{}')),
            scraped_at=datetime.fromisoformat(data['scraped_at'])
        )