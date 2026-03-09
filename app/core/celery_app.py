"""
Celery 应用配置。

用于背景任务处理，包括：
- 孤儿记录清理
- 上传任务状态检查
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "audio_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Taipei",
    enable_utc=True,
    # 优先级设定 (0=最高, 9=最低)
    task_default_priority=5,
    task_queue_max_priority=10,
    # 任务路由
    task_routes={
        "app.tasks.audio_tasks.finalize_completed_uploads": {"queue": "normal"},
        "app.tasks.audio_tasks.cleanup_abandoned_audio_records": {"queue": "low"},
        "app.tasks.audio_tasks.cleanup_expired_jobs": {"queue": "low"},
    },
)

# 自动发现 tasks
celery_app.autodiscover_tasks(["app.tasks"])
