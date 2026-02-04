import sys
import os
from sqlalchemy.dialects import postgresql

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.audio import AudioInfo


def print_audio_query(deployment_id: int):
    db = SessionLocal()
    # 模擬 AudioService.get_audios 的查詢邏輯
    query = db.query(AudioInfo).filter(AudioInfo.is_deleted == False)
    if deployment_id:
        query = query.filter(AudioInfo.deployment_id == deployment_id)

    # 編譯並印出 SQL
    # literal_binds=True 會將參數填入 SQL 中，方便閱讀
    print("--- SQLAlchemy Generated SQL ---")
    print(
        str(
            query.statement.compile(
                dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
            )
        )
    )


if __name__ == "__main__":
    print_audio_query(1)
