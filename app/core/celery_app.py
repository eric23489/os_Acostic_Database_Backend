"""
Celery 应用配置。

用于背景任务处理，包括：
- 孤儿记录清理
- 上传任务状态检查
"""

import os

from celery import Celery

# 从环境变量获取配置，或使用默认值
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

celery_app = Celery(
    "audio_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
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
        "app.tasks.audio_tasks.process_high_priority": {"queue": "high"},
        "app.tasks.audio_tasks.finalize_completed_uploads": {"queue": "normal"},
        "app.tasks.audio_tasks.cleanup_abandoned_audio_records": {"queue": "low"},
        "app.tasks.audio_tasks.cleanup_expired_jobs": {"queue": "low"},
    },
)

# 自动发现 tasks
celery_app.autodiscover_tasks(["app.tasks"])
