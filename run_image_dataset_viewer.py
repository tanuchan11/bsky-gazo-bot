import logging
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file

from bsky_gazo_bot.db import ImageDataset

logging.basicConfig(level=logging.INFO)

image_dataset = ImageDataset(Path("./data"))
app = Flask(__name__)


@app.route("/")
def get_root():
    return render_template("index.html")


@app.route("/images/unchecked")
def get_images():
    data = image_dataset.get_unchecked_images()
    return render_template("images.html", data=data)


@app.route("/images/all")
def get_images_all():
    data = image_dataset.get_all_images()
    return render_template("images.html", data=data)


@app.route("/images/<path:path>")
def get_image(path):
    return send_file(image_dataset.image_file_dir / path)


@app.route("/register", methods=["POST"])
def post_register():
    image_id = int(request.args["image_id"])
    ok = request.args["ok"].lower() == "true"
    ng_reason = request.args.get("reason", default="no reason")
    image_dataset.register_image(image_id=image_id, is_ok=ok, ng_reason=ng_reason)
    return jsonify(success=True)


@app.route("/register/all_ok")
def register_all_ok():
    ids = image_dataset.register_all_ok()
    return jsonify(success=True, registered_ids=ids)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    app.run(host=args.host, port=args.port)
