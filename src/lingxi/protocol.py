from __future__ import annotations

from dataclasses import dataclass
import re
import struct

import numpy as np


MAGIC = b"\xA5\x5A"
HEADER = struct.Struct("<2sBBHIHBBHBBHH")
MAX_SAMPLES = 32768


@dataclass(frozen=True)
class SampleFrame:
    sequence: int
    sample_rate: int
    samples: np.ndarray
    gain_code: int = 0
    coupling: str = "DC"
    flags: int = 0
    adc_bits: int = 12
    vref_mv: int = 3300
    zero_code: int = 2048


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc & 0xFFFF


def encode_frame(frame: SampleFrame) -> bytes:
    samples = np.asarray(frame.samples, dtype="<u2")
    if not 0 < len(samples) <= MAX_SAMPLES:
        raise ValueError("sample count outside supported range")
    coupling = 1 if frame.coupling.upper() == "AC" else 0
    header = HEADER.pack(
        MAGIC,
        1,
        1,
        frame.sequence & 0xFFFF,
        int(frame.sample_rate),
        len(samples),
        frame.gain_code & 0xFF,
        coupling,
        frame.flags & 0xFFFF,
        frame.adc_bits & 0xFF,
        0,
        frame.vref_mv & 0xFFFF,
        frame.zero_code & 0xFFFF,
    )
    body = header + samples.tobytes()
    return body + struct.pack("<H", crc16_modbus(body[2:]))


class BinaryFrameParser:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.crc_errors = 0
        self.format_errors = 0

    def feed(self, data: bytes) -> list[SampleFrame]:
        self.buffer.extend(data)
        frames: list[SampleFrame] = []
        while True:
            start = self.buffer.find(MAGIC)
            if start < 0:
                if self.buffer[-1:] == MAGIC[:1]:
                    self.buffer[:] = self.buffer[-1:]
                else:
                    self.buffer.clear()
                break
            if start:
                del self.buffer[:start]
            if len(self.buffer) < HEADER.size:
                break
            fields = HEADER.unpack_from(self.buffer)
            _, version, packet_type, sequence, sample_rate, count, gain, coupling, flags, adc_bits, _, vref, zero = fields
            if version != 1 or packet_type != 1 or not 0 < count <= MAX_SAMPLES:
                self.format_errors += 1
                del self.buffer[0]
                continue
            total = HEADER.size + count * 2 + 2
            if len(self.buffer) < total:
                break
            packet = bytes(self.buffer[:total])
            expected = struct.unpack_from("<H", packet, total - 2)[0]
            actual = crc16_modbus(packet[2:-2])
            if expected != actual:
                self.crc_errors += 1
                del self.buffer[0]
                continue
            samples = np.frombuffer(packet, dtype="<u2", count=count, offset=HEADER.size).copy()
            frames.append(
                SampleFrame(
                    sequence=sequence,
                    sample_rate=sample_rate,
                    samples=samples,
                    gain_code=gain,
                    coupling="AC" if coupling else "DC",
                    flags=flags,
                    adc_bits=adc_bits,
                    vref_mv=vref,
                    zero_code=zero,
                )
            )
            del self.buffer[:total]
        return frames


class LegacyFrameParser:
    _text_pattern = re.compile(
        rb"Time(?P<time>\d+)\+Fre(?P<freq>\d+)\+Amp(?P<amp>\d+)\+(?P<coupling>DC|AC)\+(?P<samples>[\d,;\s]+)"
    )

    def __init__(self) -> None:
        self.buffer = bytearray()
        self.sequence = 0
        self.format_errors = 0

    def feed(self, data: bytes) -> list[SampleFrame]:
        self.buffer.extend(data)
        frames: list[SampleFrame] = []
        while True:
            start = self.buffer.find(b"<")
            end = self.buffer.find(b">", max(0, start + 1))
            if start < 0 or end < 0:
                if start < 0:
                    self.buffer.clear()
                    break
                if start > 0:
                    del self.buffer[:start]
                break
            payload = bytes(self.buffer[start + 1 : end])
            del self.buffer[: end + 1]
            match = self._text_pattern.fullmatch(payload.strip())
            if not match:
                self.format_errors += 1
                continue
            values = [int(v) for v in re.split(rb"[,;\s]+", match.group("samples").strip()) if v]
            if not values:
                self.format_errors += 1
                continue
            timer_ticks = max(1, int(match.group("time")))
            frames.append(
                SampleFrame(
                    sequence=self.sequence,
                    sample_rate=max(1, 64_000_000 // timer_ticks),
                    samples=np.asarray(values, dtype=np.uint16),
                    gain_code=int(match.group("amp")),
                    coupling=match.group("coupling").decode("ascii"),
                )
            )
            self.sequence = (self.sequence + 1) & 0xFFFF
        return frames
