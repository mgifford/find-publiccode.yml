"""Discovery crawler for publiccode.yml files."""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result of attempting to discover publiccode.yml for a domain."""
    domain: str
    file_url: Optional[str] = None
    http_status: Optional[int] = None
    http_outcome: str = "not_attempted"  # success, redirect, timeout, error, not_found, size_exceeded
    redirect_chain: List[str] = None
    final_url: Optional[str] = None
    content: Optional[bytes] = None
    file_format: Optional[str] = None  # publiccode.yml, codemeta.json, code.json, contribute.json
    error_message: Optional[str] = None
    discovery_timestamp: str = None
    response_time_ms: Optional[float] = None

    def __post_init__(self):
        if self.redirect_chain is None:
            self.redirect_chain = []
        if self.discovery_timestamp is None:
            self.discovery_timestamp = datetime.utcnow().isoformat()


class PublicCodeCrawler:
    """Crawler to discover publiccode.yml files on government domains."""

    def __init__(self):
        """Initialize crawler with configured session."""
        self.session = self._create_session()
        self.stats = {
            "domains_checked": 0,
            "files_found": 0,
            "errors": 0,
            "timeouts": 0,
        }

    def _create_session(self) -> requests.Session:
        """Create a configured requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=2,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            "User-Agent": config.USER_AGENT,
            "Accept": "text/yaml, application/x-yaml, text/plain, */*"
        })
        
        return session

    def discover(self, domain: str) -> DiscoveryResult:
        """
        Attempt to discover publiccode.yml file for a given domain.
        
        Tests all configured paths with HTTPS first, falls back to HTTP.
        Also tests www/non-www variations if initial attempt fails.
        
        Args:
            domain: The domain to check
            
        Returns:
            DiscoveryResult with outcome and any discovered file
        """
        logger.info(f"Discovering publiccode.yml for: {domain}")
        self.stats["domains_checked"] += 1
        
        # Try primary domain (as provided)
        result = self._try_domain(domain)
        if result.http_outcome == "success":
            self.stats["files_found"] += 1
            return result
        
        # Try www/non-www variation if primary failed and enabled
        if config.TEST_WWW_VARIATIONS:
            alternate_domain = self._get_alternate_domain(domain)
            if alternate_domain != domain:
                logger.debug(f"Trying alternate domain: {alternate_domain}")
                alternate_result = self._try_domain(alternate_domain)
                if alternate_result.http_outcome == "success":
                    self.stats["files_found"] += 1
                    # Update to show original domain but found on alternate
                    alternate_result.domain = domain
                    return alternate_result
        
        return result
    
    def _get_alternate_domain(self, domain: str) -> str:
        """
        Get the www/non-www alternate of a domain.
        
        Args:
            domain: Original domain
            
        Returns:
            Alternate domain (www. added or removed)
        """
        if domain.startswith("www."):
            return domain[4:]  # Remove www.
        else:
            return f"www.{domain}"  # Add www.
    
    def _detect_file_format(self, url: str) -> str:
        """
        Detect file format from URL.
        
        Args:
            url: URL of the discovered file
            
        Returns:
            File format string (publiccode.yml, codemeta.json, code.json, contribute.json)
        """
        url_lower = url.lower()
        if 'publiccode.yml' in url_lower or 'publiccode.yaml' in url_lower:
            return 'publiccode.yml'
        elif 'codemeta.json' in url_lower:
            return 'codemeta.json'
        elif 'code.json' in url_lower:
            return 'code.json'
        elif 'contribute.json' in url_lower:
            return 'contribute.json'
        else:
            return 'unknown'
    
    def _try_domain(self, domain: str) -> DiscoveryResult:
        """
        Try to discover file on a specific domain with HTTPS/HTTP fallback.
        
        Args:
            domain: Domain to check
            
        Returns:
            DiscoveryResult
        """
        # Try HTTPS first
        if config.HTTPS_FIRST:
            result = self._try_protocol(domain, "https")
            if result.http_outcome == "success":
                return result
        
        # Fall back to HTTP
        result = self._try_protocol(domain, "http")
        return result

    def _try_protocol(self, domain: str, protocol: str) -> DiscoveryResult:
        """Try to discover file using a specific protocol."""
        base_url = f"{protocol}://{domain}"
        
        for path in config.PATHS_TO_TEST:
            url = urljoin(base_url, path)
            result = self._fetch_url(domain, url)
            
            if result.http_outcome == "success":
                logger.info(f"Found {result.file_format} at: {result.final_url}")
                return result
            
            # Small delay between requests to same domain
            time.sleep(config.RATE_LIMIT_DELAY)
        
        # No file found for this protocol
        return DiscoveryResult(
            domain=domain,
            http_outcome="not_found",
            error_message=f"No metadata file found via {protocol}"
        )

    def _fetch_url(self, domain: str, url: str) -> DiscoveryResult:
        """
        Fetch a specific URL and return discovery result.
        
        Args:
            domain: Original domain being checked
            url: Full URL to fetch
            
        Returns:
            DiscoveryResult with outcome
        """
        start_time = time.time()
        
        try:
            response = self.session.get(
                url,
                timeout=config.REQUEST_TIMEOUT,
                allow_redirects=config.FOLLOW_REDIRECTS,
                stream=True  # Stream to check size before downloading
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Check content length
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) > config.MAX_FILE_SIZE:
                logger.warning(f"File too large at {url}: {content_length} bytes")
                return DiscoveryResult(
                    domain=domain,
                    file_url=url,
                    http_status=response.status_code,
                    http_outcome="size_exceeded",
                    final_url=response.url,
                    error_message=f"File size {content_length} exceeds limit",
                    response_time_ms=response_time_ms
                )
            
            # Download content with size check
            content = b""
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > config.MAX_FILE_SIZE:
                    logger.warning(f"Downloaded content exceeded size limit at {url}")
                    return DiscoveryResult(
                        domain=domain,
                        file_url=url,
                        http_status=response.status_code,
                        http_outcome="size_exceeded",
                        final_url=response.url,
                        error_message=f"Downloaded size exceeds {config.MAX_FILE_SIZE} bytes",
                        response_time_ms=response_time_ms
                    )
            
            # Build redirect chain
            redirect_chain = []
            if response.history:
                redirect_chain = [r.url for r in response.history]
            
            # Check if successful
            if response.status_code == 200:
                logger.debug(f"Successfully fetched {url} ({len(content)} bytes)")
                return DiscoveryResult(
                    domain=domain,
                    file_url=url,
                    http_status=200,
                    http_outcome="success" if not redirect_chain else "redirect",
                    redirect_chain=redirect_chain,
                    final_url=response.url,
                    content=content,
                    file_format=self._detect_file_format(url),
                    response_time_ms=response_time_ms
                )
            else:
                logger.debug(f"HTTP {response.status_code} for {url}")
                return DiscoveryResult(
                    domain=domain,
                    file_url=url,
                    http_status=response.status_code,
                    http_outcome="error",
                    error_message=f"HTTP {response.status_code}",
                    response_time_ms=response_time_ms
                )
                
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url}")
            self.stats["timeouts"] += 1
            return DiscoveryResult(
                domain=domain,
                file_url=url,
                http_outcome="timeout",
                error_message="Request timeout",
                response_time_ms=(time.time() - start_time) * 1000
            )
            
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL error for {url}: {e}")
            self.stats["errors"] += 1
            return DiscoveryResult(
                domain=domain,
                file_url=url,
                http_outcome="ssl_error",
                error_message=f"SSL error: {str(e)[:100]}",
                response_time_ms=(time.time() - start_time) * 1000
            )
            
        except requests.exceptions.ConnectionError as e:
            logger.debug(f"Connection error for {url}: {e}")
            self.stats["errors"] += 1
            return DiscoveryResult(
                domain=domain,
                file_url=url,
                http_outcome="connection_error",
                error_message=f"Connection error: {str(e)[:100]}",
                response_time_ms=(time.time() - start_time) * 1000
            )
            
        except Exception as e:
            logger.error(f"Unexpected error fetching {url}: {e}")
            self.stats["errors"] += 1
            return DiscoveryResult(
                domain=domain,
                file_url=url,
                http_outcome="error",
                error_message=f"Unexpected error: {str(e)[:100]}",
                response_time_ms=(time.time() - start_time) * 1000
            )

    def get_stats(self) -> Dict:
        """Get crawler statistics."""
        return self.stats.copy()
