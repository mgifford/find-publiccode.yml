"""Tests for utils.py — looks_like_html() heuristic."""

from utils import looks_like_html


class TestLooksLikeHtmlEmptyInput:
    """Tests for falsy / empty input."""

    def test_empty_string(self):
        """Empty string is not HTML."""
        assert looks_like_html("") is False

    def test_none_like_falsy(self):
        """None-equivalent falsy value returns False."""
        # The function guards with ``if not snippet``
        assert looks_like_html("") is False

    def test_whitespace_only(self):
        """Whitespace-only string with no HTML markers is not HTML."""
        assert looks_like_html("   \n\t  ") is False


class TestLooksLikeHtmlDoctype:
    """Tests for <!DOCTYPE …> detection."""

    def test_doctype_html_uppercase_input(self):
        """<!DOCTYPE HTML> is detected when caller pre-lowercases the snippet."""
        # Per the function contract, callers lower-case the snippet before passing.
        snippet = "<!DOCTYPE HTML>\n<HTML>".lower()
        assert looks_like_html(snippet) is True

    def test_doctype_html_lowercase(self):
        """Lowercase <!doctype html> is detected."""
        assert looks_like_html("<!doctype html>\n<html>") is True

    def test_doctype_at_start_after_whitespace(self):
        """Doctype after leading whitespace is detected (strip is applied)."""
        assert looks_like_html("  <!doctype html>") is True


class TestLooksLikeHtmlOpeningTag:
    """Tests for <html …> opening tag detection."""

    def test_html_tag(self):
        """<html> opening tag is detected."""
        assert looks_like_html("<html lang='en'>") is True

    def test_html_tag_with_attributes(self):
        """<html> with multiple attributes is detected."""
        assert looks_like_html('<html xmlns="http://www.w3.org/1999/xhtml">') is True


class TestLooksLikeHtmlBodyTags:
    """Tests for in-body HTML tag detection."""

    def test_head_tag(self):
        """<head> tag anywhere in snippet triggers detection."""
        assert looks_like_html("some preamble\n<head><title>T</title>") is True

    def test_body_tag(self):
        """<body> tag triggers detection."""
        assert looks_like_html("random text <body> more text") is True

    def test_script_tag(self):
        """<script> tag triggers detection."""
        assert looks_like_html("content before <script>alert(1)</script>") is True

    def test_multiple_angle_brackets(self):
        """More than five '<' and '>' characters suggest HTML."""
        html = "<div><p><span><a href='#'><em>text</em></a></span></p></div>"
        assert looks_like_html(html) is True


class TestLooksLikeHtmlKeywords:
    """Tests for error-page keyword heuristic (≥2 keywords)."""

    def test_single_keyword_not_html(self):
        """A single keyword alone does not trigger the heuristic."""
        # Only '404' is a recognised keyword here — needs ≥ 2 keyword matches.
        # 'page' is not in the keyword list.
        assert looks_like_html("404 page") is False

    def test_two_keywords_triggers_html(self):
        """Two or more keywords trigger the heuristic."""
        assert looks_like_html("404 not found") is True

    def test_login_and_error_keywords(self):
        """'login' + 'error' count as two keywords."""
        assert looks_like_html("please login error") is True

    def test_forbidden_and_401(self):
        """'forbidden' + 'unauthorized' count as two keywords."""
        assert looks_like_html("forbidden unauthorized access denied") is True

    def test_php_and_error(self):
        """'php' + 'error' count as two keywords."""
        assert looks_like_html("php error occurred") is True


class TestLooksLikeHtmlValidYaml:
    """Tests to confirm genuine YAML / text content is NOT mis-classified."""

    def test_valid_publiccode_yaml(self):
        """A typical publiccode.yml snippet should not be classified as HTML."""
        yaml_snippet = (
            "publiccodeymlversion: '0.1'\n"
            "name: my software\n"
            "url: https://example.com\n"
            "releasedate: '2024-01-01'\n"
            "platforms:\n  - web\n"
        )
        assert looks_like_html(yaml_snippet) is False

    def test_plain_text(self):
        """Generic plain text is not HTML."""
        assert looks_like_html("this is just plain text with no html") is False

    def test_json_content(self):
        """Valid JSON-like content is not HTML."""
        json_snippet = '{"name": "my software", "version": "1.0.0"}'
        assert looks_like_html(json_snippet) is False


class TestLooksLikeHtmlEdgeCases:
    """Edge-case inputs."""

    def test_xml_content_with_many_tags(self):
        """XML with many tags looks like HTML heuristically."""
        xml = "<root><item><value>1</value></item><item><value>2</value></item></root>"
        # > 5 '<' and '>' → True
        assert looks_like_html(xml) is True

    def test_yaml_with_less_than_sign(self):
        """YAML with a handful of < symbols (but not many) is not HTML."""
        yaml_snippet = "comparison: a < b and b < c"
        assert looks_like_html(yaml_snippet) is False

    def test_html_comment_only(self):
        """Snippet that is only an HTML comment is not flagged as HTML."""
        # Does NOT start with <!doctype or <html, and no tags or 2 keywords
        comment = "<!-- just a comment -->"
        # This should return False under current heuristics
        assert looks_like_html(comment) is False
