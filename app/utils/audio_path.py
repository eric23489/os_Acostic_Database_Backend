"""
音档路径生成工具。

用于解析音档档名并生成 MinIO object key。

Filename 格式: {recorder_sn}.{YYMMDDHHMMSS}.{ext}
例如: 7505.240611130000.wav

Object Key 格式: {Point_Name}/{YYYY}/{MM}/Raw_Data/{Filename}
例如: TPC01/2024/06/Raw_Data/7505.240611130000.wav
"""

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AudioFileInfo:
    """解析档名后的资讯。"""

    recorder_sn: str
    record_time: datetime
    extension: str


def parse_audio_filename(filename: str) -> AudioFileInfo:
    """
    解析音档档名，取得录音机序号和录制时间。

    Args:
        filename: 档名，格式为 "7505.240611130000.wav"

    Returns:
        AudioFileInfo: 包含 recorder_sn, record_time, extension

    Raises:
        ValueError: 档名格式不符
    """
    # 支援 "7505.240611130000.wav" 或 "7505.240611130000"
    pattern = r"^(\d+)\.(\d{12})(?:\.(\w+))?$"
    match = re.match(pattern, filename)

    if not match:
        raise ValueError(f"Invalid filename format: {filename}")

    recorder_sn = match.group(1)
    timestamp_str = match.group(2)  # "240611130000"
    extension = match.group(3) or "wav"

    # 解析时间戳
    year = 2000 + int(timestamp_str[0:2])  # 24 -> 2024
    month = int(timestamp_str[2:4])  # 06
    day = int(timestamp_str[4:6])  # 11
    hour = int(timestamp_str[6:8])  # 13
    minute = int(timestamp_str[8:10])  # 00
    second = int(timestamp_str[10:12])  # 00

    record_time = datetime(year, month, day, hour, minute, second)

    return AudioFileInfo(
        recorder_sn=recorder_sn,
        record_time=record_time,
        extension=extension,
    )


def generate_object_key(point_name: str, filename: str) -> str:
    """
    生成 MinIO object key。

    Args:
        point_name: PointInfo.name (如 "TPC01")
        filename: 档名 (如 "7505.240611130000.wav")

    Returns:
        object_key: 如 "TPC01/2024/06/Raw_Data/7505.240611130000.wav"
    """
    info = parse_audio_filename(filename)

    year = info.record_time.strftime("%Y")  # "2024"
    month = info.record_time.strftime("%m")  # "06"

    return f"{point_name}/{year}/{month}/Raw_Data/{filename}"


def validate_filename_format(filename: str) -> bool:
    """
    验证档名格式是否正确。

    Args:
        filename: 档名

    Returns:
        bool: 格式是否正确
    """
    pattern = r"^\d+\.\d{12}(?:\.\w+)?$"
    return bool(re.match(pattern, filename))
