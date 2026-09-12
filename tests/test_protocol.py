import numpy as np

from lingxi.protocol import BinaryFrameParser, LegacyFrameParser, SampleFrame, encode_frame


def make_frame() -> SampleFrame:
    return SampleFrame(
        sequence=17,
        sample_rate=200_000,
        samples=np.array([0, 1024, 2048, 3072, 4095], dtype=np.uint16),
        gain_code=2,
        coupling="DC",
        flags=0,
        adc_bits=12,
        vref_mv=3300,
        zero_code=2048,
    )


def test_binary_frame_round_trip_with_chunked_input():
    encoded = encode_frame(make_frame())
    parser = BinaryFrameParser()
    assert parser.feed(b"noise" + encoded[:9]) == []
    frames = parser.feed(encoded[9:])
    assert len(frames) == 1
    frame = frames[0]
    assert frame.sequence == 17
    assert frame.sample_rate == 200_000
    assert frame.coupling == "DC"
    np.testing.assert_array_equal(frame.samples, [0, 1024, 2048, 3072, 4095])


def test_binary_parser_rejects_bad_crc_and_recovers():
    damaged = bytearray(encode_frame(make_frame()))
    damaged[-3] ^= 0x7F
    parser = BinaryFrameParser()
    assert parser.feed(bytes(damaged)) == []
    assert parser.crc_errors == 1
    assert len(parser.feed(encode_frame(make_frame()))) == 1


def test_legacy_text_frame_parses_header_and_samples():
    parser = LegacyFrameParser()
    frames = parser.feed(b"<Time00640+Fre00100+Amp2+DC+2048,2050,2047>")
    assert len(frames) == 1
    assert frames[0].sample_rate == 100_000
    assert frames[0].gain_code == 2
    assert frames[0].coupling == "DC"
    np.testing.assert_array_equal(frames[0].samples, [2048, 2050, 2047])


def test_legacy_parser_discards_nonlegacy_binary_noise():
    parser = LegacyFrameParser()
    for _ in range(20):
        parser.feed(b"\xA5\x5A\x01\x01binary-data-without-angle-brackets")
    assert len(parser.buffer) <= 1
