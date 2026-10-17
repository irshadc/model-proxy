"""HTTP server that Lambda Web Adapter forwards API Gateway requests to.

Routes:
  POST /v1/responses  -> Bedrock Responses API (stream or buffered, per the `stream` field)
  GET  /healthz       -> readiness check for Lambda Web Adapter (not routed by API Gateway)
"""

import json
import logging
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import boto3

from proxy.bedrock_responses import BedrockResponsesClient
from proxy.config import (
    HEALTH_PATH,
    MAX_REQUEST_BYTES,
    ORIGIN_VERIFY_HEADER,
    RESPONSES_PATH,
    load_settings,
)
from proxy.request_policy import InvalidRequest, build_responses_request, is_trusted_origin

logger = logging.getLogger("luna-proxy")


def log_event(level: int, **fields: object) -> None:
    logger.log(level, json.dumps(fields, default=str))


def build_handler(model_id: str, origin_secret: str, bedrock: BedrockResponsesClient):
    class ProxyHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self) -> None:
            if self.path == HEALTH_PATH:
                self._send_json(HTTPStatus.OK, {"status": "ok"})
                return
            self._send_error(HTTPStatus.NOT_FOUND, "Not found")

        def do_POST(self) -> None:
            if self.path != RESPONSES_PATH:
                self._send_error(HTTPStatus.NOT_FOUND, "Not found")
                return
            if not is_trusted_origin(self.headers.get(ORIGIN_VERIFY_HEADER), origin_secret):
                self._send_error(HTTPStatus.FORBIDDEN, "Forbidden")
                return

            raw_body = self._read_body()
            if raw_body is None:
                return
            try:
                request = build_responses_request(raw_body, model_id)
            except InvalidRequest as exc:
                self._send_error(HTTPStatus.BAD_REQUEST, str(exc))
                return
            self._forward(request.body, request.is_streaming)

        def _forward(self, body: bytes, is_streaming: bool) -> None:
            started = time.monotonic()
            try:
                upstream = bedrock.send(body, is_streaming)
            except OSError as exc:
                log_event(logging.ERROR, msg="bedrock_unreachable", error=repr(exc))
                self._send_error(HTTPStatus.BAD_GATEWAY, "Upstream model service unavailable")
                return

            # Stream only successful SSE replies; errors are small JSON bodies.
            if is_streaming and upstream.status == HTTPStatus.OK:
                sent_bytes = self._relay_stream(upstream)
            else:
                payload = upstream.read_all()
                self._send_bytes(upstream.status, upstream.content_type, payload)
                sent_bytes = len(payload)

            log_event(
                logging.INFO,
                msg="responses_call",
                stream=is_streaming,
                status=upstream.status,
                bedrock_request_id=upstream.request_id,
                bytes=sent_bytes,
                latency_ms=round((time.monotonic() - started) * 1000),
            )

        def _relay_stream(self, upstream) -> int:
            self.send_response(upstream.status)
            self.send_header("Content-Type", upstream.content_type)
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()
            sent = 0
            try:
                for chunk in upstream.iter_chunks():
                    self.wfile.write(f"{len(chunk):X}\r\n".encode() + chunk + b"\r\n")
                    self.wfile.flush()
                    sent += len(chunk)
                self.wfile.write(b"0\r\n\r\n")
            except (BrokenPipeError, ConnectionResetError):
                log_event(logging.WARNING, msg="client_disconnected", bytes=sent)
                self.close_connection = True
            return sent

        def _read_body(self) -> bytes | None:
            length_header = self.headers.get("Content-Length")
            if length_header is None or not length_header.isdigit():
                self._send_error(HTTPStatus.LENGTH_REQUIRED, "Content-Length required")
                return None
            length = int(length_header)
            if length > MAX_REQUEST_BYTES:
                self._send_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request body too large")
                return None
            return self.rfile.read(length)

        def _send_error(self, status: HTTPStatus, message: str) -> None:
            error_type = "invalid_request_error" if status < 500 else "server_error"
            self._send_json(status, {"error": {"message": message, "type": error_type}})

        def _send_json(self, status: int, payload: dict) -> None:
            self._send_bytes(status, "application/json", json.dumps(payload).encode())

        def _send_bytes(self, status: int, content_type: str, payload: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format: str, *args: object) -> None:
            pass  # replaced by structured log_event calls

    return ProxyHandler


def fetch_origin_secret(secret_arn: str, region: str) -> str:
    client = boto3.client("secretsmanager", region_name=region)
    return client.get_secret_value(SecretId=secret_arn)["SecretString"]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = load_settings()
    origin_secret = fetch_origin_secret(settings.origin_secret_arn, settings.region)
    bedrock = BedrockResponsesClient(settings.region, settings.bedrock_host)
    handler = build_handler(settings.model_id, origin_secret, bedrock)

    # Lambda Web Adapter connects over loopback; never bind a public interface.
    server = ThreadingHTTPServer(("127.0.0.1", settings.port), handler)
    log_event(logging.INFO, msg="proxy_started", port=settings.port, model=settings.model_id)
    server.serve_forever()


if __name__ == "__main__":
    main()
