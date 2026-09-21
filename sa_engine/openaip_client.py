"""HTTP transport for OpenAIP. Returns raw records, never domain objects."""

from math import isfinite

import requests

AIRSPACES_URL = "https://api.core.openaip.net/api/airspaces"


class OpenAIPResponseError(Exception):
    """The server response is not a usable paginated airspaces response."""


class OpenAIPClient:
    def __init__(self, api_key: str, *, timeout: float = 10, session=None):
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError("An OpenAIP API key is required")
        if type(timeout) not in (int, float) or not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        self._api_key = api_key
        self.timeout = timeout
        # An injected Session is owned/closed by the caller. The default requests
        # facade handles its own session lifecycle for each request.
        self._http = session if session is not None else requests

    def fetch_airspaces(self, country: str) -> list[dict]:
        """Fetch all pages in order, or fail without returning partial results.

        Pagination is one-based. A zero-page empty result is also accepted.
        Changing page counts and unexpected page numbers fail visibly.
        requests timeout/connection/HTTP exceptions propagate unchanged.
        """
        if not isinstance(country, str) or len(country) != 2 or not country.isascii() or not country.isalpha():
            raise ValueError("country must be a two-letter country code")
        country = country.upper()
        items = []
        page = 1
        total_pages = None
        while True:
            response = self._http.get(
                AIRSPACES_URL,
                headers={"x-openaip-api-key": self._api_key},
                params={"country": country, "page": page},
                timeout=self.timeout,
            )
            try:
                response.raise_for_status()
                try:
                    data = response.json()
                except ValueError as exc:
                    raise OpenAIPResponseError(f"Page {page}: invalid JSON") from exc
            finally:
                response.close()

            if not isinstance(data, dict):
                raise OpenAIPResponseError(f"Page {page}: expected an object")
            returned_page = data.get("page")
            count = data.get("totalPages")
            batch = data.get("items")
            if type(returned_page) is not int or returned_page != page:
                raise OpenAIPResponseError(f"Page {page}: unexpected page number")
            if type(count) is not int or count < 0:
                raise OpenAIPResponseError(f"Page {page}: invalid totalPages")
            if not isinstance(batch, list) or any(not isinstance(item, dict) for item in batch):
                raise OpenAIPResponseError(f"Page {page}: items must be a list of objects")
            if total_pages is not None and count != total_pages:
                raise OpenAIPResponseError(f"Page {page}: totalPages changed during pagination")
            total_pages = count
            if count == 0:
                if page != 1 or batch:
                    raise OpenAIPResponseError(f"Page {page}: inconsistent empty result")
                return []
            if page > count or (not batch and count > 1):
                raise OpenAIPResponseError(f"Page {page}: inconsistent pagination")
            items.extend(batch)
            if page == total_pages:
                return items
            page += 1
