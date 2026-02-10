import re


def dms_to_dd(dms_str: str) -> float:
    """
    將經緯度字串轉換為十進位 (Decimal Degrees) 格式。

    支援格式範例:
    - 度分 (DDM): "120°20.360' E", "24°5.951’N"

    Args:
        dms_str (str): 包含度、分、秒與方向的字串

    Returns:
        float: 轉換後的十進位數值 (WGS84)，保留 6 位小數
    """
    if not dms_str:
        return 0.0

    # 1. 統一符號：移除前後空白，將全形引號替換為半形
    clean_str = dms_str.strip().replace("’", "'").replace("”", '"')

    # 2. Regex 解析
    # 支援格式: 120° 20.360' E (度分)
    # Group 1: 度 (整數)
    # Group 2: 分 (浮點數)
    # Group 3: 方向 (NSEW)
    pattern = r"(\d+)°\s*([\d\.]+)'\s*([NSEW])"
    match = re.match(pattern, clean_str)

    if not match:
        raise ValueError(f"無法解析座標格式: {dms_str}")

    degrees = float(match.group(1))
    minutes = float(match.group(2))
    direction = match.group(3)

    # 轉換公式: 度 + (分/60)
    dd = degrees + (minutes / 60.0)

    # 南緯 (S) 或 西經 (W) 為負值
    if direction in ["S", "W"]:
        dd = -dd

    return round(dd, 6)
