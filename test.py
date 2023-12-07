import tempfile
from pathlib import Path

import numpy as np
import PIL.Image
import pytest

from bsky_gazo_bot.db import EmptyPostImageException, ImageDataset


def test_image_dataset():
    with tempfile.TemporaryDirectory() as data_dir:
        data_dir = Path(data_dir)
        example_image = PIL.Image.fromarray(
            np.random.randint(low=0, high=256, size=(128, 128, 3), dtype=np.uint8)
        ).tobytes()
        dataset = ImageDataset(data_dir)

        # can add images
        dataset.add("post-cid-1", "post-uri-1", 0, example_image)
        dataset.add("post-cid-2", "post-uri-2", 0, example_image)
        dataset.add("post-cid-3", "post-uri-3", 0, example_image)
        assert len(dataset.get_unchecked_images()) == 3

        # can register images
        dataset.register_image(1, True)
        assert len(dataset.get_unchecked_images()) == 2
        dataset.register_image(2, False, ng_reason="foo")
        dataset.register_image(3, True)

        # can update regsited image
        dataset.register_image(2, False, ng_reason="bar")

        # can sample image: 2 images are ok, 1 is ng
        dataset.sample()
        dataset.sample()
        assert len(dataset.get_all_post_history()) == 2
        dataset.sample()

        # can raises exception when there is no image to be post
        with pytest.raises(EmptyPostImageException):
            dataset.sample(100)
