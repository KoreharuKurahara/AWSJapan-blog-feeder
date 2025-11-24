import json
from lambda_function import lambda_handler

def main():
    """ローカル環境でLambda関数をテスト実行"""
    print("AWS News Feederのローカルテストを開始します...")
    
    # テスト用のイベントデータ
    test_event = {}
    test_context = None
    
    try:
        # Lambda関数を実行
        result = lambda_handler(test_event, test_context)
        
        # 結果を表示
        status_code = result.get('statusCode')
        body = json.loads(result.get('body', '{}'))
        
        print("\n実行結果:")
        print(f"ステータスコード: {status_code}")
        print(f"処理結果: {json.dumps(body, ensure_ascii=False, indent=2)}")
        
        if status_code == 200:
            print("\n✅ テスト成功!")
        else:
            print("\n❌ テスト失敗")
            
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        raise

if __name__ == "__main__":
    main()
