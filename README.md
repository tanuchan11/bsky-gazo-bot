# bsky_gazo_bot

## How to init

```bash
pipenv install --dev
pipenv shell
```

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
