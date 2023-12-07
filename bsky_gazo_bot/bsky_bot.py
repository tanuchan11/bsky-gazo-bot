import datetime
import io
import logging
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import requests
from PIL import Image


@dataclass
class Ref:
    uri: str
    cid: str


@dataclass
class ReplyRef:
    root: Ref
    parent: Ref


class BskyBot:
    init_session: Callable[[], Dict]

    def __init__(
        self,
        username: str,
        password: str,
        min_request_interval_sec: int = 0,
        max_retry: int = 5,
        logger: logging.Logger = logging.getLogger(__name__),
    ) -> None:
        assert len(username), "Empty username"
        assert len(password), "Empty password"
        self.api_server = "https://bsky.social"
        self.logger = logger
        self.last_requested = None
        self.min_request_interval_sec = min_request_interval_sec
        self.max_retry = max_retry
        self.init_session = lambda: self.init_session_impl(username, password)
        self.init_session()

    def __init_headers(self) -> Dict[str, Any]:
        return {"Authorization": "Bearer " + self.apt_auth_token}

    def __may_wait(self) -> None:
        """May wait `min_request_interval_sec` to avoid too frequent request to the api server."""
        if self.last_requested is None:
            self.last_requested = datetime.datetime.now()
        else:
            now = datetime.datetime.now()
            time.sleep(min(self.min_request_interval_sec, (now - self.last_requested).seconds))
            self.last_requested = now

    def __api_call(
        self,
        method: str,
        url: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        data: Optional[bytes] = None,
    ) -> Dict:
        f = {"get": requests.get, "post": requests.post}[method]
        for _ in range(self.max_retry):
            try:
                self.__may_wait()
                res = f(url, json=json, params=params, headers=headers, data=data)
                assert res.ok, res.text
                json_dict = res.json()
                return json_dict
            except Exception as e:
                self.logger.error(f"Failed to call api {method} {url} {json} {params} due to {e}")
                self.logger.error(traceback.print_exc())
        raise RuntimeError(f"Reaches max retry = {self.max_retry}")

    def init_session_impl(self, username: str, password: str) -> Dict:
        self.logger.info("Initialize session")
        data = self.__api_call(
            "post",
            self.api_server + "/xrpc/com.atproto.server.createSession",
            json={"identifier": username, "password": password},
        )
        self.apt_auth_token, self.did = data["accessJwt"], data["did"]
        return data

    def update_seen(self) -> Dict:
        self.logger.info(f"Update seen")
        seen_at = datetime.datetime.now().isoformat().replace("+00:00", "Z")
        return self.__api_call(
            "post",
            self.api_server + "/xrpc/app.bsky.notification.updateSeen",
            json={"seenAt": seen_at},
            headers=self.__init_headers(),
        )

    def get_notifications(self, limit: int = 1) -> Dict:
        self.logger.info(f"Get {limit} notifications")
        assert limit > 0, "limit <= 0"
        return self.__api_call(
            "get",
            self.api_server + "/xrpc/app.bsky.notification.listNotifications",
            params={"limit": limit},
            headers=self.__init_headers(),
        )

    def get_post_thread(self, uri: str, depth: int) -> Dict[str, Any]:
        self.logger.info(f"Get thread uri = {uri} ")
        return self.__api_call(
            "get",
            self.api_server + "/xrpc/app.bsky.feed.getPostThread",
            params={"uri": uri, "depth": depth},
            headers=self.__init_headers(),
        )

    def upload_blob(self, image: Path) -> Dict[str, Any]:
        self.logger.info("Upload image")
        headers = self.__init_headers()
        headers["Content-Type"] = "image/jpeg"
        with io.BytesIO() as buffer:
            Image.open(image).save(buffer, "JPEG")
            buffer.seek(0)
            return self.__api_call(
                "post", self.api_server + "/xrpc/com.atproto.repo.uploadBlob", data=buffer.read(), headers=headers
            )

    def create_record(
        self,
        text: str,
        image: Optional[Path] = None,
        reply_ref: Optional[ReplyRef] = None,
    ) -> Dict:
        self.logger.info(f"Post feed text={text}, images={image}")
        data = {
            "repo": self.did,
            "collection": "app.bsky.feed.post",
            "record": {
                "$type": "app.bsky.feed.post",
                "text": text,
                "createdAt": datetime.datetime.now().isoformat() + "Z",
            },
        }
        if reply_ref:
            data["record"]["reply"] = {
                "root": {"uri": reply_ref.root.uri, "cid": reply_ref.root.cid},
                "parent": {"uri": reply_ref.parent.uri, "cid": reply_ref.parent.cid},
            }
        if image:
            image_ref = self.upload_blob(image)
            data["record"]["embed"] = {
                "$type": "app.bsky.embed.images",
                "images": [{"alt": "", "image": image_ref["blob"]}],
            }
            data["record"]["embed"]["$type"] = "app.bsky.embed.images"

        return self.__api_call(
            "post", self.api_server + "/xrpc/com.atproto.repo.createRecord", json=data, headers=self.__init_headers()
        )
