"""Shared utility helpers for the publiccode.yml discovery framework."""


def looks_like_html(snippet: str) -> bool:
    """Heuristic to detect HTML or error pages from a text snippet.

    Args:
        snippet: Lowercased text snippet (first ~1-2 KB of response body).

    Returns:
        True if the snippet appears to be HTML, False otherwise.
    """
    if not snippet:
        return False

    s = snippet.strip()
    if s.startswith('<!doctype') or s.startswith('<html'):
        return True

    # Presence of HTML tags early in the document
    _html_tags = ('<html', '<head', '<body', '<!doctype', '<script')
    if any(tag in s for tag in _html_tags):
        return True

    # CMS/error keywords that often indicate HTML landing pages
    keywords = [
        '404', 'not found', 'error', 'forbidden', 'unauthorized',
        'login', 'index of', '<title>error', 'php',
    ]
    if sum(1 for kw in keywords if kw in s) >= 2:
        return True

    # Many angle brackets -> likely HTML
    if s.count('<') > 5 and s.count('>') > 5:
        return True

    return False
