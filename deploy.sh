#!/bin/bash

# 作業ディレクトリの作成
echo "パッケージングディレクトリの準備..."
rm -rf package/
mkdir -p package/

# 依存関係のインストール
echo "依存関係のインストール..."
pip install -r requirements.txt -t package/

# Lambda関数のコピー
echo "Lambda関数のコピー..."
cp lambda_function.py package/

# パッケージの作成
echo "デプロイパッケージの作成..."
cd package
zip -r ../deployment-package.zip .
cd ..

echo "デプロイパッケージが作成されました: deployment-package.zip"
echo ""
echo "デプロイ手順:"
echo "1. AWSマネジメントコンソールにログイン"
echo "2. Lambda関数を作成または選択"
echo "3. 作成されたdeployment-package.zipをアップロード"
echo "4. 環境変数を設定"
echo "   - SLACK_WEBHOOK_URL: Slack Incoming Webhookのエンドポイント"
echo "5. 実行ロールにBedrockの権限を追加"
echo "6. EventBridgeでスケジュール実行を設定（例：1時間ごと）"
