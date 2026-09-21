"""Presentation contracts, not reimplementation of detector or browser internals."""

import json
from dataclasses import replace
from pathlib import Path

import folium
import pytest
import requests
from shapely.geometry import MultiPolygon, Polygon, box

from sa_engine.artifacts import write_artifacts
from sa_engine.demo import demo_report, synthetic_result
from sa_engine.history import RunHistory
from sa_engine.map_view import render_map
from sa_engine.models import VerificationStatus, VerticalLimit
from sa_engine.report import build_report, latest_live_report, load_report, report_text


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Presentation must not fetch HTTP')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


@pytest.fixture
def scenario(tmp_path):
    history = RunHistory(tmp_path/'history'/'runs.jsonl',tmp_path/'history'/'positions.jsonl')
    return synthetic_result(history), history


def test_demo_is_deterministic_and_real_alert():
    first, second = demo_report(), demo_report()
    assert first == second
    assert first['mode'] == 'synthetic'
    assert len(first['alerts']) == 1
    alert = first['alerts'][0]
    assert alert['alert_type'] == 'prohibited_area_entry'
    assert alert['verification_status'] == 'confirmed'
    assert alert['distance_to_boundary_m'] > 0
    assert len(alert['recent_positions']) == 4
    assert first['run']['stale_count'] == 1


@pytest.mark.parametrize('status', list(VerificationStatus))
def test_explicit_report_serialization(scenario, status):
    result, _ = scenario
    result.alerts[0].verification_status = status
    result.alerts[0].zone.upper = VerticalLimit(None,None,None,unlimited=True)
    result.metadata['client_secret'] = 'NEVER-EXPORT'
    result.metadata['client'] = object()
    report = build_report(result,mode='synthetic')
    encoded = json.dumps(report,allow_nan=False)
    restored = json.loads(encoded)
    assert 'NEVER-EXPORT' not in encoded
    assert restored['alerts'][0]['verification_status'] == status.value
    assert restored['alerts'][0]['zone']['upper'] == dict(value=None,unit=None,reference=None,unlimited=True)
    assert restored['alerts'][0]['aircraft']['geo_altitude_ft'] is None
    text = report_text(restored)
    for label in ('SYNTHETIC','DEMO01','UNLIMITED',status.value.upper(),'activation: unknown','Boundary distance','source:'):
        assert label in text


@pytest.mark.parametrize('code, expected', [
    (0, 'ADS-B (0)'), (1, 'ASTERIX (1)'), (2, 'MLAT (2)'),
    (3, 'FLARM (3)'), (7, 'Unknown (7)'), (None, 'unavailable'),
])
def test_position_source_presentation_preserves_raw_value(scenario, code, expected):
    result, _ = scenario
    aircraft = result.alerts[0].aircraft
    aircraft.position_source = code
    report = build_report(result, mode='synthetic')
    assert f'source: {expected}' in report_text(report)
    assert f'source: {expected}' in render_map(report, tiles=None).get_root().render()
    restored = json.loads(json.dumps(report))
    assert restored['alerts'][0]['aircraft']['position_source'] == code
    assert next(a for a in restored['aircraft'] if a['icao24'] == aircraft.icao24)['position_source'] == code
    assert aircraft.position_source == code


@pytest.mark.parametrize('altitude, expected', [
    (3200, '3200 ft'), (0, '0 ft'), (None, 'unavailable'),
])
def test_geometric_altitude_presentation_preserves_raw_value(scenario, altitude, expected):
    result, _ = scenario
    aircraft = result.alerts[0].aircraft
    aircraft.geo_altitude_ft = altitude
    report = build_report(result, mode='synthetic')
    assert f'geometric altitude: {expected}' in report_text(report)
    assert f'geometric altitude: {expected}' in render_map(report, tiles=None).get_root().render()
    restored = json.loads(json.dumps(report))
    assert restored['alerts'][0]['aircraft']['geo_altitude_ft'] == altitude
    assert next(a for a in restored['aircraft'] if a['icao24'] == aircraft.icao24)['geo_altitude_ft'] == altitude
    assert aircraft.geo_altitude_ft == altitude


def children(view, name):
    group = next(child for child in view._children.values()
                 if isinstance(child,folium.FeatureGroup) and child.layer_name == name)
    return list(group._children.values())


def test_geometry_and_coordinate_contracts(scenario):
    result, _ = scenario
    outer = box(25,64,25.1,64.1)
    polygon = Polygon(outer.exterior.coords,[box(25.02,64.02,25.04,64.04).exterior.coords])
    result.zones[0].polygon = polygon
    result.zones.append(replace(result.zones[0],id='MULTI',polygon=MultiPolygon([box(25.2,64,25.3,64.1),box(25.4,64,25.5,64.1)])))
    track = [dict(icao24='000001',lat=64.01,lon=25.01),dict(icao24='000001',lat=64.02,lon=25.02)]
    report = build_report(result,tracks={'000001':track},mode='synthetic')
    view = render_map(report,tiles=None)
    zones = children(view,'prohibited')
    assert zones[0].data['features'][0]['geometry']['type'] == 'Polygon'
    assert len(zones[0].data['features'][0]['geometry']['coordinates']) == 2
    assert zones[0].data['features'][0]['geometry']['coordinates'][0][0][0] == pytest.approx(25.1)
    assert zones[1].data['features'][0]['geometry']['type'] == 'MultiPolygon'
    assert len(zones[1].data['features'][0]['geometry']['coordinates']) == 2
    marker = children(view,'alerted traffic')[0]
    assert marker.location == [64.02,25.02]
    line = children(view,'tracks')[0]
    assert line.locations == [[64.01,25.01],[64.02,25.02]]
    assert len(children(view,'normal traffic')) == 2
    html = view.get_root().render()
    for label in ('SYNTHETIC','CONFIRMED','stale','normal traffic','alerted traffic','tracks'):
        assert label in html


def test_bundle_and_latest_selection(scenario,tmp_path):
    result, history = scenario
    root = tmp_path/'bundles'
    folder = write_artifacts(result,history,root,mode='synthetic')
    assert {file.name for file in folder.iterdir()} == {'alerts.json','alerts.txt','map.html'}
    assert load_report(folder/'alerts.json')['mode'] == 'synthetic'
    assert 'SYNTHETIC' in (folder/'map.html').read_text(encoding='utf-8')
    assert latest_live_report(root) is None
    # Test-only mode selection; no claim that this synthetic data is live.
    result.metadata['run_id'] = 'test-live-snapshot'
    write_artifacts(result,history,root,mode='live')
    assert latest_live_report(root)['run']['run_id'] == 'test-live-snapshot'
    assert latest_live_report(tmp_path/'missing') is None


def test_empty_run_renders_normally(scenario):
    result, _ = scenario
    result.aircraft = []
    result.zones = []
    result.alerts = []
    result.metadata['alert_count'] = 0
    report = build_report(result)
    assert 'No alerts' in report_text(report)
    assert 'LIVE-LATEST' in render_map(report,tiles=None).get_root().render()


def test_safe_paths_and_popup_text(scenario,tmp_path):
    result, history = scenario
    result.metadata['run_id'] = '../escape'
    with pytest.raises(ValueError,match='safe directory'):
        write_artifacts(result,history,tmp_path/'out')
    result.zones[0].name = '<script>alert(1)</script>'
    html = render_map(build_report(result),tiles=None).get_root().render()
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html


def test_streamlit_demo_and_empty_live_mode(tmp_path):
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=30).run()
    assert not app.exception
    assert [metric.value for metric in app.metric] == ['1','3','2','1','1']
    app.sidebar.radio[0].set_value('Latest saved live run').run()
    app.sidebar.text_input[0].set_value(str(tmp_path/'no-runs')).run()
    assert not app.exception
    assert any('No saved live artifact' in info.value for info in app.info)


def test_saved_live_ui_consumes_results_without_detection(scenario,tmp_path,monkeypatch):
    from streamlit.testing.v1 import AppTest
    result, history = scenario
    root = tmp_path/'artifacts'
    write_artifacts(result,history,root,mode='live')
    app = AppTest.from_file(Path(__file__).resolve().parents[1]/'app.py',default_timeout=30).run()
    def forbidden(*args, **kwargs):
        raise AssertionError('Presentation must not recompute detection')
    monkeypatch.setattr('sa_engine.geometry.find_alerts', forbidden)
    app.sidebar.radio[0].set_value('Latest saved live run').run()
    app.sidebar.text_input[0].set_value(str(root)).run()
    assert not app.exception
    assert app.metric[-1].value == '1'
    assert any('LIVE-LATEST' in title.value for title in app.subheader)
