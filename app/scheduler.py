"""Scheduler integre — lance l'inventaire automatiquement via APScheduler.

Active si SCHEDULER_ENABLED=true dans .env.
Par defaut, run quotidien a 02:00 (configurable via SCHEDULER_HOUR / SCHEDULER_MINUTE).
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("cloudinventory.scheduler")

_scheduler = None


def _run_inventory_job(app):
    """Job planifie : execute run_inventory dans le contexte Flask."""
    with app.app_context():
        from collector.inventory_runner import run_inventory
        logger.info("Scheduler : lancement automatique de l'inventaire")
        try:
            run = run_inventory()
            logger.info("Scheduler : run #%d termine — %s (%d VMs)",
                        run.id, run.status, run.vm_count or 0)
        except Exception:
            logger.exception("Scheduler : erreur lors du run automatique")


def init_scheduler(app):
    """Initialise et demarre le scheduler si active."""
    global _scheduler

    enabled = app.config.get("SCHEDULER_ENABLED", False)
    if not enabled:
        logger.debug("Scheduler desactive (SCHEDULER_ENABLED=false)")
        return

    hour = app.config.get("SCHEDULER_HOUR", 2)
    minute = app.config.get("SCHEDULER_MINUTE", 0)

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        func=_run_inventory_job,
        args=[app],
        trigger="cron",
        hour=hour,
        minute=minute,
        id="daily_inventory",
        name="Inventaire quotidien",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Scheduler demarre : inventaire quotidien a %02d:%02d", hour, minute)


def get_scheduler_info():
    """Retourne les infos du scheduler pour le dashboard/API."""
    if not _scheduler:
        return {"enabled": False}

    job = _scheduler.get_job("daily_inventory")
    if not job:
        return {"enabled": True, "next_run": None}

    return {
        "enabled": True,
        "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
    }
