import datetime
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from pprint import pformat

from bsky_gazo_bot.cron_scheduler import CronScheduler
from bsky_gazo_bot.gazo_bot import GazoBot


@dataclass
class RunGazoBotConfig:
    log_dir: Path
    data_dir: Path
    reply_notification_period_sec: int
    seconds_duplicate_post: int
    init_session_priod_sec: int
    backup_priod_sec: int
    heart_beat_sec: int
    post_on_start: bool


class HeartBeater:
    def __init__(self, period_sec: int) -> None:
        self.start = datetime.datetime.now()
        self.period_sec = period_sec

    def __call__(self) -> bool:
        res = False
        now = datetime.datetime.now()
        if (now - self.start).seconds > self.period_sec:
            res = True
            self.start = datetime.datetime.now()
        return res


def run_gazo_bot(config: RunGazoBotConfig, logger: logging.Logger) -> None:
    logger.info(f"Run gazo bot {pformat(asdict(config))}")
    gazo_bot = GazoBot(
        seconds_duplicate_post=config.seconds_duplicate_post,
        data_dir=config.data_dir,
        username=os.environ["BSKY_USERNAME"],
        password=os.environ["BSKY_PASSWORD"],
        logger=logger,
    )
    reply_notification_beater = HeartBeater(config.reply_notification_period_sec)
    init_session_beater = HeartBeater(config.init_session_priod_sec)
    backup_beater = HeartBeater(config.backup_priod_sec)
    cron_scheduler = CronScheduler(target_hours=[13, 19])
    if config.post_on_start:
        gazo_bot.post_image()
    try:
        while True:
            if init_session_beater():
                gazo_bot.reset_session()
            if reply_notification_beater():
                gazo_bot.reply_nofitications()
            if backup_beater():
                gazo_bot.backup_data_dir()
            if cron_scheduler():
                gazo_bot.post_image()
            time.sleep(config.heart_beat_sec)
    finally:
        gazo_bot.close()


if __name__ == "__main__":
    hours_to_seconds = lambda x: x * 60 * 60
    days_to_seconds = lambda x: x * 24 * 60 * 60
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("log_dir", type=Path)
    parser.add_argument("--data_dir", type=Path, default=Path("./data"))
    parser.add_argument("--days_duplicate_post", type=int, default=7)
    parser.add_argument("--init_session_priod_sec", type=int, default=60 * 60)
    parser.add_argument("--reply_notification_period_sec", type=int, default=60 * 2)
    parser.add_argument("--backup_priod_hour", type=int, default=12)
    parser.add_argument("--heart_beat_sec", type=int, default=5)
    parser.add_argument("--post_on_start", action="store_true")

    args = parser.parse_args()

    # init directories
    config = RunGazoBotConfig(
        log_dir=args.log_dir,
        data_dir=args.data_dir,
        seconds_duplicate_post=days_to_seconds(args.days_duplicate_post),
        init_session_priod_sec=args.init_session_priod_sec,
        reply_notification_period_sec=args.reply_notification_period_sec,
        backup_priod_sec=hours_to_seconds(args.backup_priod_hour),
        heart_beat_sec=args.heart_beat_sec,
        post_on_start=args.post_on_start,
    )

    config.log_dir.mkdir(parents=True, exist_ok=True)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    log_file = config.log_dir / f"{Path(__file__).stem}.log"

    # init logger
    logger = logging.getLogger(__name__)
    [logger.removeHandler(x) for x in logger.handlers]

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(name)s %(asctime)s] %(message)s")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    try:
        run_gazo_bot(config, logger)
    finally:
        import traceback

        logger.error(traceback.format_exc())
