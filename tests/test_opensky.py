"""Offline Stage 4 tests. No traffic is connected to detection."""

import json
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from sa_engine.opensky_adapter import parse_state_vector, parse_states
from sa_engine.opensky_auth import (
    TOKEN_URL,
    OpenSkyTokenManager,
    OpenSkyTokenResponseError,
)
from sa_engine.opensky_client import (
    FINLAND_BBOX,
    STATES_URL,
    OpenSkyClient,
    OpenSkyResponseError,
)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Real HTTP is forbidden in Stage 4 tests')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


@pytest.fixture
def payload():
    path = Path(__file__).parent / 'fixtures' / 'opensky_states_synthetic.json'
    return json.loads(path.read_text())


def reply(data):
    response = Mock()
    response.json.return_value = data
    return response


def token_setup(data=None):
    session = Mock()
    session.post.return_value = reply(data if data is not None else
                                      {'access_token': 'dummy-token', 'expires_in': 120})
    clock = Mock(return_value=1000)
    manager = OpenSkyTokenManager('dummy-id', 'dummy-secret', session=session,
                                 clock=clock, timeout=7, refresh_margin=30)
    return manager, session, clock


def test_token_first_request_and_reuse():
    manager, session, clock = token_setup()
    assert manager.get_token() == 'dummy-token'
    clock.return_value = 1089
    assert manager.get_token() == 'dummy-token'
    session.post.assert_called_once_with(TOKEN_URL,
        data={'grant_type': 'client_credentials', 'client_id': 'dummy-id',
              'client_secret': 'dummy-secret'},
        headers={'Content-Type': 'application/x-www-form-urlencoded'}, timeout=7)
    session.post.return_value.close.assert_called_once()


@pytest.mark.parametrize('now', [1090, 1121])
def test_refresh_at_margin_and_after_expiry(now):
    manager, session, clock = token_setup()
    manager.get_token()
    clock.return_value = now
    session.post.return_value = reply({'access_token': 'new-token', 'expires_in': 120})
    assert manager.get_token() == 'new-token'
    assert session.post.call_count == 2


def test_short_lifetime_is_not_reused_inside_margin():
    manager, session, _ = token_setup({'access_token': 'short', 'expires_in': 10})
    manager.get_token()
    manager.get_token()
    assert session.post.call_count == 2


def test_network_time_counts_towards_expiry():
    manager, _, clock = token_setup()
    clock.side_effect = [1000, 1121]
    with pytest.raises(OpenSkyTokenResponseError, match='expired during'):
        manager.get_token()


@pytest.mark.parametrize('data', [[], {}, {'expires_in': 120},
    {'access_token': None, 'expires_in': 120}, {'access_token': '', 'expires_in': 120},
    {'access_token': 'a b', 'expires_in': 120}, {'access_token': 123, 'expires_in': 120},
    {'access_token': 'token'}, {'access_token': 'token', 'expires_in': None},
    {'access_token': 'token', 'expires_in': '120'},
    {'access_token': 'token', 'expires_in': True},
    {'access_token': 'token', 'expires_in': 0},
    {'access_token': 'token', 'expires_in': -1},
    {'access_token': 'token', 'expires_in': float('inf')},
    {'access_token': 'token', 'expires_in': float('nan')},
])
def test_malformed_token_response(data):
    manager, session, _ = token_setup(data)
    with pytest.raises(OpenSkyTokenResponseError):
        manager.get_token()
    session.post.return_value.close.assert_called_once()


def test_invalid_token_json():
    manager, session, _ = token_setup()
    session.post.return_value.json.side_effect = ValueError('invalid JSON')
    with pytest.raises(OpenSkyTokenResponseError):
        manager.get_token()


def test_auth_http_failure():
    manager, session, _ = token_setup()
    session.post.return_value.raise_for_status.side_effect = requests.HTTPError('401')
    with pytest.raises(requests.HTTPError):
        manager.get_token()
    session.post.return_value.json.assert_not_called()
    session.post.return_value.close.assert_called_once()
    assert session.post.call_count == 1


def test_failed_refresh_does_not_return_old_token():
    manager, session, clock = token_setup()
    manager.get_token()
    clock.return_value = 1090
    session.post.side_effect = requests.Timeout('timeout')
    with pytest.raises(requests.Timeout):
        manager.get_token()
    assert session.post.call_count == 2


@pytest.mark.parametrize('kwargs', [{'client_id': ''}, {'client_secret': None},
    {'timeout': 0}, {'timeout': True}, {'refresh_margin': -1},
    {'refresh_margin': float('nan')}])
def test_invalid_token_configuration(kwargs):
    options = dict(client_id='dummy', client_secret='dummy')
    options.update(kwargs)
    with pytest.raises(ValueError):
        OpenSkyTokenManager(**options)


def traffic_setup(data):
    tokens = Mock()
    tokens.get_token.return_value = 'dummy-token'
    session = Mock()
    session.get.return_value = reply(data)
    return OpenSkyClient(tokens, session=session, timeout=8), session, tokens


def test_traffic_request_contract(payload):
    client, session, tokens = traffic_setup(payload)
    assert client.fetch_states() is payload
    session.get.assert_called_once_with(STATES_URL,
        headers={'Authorization': 'Bearer dummy-token'},
        params=dict(lamin=59.0, lomin=19.0, lamax=70.5, lomax=32.0, extended=1), timeout=8)
    tokens.get_token.assert_called_once()
    session.get.return_value.close.assert_called_once()
    assert FINLAND_BBOX == (59.0, 19.0, 70.5, 32.0)


def test_custom_bbox():
    client, session, _ = traffic_setup({'time': 1000, 'states': []})
    client.fetch_states((60, 24, 61, 25))
    assert session.get.call_args.kwargs['params'] == dict(lamin=60,lomin=24,lamax=61,lomax=25,extended=1)


@pytest.mark.parametrize('states', [None, []])
def test_empty_states(states):
    client, _, _ = traffic_setup({'time': 1000, 'states': states})
    assert client.fetch_states()['states'] == states
    assert parse_states(states) == ([], 0)


@pytest.mark.parametrize('data', [None, [], {}, {'time': 1000},
    {'time': True, 'states': []}, {'time': '1000', 'states': []},
    {'time': -1, 'states': []}, {'time': 1000, 'states': {}},
    {'time': 1000, 'states': [None]}])
def test_malformed_traffic(data):
    client, _, _ = traffic_setup(data)
    with pytest.raises(OpenSkyResponseError):
        client.fetch_states()


def test_invalid_traffic_json():
    client, session, _ = traffic_setup(None)
    session.get.return_value.json.side_effect = ValueError('invalid')
    with pytest.raises(OpenSkyResponseError):
        client.fetch_states()
    session.get.return_value.close.assert_called_once()


@pytest.mark.parametrize('error', [requests.Timeout('timeout'), requests.ConnectionError('offline')])
def test_transport_errors(error):
    client, session, _ = traffic_setup(None)
    session.get.side_effect = error
    with pytest.raises(type(error)) as caught:
        client.fetch_states()
    assert caught.value is error
    assert session.get.call_count == 1
    manager, auth_session, _ = token_setup()
    auth_session.post.side_effect = error
    with pytest.raises(type(error)):
        manager.get_token()
    assert auth_session.post.call_count == 1


@pytest.mark.parametrize('status', [401, 403, 429, 500])
def test_traffic_http_errors(status):
    client, session, _ = traffic_setup(None)
    session.get.return_value.raise_for_status.side_effect = requests.HTTPError(str(status))
    with pytest.raises(requests.HTTPError):
        client.fetch_states()
    session.get.return_value.json.assert_not_called()
    session.get.return_value.close.assert_called_once()
    assert session.get.call_count == 1


@pytest.mark.parametrize('bbox', [None, (1,2), (61,24,60,25), (-91,0,1,2),
    (0,179,1,-179), (0,0,float('nan'),1), (True,0,2,1)])
def test_invalid_bbox_before_auth(bbox):
    client, session, tokens = traffic_setup(None)
    with pytest.raises(ValueError):
        client.fetch_states(bbox)
    tokens.get_token.assert_not_called()
    session.get.assert_not_called()


def test_normal_vector(payload):
    aircraft = parse_state_vector(payload['states'][0])
    assert aircraft.icao24 == 'abc001'
    assert aircraft.callsign == 'FIN123'
    assert (aircraft.lon, aircraft.lat) == (24.9, 60.2)
    assert aircraft.baro_altitude_ft == pytest.approx(3280.84)
    assert aircraft.geo_altitude_ft == pytest.approx(3608.924)
    assert (aircraft.time_position, aircraft.last_contact) == (1000,1002)
    assert (aircraft.velocity, aircraft.heading) == (80,270)
    assert aircraft.on_ground is False
    assert (aircraft.position_source, aircraft.category) == (0,3)


@pytest.mark.parametrize('callsign,expected', [(None,None), ('   ',None), (' ABC ', 'ABC')])
def test_callsign(payload, callsign, expected):
    payload['states'][0][1] = callsign
    assert parse_state_vector(payload['states'][0]).callsign == expected


def test_null_altitude_and_metadata_preserved(payload):
    aircraft = parse_state_vector(payload['states'][1])
    assert aircraft.baro_altitude_ft is None
    assert aircraft.geo_altitude_ft is None
    assert aircraft.velocity is None
    assert aircraft.heading is None


@pytest.mark.parametrize('index', [5,6])
def test_missing_position_returns_none(payload, index):
    row = payload['states'][0]
    row[index] = None
    assert parse_state_vector(row) is None


def test_ground_flarm_uav_and_missing_time(payload):
    assert parse_state_vector(payload['states'][2]).on_ground is True
    assert parse_state_vector(payload['states'][3]).position_source == 3
    assert parse_state_vector(payload['states'][4]).category == 14
    row = payload['states'][0]
    row[3] = None
    row[17] = None
    aircraft = parse_state_vector(row)
    assert aircraft.time_position is None
    assert aircraft.last_contact == 1002
    assert aircraft.category is None


@pytest.mark.parametrize('raw', [None, {}, [], [None]*17])
def test_short_or_nonarray_vector(raw):
    with pytest.raises(ValueError, match='18 fields'):
        parse_state_vector(raw)


@pytest.mark.parametrize('index,value', [(0,'bad'), (1,1), (3,True), (4,None),
    (5,181), (6,91), (7,'1000'), (7,float('inf')), (8,1), (9,float('nan')),
    (10,True), (13,float('nan')), (16,None), (17,-1)])
def test_malformed_mapped_fields(payload, index, value):
    row = payload['states'][0]
    row[index] = value
    with pytest.raises(ValueError):
        parse_state_vector(row)


def test_batch_reports_bad_row_even_without_position(payload):
    payload['states'][5][8] = 'invalid'
    with pytest.raises(ValueError, match='row 5.*on_ground'):
        parse_states(payload['states'])


def test_appended_fields_are_ignored(payload):
    row = payload['states'][0]
    assert parse_state_vector(row + ['future']) == parse_state_vector(row)


def test_offline_auth_client_adapter_integration(payload):
    manager, auth_session, _ = token_setup()
    traffic_session = Mock()
    traffic_session.get.return_value = reply(payload)
    client = OpenSkyClient(manager, session=traffic_session)
    raw = client.fetch_states()
    aircraft, skipped = parse_states(raw['states'])
    assert raw['time'] == 1010
    assert len(aircraft) == 5
    assert skipped == 1
    assert [item.icao24 for item in aircraft] == ['abc001','abc002','abc003','abc004','abc005']
    assert aircraft[1].baro_altitude_ft is None
    assert aircraft[2].on_ground
    assert aircraft[3].position_source == 3
    assert aircraft[4].category == 14
    assert traffic_session.get.call_args.kwargs['headers'] == {'Authorization': 'Bearer dummy-token'}
    client.fetch_states()
    assert auth_session.post.call_count == 1


def test_configurable_zero_margin_exact_expiry():
    session = Mock()
    session.post.return_value = reply({'access_token': 'dummy', 'expires_in': 10})
    clock = Mock(return_value=100)
    manager = OpenSkyTokenManager('dummy', 'dummy', session=session, clock=clock, refresh_margin=0)
    manager.get_token()
    clock.return_value = 109
    manager.get_token()
    assert session.post.call_count == 1
    clock.return_value = 110
    manager.get_token()
    assert session.post.call_count == 2


def test_auth_failure_prevents_traffic_request():
    client, session, tokens = traffic_setup(None)
    tokens.get_token.side_effect = requests.HTTPError('auth rejected')
    with pytest.raises(requests.HTTPError):
        client.fetch_states()
    session.get.assert_not_called()


def test_manual_script_with_fake_http(payload, monkeypatch, capsys):
    import inspect_traffic
    monkeypatch.setattr(inspect_traffic, 'load_dotenv', lambda: None)
    monkeypatch.setenv('OPENSKY_CLIENT_ID', 'dummy-id')
    monkeypatch.setenv('OPENSKY_CLIENT_SECRET', 'dummy-secret')
    post = Mock(return_value=reply({'access_token': 'dummy-token', 'expires_in': 120}))
    get = Mock(return_value=reply(payload))
    monkeypatch.setattr(requests, 'post', post)
    monkeypatch.setattr(requests, 'get', get)
    inspect_traffic.main()
    output = capsys.readouterr().out
    assert 'Response time: 1010; raw state count: 6' in output
    assert '18 fields' in output
    assert 'Parsed aircraft: 5; missing-position rows filtered: 1' in output
    for secret in ('dummy-id', 'dummy-secret', 'dummy-token'):
        assert secret not in output


def test_import_manual_script_has_no_io(monkeypatch, capsys):
    import importlib

    import inspect_traffic
    load = Mock(side_effect=AssertionError('import must not load credentials'))
    monkeypatch.setattr('dotenv.load_dotenv', load)
    importlib.reload(inspect_traffic)
    assert capsys.readouterr().out == ''
    load.assert_not_called()
