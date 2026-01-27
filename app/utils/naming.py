import re
import random
import string
from pypinyin import pinyin, Style


def generate_slug_from_zh(text: str) -> str:
    """
    Generate a URL-friendly slug from Chinese text.

    Rules:
    1. Convert Chinese to Pinyin (no tones).
    2. Lowercase.
    3. Replace non-alphanumeric characters with hyphens.
    4. Truncate to 50 chars (leave room for suffixes).
    5. Strip leading/trailing hyphens.
    """
    if not text:
        return "project-" + "".join(
            random.choices(string.ascii_lowercase + string.digits, k=6)
        )

    # 1. Convert to Pinyin
    # pinyin returns list of lists, e.g. [['hai'], ['yang']]
    pinyin_list = pinyin(text, style=Style.NORMAL)
    slug = "-".join([item[0] for item in pinyin_list])

    # 2. Normalize
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")

    # 3. Truncate
    return slug[:50]
