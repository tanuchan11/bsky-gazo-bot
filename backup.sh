#!/bin/bash

set -eux

TARGET_DIR=$1

IMAGES_DIR=$TARGET_DIR/images
SQL_FILE=$TARGET_DIR/db.sqlite3

TMP_IMAGE_FILE=/tmp/backup_tmp.tar.gz

if [ ! -d $IMAGES_DIR ] || [ ! -f $SQL_FILE ]; then
    echo "${IMAGES_DIR} or ${SQL_FILE} does not exist"
    exit 1
fi

# 画像ファイルを固める
tar -zcf $TMP_IMAGE_FILE -C $TARGET_DIR images

# Google driveにアップロード
rclone sync $SQL_FILE google_drive:gazo_bot/db.sqlite3
rclone sync $TMP_IMAGE_FILE google_drive:gazo_bot/backup_tmp.tar.gz
