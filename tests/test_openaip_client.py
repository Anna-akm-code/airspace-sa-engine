"""Offline HTTP contract tests; fake transport never opens a socket."""

import importlib
from unittest.mock import Mock

import pytest
import requests

from sa_engine.openaip_client import AIRSPACES_URL, OpenAIPClient, OpenAIPResponseError


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch):
    def blocked(*args, **kwargs):
        pytest.fail('Real HTTP is forbidden in client tests')
    monkeypatch.setattr(requests.sessions.Session, 'request', blocked)


def response(data):
    result = Mock()
    result.json.return_value = data
    return result


def envelope(page=1, total=1, items=None):
    return {'page': page, 'totalPages': total, 'items': [{}] if items is None else items}


def client_for(*responses):
    session = Mock()
    session.get.side_effect = responses
    return OpenAIPClient('dummy-test-key', timeout=7, session=session), session


def test_one_page_and_request_contract():
    raw = {'arbitrary': 'raw data, not a Zone'}
    reply = response(envelope(items=[raw]))
    client, session = client_for(reply)
    assert client.fetch_airspaces('fi') == [raw]
    session.get.assert_called_once_with(AIRSPACES_URL,
        headers={'x-openaip-api-key': 'dummy-test-key'},
        params={'country': 'FI', 'page': 1}, timeout=7)
    reply.raise_for_status.assert_called_once()
    reply.close.assert_called_once()


def test_pages_are_combined_once_in_order():
    batches = [[{'id': 'a'}, {'id': 'b'}], [{'id': 'c'}], [{'id': 'd'}]]
    replies = [response(envelope(i, 3, batch)) for i, batch in enumerate(batches, 1)]
    client, session = client_for(*replies)
    assert client.fetch_airspaces('FI') == sum(batches, [])
    assert session.get.call_count == 3
    for page, call in enumerate(session.get.call_args_list, 1):
        assert call.kwargs == dict(headers={'x-openaip-api-key': 'dummy-test-key'},
                                   params={'country': 'FI', 'page': page}, timeout=7)
    for reply in replies:
        reply.close.assert_called_once()


@pytest.mark.parametrize('total', [0, 1])
def test_empty_result(total):
    client, session = client_for(response(envelope(total=total, items=[])))
    assert client.fetch_airspaces('FI') == []
    assert session.get.call_count == 1


@pytest.mark.parametrize('error', [requests.Timeout('timeout'), requests.ConnectionError('offline')])
def test_network_failure_propagates_without_retry(error):
    client, session = client_for(error)
    with pytest.raises(type(error)) as caught:
        client.fetch_airspaces('FI')
    assert caught.value is error
    assert session.get.call_count == 1


def test_http_error_precedes_json_and_propagates():
    reply = response(None)
    error = requests.HTTPError('403')
    reply.raise_for_status.side_effect = error
    client, session = client_for(reply)
    with pytest.raises(requests.HTTPError) as caught:
        client.fetch_airspaces('FI')
    assert caught.value is error
    reply.json.assert_not_called()
    reply.close.assert_called_once()
    assert session.get.call_count == 1


def test_invalid_json_is_response_error():
    reply = response(None)
    reply.json.side_effect = ValueError('invalid JSON')
    client, _ = client_for(reply)
    with pytest.raises(OpenAIPResponseError, match='invalid JSON'):
        client.fetch_airspaces('FI')
    reply.close.assert_called_once()


@pytest.mark.parametrize('data', [
    None, [], {}, envelope(page=0), envelope(page=True), envelope(page='1'),
    envelope(total=-1), envelope(total=True), envelope(total='1'),
    envelope(items='bad'), envelope(items=[None]), envelope(total=0),
    envelope(total=2, items=[]),
])
def test_malformed_envelope(data):
    client, session = client_for(response(data))
    with pytest.raises(OpenAIPResponseError):
        client.fetch_airspaces('FI')
    assert session.get.call_count == 1


@pytest.mark.parametrize('second', [envelope(page=1, total=2), envelope(page=2, total=3)])
def test_inconsistent_pagination_fails(second):
    client, session = client_for(response(envelope(total=2)), response(second))
    with pytest.raises(OpenAIPResponseError):
        client.fetch_airspaces('FI')
    assert session.get.call_count == 2


def test_later_page_failure_does_not_return_partial_results():
    client, session = client_for(response(envelope(total=2)), requests.Timeout('second page'))
    with pytest.raises(requests.Timeout):
        client.fetch_airspaces('FI')
    assert session.get.call_count == 2


@pytest.mark.parametrize('key', ['', ' ', None])
def test_missing_key_rejected(key):
    with pytest.raises(ValueError):
        OpenAIPClient(key)


@pytest.mark.parametrize('timeout', [0, -1, True, float('inf'), float('nan')])
def test_invalid_timeout_rejected(timeout):
    with pytest.raises(ValueError):
        OpenAIPClient('dummy', timeout=timeout)


def test_importing_manual_script_has_no_network_or_output(capsys):
    import inspect_zones
    importlib.reload(inspect_zones)
    assert capsys.readouterr().out == ''
