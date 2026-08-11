#!/usr/bin/env python3
"""
Scheduler for Weather Bot
Runs the weather analysis on schedule: Friday 23:00 and Tuesday 23:00 (Asia/Tehran)
"""

import os
import sys
import yaml
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

sys.path.insert(0, os.path.dirname(__file__))
from weather_bot import main as run_weather_bot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')


def load_config():
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def job():
    logger.info("🕐 Scheduled job triggered")
    try:
        run_weather_bot()
    except Exception as e:
        logger.error(f"Job failed: {e}")


def main():
    config = load_config()
    cron_expr = config.get('schedule', {}).get('cron_expression', '0 23 * * 2,5')
    timezone = config['location'].get('timezone', 'Asia/Tehran')

    # Parse cron expression: "0 23 * * 2,5" -> minute=0, hour=23, day_of_week='tue,fri'
    parts = cron_expr.split()
    if len(parts) == 5:
        minute, hour, dom, month, dow = parts
    else:
        minute, hour, dow = '0', '23', 'tue,fri'

    scheduler = BlockingScheduler(timezone=timezone)
    scheduler.add_job(
        job,
        CronTrigger(
            minute=minute,
            hour=hour,
            day_of_week=dow,
            timezone=timezone
        ),
        id='weather_bot_job',
        name='Weather Forecast Analysis',
        replace_existing=True
    )

    logger.info(f"📅 Scheduler started: {cron_expr} ({timezone})")
    logger.info("Press Ctrl+C to stop")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()