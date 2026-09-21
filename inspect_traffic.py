"""Manual OpenSky inspection only: no detection, logging, or saved traffic."""

import os

from dotenv import load_dotenv

from sa_engine.opensky_adapter import parse_states
from sa_engine.opensky_auth import OpenSkyTokenManager
from sa_engine.opensky_client import OpenSkyClient


def main():
    load_dotenv()
    client_id = os.getenv('OPENSKY_CLIENT_ID')
    client_secret = os.getenv('OPENSKY_CLIENT_SECRET')
    if not client_id or not client_secret:
        raise ValueError('Set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in the environment or .env')
    tokens = OpenSkyTokenManager(client_id, client_secret)
    response = OpenSkyClient(tokens).fetch_states()
    states = response['states'] or []
    print(f"Response time: {response['time']}; raw state count: {len(states)}")
    if states:
        print(f'First raw state ({len(states[0])} fields): {states[0]}')
    aircraft, skipped = parse_states(response['states'])
    print(f'Parsed aircraft: {len(aircraft)}; missing-position rows filtered: {skipped}')


if __name__ == '__main__':
    main()
