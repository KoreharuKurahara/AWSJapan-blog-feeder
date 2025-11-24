import os
import json
import feedparser
import boto3
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# 環境変数の設定
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
if not SLACK_WEBHOOK_URL:
    raise ValueError("SLACK_WEBHOOK_URL environment variable is not set")

AWS_BLOG_RSS_URL = os.getenv('AWS_BLOG_RSS_URL', 'https://aws.amazon.com/jp/blogs/news/feed/')
if not AWS_BLOG_RSS_URL:
    raise ValueError("AWS_BLOG_RSS_URL environment variable is not set")

def get_latest_posts():
    """AWSブログのRSSフィードから最新の投稿を取得"""
    print(f"Fetching RSS feed from: {AWS_BLOG_RSS_URL}")
    feed = feedparser.parse(AWS_BLOG_RSS_URL)
    print(f"RSS feed parsed successfully. Total entries: {len(feed.entries)}")
    return feed.entries

def is_within_last_24_hours(post):
    """投稿が直近24時間以内かどうかを判定"""
    now = datetime.now(timezone.utc)  # UTC
    
    # feedparserのpublished_parsedはUTC時間のtupleを返す
    # 適切にUTCタイムゾーン情報を付加して比較
    post_time = datetime(*post.published_parsed[:6], tzinfo=timezone.utc)
    
    time_difference = now - post_time
    is_recent = time_difference.total_seconds() < 24 * 60 * 60  # 24時間以内
    
    # 日本時間での表示用に変換
    jst_now = now.astimezone(timezone(timedelta(hours=9)))
    jst_post_time = post_time.astimezone(timezone(timedelta(hours=9)))
    
    print(f"Post: '{post.title[:50]}...' | Published (JST): {jst_post_time} | Recent: {is_recent}")
    return is_recent

def summarize_content(content):
    """Amazon Bedrock APIを使用して記事内容を要約"""
    bedrock = boto3.client('bedrock-runtime')
    
    # Claude 3.5 Sonnetモデルを使用
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 500,
        "messages": [
            {
                "role": "assistant",
                "content": "AWSの技術記事を簡潔に要約します。"
            },
            {
                "role": "user",
                "content": f"以下の記事を300字程度で要約してください：\n{content}"
            }
        ]
    })
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
        contentType="application/json",
        accept="application/json",
        body=body
    )
    
    response_body = json.loads(response.get('body').read())
    return response_body['content'][0]['text']

def post_to_slack(message_blocks):
    """Slackに投稿"""
    print(f"Posting to Slack webhook URL: {SLACK_WEBHOOK_URL}")

    message = {"blocks": message_blocks}
    
    response = requests.post(
        SLACK_WEBHOOK_URL,
        data=json.dumps(message),
        headers={'Content-Type': 'application/json'}
    )
    return response.status_code == 200

def create_article_blocks(title, summary, link, post_time):
    """記事の投稿用ブロックを作成"""
    formatted_time = post_time.strftime('%Y-%m-%d %H:%M')
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "🆕 AWS Blog 新着記事"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{title}*\n\n{summary}\n\n_投稿日時: {formatted_time}_"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"👉 <{link}|記事を読む>"
            }
        },
        {
            "type": "divider"
        }
    ]

def create_no_updates_blocks():
    """更新なしメッセージ用ブロックを作成"""
    current_time = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "AWS Blog 更新確認"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{current_time}* 時点で新着記事はありませんでした。"
            }
        },
        {
            "type": "divider"
        }
    ]

def lambda_handler(event, context):
    """Lambda関数のメインハンドラー"""
    try:
        # 最新の投稿を取得
        posts = get_latest_posts()
        
        # 24時間以内の投稿をフィルタリング
        recent_posts = [post for post in posts if is_within_last_24_hours(post)]
        
        if recent_posts:
            processed_articles = []
            # 全ての新着記事を処理
            for post in recent_posts:
                title = post.title
                # # content:encoded（詳細本文）があれば優先、なければdescription
                if hasattr(post, 'content') and isinstance(post.content, list) and len(post.content) > 0 and hasattr(post.content[0], 'value'):
                    content = post.content[0].value
                else:
                    content = post.description
                link = post.link
                post_time = datetime(*post.published_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                
                # 記事を要約
                summary = summarize_content(content)
                
                # Slackに投稿用ブロックを作成して投稿
                message_blocks = create_article_blocks(title, summary, link, post_time)
                success = post_to_slack(message_blocks)
                
                if success:
                    print(f"Summary (first 100 chars): {summary[:100]}")
                    processed_articles.append({
                        'title': title,
                        'post_time': post_time.strftime('%Y-%m-%d %H:%M')
                    })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Successfully processed AWS blog posts',
                    'processed_articles': processed_articles,
                    'count': len(processed_articles)
                })
            }
        else:
            # 更新なしメッセージを投稿
            message_blocks = create_no_updates_blocks()
            success = post_to_slack(message_blocks)
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No new posts in the last 24 hours',
                    'success': success
                })
            }
            
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
