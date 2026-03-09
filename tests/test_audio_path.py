"""Tests for audio path utilities."""

from datetime import datetime

import pytest

from app.utils.audio_path import (
    generate_object_key,
    parse_audio_filename,
    validate_filename_format,
)


class TestParseAudioFilename:
    """Tests for parse_audio_filename function."""

    def test_parse_valid_filename_with_extension(self):
        """Test parsing a valid filename with extension."""
        result = parse_audio_filename("7505.240611130000.wav")

        assert result.recorder_sn == "7505"
        assert result.record_time == datetime(2024, 6, 11, 13, 0, 0)
        assert result.extension == "wav"

    def test_parse_valid_filename_without_extension(self):
        """Test parsing a valid filename without extension."""
        result = parse_audio_filename("7505.240611130000")

        assert result.recorder_sn == "7505"
        assert result.record_time == datetime(2024, 6, 11, 13, 0, 0)
        assert result.extension == "wav"  # default

    def test_parse_different_recorder_sn(self):
        """Test parsing with different recorder serial numbers."""
        result = parse_audio_filename("8444.240629073900.wav")

        assert result.recorder_sn == "8444"
        assert result.record_time == datetime(2024, 6, 29, 7, 39, 0)

    def test_parse_different_extension(self):
        """Test parsing with different file extension."""
        result = parse_audio_filename("7505.240611130000.flac")

        assert result.extension == "flac"

    def test_parse_invalid_filename_raises_error(self):
        """Test that invalid filenames raise ValueError."""
        invalid_names = [
            "invalid.wav",
            "7505.wav",
            "7505.24061113000.wav",  # 11 digits instead of 12
            "7505.2406111300001.wav",  # 13 digits instead of 12
            "test_file.wav",
            "",
        ]

        for name in invalid_names:
            with pytest.raises(ValueError):
                parse_audio_filename(name)


class TestGenerateObjectKey:
    """Tests for generate_object_key function."""

    def test_generate_object_key_basic(self):
        """Test basic object key generation."""
        key = generate_object_key("TPC01", "7505.240611130000.wav")

        assert key == "TPC01/2024/06/Raw_Data/7505.240611130000.wav"

    def test_generate_object_key_different_month(self):
        """Test object key generation with different month."""
        key = generate_object_key("TPC02", "8444.241201153000.wav")

        assert key == "TPC02/2024/12/Raw_Data/8444.241201153000.wav"

    def test_generate_object_key_different_point(self):
        """Test object key generation with different point name."""
        key = generate_object_key("STATION_A", "7505.240611130000.wav")

        assert key == "STATION_A/2024/06/Raw_Data/7505.240611130000.wav"


class TestValidateFilenameFormat:
    """Tests for validate_filename_format function."""

    def test_valid_formats(self):
        """Test that valid formats return True."""
        valid_names = [
            "7505.240611130000.wav",
            "8444.240629073900.flac",
            "12345.991231235959.mp3",
            "1.000101000000.wav",
            "7505.240611130000",  # without extension
        ]

        for name in valid_names:
            assert validate_filename_format(name) is True

    def test_invalid_formats(self):
        """Test that invalid formats return False."""
        invalid_names = [
            "invalid.wav",
            "7505.wav",
            "7505.24061113000.wav",
            "test_file.wav",
            "",
            "7505-240611130000.wav",  # wrong separator
        ]

        for name in invalid_names:
            assert validate_filename_format(name) is False
