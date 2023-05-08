import datetime
import logging
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import requests


@dataclass
class Ref:
    uri: str
    cid: str


@dataclass
class ReplyRef:
    root: Ref
    parent: Ref


class BskyBot:
    init_session: Callable[[], None]

    def __init__(
        self,
        username: str,
        password: str,
        min_request_interval_sec: int = 0,
        logger: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        assert len(username), "Empty username"
        assert len(password), "Empty password"
        self.api_server = "https://bsky.social"
        self.logger = logger
        self.last_requested = None
        self.min_request_interval_sec = min_request_interval_sec

        self.init_session = lambda: self.init_session_impl(username, password)
        self.init_session()

    def __may_wait(self) -> None:
        """May wait `min_request_interval_sec` to avoid too frequent request to the api server."""
        if self.last_requested is None:
            self.last_requested = datetime.datetime.now()
        else:
            now = datetime.datetime.now()
            time.sleep(min(self.min_request_interval_sec, (now - self.last_requested).seconds))
            self.last_requested = now

    def init_session_impl(self, username: str, password: str) -> None:
        self.logger.info("Initialize session")
        try:
            self.__may_wait()
            res = requests.post(
                self.api_server + "/xrpc/com.atproto.server.createSession",
                json={"identifier": username, "password": password},
            )
            assert res.ok, f"response of createSession is not OK: {res.text}"
            res = res.json()
            self.apt_auth_token, self.did = res["accessJwt"], res["did"]
        except Exception as e:
            self.logger.error(
                f"Failed to initialize session with server {self.api_server}. Check username and password."
            )
            self.logger.error(traceback.print_exc())
            raise e

    def __init_headers(self) -> Dict[str, Any]:
        return {"Authorization": "Bearer " + self.apt_auth_token}

    def update_seen(self) -> str:
        self.logger.info(f"Update seen")
        try:
            seen_at = datetime.datetime.now().isoformat().replace("+00:00", "Z")
            self.__may_wait()
            res = requests.post(
                self.api_server + "/xrpc/app.bsky.notification.updateSeen",
                json={"seenAt": seen_at},
                headers=self.__init_headers(),
            )
            assert res.ok, res.text
            return seen_at
        except Exception as e:
            self.logger.error(f"Failed to update seen {e}")
            raise e

    def get_notifications(self, limit: int = 1) -> Dict:
        self.logger.info(f"Get {limit} notifications")
        try:
            assert limit > 0, "limit <= 0"
            self.__may_wait()
            res = requests.get(
                self.api_server + "/xrpc/app.bsky.notification.listNotifications",
                params={"limit": limit},
                headers=self.__init_headers(),
            )
            assert res.ok, res.text
            return res.json()
        except Exception as e:
            self.logger.error(f"Failed to get notificatios {e}")
            raise e

    def get_post_thread(self, uri: str, depth: int) -> Dict[str, Any]:
        self.logger.info(f"Get thread uri = {uri} ")
        try:
            self.__may_wait()
            res = requests.get(
                self.api_server + "/xrpc/app.bsky.feed.getPostThread",
                params={"uri": uri, "depth": depth},
                headers=self.__init_headers(),
            )
            assert res.ok, res.text
            return res.json()
        except Exception as e:
            self.logger.error(f"Failed to get post thread {e}")
            raise e

    def upload_image(self, image_bytes: bytes) -> Dict[str, Any]:
        try:
            headers = self.__init_headers()
            headers["Content-Type"] = "image/jpeg"
            self.__may_wait()
            res = requests.post(
                self.api_server + "/xrpc/com.atproto.repo.uploadBlob", data=image_bytes, headers=headers
            )
            assert res.ok
            return res.json()
        except Exception as e:
            self.logger.error(f"Failed to upload image. due to {e}")
            raise e

    def post_feed(self, text: str, image: Optional[Path] = None, reply_ref: Optional[ReplyRef] = None) -> None:
        self.logger.info(f"Post feed text={text}, images={image}")
        try:
            data = {
                "collection": "app.bsky.feed.post",
                "$type": "app.bsky.feed.post",
                "repo": self.did,
                "record": {"createdAt": datetime.datetime.now().isoformat().replace("+00:00", "Z"), "text": text},
            }
            if reply_ref:
                data["record"]["reply"] = {
                    "root": {"uri": reply_ref.root.uri, "cid": reply_ref.root.cid},
                    "parent": {"uri": reply_ref.parent.uri, "cid": reply_ref.parent.cid},
                }
            if image:
                data["record"]["embed"] = {}
                data["record"]["embed"]["$type"] = "app.bsky.embed.images"
                upload_image = self.upload_image(image.open("rb").read())
                data["record"]["embed"]["images"] = [{"alt": "", "image": upload_image["blob"]}]

            self.__may_wait()
            res = requests.post(
                self.api_server + "/xrpc/com.atproto.repo.createRecord", json=data, headers=self.__init_headers()
            )
            assert res.ok, res.text
        except Exception as e:
            self.logger.error(f"Faield to post feed text={text}, image={image}, reply_ref={reply_ref}")
            raise e
