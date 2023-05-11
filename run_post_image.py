import os
from dataclasses import dataclass
from pathlib import Path

from bsky_gazo_bot.gazo_bot import GazoBot


@dataclass
class RunGazoBotConfig:
    log_dir: Path
    data_dir: Path


def run_gazo_bot(config: RunGazoBotConfig) -> None:
    gazo_bot = GazoBot(
        seconds_duplicate_post=120,
        data_dir=config.data_dir,
        username=os.environ["BSKY_USERNAME"],
        password=os.environ["BSKY_PASSWORD"],
    )
    gazo_bot.post_image()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("log_dir", type=Path)
    parser.add_argument("--data_dir", type=Path, default=Path("./data"))

    args = parser.parse_args()

    # init directories
    config = RunGazoBotConfig(log_dir=args.log_dir, data_dir=args.data_dir)

    config.log_dir.mkdir(parents=True, exist_ok=True)
    assert config.data_dir.exists()
    run_gazo_bot(config)
