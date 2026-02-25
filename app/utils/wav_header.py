"""
WAV header 解析工具。

WAV RIFF header 標準格式（前 44 bytes）：
  Offset  Size  Description
  0       4     ChunkID ("RIFF")
  4       4     ChunkSize
  8       4     Format ("WAVE")
  12      4     Subchunk1ID ("fmt ")
  16      4     Subchunk1Size (16 for PCM)
  20      2     AudioFormat (1 = PCM)
  22      2     NumChannels
  24      4     SampleRate
  28      4     ByteRate
  32      2     BlockAlign
  34      2     BitsPerSample
  36      4     Subchunk2ID ("data")
  40      4     Subchunk2Size (data size in bytes)
"""

import struct
from dataclasses import dataclass


@dataclass
class WavHeaderInfo:
    """WAV RIFF header 解析結果。"""

    num_channels: int
    sample_rate: int
    byte_rate: int
    bits_per_sample: int
    data_size: int
    is_valid: bool

    @property
    def duration_seconds(self) -> float:
        """計算錄音時長（秒）。"""
        if self.byte_rate == 0:
            return 0.0
        return self.data_size / self.byte_rate


def parse_wav_header(data: bytes) -> WavHeaderInfo:
    """
    解析 WAV RIFF header。

    Args:
        data: 至少 44 bytes 的原始資料

    Returns:
        WavHeaderInfo，is_valid=False 表示非有效 WAV header
    """
    if len(data) < 44 or data[0:4] != b"RIFF" or data[8:12] != b"WAVE":
        return WavHeaderInfo(
            num_channels=0,
            sample_rate=0,
            byte_rate=0,
            bits_per_sample=0,
            data_size=0,
            is_valid=False,
        )

    return WavHeaderInfo(
        num_channels=struct.unpack_from("<H", data, 22)[0],
        sample_rate=struct.unpack_from("<I", data, 24)[0],
        byte_rate=struct.unpack_from("<I", data, 28)[0],
        bits_per_sample=struct.unpack_from("<H", data, 34)[0],
        data_size=struct.unpack_from("<I", data, 40)[0],
        is_valid=True,
    )
