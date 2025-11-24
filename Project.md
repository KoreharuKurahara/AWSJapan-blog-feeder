# AWS News Feeder プロジェクトのプロンプトテンプレート

## 1. システム要件

1. 監視対象

   - RSS URL: [監視したいブログのRSS URL]
   - 確認頻度: 毎日指定時刻（例：JST 12:00）
   - 判定期間: 直近24時間以内の記事

2. 記事処理

   - 取得: RSSフィードから記事を取得
   - 要約: Amazon Bedrock (Claude)で記事を要約
   - 投稿: Slackに要約を投稿

3. 通知要件

   - 新着記事あり: タイトル、要約、リンク、投稿日時を表示
   - 新着記事なし: 「更新なし」メッセージを表示
   - 処理単位: 期間内の全記事を個別に処理

## 2. 必要なファイル構成

```javascript
project_name/
├── README.md          # システム概要、セットアップ手順
├── requirements.txt   # Python依存パッケージ
├── lambda_function.py # メイン処理
├── test_locally.py   # ローカルテスト用
├── setup.sh          # 環境構築スクリプト
├── deploy.sh         # デプロイパッケージ作成
└── .env.example      # 環境変数テンプレート
```

## 3. 必要な環境変数

```javascript
# Slack設定
SLACK_WEBHOOK_URL=your_webhook_url

# AWS認証情報
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_DEFAULT_REGION=your_region

# RSS設定（オプション）
AWS_BLOG_RSS_URL=your_rss_url
```

## 4. AWSサービス構成

- AWS Lambda
  - ランタイム: Python 3.11
  - タイムアウト: 5分
  - 必要な権限: Amazon Bedrock

- Amazon EventBridge
  - スケジュール: cron(0 3 * * ? *)  # UTC 03:00 = JST 12:00

- Amazon Bedrock
  - モデル: Claude 3.5 Sonnet

## 5. デプロイ時の設定

- タグ設定
  Project: [プロジェクト名]
  Billing: [課金タグ]

- 環境変数
  SLACK_WEBHOOK_URL: Slack Incoming Webhook URL
  AWS_BLOG_RSS_URL: 監視対象のRSS URL（オプション）

## 6. カスタマイズのポイント

1. RSS URL: 監視したいブログのURLに変更
2. 実行時間: EventBridgeのcron式を調整
3. 判定期間: is\_within\_last\_24\_hours関数の期間を調整
4. 要約プロンプト: summarize\_content関数のプロンプトを調整
5. Slack通知: create\_article\_blocks関数のメッセージフォーマットを調整
