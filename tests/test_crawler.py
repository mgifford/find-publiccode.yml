"""Tests for crawler.py — PublicCodeCrawler and DiscoveryResult."""

from unittest.mock import MagicMock, patch

import pytest
import requests

from crawler import DiscoveryResult, PublicCodeCrawler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def crawler():
    """Return a PublicCodeCrawler with a mocked requests session."""
    with patch("crawler.requests.Session") as mock_session_cls:
        mock_session_cls.return_value = MagicMock()
        c = PublicCodeCrawler()
    c.session = MagicMock()
    return c


def _make_response(
    status_code=200,
    content=b"",
    url="https://example.gov/publiccode.yml",
    history=None,
    headers=None,
):
    """Build a mock requests.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.url = url
    resp.history = history or []
    resp.headers = headers or {}
    # iter_content yields content in one chunk
    resp.iter_content = MagicMock(
        return_value=iter([content]) if content else iter([])
    )
    return resp


# ---------------------------------------------------------------------------
# DiscoveryResult dataclass
# ---------------------------------------------------------------------------

class TestDiscoveryResult:
    """Tests for the DiscoveryResult dataclass."""

    def test_defaults(self):
        """Default values are set correctly."""
        r = DiscoveryResult(domain="example.gov")
        assert r.domain == "example.gov"
        assert r.http_outcome == "not_attempted"
        assert r.redirect_chain == []
        assert r.file_url is None
        assert r.content is None

    def test_discovery_timestamp_auto_set(self):
        """discovery_timestamp is automatically populated."""
        r = DiscoveryResult(domain="x.gov")
        assert r.discovery_timestamp is not None
        assert "T" in r.discovery_timestamp

    def test_redirect_chain_not_shared(self):
        """Each DiscoveryResult instance has its own redirect_chain list."""
        r1 = DiscoveryResult(domain="a.gov")
        r2 = DiscoveryResult(domain="b.gov")
        r1.redirect_chain.append("https://a.gov/redirect")
        assert r2.redirect_chain == []


# ---------------------------------------------------------------------------
# _detect_file_format
# ---------------------------------------------------------------------------

class TestDetectFileFormat:
    """Tests for _detect_file_format."""

    @pytest.mark.parametrize("url,expected", [
        ("https://example.gov/publiccode.yml", "publiccode.yml"),
        ("https://example.gov/.well-known/publiccode.yml", "publiccode.yml"),
        ("https://example.gov/publiccode.yaml", "publiccode.yml"),
        ("https://example.gov/.well-known/publiccode.yaml", "publiccode.yml"),
        ("https://example.gov/PUBLICCODE.YML", "publiccode.yml"),  # case-insensitive
        ("https://example.gov/codemeta.json", "codemeta.json"),
        ("https://example.gov/.well-known/codemeta.json", "codemeta.json"),
        ("https://example.gov/code.json", "code.json"),
        ("https://example.gov/.well-known/code.json", "code.json"),
        ("https://example.gov/contribute.json", "contribute.json"),
        ("https://example.gov/.well-known/contribute.json", "contribute.json"),
        ("https://example.gov/unknown.txt", "unknown"),
    ])
    def test_format_detection(self, url, expected, crawler):
        """URL patterns map to the correct file format string."""
        assert crawler._detect_file_format(url) == expected


# ---------------------------------------------------------------------------
# _get_alternate_domain
# ---------------------------------------------------------------------------

class TestGetAlternateDomain:
    """Tests for _get_alternate_domain."""

    def test_adds_www_to_bare_domain(self, crawler):
        """A domain without www. gets www. prepended."""
        assert crawler._get_alternate_domain("example.gov") == "www.example.gov"

    def test_removes_www_from_www_domain(self, crawler):
        """A domain starting with www. gets the prefix stripped."""
        assert crawler._get_alternate_domain("www.example.gov") == "example.gov"

    def test_non_www_subdomain_gets_www_prepended(self, crawler):
        """A subdomain (not www.) gets www. prepended."""
        assert crawler._get_alternate_domain("api.example.gov") == "www.api.example.gov"


# ---------------------------------------------------------------------------
# _fetch_url — mocked HTTP layer
# ---------------------------------------------------------------------------

VALID_YAML_BYTES = b"publiccodeYmlVersion: '0.1'\nname: App\nurl: https://x.gov\n"


class TestFetchUrl:
    """Tests for _fetch_url using mocked network responses."""

    def test_success_200(self, crawler):
        """HTTP 200 with YAML content returns outcome='success'."""
        resp = _make_response(
            status_code=200,
            content=VALID_YAML_BYTES,
            url="https://example.gov/publiccode.yml",
        )
        # HEAD succeeds with no Content-Length, not html
        head_resp = MagicMock()
        head_resp.headers = {}
        head_resp.status_code = 200
        head_resp.url = "https://example.gov/publiccode.yml"
        crawler.session.head.return_value = head_resp
        crawler.session.get.return_value = resp

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")

        assert result.http_outcome == "success"
        assert result.http_status == 200
        assert result.content == VALID_YAML_BYTES
        assert result.file_format == "publiccode.yml"

    def test_404_returns_error(self, crawler):
        """HTTP 404 response returns outcome='error'."""
        resp = _make_response(status_code=404, url="https://example.gov/publiccode.yml")
        head_resp = MagicMock()
        head_resp.headers = {}
        head_resp.status_code = 404
        head_resp.url = "https://example.gov/publiccode.yml"
        crawler.session.head.return_value = head_resp
        crawler.session.get.return_value = resp

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "error"
        assert result.http_status == 404

    def test_timeout_returns_timeout(self, crawler):
        """Request timeout is caught and returns outcome='timeout'."""
        crawler.session.head.side_effect = requests.exceptions.Timeout()
        crawler.session.get.side_effect = requests.exceptions.Timeout()

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "timeout"

    def test_ssl_error_handled(self, crawler):
        """SSL error is caught and returns outcome='ssl_error'."""
        crawler.session.head.side_effect = requests.exceptions.SSLError("cert error")
        crawler.session.get.side_effect = requests.exceptions.SSLError("cert error")

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "ssl_error"

    def test_connection_error_handled(self, crawler):
        """Connection error is caught and returns outcome='connection_error'."""
        err = requests.exceptions.ConnectionError("refused")
        crawler.session.head.side_effect = err
        crawler.session.get.side_effect = err

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "connection_error"

    def test_size_exceeded_via_content_length_header(self, crawler):
        """Response with Content-Length exceeding limit returns 'size_exceeded'."""
        large_size = str(600 * 1024)  # 600 KB > 512 KB limit
        head_resp = MagicMock()
        head_resp.headers = {"Content-Length": large_size}
        head_resp.status_code = 200
        head_resp.url = "https://example.gov/publiccode.yml"
        crawler.session.head.return_value = head_resp

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "size_exceeded"

    def test_html_content_type_from_head_skips_download(self, crawler):
        """HEAD response with HTML content-type returns 'html_content'."""
        head_resp = MagicMock()
        head_resp.headers = {"Content-Type": "text/html; charset=utf-8"}
        head_resp.status_code = 200
        head_resp.url = "https://example.gov/publiccode.yml"
        crawler.session.head.return_value = head_resp

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "html_content"
        # GET should NOT have been called
        crawler.session.get.assert_not_called()

    def test_html_downloaded_content_detected(self, crawler):
        """Downloaded HTML content is caught and returns 'html_content'."""
        html_content = (
            b"<!doctype html><html><head></head>"
            b"<body>Not Found</body></html>"
        )
        resp = _make_response(
            status_code=200,
            content=html_content,
            url="https://example.gov/publiccode.yml"
        )
        head_resp = MagicMock()
        head_resp.headers = {}
        crawler.session.head.return_value = head_resp
        crawler.session.get.return_value = resp

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "html_content"

    def test_redirect_chain_populated(self, crawler):
        """Redirect history is captured in redirect_chain."""
        redir = MagicMock()
        redir.url = "https://www.example.gov/publiccode.yml"
        resp = _make_response(
            status_code=200,
            content=VALID_YAML_BYTES,
            url="https://example.gov/publiccode.yml",
            history=[redir],
        )
        head_resp = MagicMock()
        head_resp.headers = {}
        crawler.session.head.return_value = head_resp
        crawler.session.get.return_value = resp

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.redirect_chain == ["https://www.example.gov/publiccode.yml"]
        assert result.http_outcome == "redirect"

    def test_unexpected_exception_handled(self, crawler):
        """An unexpected exception during fetch returns outcome='error'."""
        crawler.session.head.side_effect = RuntimeError("unexpected")
        crawler.session.get.side_effect = RuntimeError("unexpected")

        result = crawler._fetch_url("example.gov", "https://example.gov/publiccode.yml")
        assert result.http_outcome == "error"


# ---------------------------------------------------------------------------
# _try_domain / _try_protocol (high-level)
# ---------------------------------------------------------------------------

class TestTryDomain:
    """Tests for _try_domain."""

    def test_returns_success_on_first_https_hit(self, crawler):
        """When HTTPS succeeds, _try_domain returns without trying HTTP."""
        success = DiscoveryResult(
            domain="example.gov",
            http_outcome="success",
            file_format="publiccode.yml",
            content=VALID_YAML_BYTES,
        )
        with patch.object(crawler, "_try_protocol", return_value=success) as mock_tp:
            result = crawler._try_domain("example.gov")

        assert result.http_outcome == "success"
        # Only called once (HTTPS succeeded)
        mock_tp.assert_called_once()

    def test_falls_back_to_http_when_https_fails(self, crawler):
        """When HTTPS fails, _try_domain falls back to HTTP."""
        not_found = DiscoveryResult(
            domain="example.gov", http_outcome="not_found"
        )
        http_success = DiscoveryResult(
            domain="example.gov",
            http_outcome="success",
            file_format="publiccode.yml",
        )
        with patch.object(
            crawler, "_try_protocol", side_effect=[not_found, http_success]
        ):
            result = crawler._try_domain("example.gov")

        assert result.http_outcome == "success"


# ---------------------------------------------------------------------------
# discover() — www/non-www alternates
# ---------------------------------------------------------------------------

class TestDiscover:
    """Tests for discover()."""

    def test_discover_success_increments_stat(self, crawler):
        """Successful discovery increments files_found stat."""
        success = DiscoveryResult(
            domain="example.gov",
            http_outcome="success",
            file_format="publiccode.yml",
            content=VALID_YAML_BYTES,
        )
        with patch.object(crawler, "_try_domain", return_value=success):
            crawler.discover("example.gov")

        assert crawler.stats["files_found"] == 1
        assert crawler.stats["domains_checked"] == 1

    def test_discover_not_found_tries_www_alternate(self, crawler):
        """When primary fails, www alternate is attempted."""
        not_found = DiscoveryResult(domain="example.gov", http_outcome="not_found")
        www_success = DiscoveryResult(
            domain="www.example.gov",
            http_outcome="success",
            file_format="publiccode.yml",
        )
        with patch.object(
            crawler, "_try_domain", side_effect=[not_found, www_success]
        ):
            result = crawler.discover("example.gov")

        assert result.http_outcome == "success"
        assert result.domain == "example.gov"  # domain reset to original

    def test_discover_returns_not_found_when_both_fail(self, crawler):
        """Returns not_found when both primary and alternate fail."""
        not_found = DiscoveryResult(domain="example.gov", http_outcome="not_found")
        with patch.object(crawler, "_try_domain", return_value=not_found):
            result = crawler.discover("example.gov")

        assert result.http_outcome == "not_found"


# ---------------------------------------------------------------------------
# _check_common_files
# ---------------------------------------------------------------------------

class TestCheckCommonFiles:
    """Tests for _check_common_files (robots.txt / humans.txt hinting)."""

    def test_returns_none_on_connection_error(self, crawler):
        """Connection error during robots.txt fetch returns None."""
        crawler.session.get.side_effect = Exception("connection refused")
        result = crawler._check_common_files("example.gov", "https://example.gov")
        assert result is None

    def test_returns_none_when_no_publiccode_reference(self, crawler):
        """robots.txt without publiccode reference returns None."""
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "User-agent: *\nDisallow: /admin\n"
        crawler.session.get.return_value = resp

        result = crawler._check_common_files("example.gov", "https://example.gov")
        assert result is None

    def test_returns_none_on_non_200_response(self, crawler):
        """Non-200 status code for robots.txt is skipped."""
        resp = MagicMock()
        resp.status_code = 404
        crawler.session.get.return_value = resp

        result = crawler._check_common_files("example.gov", "https://example.gov")
        assert result is None


# ---------------------------------------------------------------------------
# get_stats
# ---------------------------------------------------------------------------

class TestGetStats:
    """Tests for get_stats."""

    def test_initial_stats(self, crawler):
        """Initial stats are all zero."""
        stats = crawler.get_stats()
        assert stats["domains_checked"] == 0
        assert stats["files_found"] == 0
        assert stats["errors"] == 0
        assert stats["timeouts"] == 0

    def test_stats_returns_copy(self, crawler):
        """get_stats returns a copy, not the internal dict."""
        stats = crawler.get_stats()
        stats["files_found"] = 999
        assert crawler.stats["files_found"] == 0
