# bsky_gazo_bot

## How to init

1. `pip install sqlalchemy Flask requests`
2. `tar`と[rclone](https://rclone.org/)が使えるようにする

### How to run

```bash
# botの実行
env BSKY_USERNAME=<your-user-name.bsky.social> BSKY_PASSWORD=<password> python run_gazo_bot.py

# 画像チェックUIの起動
python run_image_dataset_viewer.py
```

## TODO

- [ ] 仮運用
- [ ] 引用ポストの追跡とランキング作成
