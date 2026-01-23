from app.utils.path_utils import parse_filename_and_generate_key


def test_parse_filename_and_generate_key_valid():
    """
    Test generating object key from a valid filename format.
    Format: ID.YYMMDDHHMMSS.wav
    """
    point_name = "PointA"
    filename = "7505.240611130000.wav"
    # Expected: point_name/20YY/MM/Raw_Data/filename
    expected = "PointA/2024/06/Raw_Data/7505.240611130000.wav"

    assert parse_filename_and_generate_key(point_name, filename) == expected


def test_parse_filename_and_generate_key_invalid():
    """
    Test fallback behavior when filename format is not recognized.
    """
    point_name = "PointA"
    filename = "invalid_filename.wav"
    expected = "PointA/unknown_date/Raw_Data/invalid_filename.wav"

    assert parse_filename_and_generate_key(point_name, filename) == expected
