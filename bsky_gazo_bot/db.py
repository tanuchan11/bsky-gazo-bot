import datetime
import logging
import random
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import Column
from sqlalchemy.sql.expression import func
from sqlalchemy.types import Boolean, DateTime, Integer, String

Base = declarative_base()


class EmptyPostImageException(Exception):
    pass


class Image(Base):
    __tablename__ = "image"
    id = Column(Integer, primary_key=True)
    post_cid = Column(String(255))
    post_uri = Column(String(255))
    filename = Column(String(255))
    index = Column(Integer)
    add_date = Column(DateTime)


class ImageCheck(Base):
    __tablename__ = "image_check"
    id = Column(Integer, primary_key=True)
    image_id = Column(Integer)
    checked = Column(Boolean)
    ng_reason = Column(String)
    ok = Column(Boolean)
    checked_date = Column(DateTime)


class ImagePostHistory(Base):
    __tablename__ = "image_post_history"
    id = Column(Integer, primary_key=True)
    image_id = Column(Integer)
    post_date = Column(DateTime)


class ImageDataset:
    def __init__(self, data_dir: Path, logger: logging.Logger = logging.getLogger(__name__)):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger

        self.image_file_dir = data_dir / "images"
        self.image_file_dir.mkdir(parents=True, exist_ok=True)
        engine = sqlalchemy.create_engine(f'sqlite:///{data_dir.absolute() / "db.sqlite3"}')
        Base.metadata.create_all(engine)
        self.session = sessionmaker(engine)()

    def is_added(self, post_cid: str, post_uri: str) -> bool:
        return (
            not self.session.query(Image).filter(Image.post_cid == post_cid).filter(Image.post_uri == post_uri).first()
            is None
        )

    def add_image_file(self, file_id: str, image_path: Path) -> int:
        self.logger.info(f"add image file id={file_id} image_path={image_path}")
        assert image_path.exists() and image_path.suffix == ".jpg"
        image_path_dst = (self.image_file_dir / f"{file_id}").with_suffix(".jpg")
        assert not image_path_dst.exists(), image_path_dst
        shutil.copy(image_path, image_path_dst)
        image = Image(
            post_cid=file_id, post_uri=file_id, index=0, filename=image_path_dst.name, add_date=datetime.datetime.now()
        )
        self.session.add(image)
        self.session.commit()
        return image.id

    def add(self, post_cid: str, post_uri: str, index: int, image_data: bytes) -> int:
        self.logger.info(f"Add image cid={post_cid} uri={post_uri}")
        filename = (self.image_file_dir / f"{post_cid}_{index:01}").with_suffix(".jpg")
        assert not filename.exists(), filename
        with filename.open("wb") as f:
            f.write(image_data)
        image = Image(
            post_cid=post_cid, post_uri=post_uri, index=index, filename=filename.name, add_date=datetime.datetime.now()
        )
        self.session.add(image)
        self.session.commit()
        return image.id

    def register_all_ok(self) -> list[int]:
        checked_date = datetime.datetime.now()
        res = []
        for image in self.session.query(Image).all():
            image_check: ImageCheck = self.session.query(ImageCheck).filter(ImageCheck.image_id == image.id).first()
            if image_check is None:
                image_check = ImageCheck(
                    image_id=image.id, checked=True, ng_reason=None, ok=True, checked_date=checked_date
                )
                self.session.add(image_check)
                res.append(image.id)
        self.session.commit()
        self.logger.info(f"register_all_ok: {len(res)} images.")
        return res

    def register_image(
        self,
        image_id: int,
        is_ok: bool,
        ng_reason: Optional[str] = None,
        checked_date: Optional[datetime.datetime] = None,
    ) -> None:
        self.logger.info(f"Register image {image_id}, {is_ok}, {ng_reason}, {checked_date}")
        if checked_date is None:
            checked_date = datetime.datetime.now()
        if not is_ok:
            assert ng_reason is not None
        image_check = self.session.query(ImageCheck).filter(ImageCheck.image_id == image_id).first()
        if image_check is None:
            image_check = ImageCheck(
                image_id=image_id, checked=True, ng_reason=ng_reason, ok=is_ok, checked_date=checked_date
            )
            self.session.add(image_check)
        else:
            image_check.is_ok = is_ok
            image_check.ng_reason = ng_reason
            image_check.checked_date = checked_date
        self.session.commit()

    def random_sample(self) -> Path:
        self.logger.info("Random sample")
        image = self.session.query(Image).order_by(func.random()).first()
        if image is None:
            raise EmptyPostImageException
        return self.image_file_dir / image.filename

    def sample(self, seconds: int = 0) -> Path:
        self.logger.info(f"Sample an image {seconds}")
        no_posted: List[ImageCheck] = []
        no_posted_since_n_secs: List[Tuple[ImageCheck, int]] = []
        post_date = datetime.datetime.now()
        for image_check in self.session.query(ImageCheck).filter(ImageCheck.ok == True).all():
            image_post_history = (
                self.session.query(ImagePostHistory)
                .filter(ImagePostHistory.image_id == image_check.image_id)
                .order_by(sqlalchemy.desc(ImagePostHistory.post_date))
                .first()
            )
            if image_post_history:
                diff: int = (post_date - image_post_history.post_date).total_seconds()
                if diff > seconds:
                    no_posted_since_n_secs.append((image_check, diff))
            else:
                no_posted.append(image_check)

        if len(no_posted):
            image_check = random.choice(no_posted)
            image = self.session.query(Image).filter(Image.id == image_check.image_id).first()
            self.session.add(ImagePostHistory(image_id=image.id, post_date=post_date))
            self.session.commit()
            return self.image_file_dir / image.filename

        if len(no_posted_since_n_secs):
            weights = [x[1] for x in no_posted_since_n_secs]
            image_check, image_post_history = random.choices(no_posted_since_n_secs, weights=weights)[0]
            image = self.session.query(Image).filter(Image.id == image_check.image_id).first()
            self.session.add(ImagePostHistory(image_id=image.id, post_date=post_date))
            self.session.commit()
            return self.image_file_dir / image.filename

        raise EmptyPostImageException("Not image to be post")

    def get_all_post_history(self):
        self.logger.info("Get Post history")
        return self.session.query(ImagePostHistory).order_by(sqlalchemy.desc(ImagePostHistory.post_date)).all()

    def get_unchecked_images(self) -> List[Tuple[int, str, datetime.datetime]]:
        """Returns List of image's id, and image's posix path."""
        self.logger.info("Get unchecked images")
        res = []
        for image in self.session.query(Image).all():
            image_check = self.session.query(ImageCheck).filter(ImageCheck.image_id == image.id).first()
            if image_check is None:
                res.append((image.id, image.filename, image.add_date, False))
        return res

    def get_all_images(self) -> List[Tuple[Path, bool]]:
        self.logger.info("Get all images")
        res = []
        for image in self.session.query(Image).all():
            image_check = self.session.query(ImageCheck).filter(ImageCheck.image_id == image.id).first()
            checked = image_check is not None
            res.append((image.id, image.filename, image.add_date, checked))
        return res


class Reply(Base):
    __tablename__ = "reply"
    id = Column(Integer, primary_key=True)
    post_cid = Column(String(255))
    post_uri = Column(String(255))
    post_text = Column(String)
    reply_date = Column(DateTime)
    reply_text = Column(String)


class ReplyDataset:
    def __init__(self, data_dir: Path, logger: logging.Logger = logging.getLogger(__name__)):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logger
        engine = sqlalchemy.create_engine(f'sqlite:///{data_dir.absolute() / "db.sqlite3"}')
        Base.metadata.create_all(engine)
        self.session = sessionmaker(engine)()

    def is_added(self, post_cid: str, post_uri: str) -> bool:
        return (
            not self.session.query(Reply).filter(Reply.post_cid == post_cid).filter(Reply.post_uri == post_uri).first()
            is None
        )

    def add(self, post_cid: str, post_uri: str, post_text: str, reply_text: str) -> None:
        self.logger.info(f"Add reply cid={post_cid} uri={post_uri} post_text={post_text} reply_text={reply_text}")
        reply = Reply(
            post_cid=post_cid,
            post_uri=post_uri,
            post_text=post_text,
            reply_date=datetime.datetime.now(),
            reply_text=reply_text,
        )
        self.session.add(reply)
        self.session.commit()
