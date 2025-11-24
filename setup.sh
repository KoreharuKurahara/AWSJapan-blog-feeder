#!/bin/bash

# 仮想環境の作成
echo "Python仮想環境を作成中..."
python3 -m venv .venv

# 仮想環境の有効化
echo "仮想環境を有効化..."
source .venv/bin/activate

# 依存関係のインストール
echo "依存関係をインストール中..."
pip install -r requirements.txt

# .envファイルの作成
if [ ! -f .env ]; then
    echo "環境変数ファイルをセットアップ中..."
    cp .env.example .env
    echo ".envファイルが作成されました。必要な環境変数を設定してください。"
fi

echo ""
echo "セットアップ完了！"
echo "仮想環境を有効化するには以下のコマンドを実行してください："
echo "source .venv/bin/activate"
