import logging
import subprocess
from pathlib import Path
from typing import Dict, Optional

import requests

from bsky_gazo_bot.bsky_bot import BskyBot, Ref, ReplyRef
from bsky_gazo_bot.db import EmptyPostImageException, ImageDataset, ReplyDataset


class GazoBot:
    def __init__(
        self,
        data_dir: Path,
        username: str,
        password: str,
        seconds_duplicate_post: int,
        logger: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        self.logger = logger
        self.seconds_duplicate_post = seconds_duplicate_post
        self.bsky_bot = BskyBot(username, password, min_request_interval_sec=1, logger=logger)
        self.image_dataset = ImageDataset(data_dir=data_dir, logger=logger)
        self.reply_dataset = ReplyDataset(data_dir=data_dir, logger=logger)
        self.data_dir = data_dir
        self.username = username

    def backup_data_dir(self) -> None:
        res = subprocess.run(f"bash backup.sh {self.data_dir}".split(), capture_output=True)
        self.logger.info(f"Run backup.sh. returncode = {res.returncode}, {res.stdout.decode()} {res.stderr.decode()}")
        assert res.returncode == 0, f"Failed to run backup.sh"

    def reset_session(self) -> None:
        self.logger.info(f"Init session")
        self.bsky_bot.init_session()

    def __gather_image(self, notification: Dict) -> None:
        # もし登録されていなかったら画像投稿の詳細を取得
        cid, uri = notification["cid"], notification["uri"]
        if self.image_dataset.is_added(cid, uri):
            return

        # ダウンロードして保存
        data = self.bsky_bot.get_post_thread(uri, 1)
        if "thread" in data:
            thread = data["thread"]
            for i, image in enumerate(thread["post"]["embed"]["images"]):
                self.image_dataset.add(cid, uri, i, requests.get(image["fullsize"]).content)

            # お礼を投稿
            self.bsky_bot.create_record(
                "受け付けました。確認の上で投稿候補に加わります。", reply_ref=ReplyRef(root=Ref(uri=uri, cid=cid), parent=Ref(uri=uri, cid=cid))
            )

    def __reply_to_text(self, notification: Dict) -> None:
        cid, uri = notification["cid"], notification["uri"]
        if self.reply_dataset.is_added(cid, uri):
            return
        data = self.bsky_bot.get_post_thread(uri, 1)
        if not "thread" in data:
            return
        thread = data["thread"]
        text = thread["post"]["record"]["text"]
        text = text.replace(f"@{self.username} ", "").strip()

        if text == "ping":
            reply_text = "pong"
            self.bsky_bot.create_record(
                reply_text, reply_ref=ReplyRef(root=Ref(uri=uri, cid=cid), parent=Ref(uri=uri, cid=cid))
            )
            self.reply_dataset.add(cid, uri, text, reply_text)
        elif text == "pull":
            try:
                image = self.image_dataset.random_sample()
            except EmptyPostImageException:
                self.logger.info("Empty post image.")
                self.bsky_bot.create_record(
                    "画像がありません", reply_ref=ReplyRef(root=Ref(uri=uri, cid=cid), parent=Ref(uri=uri, cid=cid))
                )
                return
            self.bsky_bot.create_record(
                "", reply_ref=ReplyRef(root=Ref(uri=uri, cid=cid), parent=Ref(uri=uri, cid=cid)), image=image
            )
            self.reply_dataset.add(cid, uri, text, "")
        else:
            pass

    def reply_nofitications(self) -> None:
        """メンションされた投稿のうち，画像添付のもので保存したことない画像をすべて保存する"""
        self.logger.info("Gather image")
        for notification in self.bsky_bot.get_notifications(100)["notifications"]:
            # メンション投稿だけをフィルタリングする
            if notification["reason"] != "mention":
                continue

            # 画像つき投稿のみをフィルタリングする
            if (
                "record" in notification
                and "embed" in notification["record"]
                and notification["record"]["embed"]["$type"] == "app.bsky.embed.images"
            ):
                self.__gather_image(notification)
            else:
                self.__reply_to_text(notification)

    def post_image(self) -> None:
        """画像を1つ投稿する"""
        self.logger.info("Post image")
        image: Optional[Path] = None
        try:
            image = self.image_dataset.sample(seconds=self.seconds_duplicate_post)
        except EmptyPostImageException:
            self.logger.info("Empty post image.")
            self.bsky_bot.create_record("投稿する画像がありません")
            return
        except Exception as e:
            raise e
        assert image
        self.bsky_bot.create_record(text="", image=image)

    def close(self):
        self.backup_data_dir()
