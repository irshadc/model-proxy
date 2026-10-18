import pytest

from proxy.config import parse_model_allowlist
from proxy.request_policy import InvalidRequest, build_responses_request, is_trusted_origin

ALLOWED = frozenset({"global.openai.gpt-6-luna", "us.openai.gpt-6-luna"})


def test_allowed_model_passes_through_unchanged():
    raw = b'{"model":"global.openai.gpt-6-luna","input":"hi","stream":true}'
    request = build_responses_request(raw, ALLOWED)
    assert request.body == raw
    assert request.is_streaming is True


def test_stream_defaults_to_buffered():
    raw = b'{"model":"us.openai.gpt-6-luna","input":"hi"}'
    assert build_responses_request(raw, ALLOWED).is_streaming is False


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        b"[1,2]",
        b'{"model":"global.openai.gpt-6-luna"}',
        b'{"model":"global.openai.gpt-6-luna","input":"hi","stream":"yes"}',
        b'{"input":"hi"}',
        b'{"model":"","input":"hi"}',
        b'{"model":"gpt-6-luna","input":"hi"}',
        b'{"model":"global.anthropic.claude-opus-5","input":"hi"}',
    ],
)
def test_invalid_bodies_rejected(body):
    with pytest.raises(InvalidRequest):
        build_responses_request(body, ALLOWED)


def test_origin_check():
    assert is_trusted_origin("s3cret", "s3cret")
    assert not is_trusted_origin("wrong", "s3cret")
    assert not is_trusted_origin(None, "s3cret")


def test_allowlist_parsing():
    assert parse_model_allowlist(" a , b,,") == frozenset({"a", "b"})
    with pytest.raises(RuntimeError):
        parse_model_allowlist(" , ")
