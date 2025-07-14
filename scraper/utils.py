"""
Utility functions for rate limiting and retry logic.
"""

import time
import random
import logging
from typing import Callable, Any, Optional
from functools import wraps
from dataclasses import dataclass


@dataclass
class RateLimiter:
    """Rate limiter to control request frequency."""
    
    requests_per_second: float = 1.0
    burst_size: int = 5
    
    def __post_init__(self):
        self.last_request_time = 0.0
        self.tokens = self.burst_size
        self.logger = logging.getLogger(__name__)
    
    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        current_time = time.time()
        
        # Add tokens based on time passed
        time_passed = current_time - self.last_request_time
        self.tokens = min(self.burst_size, 
                         self.tokens + time_passed * self.requests_per_second)
        
        if self.tokens < 1:
            wait_time = (1 - self.tokens) / self.requests_per_second
            self.logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
            self.tokens = 0
        else:
            self.tokens -= 1
        
        self.last_request_time = time.time()


def retry_on_failure(max_retries: int = 3, 
                    backoff_factor: float = 2.0,
                    exceptions: tuple = (Exception,),
                    jitter: bool = True) -> Callable:
    """Decorator for retrying failed operations.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Exponential backoff multiplier
        exceptions: Tuple of exceptions to catch and retry
        jitter: Whether to add random jitter to backoff
    
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(__name__)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {e}")
                        raise
                    
                    # Calculate backoff time
                    backoff_time = backoff_factor ** attempt
                    if jitter:
                        backoff_time *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. "
                                 f"Retrying in {backoff_time:.2f} seconds...")
                    time.sleep(backoff_time)
            
            return None
        return wrapper
    return decorator


class CircuitBreaker:
    """Circuit breaker pattern for handling failures."""
    
    def __init__(self, failure_threshold: int = 5, 
                 recovery_timeout: int = 60):
        """Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Time in seconds before attempting recovery
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
        self.logger = logging.getLogger(__name__)
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with circuit breaker protection."""
        if self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                self.logger.info("Circuit breaker transitioning to half-open")
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful operation."""
        self.failure_count = 0
        if self.state == "half-open":
            self.state = "closed"
            self.logger.info("Circuit breaker closed after successful recovery")
    
    def _on_failure(self) -> None:
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


def random_user_agent() -> str:
    """Return a random user agent string."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
    ]
    return random.choice(user_agents)


def get_proxy_config() -> Optional[dict]:
    """Get proxy configuration if available."""
    # This can be extended to read from environment variables or config files
    return None