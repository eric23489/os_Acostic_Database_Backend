def parse_filename_and_generate_key(point_name: str, filename: str) -> str:
    """
    Generate MinIO object key based on filename format.

    Filename format example: 7505.240611130000.wav
    Target Object Key: point_name/YYYY/MM/Raw_Data/filename
    """
    try:
        parts = filename.split(".")
        # 預期格式至少有 [ID, Timestamp, Extension]
        if len(parts) >= 2:
            timestamp_str = parts[1]  # e.g., 240611130000
            if len(timestamp_str) >= 4:
                yy = timestamp_str[:2]  # 24
                mm = timestamp_str[2:4]  # 06
                yyyy = f"20{yy}"  # 2024
                return f"{point_name}/{yyyy}/{mm}/Raw_Data/{filename}"
    except Exception:
        pass

    # Fallback path if parsing fails
    return f"{point_name}/unknown_date/Raw_Data/{filename}"
