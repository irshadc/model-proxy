"""End-to-end tests of the HTTP handler against a fake Bedrock client (no AWS calls)."""

import http.client
import json
import threading
from http.server import ThreadingHTTPServer

import pytest

from proxy.server import build_handler

SECRET = "origin-secret"
MODEL = "global.openai.gpt-6-luna"
SSE_EVENTS = [b'event: response.output_text.delta\ndata: {"delta":"Hel"}\n\n',
              b'event: response.output_text.delta\ndata: {"delta":"lo"}\n\n']


class FakeUpstream:
    def __init__(self, status, content_type, chunks):
        self.status, self.content_type, self.request_id = status, content_type, "req-1"
        self._chunks = chunks

    def iter_chunks(self):
        yield from self._chunks

    def read_all(self):
        return b"".join(self._chunks)


class FakeBedrock:
    def __init__(self):
        self.calls = []

    def send(self, body, is_streaming):
        self.calls.append((json.loads(body), is_streaming))
        if is_streaming:
            return FakeUpstream(200, "text/event-stream", SSE_EVENTS)
        return FakeUpstream(200, "application/json", [b'{"output_text":"Hello"}'])


@pytest.fixture
def proxy():
    bedrock = FakeBedrock()
    server = ThreadingHTTPServer(("127.0.0.1", 0), build_handler(MODEL, SECRET, bedrock))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server.server_address[1], bedrock
    server.shutdown()


def post(port, body, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/v1/responses", body=json.dumps(body),
                 headers={"Content-Type": "application/json", **(headers or {})})
    response = conn.getresponse()
    return response.status, response.getheader("Content-Type"), response.read()


def test_rejects_calls_without_origin_secret(proxy):
    port, bedrock = proxy
    status, _, _ = post(port, {"input": "hi"})
    assert status == 403
    assert bedrock.calls == []


def test_buffered_mode(proxy):
    port, bedrock = proxy
    status, ctype, body = post(port, {"input": "hi", "model": "other"}, {"X-Origin-Verify": SECRET})
    assert (status, ctype) == (200, "application/json")
    assert json.loads(body)["output_text"] == "Hello"
    sent, is_streaming = bedrock.calls[0]
    assert sent["model"] == MODEL and is_streaming is False


def test_streaming_mode_relays_sse(proxy):
    port, bedrock = proxy
    status, ctype, body = post(port, {"input": "hi", "stream": True}, {"X-Origin-Verify": SECRET})
    assert (status, ctype) == (200, "text/event-stream")
    assert body == b"".join(SSE_EVENTS)
    assert bedrock.calls[0][1] is True


def test_bad_request(proxy):
    port, _ = proxy
    status, _, body = post(port, {"stream": True}, {"X-Origin-Verify": SECRET})
    assert status == 400
    assert json.loads(body)["error"]["type"] == "invalid_request_error"
