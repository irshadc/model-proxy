import json

import pytest

from proxy.request_policy import InvalidRequest, build_responses_request, is_trusted_origin

MODEL = "global.openai.gpt-6-luna"


def test_model_is_pinned_and_stream_flag_read():
    request = build_responses_request(b'{"model":"gpt-4o","input":"hi","stream":true}', MODEL)
    assert json.loads(request.body)["model"] == MODEL
    assert request.is_streaming is True


def test_stream_defaults_to_buffered():
    assert build_responses_request(b'{"input":"hi"}', MODEL).is_streaming is False


@pytest.mark.parametrize(
    "body",
    [b"not json", b"[1,2]", b'{"model":"x"}', b'{"input":"hi","stream":"yes"}'],
)
def test_invalid_bodies_rejected(body):
    with pytest.raises(InvalidRequest):
        build_responses_request(body, MODEL)


def test_origin_check():
    assert is_trusted_origin("s3cret", "s3cret")
    assert not is_trusted_origin("wrong", "s3cret")
    assert not is_trusted_origin(None, "s3cret")
