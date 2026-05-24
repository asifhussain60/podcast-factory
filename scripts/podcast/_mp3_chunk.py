"""_mp3_chunk.py — pure-stdlib MP3 chunker.

Splits a raw MP3 byte-stream into N approximately-equal chunks ≤ max_bytes
each, cutting only at MP3 frame-sync boundaries so each chunk is a valid
decodable MP3 on its own. Used by transcribe_reference_mp3s.py to work
around Azure Speech Fast Transcription's practical ceiling on long audio
files (the synchronous endpoint stops returning content for episodes
beyond ~25 minutes / ~50 MB, even though the docs claim 2 hours).

Why pure stdlib: per `_azure.py` policy, the podcast scripts do not pull
pip dependencies. MP3 frame parsing is simple enough that 60 lines of
struct-and-bit-twiddling covers the cases we care about.

WHAT'S A FRAME

  MPEG audio frames start with an 11-bit sync word (0b11111111111 →
  bytes 0xFF 0xFB / 0xFF 0xFA / 0xFF 0xF3 / 0xFF 0xF2). After the sync
  word are 21 bits describing version, layer, bitrate, sample rate,
  padding, etc. From those, frame size in bytes is:

    frame_size = (144 * bitrate_kbps * 1000) // sample_rate_hz
                 + (1 if padding else 0)

  (Layer III; for Layer II divide-coefficient is 144 too.)

WHAT WE SKIP

  ID3v2 tag at the start of the file (the first 10 bytes carry the tag
  size in synchsafe form). We DON'T need to preserve ID3 tags in the
  chunks — the transcription API doesn't care.
"""
from __future__ import annotations

# MPEG-1 Layer III bitrate table (kbps). Index 0 = "free", 15 = "bad" (reserved).
_BITRATE_MPEG1_L3 = [
    None, 32, 40, 48, 56, 64, 80, 96,
    112, 128, 160, 192, 224, 256, 320, None,
]
# MPEG-2/2.5 Layer III bitrate table (kbps)
_BITRATE_MPEG2_L3 = [
    None, 8, 16, 24, 32, 40, 48, 56,
    64, 80, 96, 112, 128, 144, 160, None,
]
_SAMPLE_RATE = {
    3: [44100, 48000, 32000, None],  # MPEG-1
    2: [22050, 24000, 16000, None],  # MPEG-2
    0: [11025, 12000, 8000, None],   # MPEG-2.5
}


def _skip_id3v2(buf: bytes) -> int:
    """Return byte offset past an ID3v2 tag at buf[0:] (or 0 if none)."""
    if len(buf) < 10 or buf[:3] != b"ID3":
        return 0
    # Synchsafe-encoded size: 4 bytes, each high-bit clear, big-endian
    size = (buf[6] << 21) | (buf[7] << 14) | (buf[8] << 7) | buf[9]
    return 10 + size


def _parse_frame(buf: bytes, off: int) -> int | None:
    """Return frame size in bytes at buf[off:], or None if not a valid header."""
    if off + 4 > len(buf):
        return None
    if buf[off] != 0xFF:
        return None
    b1 = buf[off + 1]
    if (b1 & 0xE0) != 0xE0:  # sync word incomplete
        return None
    version_bits = (b1 >> 3) & 0x03   # 0=2.5, 2=2, 3=1
    layer_bits = (b1 >> 1) & 0x03      # 1=L3, 2=L2, 3=L1
    if version_bits == 1 or layer_bits == 0:
        return None
    b2 = buf[off + 2]
    bitrate_idx = (b2 >> 4) & 0x0F
    sr_idx = (b2 >> 2) & 0x03
    padding = (b2 >> 1) & 0x01
    if version_bits == 3:
        bitrate = _BITRATE_MPEG1_L3[bitrate_idx]
    else:
        bitrate = _BITRATE_MPEG2_L3[bitrate_idx]
    sample_rate = _SAMPLE_RATE.get(version_bits, [None] * 4)[sr_idx]
    if not bitrate or not sample_rate:
        return None
    if layer_bits == 1:  # Layer III
        coeff = 144 if version_bits == 3 else 72
    elif layer_bits == 2:
        coeff = 144
    else:
        coeff = 12
    frame_size = (coeff * bitrate * 1000) // sample_rate + padding
    if frame_size < 4:
        return None
    return frame_size


def chunk_mp3_bytes(data: bytes, max_bytes: int = 9_500_000) -> list[bytes]:
    """Split MP3 byte-stream into chunks ≤ max_bytes, cut at frame boundaries.

    Each returned chunk is a valid standalone MP3 (no ID3 header, just frames).
    Default max_bytes 9.5MB leaves headroom under typical multipart-form caps
    and under Azure Speech's practical sweet-spot for synchronous transcription.
    """
    start = _skip_id3v2(data)
    chunks: list[bytes] = []
    chunk_start = start
    cursor = start
    n = len(data)
    while cursor < n:
        # Find next valid frame header
        if data[cursor] != 0xFF:
            # Resync: search forward for 0xFF
            nxt = data.find(b"\xFF", cursor + 1)
            if nxt < 0:
                break
            cursor = nxt
            continue
        size = _parse_frame(data, cursor)
        if size is None:
            cursor += 1
            continue
        # Would this frame push us over the budget?
        if cursor + size - chunk_start > max_bytes and chunk_start != cursor:
            chunks.append(data[chunk_start:cursor])
            chunk_start = cursor
        cursor += size
    if chunk_start < n:
        chunks.append(data[chunk_start:n])
    return chunks
