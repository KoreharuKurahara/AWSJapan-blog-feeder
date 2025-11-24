import json
import os
import sys
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

# Import handlers
from lambda_function import lambda_handler as feed_handler
from interaction_handler import lambda_handler as interaction_handler

def test_feed_real():
    """実際のRSSフィードを使用してテスト"""
    print("\n=== RSSフィード処理テスト (Real) ===")
    result = feed_handler({}, None)
    print_result(result)

def test_feed_mock():
    """ダミー記事を使用して生成ロジックを強制テスト"""
    print("\n=== RSSフィード処理テスト (Mock Article) ===")
    
    # ダミーの記事データ
    mock_entry = MagicMock()
    mock_entry.title = "Amazon EC2の新しいインスタンスタイプが発表されました"
    mock_entry.link = "https://aws.amazon.com/jp/blogs/news/dummy-ec2-article"
    mock_entry.published_parsed = datetime.now(timezone.utc).timetuple()
    mock_entry.content = [{"value": "Amazon EC2に新しいインスタンスタイプが追加されました。これにより、ハイパフォーマンスコンピューティング(HPC)ワークロードのパフォーマンスが向上します。コスト最適化とスケーラビリティの観点からも..."}]
    
    # get_latest_postsをモック化
    with patch('lambda_function.get_latest_posts', return_value=[mock_entry]):
        # is_within_last_24_hoursはTrueになるはず
        result = feed_handler({}, None)
        print_result(result)

def test_interaction():
    """Slackボタンクリックのシミュレーション"""
    print("\n=== Slackインタラクションテスト ===")
    
    # ユーザーに入力を求める
    question_id = input("テストするQuestion IDを入力してください (DynamoDBから取得): ")
    if not question_id:
        print("スキップします")
        return

    selected_option = input("選択する選択肢番号 (1-4): ")
    
    # Slackからのペイロードを模倣
    payload = {
        "type": "block_actions",
        "actions": [
            {
                "action_id": f"option_{selected_option}",
                "value": f"{question_id}:{selected_option}"
            }
        ]
    }
    
    body = f"payload={json.dumps(payload)}"
    
    event = {
        "body": body,
        "isBase64Encoded": False
    }
    
    result = interaction_handler(event, None)
    print_result(result)

def print_result(result):
    print("\n--- 実行結果 ---")
    print(f"Status Code: {result.get('statusCode')}")
    body = result.get('body')
    try:
        parsed_body = json.loads(body)
        print(json.dumps(parsed_body, ensure_ascii=False, indent=2))
    except:
        print(body)

def main():
    while True:
        print("\n=================================")
        print("AWS News Feeder ローカルテスト")
        print("=================================")
        print("1. RSSフィード処理 (Real - 実際のRSSを取得)")
        print("2. RSSフィード処理 (Mock - ダミー記事で強制実行)")
        print("3. Slackインタラクション (ボタンクリック)")
        print("q. 終了")
        
        choice = input("\n実行するテストを選択してください: ")
        
        if choice == '1':
            test_feed_real()
        elif choice == '2':
            test_feed_mock()
        elif choice == '3':
            test_interaction()
        elif choice.lower() == 'q':
            break
        else:
            print("無効な選択です")

if __name__ == "__main__":
    main()
