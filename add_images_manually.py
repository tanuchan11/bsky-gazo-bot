import logging
import time
from pathlib import Path

from bsky_gazo_bot.db import ImageDataset


def add_images_manually(input_dir: Path, data_dir: Path, skip_register: bool, ext: str = "jpg") -> None:
    assert input_dir.exists()
    image_dataset = ImageDataset(data_dir=data_dir)
    base_id = "manually_add_" + str(time.time()).replace(".", "_")
    print(f"base_id = {base_id}")

    for i, file in enumerate(input_dir.glob(f"*.{ext}")):
        file_id = f"{base_id}_{i:04}"
        image_id = image_dataset.add_image_file(file_id=file_id, image_path=file)

        if skip_register:
            # センシティブ画像の登録をスキップ
            image_dataset.register_image(image_id=image_id, is_ok=True, ng_reason="manually add")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--data_dir", type=Path, default=Path("./data"))
    parser.add_argument("--skip_register", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    add_images_manually(input_dir=args.input_dir, data_dir=args.data_dir, skip_register=args.skip_register)
