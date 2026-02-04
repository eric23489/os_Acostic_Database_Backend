import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 將專案根目錄加入 Python 路徑
sys.path.append(os.getcwd())

from app.core.config import settings
from app.models.project import ProjectInfo
from app.models.point import PointInfo
from app.models.deployment import DeploymentInfo
from app.models.recorder import RecorderInfo


def delete_data():
    # 覆寫連線設定：強制使用 localhost
    database_url = f"postgresql://{settings.postgres_user}:{settings.postgres_password}@localhost:{settings.postgres_port}/{settings.postgres_db}"
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        print("🗑️ 開始清除 TaiwanPower 2nd 資料 (直接連線 DB)...")

        project_name = "taiwanpower2nd"

        # 1. 搜尋 Project
        print(f"🔍 搜尋專案: {project_name}")
        project = db.query(ProjectInfo).filter(ProjectInfo.name == project_name).first()

        if not project:
            print(f"⚠️ 找不到專案 '{project_name}'，無需刪除。")
            return

        print(f"✅ 找到專案 ID: {project.id}")

        # 2. 搜尋並刪除 Points 與 Deployments
        points = db.query(PointInfo).filter(PointInfo.project_id == project.id).all()
        print(f"📊 找到 {len(points)} 個測站，準備刪除...")

        recorder_ids = set()
        for point in points:
            print(f"  📍 處理測站: {point.name} (ID: {point.id})")

            # 搜尋該 Point 的 Deployments
            deployments = (
                db.query(DeploymentInfo)
                .filter(DeploymentInfo.point_id == point.id)
                .all()
            )
            for dep in deployments:
                recorder_ids.add(dep.recorder_id)
                print(f"    🗑️ 刪除 Deployment ID: {dep.id}")
                db.delete(dep)

            # 刪除 Point
            print(f"    🗑️ 刪除測站: {point.name}")
            db.delete(point)

        # 3. 刪除 Project
        print(f"🗑️ 刪除專案: {project_name}")
        db.delete(project)

        # 確保前面的刪除操作已在資料庫中生效 (Transaction 內)，以便正確計算 Recorder 的使用量
        db.flush()

        # 4. 刪除 Recorders
        if recorder_ids:
            print(f"🔍 檢查 {len(recorder_ids)} 個儀器是否需要刪除...")
            recorders = (
                db.query(RecorderInfo).filter(RecorderInfo.id.in_(recorder_ids)).all()
            )
            for rec in recorders:
                # 檢查是否還有其他 Deployment 使用此 Recorder
                count = (
                    db.query(DeploymentInfo)
                    .filter(DeploymentInfo.recorder_id == rec.id)
                    .count()
                )
                rec_name = f"{rec.brand} {rec.model} ({rec.sn})"
                if count == 0:
                    print(f"    🗑️ 刪除儀器: {rec_name} (ID: {rec.id})")
                    db.delete(rec)
                else:
                    print(f"    ⚠️ 儀器 {rec_name} 仍被其他佈放使用，跳過刪除。")

        db.commit()
        print("✨ 資料清除完成！")

    except Exception as e:
        db.rollback()
        print(f"❌ 發生錯誤: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    delete_data()
