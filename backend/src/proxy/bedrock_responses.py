"""SigV4-signed calls to the bedrock-runtime OpenAI Responses endpoint."""

import http.client
from collections.abc import Iterator
from dataclasses import dataclass

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

from proxy.config import UPSTREAM_READ_CHUNK_BYTES, UPSTREAM_TIMEOUT_SECONDS

SIGNING_SERVICE = "bedrock"
UPSTREAM_PATH = "/openai/v1/responses"


@dataclass
class UpstreamResponse:
    status: int
    content_type: str
    request_id: str
    _response: http.client.HTTPResponse
    _connection: http.client.HTTPSConnection

    def iter_chunks(self) -> Iterator[bytes]:
        """Yield bytes as soon as Bedrock sends them (keeps SSE latency low)."""
        try:
            while chunk := self._response.read1(UPSTREAM_READ_CHUNK_BYTES):
                yield chunk
        finally:
            self._connection.close()

    def read_all(self) -> bytes:
        try:
            return self._response.read()
        finally:
            self._connection.close()


class BedrockResponsesClient:
    def __init__(self, region: str, host: str) -> None:
        self._region = region
        self._host = host
        self._session = boto3.Session(region_name=region)

    def send(self, body: bytes, is_streaming: bool) -> UpstreamResponse:
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream" if is_streaming else "application/json",
        }
        signed_headers = self._sign(body, headers)

        connection = http.client.HTTPSConnection(self._host, timeout=UPSTREAM_TIMEOUT_SECONDS)
        try:
            connection.request("POST", UPSTREAM_PATH, body=body, headers=signed_headers)
            response = connection.getresponse()
        except Exception:
            connection.close()
            raise
        return UpstreamResponse(
            status=response.status,
            content_type=response.getheader("Content-Type", "application/json"),
            request_id=response.getheader("x-amzn-RequestId", ""),
            _response=response,
            _connection=connection,
        )

    def _sign(self, body: bytes, headers: dict[str, str]) -> dict[str, str]:
        aws_request = AWSRequest(
            method="POST", url=f"https://{self._host}{UPSTREAM_PATH}", data=body, headers=headers
        )
        frozen = self._session.get_credentials().get_frozen_credentials()
        SigV4Auth(frozen, SIGNING_SERVICE, self._region).add_auth(aws_request)
        return dict(aws_request.headers.items())
