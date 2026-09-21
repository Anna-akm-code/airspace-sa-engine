"""OpenSky OAuth2 client-credentials tokens; no traffic or domain parsing."""

from math import isfinite
from time import monotonic

import requests

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network/"
    "protocol/openid-connect/token"
)


class OpenSkyTokenResponseError(Exception):
    """The token endpoint returned malformed data (not an HTTP failure)."""


class OpenSkyTokenManager:
    def __init__(self, client_id: str, client_secret: str, *, timeout: float = 10,
                 refresh_margin: float = 30, session=None, clock=monotonic):
        if any(not isinstance(value, str) or not value.strip()
               for value in (client_id, client_secret)):
            raise ValueError("OpenSky client_id and client_secret are required")
        for name, value in (("timeout", timeout), ("refresh_margin", refresh_margin)):
            if type(value) not in (int, float) or not isfinite(value) or value < 0:
                raise ValueError(f"{name} must be a finite nonnegative number")
        if timeout == 0:
            raise ValueError("timeout must be positive")
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = session if session is not None else requests
        self._clock = clock
        self._timeout = timeout
        self._margin = refresh_margin
        self._token = None
        self._expires_at = 0

    def get_token(self) -> str:
        """Reuse a token until its expiry margin; no retries or refresh-token flow.

        Expiry is measured from request start, conservatively including network
        latency. Injected sessions belong to the caller. Not thread-safe.
        """
        now = self._clock()
        if self._token is not None and now < self._expires_at - self._margin:
            return self._token
        response = self._http.post(
            TOKEN_URL,
            data={"grant_type": "client_credentials", "client_id": self._client_id,
                  "client_secret": self._client_secret},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self._timeout,
        )
        try:
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError as exc:
                raise OpenSkyTokenResponseError("Token response is not valid JSON") from exc
        finally:
            response.close()
        if not isinstance(data, dict):
            raise OpenSkyTokenResponseError("Token response must be an object")
        token = data.get("access_token")
        lifetime = data.get("expires_in")
        if not isinstance(token, str) or not token or any(c.isspace() for c in token):
            raise OpenSkyTokenResponseError("access_token must be a nonempty token string")
        if (type(lifetime) not in (int, float) or not isfinite(lifetime)
                or lifetime <= 0):
            raise OpenSkyTokenResponseError("expires_in must be a positive finite number")
        expires_at = now + lifetime
        if self._clock() >= expires_at:
            raise OpenSkyTokenResponseError("Token expired during its request")
        # Update cache only after the entire response has been validated.
        self._token = token
        self._expires_at = expires_at
        return token
