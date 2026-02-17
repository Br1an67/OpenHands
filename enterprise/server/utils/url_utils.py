"""Utility functions for URL handling.

This module provides secure URL utilities that prevent Host header poisoning
by using configured hostnames rather than deriving them from request headers.
"""

from urllib.parse import quote

from fastapi import Request
from server.constants import WEB_HOST


def get_canonical_base_url(request: Request | None = None) -> str:
    """Get the canonical base URL from WEB_HOST configuration.

    This prevents Host header poisoning attacks by using the configured
    WEB_HOST rather than deriving the hostname from the request.

    For localhost development, this uses the configured WEB_HOST (which defaults
    to 'localhost' or whatever is set in the environment). If WEB_HOST is
    'localhost', we use HTTP; otherwise HTTPS is enforced.

    Args:
        request: Optional request object. Currently unused but kept for
                 potential future use and API consistency.

    Returns:
        The canonical base URL (e.g., 'https://app.all-hands.dev')
    """
    scheme = 'http' if WEB_HOST == 'localhost' else 'https'
    return f'{scheme}://{WEB_HOST}'


def get_canonical_scheme() -> str:
    """Get the canonical scheme (http or https) based on WEB_HOST.

    Returns 'http' for localhost, 'https' for all other hosts.
    """
    return 'http' if WEB_HOST == 'localhost' else 'https'


def build_canonical_url(path: str, request: Request | None = None) -> str:
    """Build a canonical URL with the given path.

    This prevents Host header poisoning by using the configured WEB_HOST.

    Args:
        path: The URL path (should start with '/')
        request: Optional request object (unused, for API consistency)

    Returns:
        The full canonical URL (e.g., 'https://app.all-hands.dev/oauth/callback')
    """
    base_url = get_canonical_base_url(request)
    # Ensure path starts with /
    if not path.startswith('/'):
        path = '/' + path
    return f'{base_url}{path}'


def build_canonical_redirect_uri(path: str) -> str:
    """Build a canonical OAuth redirect URI.

    This is specifically for OAuth flows where the redirect_uri must match
    exactly what's registered with the OAuth provider.

    Args:
        path: The callback path (e.g., '/oauth/keycloak/callback')

    Returns:
        The full redirect URI (e.g., 'https://app.all-hands.dev/oauth/keycloak/callback')
    """
    return build_canonical_url(path)


def build_url_encoded_redirect_uri(path: str) -> str:
    """Build a URL-encoded OAuth redirect URI for use in query parameters.

    Args:
        path: The callback path (e.g., '/oauth/keycloak/callback')

    Returns:
        URL-encoded redirect URI (e.g., 'https%3A%2F%2Fapp.all-hands.dev%2Foauth%2Fkeycloak%2Fcallback')
    """
    redirect_uri = build_canonical_redirect_uri(path)
    return quote(redirect_uri, safe='')


def is_localhost() -> bool:
    """Check if the configured WEB_HOST is localhost.

    Returns:
        True if WEB_HOST is 'localhost', False otherwise
    """
    return WEB_HOST == 'localhost'
