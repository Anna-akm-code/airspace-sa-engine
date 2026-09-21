"""Stage 5 behavior tests: all HTTP is fake and all disk writes use tmp_path."""

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from sa_engine.freshness import position_freshness
from sa_engine.history import HistoryError, RunHistory, append_jsonl
from sa_engine.live_workflow import run_detection
from sa_engine.models import VerificationStatus
from sa_engine.openaip_adapter import parse_supported_zones
from sa_engine.openaip_cache import CacheError, OpenAIPCache
from sa_engine.openaip_client import OpenAIPClient
from sa_engine.opensky_auth import OpenSkyTokenManager
from sa_engine.opensky_client import OpenSkyClient


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Live HTTP is forbidden in Stage 5 tests')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


def fixture(name):
    return json.loads((Path(__file__).parent / 'fixtures' / name).read_text())


def response(data):
    reply = Mock()
    reply.json.return_value = data
    return reply


def test_cache_missing_fresh_expired(tmp_path):
    clock = Mock(return_value=1000)
    client = Mock()
    client.fetch_airspaces.return_value = [{'type': 1}]
    cache = OpenAIPCache(tmp_path/'cache.json', ttl_s=60, clock=clock)
    first = cache.load(client)
    assert first.source == 'live'
    assert json.loads(cache.path.read_text())['records'] == [{'type': 1}]
    clock.return_value = 1059
    assert cache.load(client).source == 'cache'
    assert client.fetch_airspaces.call_count == 1
    clock.return_value = 1060
    assert cache.load(client).source == 'live'
    assert client.fetch_airspaces.call_count == 2


@pytest.mark.parametrize('content', ['broken', '{}', '{"version": 1, "country": "FI", "fetched_at": 9999, "records": []}'])
def test_bad_cache_stops_without_http(tmp_path, content):
    path = tmp_path/'cache.json'
    path.write_text(content)
    client = Mock()
    with pytest.raises(CacheError):
        OpenAIPCache(path, clock=lambda: 1000).load(client)
    client.fetch_airspaces.assert_not_called()
    assert path.read_text() == content


def test_cache_country_change_and_zero_ttl(tmp_path):
    client = Mock()
    client.fetch_airspaces.return_value = []
    cache = OpenAIPCache(tmp_path/'cache.json', clock=lambda: 1000)
    cache.load(client, 'FI')
    cache.load(client, 'SE')
    assert client.fetch_airspaces.call_count == 2
    OpenAIPCache(cache.path, ttl_s=0, clock=lambda: 1000).load(client, 'SE')
    assert client.fetch_airspaces.call_count == 3


def test_failed_cache_replace_keeps_old_file(tmp_path, monkeypatch):
    client = Mock()
    client.fetch_airspaces.return_value = []
    cache = OpenAIPCache(tmp_path/'cache.json', ttl_s=0, clock=lambda: 1000)
    cache.load(client)
    original = cache.path.read_bytes()
    monkeypatch.setattr('sa_engine.openaip_cache.os.replace', Mock(side_effect=OSError('write failed')))
    with pytest.raises(OSError):
        cache.load(client)
    assert cache.path.read_bytes() == original
    assert list(tmp_path.glob('*.tmp')) == []


@pytest.mark.parametrize('timestamp,expected', [(1000,'fresh'), (940,'fresh'), (939,'stale'), (None,'missing_time'), (1001,'fresh')])
def test_freshness(aircraft_inside, timestamp, expected):
    aircraft = replace(aircraft_inside, time_position=timestamp, last_contact=1000)
    assert position_freshness(aircraft, 1000, 60) == expected


def test_jsonl_append(tmp_path):
    path = tmp_path/'runs.jsonl'
    append_jsonl(path, [{'run': 1}])
    append_jsonl(path, [{'run': 2}, {'run': 3}])
    assert [json.loads(line) for line in path.read_text().splitlines()] == [dict(run=i) for i in (1,2,3)]


def test_track_order_filter_limit_and_missing(tmp_path):
    history = RunHistory(tmp_path/'runs.jsonl', tmp_path/'positions.jsonl')
    assert history.last_positions('abc') == []
    rows = [dict(icao24=icao, observed_at=stamp, lat=60, lon=24)
            for icao, stamp in [('abc',30),('other',99),('abc',10),('abc',20)]]
    append_jsonl(history.positions_path, rows)
    assert [row['observed_at'] for row in history.last_positions('abc',2)] == [20,30]
    assert len(history.last_positions('abc',10)) == 3
    assert history.last_positions('missing') == []


@pytest.mark.parametrize('line', ['invalid\n', '{}\n', '\n'])
def test_malformed_history_fails(tmp_path, line):
    history = RunHistory(tmp_path/'runs', tmp_path/'positions')
    history.positions_path.write_text(line)
    with pytest.raises(HistoryError, match='line 1'):
        history.last_positions('abc')


def test_partial_last_line_blocks_append(tmp_path):
    path = tmp_path/'history'
    path.write_text('{"broken":')
    with pytest.raises(HistoryError):
        append_jsonl(path, [{'next': 1}])
    assert path.read_text() == '{"broken":'


def test_supported_selection_and_malformed_boundary():
    rows = fixture('openaip_airspaces.json')[:3]
    zones, counts = parse_supported_zones(rows + [{'type': 7}, {'type': 7}, {'type': 8}])
    assert len(zones) == 3
    assert counts == {7:2, 8:1}
    for row in ({'type': True}, {'type': 1}, {}):
        with pytest.raises(ValueError):
            parse_supported_zones([row])


def setup_workflow(tmp_path):
    zones = fixture('openaip_airspaces.json')[:1] + [{'type': 7}]
    raw = fixture('opensky_states_synthetic.json')['states'][0]
    # Fresh inside footprint; second row stale despite recent last_contact.
    raw[5:7] = [24.25,60.25]
    stale = raw.copy()
    stale[0], stale[3], stale[4] = 'abc099', 900, 1009
    ground = raw.copy()
    ground[0], ground[8] = 'abc098', True
    missing_time = raw.copy()
    missing_time[0], missing_time[3] = 'abc097', None
    missing_pos = raw.copy()
    missing_pos[5] = None
    aip_session = Mock()
    aip_session.get.return_value = response(dict(page=1,totalPages=1,items=zones))
    auth_session = Mock()
    auth_session.post.return_value = response(dict(access_token='dummy-token',expires_in=120))
    sky_session = Mock()
    sky_session.get.return_value = response(dict(time=1010,states=[raw,stale,ground,missing_time,missing_pos]))
    aip = OpenAIPClient('dummy-key', session=aip_session)
    sky = OpenSkyClient(OpenSkyTokenManager('dummy-id','dummy-secret',session=auth_session,
                                           clock=lambda: 0), session=sky_session)
    cache = OpenAIPCache(tmp_path/'cache.json', clock=lambda: 1010)
    history = RunHistory(tmp_path/'runs.jsonl',tmp_path/'positions.jsonl')
    return aip, sky, cache, history, aip_session, sky_session


def test_full_workflow_and_history(tmp_path, caplog):
    aip, sky, cache, history, aip_session, sky_session = setup_workflow(tmp_path)
    result = run_detection(aip,sky,cache,history,clock=lambda:1010)
    stats = result.metadata
    assert (stats['raw_zone_count'], stats['supported_zone_count'], stats['unsupported_zone_count']) == (2,1,1)
    assert (stats['traffic_observation_count'],stats['positioned_count'],stats['missing_position_count']) == (5,4,1)
    assert (stats['fresh_count'],stats['stale_count'],stats['missing_time_count'],stats['on_ground_count']) == (2,1,1,1)
    assert len(result.alerts) == 1
    assert result.alerts[0].aircraft.icao24 == 'abc001'
    assert result.alerts[0].verification_status is VerificationStatus.POTENTIAL
    runs = [json.loads(line) for line in history.runs_path.read_text().splitlines()]
    assert runs[0]['alert_count'] == 1
    positions = [json.loads(line) for line in history.positions_path.read_text().splitlines()]
    assert len(positions) == 4
    assert positions[1]['position_age_s'] == 110
    assert positions[0]['run_id'] == runs[0]['run_id']
    assert history.last_positions('abc001')[0]['lat'] == 60.25
    second = run_detection(aip,sky,cache,history,clock=lambda:1010)
    assert second.metadata['zone_source'] == 'cache'
    assert aip_session.get.call_count == 1
    assert sky_session.get.call_count == 2  # Traffic is never reused as current.
    assert len(history.last_positions('abc001')) == 2
    assert 'Unsupported' in caplog.text
    for secret in ('dummy-key','dummy-token','dummy-secret'):
        assert secret not in caplog.text + history.runs_path.read_text() + history.positions_path.read_text()


def test_empty_traffic_success(tmp_path):
    aip, sky, cache, history, _, sky_session = setup_workflow(tmp_path)
    sky_session.get.return_value = response(dict(time=1010,states=None))
    result = run_detection(aip,sky,cache,history,clock=lambda:1010)
    assert result.alerts == []
    assert result.metadata['positioned_count'] == 0
    assert history.runs_path.exists()


def test_failure_logs_and_no_success_history(tmp_path, caplog):
    aip, sky, cache, history, _, sky_session = setup_workflow(tmp_path)
    sky_session.get.side_effect = requests.Timeout('sensitive-error-text')
    with pytest.raises(requests.Timeout):
        run_detection(aip,sky,cache,history,clock=lambda:1010)
    assert 'Run stopped (Timeout)' in caplog.text
    assert 'sensitive-error-text' not in caplog.text
    assert not history.runs_path.exists()


def test_bad_supported_record_aborts_before_traffic(tmp_path):
    aip, sky, cache, history, aip_session, sky_session = setup_workflow(tmp_path)
    aip_session.get.return_value = response(dict(page=1,totalPages=1,items=[{'type': 1}]))
    with pytest.raises(ValueError, match='OpenAIP record 0'):
        run_detection(aip,sky,cache,history,clock=lambda:1010)
    sky_session.get.assert_not_called()
    assert not history.runs_path.exists()


def test_cli_summary_with_offline_workflow(tmp_path, monkeypatch, capsys):
    import detect_only
    aip, sky, cache, history, _, _ = setup_workflow(tmp_path)
    result = run_detection(aip,sky,cache,history,clock=lambda:1010)
    monkeypatch.setattr(detect_only, 'load_dotenv', lambda: None)
    for name in ('OPENAIP_API_KEY','OPENSKY_CLIENT_ID','OPENSKY_CLIENT_SECRET'):
        monkeypatch.setenv(name, 'dummy')
    monkeypatch.setattr(detect_only, 'run_detection', Mock(return_value=result))
    monkeypatch.setattr('sys.argv', ['detect_only.py', '--runs',str(history.runs_path),
                                   '--positions',str(history.positions_path), '--artifacts',str(tmp_path/'artifacts')])
    detect_only.main()
    output = capsys.readouterr().out
    assert 'unsupported=1' in output
    assert 'fresh=2 stale=1' in output
    assert 'recent_track_count=1' in output
    assert 'distance to boundary:' in output
    assert ' km |' in output
    assert 'potential' in output
    assert 'not legal infringements' in output


def test_cache_history_collision_rejected(tmp_path):
    aip, sky, cache, history, aip_session, _ = setup_workflow(tmp_path)
    cache.path = history.runs_path
    with pytest.raises(ValueError, match='paths must be distinct'):
        run_detection(aip,sky,cache,history)
    aip_session.get.assert_not_called()
