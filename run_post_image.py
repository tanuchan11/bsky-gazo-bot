import os
from dataclasses import dataclass
from pathlib import Path

from bsky_gazo_bot.gazo_bot import GazoBot


@dataclass
class RunGazoBotConfig:
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
    parser.add_argument("--data_dir", type=Path, default=Path("./data"))

    args = parser.parse_args()

    # init directories
    config = RunGazoBotConfig(data_dir=args.data_dir)
    assert config.data_dir.exists()
    run_gazo_bot(config)
