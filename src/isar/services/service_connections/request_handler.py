import logging
from typing import Any, Optional

import requests
from requests.exceptions import (
    ConnectTimeout,
    ConnectionError,
    HTTPError,
    RequestException,
    Timeout,
)
from requests.models import Response

from isar.config import config


class RequestHandler:
    def __init__(self):
        self.logger = logging.getLogger("state_machine")

    def base_request(
        self,
        url: str,
        method: str,
        json_body: Any,
        timeout: float,
        auth: tuple,
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> Response:
        try:
            response = requests.request(
                url=url,
                method=method,
                auth=auth,
                headers=headers,
                timeout=timeout,
                json=json_body,
                data=data,
                params=params,
                **kwargs,
            )
        except Timeout as e:
            self.logger.exception("Timeout exception")
            raise RequestException from e
        except ConnectionError as e:
            self.logger.exception("Connection error")
            raise RequestException from e
        except ConnectTimeout as e:
            self.logger.exception(
                "The request timed out while trying to connect to the remote server."
            )
            raise RequestException from e
        except RequestException as e:
            raise RequestException from e
        except Exception as e:
            self.logger.exception("An unhandled exception occurred during a request")
            raise RequestException from e
        try:
            response.raise_for_status()
        except HTTPError as e:
            self.logger.exception(
                f"Http error. Http status code= {response.status_code}"
            )
            raise RequestException from e
        return response

    def get(
        self,
        url: str,
        json_body=None,
        request_timeout: float = config.getfloat("DEFAULT", "request_timeout"),
        auth: Optional[tuple] = None,
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> Response:
        try:
            response = self.base_request(
                url=url,
                method="GET",
                auth=auth,
                headers=headers,
                timeout=request_timeout,
                json_body=json_body,
                data=data,
                params=params,
                **kwargs,
            )
        except RequestException as e:
            raise RequestException from e
        return response

    def post(
        self,
        url: str,
        json_body=None,
        request_timeout: float = config.getfloat("DEFAULT", "request_timeout"),
        auth: Optional[tuple] = None,
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> Response:
        try:
            response = self.base_request(
                url=url,
                method="POST",
                auth=auth,
                headers=headers,
                timeout=request_timeout,
                json_body=json_body,
                data=data,
                params=params,
                **kwargs,
            )
        except RequestException as e:
            raise RequestException from e
        return response

    def delete(
        self,
        url: str,
        json_body=None,
        request_timeout: float = config.getfloat("DEFAULT", "request_timeout"),
        auth: Optional[tuple] = None,
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> Response:
        try:
            response = self.base_request(
                url=url,
                method="DELETE",
                auth=auth,
                headers=headers,
                timeout=request_timeout,
                json_body=json_body,
                data=data,
                params=params,
                **kwargs,
            )
        except RequestException as e:
            raise RequestException from e
        return response

    def put(
        self,
        url: str,
        json_body=None,
        request_timeout: float = config.getfloat("DEFAULT", "request_timeout"),
        auth: Optional[tuple] = None,
        headers: Optional[dict] = None,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        **kwargs,
    ) -> Response:
        try:
            response = self.base_request(
                url=url,
                method="PUT",
                auth=auth,
                headers=headers,
                timeout=request_timeout,
                json_body=json_body,
                data=data,
                params=params,
                **kwargs,
            )
        except RequestException as e:
            raise RequestException from e
        return response
