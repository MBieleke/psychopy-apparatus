from psychopy_apparatus.utils.protocol import (
    ADDR_CLIENT,
    build_message,
    cobs_decode,
    cobs_encode,
    parse_message,
)


def test_cobs_round_trip():
    raw = bytes([0x10, 0x00, 0x11, 0x22, 0x00, 0x33])
    encoded = cobs_encode(raw)

    assert encoded.endswith(b"\x00")
    assert cobs_decode(encoded[:-1]) == raw


def test_cobs_decode_rejects_truncated_frame():
    encoded = cobs_encode(b"\x01\x02\x00\x03")

    truncated = encoded[:-2]

    try:
        cobs_decode(truncated)
    except ValueError as exc:
        assert "truncated" in str(exc)
    else:
        raise AssertionError("Expected ValueError for truncated COBS frame")


def test_parse_message_rejects_truncated_payload():
    msg = build_message(0x80, seq=7, payload=b"\xAA\xBB", dst=ADDR_CLIENT, flags=0)

    assert parse_message(msg[:-1]) is None


def test_parse_message_rejects_trailing_bytes():
    msg = build_message(0x80, seq=7, payload=b"\xAA\xBB", dst=ADDR_CLIENT, flags=0)

    assert parse_message(msg + b"\x99") is None
