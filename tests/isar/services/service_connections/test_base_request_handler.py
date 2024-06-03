import pytest
import requests
from requests.exceptions import (
    ConnectionError,
    ConnectTimeout,
    RequestException,
    Timeout,
)
from requests.models import Response

from isar.services.service_connections.request_handler import RequestHandler

url = "http://10.0.0.1"


def test_request_handler_success(requests_mock):
    base_handler = RequestHandler()
    requests_mock.get(url, json=[{"Success": 1}], status_code=200)
    requests_mock.delete(url, json=[{"Success": 1}], status_code=200)
    requests_mock.put(url, json=[{"Success": 1}], status_code=200)
    requests_mock.post(url, json=[{"Success": 1}], status_code=200)

    put_response = base_handler.put(url)
    get_response = base_handler.get(url)
    post_response = base_handler.post(url)
    delete_response = base_handler.delete(url)

    assert isinstance(put_response, Response)
    assert put_response.status_code == 200

    assert isinstance(get_response, Response)
    assert get_response.status_code == 200

    assert isinstance(post_response, Response)
    assert post_response.status_code == 200

    assert isinstance(delete_response, Response)
    assert delete_response.status_code == 200


def test_request_http_error(requests_mock):
    base_handler = RequestHandler()
    requests_mock.get(url, json=[], status_code=400)
    requests_mock.delete(url, json=[], status_code=400)
    requests_mock.put(url, json=[], status_code=400)
    requests_mock.post(url, json=[{"Success": 1}], status_code=400)
    with pytest.raises(RequestException):
        base_handler.post(url)
    with pytest.raises(RequestException):
        base_handler.put(url)
    with pytest.raises(RequestException):
        base_handler.delete(url)
    with pytest.raises(RequestException):
        base_handler.get(url)


@pytest.mark.parametrize(
    "exception",
    [Timeout(), ConnectionError(), KeyError(), ConnectTimeout()],
)
def test_request_exception(mocker, exception):
    base_handler = RequestHandler()
    mocker.patch.object(requests, "request", side_effect=exception)
    with pytest.raises(RequestException):
        base_handler.put(url)
    with pytest.raises(RequestException):
        base_handler.post(url)
    with pytest.raises(RequestException):
        base_handler.delete(url)
    with pytest.raises(RequestException):
        base_handler.get(url)


def test_timeout_exception():
    base_handler = RequestHandler()
    with pytest.raises(RequestException):
        base_handler.put(url, request_timeout=1e-10)
    with pytest.raises(RequestException):
        base_handler.post(url, request_timeout=1e-10)
    with pytest.raises(RequestException):
        base_handler.delete(url, request_timeout=1e-10)
    with pytest.raises(RequestException):
        base_handler.get(url, request_timeout=1e-10)
