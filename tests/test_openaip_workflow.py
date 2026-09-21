"""Full offline path: mocked HTTP -> real client -> adapter -> detection."""

import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests

from sa_engine.models import AlertType, DataQuality, VerificationStatus
from sa_engine.openaip_client import OpenAIPClient
from sa_engine.openaip_workflow import check_openaip_airspaces


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Live HTTP is forbidden in workflow tests')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


@pytest.fixture
def records():
    path = Path(__file__).parent / 'fixtures' / 'openaip_airspaces.json'
    return json.loads(path.read_text(encoding='utf-8'))


def client_for(records):
    session = Mock()
    replies = []
    for page, raw in enumerate(records, 1):
        reply = Mock()
        reply.json.return_value = dict(page=page, totalPages=len(records), items=[raw])
        replies.append(reply)
    session.get.side_effect = replies
    return OpenAIPClient('offline-dummy-key', session=session)


def test_http_to_alert_preserves_uncertainty(records, aircraft_inside):
    aircraft = replace(aircraft_inside, lon=24.25, lat=60.25, baro_altitude_ft=None)
    zones, alerts = check_openaip_airspaces(client_for(records[:2]), aircraft, now=1010)
    assert [zone.id for zone in zones] == [raw['_id'] for raw in records[:2]]
    assert [alert.alert_type for alert in alerts] == [
        AlertType.RESTRICTED_AREA_ENTRY, AlertType.DANGER_AREA_EXPOSURE,
    ]
    for zone, alert in zip(zones, alerts):
        assert alert.zone is zone
        assert alert.aircraft is aircraft
        assert alert.verification_status is VerificationStatus.UNKNOWN
        assert alert.data_quality is DataQuality.NO_ALTITUDE
        assert alert.distance_to_boundary_m > 0


def test_explicit_selection_and_approximate_altitude(records, aircraft_inside):
    # The synthetic 3000 ft barometric altitude is only approximate against MSL.
    zones, alerts = check_openaip_airspaces(
        client_for(records[:2]), aircraft_inside, now=1010,
        zone_ids=[records[1]['_id']],
    )
    assert len(zones) == len(alerts) == 1
    assert alerts[0].alert_type is AlertType.DANGER_AREA_EXPOSURE
    assert alerts[0].verification_status is VerificationStatus.POTENTIAL


@pytest.mark.parametrize('field,value', [('type', 7), ('upperLimit', None)])
def test_batch_failure_prevents_detection(records, aircraft_inside, monkeypatch, field, value):
    records[1][field] = value
    detector = Mock()
    monkeypatch.setattr('sa_engine.openaip_workflow.find_alerts', detector)
    with pytest.raises(ValueError, match='record index 1.*synthetic-2') as caught:
        check_openaip_airspaces(client_for(records[:2]), aircraft_inside, now=1010)
    assert isinstance(caught.value.__cause__, ValueError)
    detector.assert_not_called()


@pytest.mark.parametrize('ids', [[], ['missing-id']])
def test_invalid_selection_fails(records, aircraft_inside, ids):
    with pytest.raises(ValueError):
        check_openaip_airspaces(client_for(records[:1]), aircraft_inside, now=1010, zone_ids=ids)
