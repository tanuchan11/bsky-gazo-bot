import datetime
import logging
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from pprint import pformat

from gazo_bot import GazoBot


@dataclass
class RunGazoBotConfig:
    log_dir: Path
    data_dir: Path
    gather_image_period_sec: int
    post_image_period_sec: int
    seconds_duplicate_post: int


class HearBeater:
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
    post_image_beater = HearBeater(config.post_image_period_sec)
    try:
        while True:
            gazo_bot.gather_image()
            if post_image_beater():
                gazo_bot.post_image()
            time.sleep(config.gather_image_period_sec)
    finally:
        gazo_bot.close()


if __name__ == "__main__":
    hours_to_seconds = lambda x: x * 60 * 60
    days_to_seconds = lambda x: x * 24 * 60 * 60
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("log_dir", type=Path)
    parser.add_argument("--data_dir", type=Path, default=Path("./data"))
    parser.add_argument("--gather_image_period_sec", type=int, default=60 * 5)
    parser.add_argument("--hours_post", type=int, default=24)
    parser.add_argument("--days_duplicate_post", type=int, default=30)
    args = parser.parse_args()

    # init directories
    config = RunGazoBotConfig(
        log_dir=args.log_dir,
        data_dir=args.data_dir,
        gather_image_period_sec=args.gather_image_period_sec,
        post_image_period_sec=hours_to_seconds(args.hours_post),
        seconds_duplicate_post=days_to_seconds(args.days_duplicate_post),
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
