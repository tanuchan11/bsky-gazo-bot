import logging
import subprocess
from pathlib import Path
from typing import Optional

import requests

from bsky_gazo_bot.bsky_bot import BskyBot, Ref, ReplyRef
from bsky_gazo_bot.image_dataset import EmptyPostImageException, ImageDataset


class GazoBot:
    def __init__(
        self,
        seconds_duplicate_post: int,
        data_dir: Path,
        username: str,
        password: str,
        logger: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        self.logger = logger
        self.seconds_duplicate_post = seconds_duplicate_post
        self.bsky_bot = BskyBot(username, password, min_request_interval_sec=1, logger=logger)
        self.image_dataset = ImageDataset(data_dir=data_dir)
        self.data_dir = data_dir

    def backup_data_dir(self) -> None:
        res = subprocess.run(f"bash backup.sh {self.data_dir}".split(), capture_output=True)
        self.logger.info(f"Run backup.sh. returncode = {res.returncode}, {res.stdout.decode()} {res.stderr.decode()}")
        assert res.returncode == 0, f"Failed to run backup.sh"

    def reset_session(self) -> None:
        self.logger.info(f"Init session")
        self.bsky_bot.init_session()

    def gather_image(self) -> None:
        """メンションされた投稿のうち，画像添付のもので保存したことない画像をすべて保存する"""
        self.logger.info("Gather image")
        for notification in self.bsky_bot.get_notifications(100)["notifications"]:
            # 画像のメンション投稿だけをフィルタリングする
            if notification["reason"] != "mention":
                continue
            record = notification["record"]
            if not "embed" in record:
                continue
            embed = record["embed"]
            if embed["$type"] != "app.bsky.embed.images":
                continue

            # もし登録されていなかったら画像投稿の詳細を取得
            cid, uri = notification["cid"], notification["uri"]
            if self.image_dataset.is_added(cid, uri):
                continue

            # ダウンロードして保存
            thread = self.bsky_bot.get_post_thread(uri, 1)["thread"]
            for i, image in enumerate(thread["post"]["embed"]["images"]):
                self.image_dataset.add(cid, uri, i, requests.get(image["fullsize"]).content)

            # お礼を投稿
            self.bsky_bot.post_feed(
                "受け付けました。確認の上で投稿候補に加わります。", reply_ref=ReplyRef(root=Ref(uri=uri, cid=cid), parent=Ref(uri=uri, cid=cid))
            )

    def post_image(self) -> None:
        """画像を1つ投稿する"""
        self.logger.info("Post image")
        image: Optional[Path] = None
        try:
            image = self.image_dataset.sample(seconds=self.seconds_duplicate_post)
        except EmptyPostImageException:
            self.logger.info("Empty post image.")
            self.bsky_bot.post_feed("投稿する画像がありません")
            return
        except Exception as e:
            raise e
        assert image
        self.bsky_bot.post_feed(text="", image=image)

    def close(self):
        self.backup_data_dir()
