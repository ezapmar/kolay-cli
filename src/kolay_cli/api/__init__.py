"""
API package for kolay-cli.
Provides the KolayClient for HTTP requests and centralized error handling.
"""
from .client import KolayClient, safe_id
from .errors import APIError, HTTP_ERRORS

__all__ = ["KolayClient", "safe_id", "APIError", "HTTP_ERRORS"]
