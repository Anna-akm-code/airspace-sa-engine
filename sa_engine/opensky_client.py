"""OpenSky traffic HTTP client. Returns raw data, never Aircraft objects."""

from math import isfinite

import requests

from .opensky_auth import OpenSkyTokenManager

STATES_URL = "https://opensky-network.org/api/states/all"
# (lamin, lomin, lamax, lomax): approximate query rectangle, not national borders.
FINLAND_BBOX = (59.0, 19.0, 70.5, 32.0)


class OpenSkyResponseError(Exception):
    """Malformed traffic response; distinct from transport/HTTP failures."""


class OpenSkyClient:
    def __init__(self, tokens: OpenSkyTokenManager, *, timeout: float = 10, session=None):
        if type(timeout) not in (int, float) or not isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive finite number")
        self._tokens = tokens
        self._timeout = timeout
        self._http = session if session is not None else requests

    def fetch_states(self, bbox=FINLAND_BBOX) -> dict:
        """Return the time/states envelope unchanged, including states=None.

        None or [] means no states; a missing states key is malformed. Row field
        validation belongs to the adapter. HTTP errors (including 401/429) are
        visible to the caller, without retries. Injected sessions are caller-owned.
        """
        if (not isinstance(bbox, (tuple, list)) or len(bbox) != 4
                or any(type(v) not in (int, float) or not isfinite(v) for v in bbox)):
            raise ValueError("bbox must contain four finite numbers: lamin,lomin,lamax,lomax")
        lamin, lomin, lamax, lomax = bbox
        if not (-90 <= lamin < lamax <= 90 and -180 <= lomin < lomax <= 180):
            raise ValueError("bbox must have ordered WGS84 bounds; no dateline wrapping")
        response = self._http.get(
            STATES_URL,
            headers={"Authorization": f"Bearer {self._tokens.get_token()}"},
            params=dict(lamin=lamin, lomin=lomin, lamax=lamax, lomax=lomax, extended=1),
            timeout=self._timeout,
        )
        try:
            response.raise_for_status()
            try:
                data = response.json()
            except ValueError as exc:
                raise OpenSkyResponseError("Traffic response is not valid JSON") from exc
        finally:
            response.close()
        if not isinstance(data, dict) or type(data.get("time")) is not int or data["time"] < 0:
            raise OpenSkyResponseError("Traffic response requires a nonnegative integer time")
        if "states" not in data:
            raise OpenSkyResponseError("Traffic response is missing states")
        states = data["states"]
        if states is not None and (not isinstance(states, list)
                                   or any(not isinstance(row, list) for row in states)):
            raise OpenSkyResponseError("states must be null or an array of state arrays")
        return data
