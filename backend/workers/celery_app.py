from celery import Celery
from core.config import settings

celery_app = Celery(
    "smartcheckout",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Dakar",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_routes={
        "workers.tasks.generate_receipt_pdf": {"queue": "pdf"},
        "workers.tasks.notify_*": {"queue": "notifications"},
        "workers.tasks.generate_monthly_report": {"queue": "reports"},
    },
    beat_schedule={
        "check-expired-orders": {
            "task": "workers.tasks.cancel_expired_orders",
            "schedule": 300.0,  # toutes les 5 minutes
        },
        "generate-monthly-reports": {
            "task": "workers.tasks.generate_monthly_reports",
            "schedule": 3600.0,  # toutes les heures (check si 1er du mois)
        },
        "send-stock-alerts": {
            "task": "workers.tasks.send_stock_alerts",
            "schedule": 3600.0,  # toutes les heures
        },
        "check-subscription-expiry": {
            "task": "workers.tasks.check_subscription_expiry",
            "schedule": 86400.0,  # quotidien
        },
        "compute-customer-scores": {
            "task": "workers.tasks.compute_customer_scores",
            "schedule": 86400.0,  # quotidien
        },
    },
)
