import datetime
import logging
from pathlib import Path

from PIL import Image

from bsky_gazo_bot.db import ImageDataset


def add_images_manually(input_dir: Path, data_dir: Path, skip_register: bool, ext: str = "jpg") -> None:
    assert input_dir.exists()
    image_dataset = ImageDataset(data_dir=data_dir)
    uniq_id = "manually_add_" + str(datetime.datetime.now()).replace(" ", "_")
    for i, file in enumerate(input_dir.glob(f"*.{ext}")):
        image = Image.open(file)

        # 大きい画像はリサイズ
        max_size = max(image.width, image.height)
        if max_size > 1000:
            ratio = 1000 / max_size
            image = image.resize((int(image.width * ratio), int(image.height * ratio)))

        # 画像の追加
        image_id = image_dataset.add(post_cid=uniq_id, post_uri=uniq_id, index=i, image_data=image.tobytes())

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
