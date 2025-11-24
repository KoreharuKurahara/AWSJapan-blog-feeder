import os
import json
import feedparser
import boto3
import requests
import uuid
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

# DynamoDB Configuration
TABLE_NAME = 'SaaQuestions'
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(TABLE_NAME)

def get_latest_posts():
    """AWSブログのRSSフィードから最新の投稿を取得"""
    print(f"Fetching RSS feed from: {AWS_BLOG_RSS_URL}")
    feed = feedparser.parse(AWS_BLOG_RSS_URL)
    print(f"RSS feed parsed successfully. Total entries: {len(feed.entries)}")
    return feed.entries

def is_within_last_24_hours(post):
    """投稿が直近24時間以内かどうかを判定"""
    now = datetime.now(timezone.utc)
    post_time = datetime(*post.published_parsed[:6], tzinfo=timezone.utc)
    time_difference = now - post_time
    is_recent = time_difference.total_seconds() < 24 * 60 * 60
    
    jst_now = now.astimezone(timezone(timedelta(hours=9)))
    jst_post_time = post_time.astimezone(timezone(timedelta(hours=9)))
    
    print(f"Post: '{post.title[:50]}...' | Published (JST): {jst_post_time} | Recent: {is_recent}")
    return is_recent

def invoke_bedrock(messages, max_tokens=1000):
    """Bedrock APIを呼び出すヘルパー関数"""
    bedrock = boto3.client('bedrock-runtime')
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages
    })
    
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-5-sonnet-20240620-v1:0",
        contentType="application/json",
        accept="application/json",
        body=body
    )
    
    response_body = json.loads(response.get('body').read())
    return response_body['content'][0]['text']

def summarize_content(content):
    """記事内容を要約"""
    messages = [
        {"role": "assistant", "content": "AWSの技術記事を簡潔に要約します。"},
        {"role": "user", "content": f"以下の記事を300字程度で要約してください：\n{content}"}
    ]
    return invoke_bedrock(messages, max_tokens=500)

def check_saa_relevance(content):
    """記事がSAA試験に関連するか判定"""
    prompt = f"""
    あなたはAWS認定試験の専門家です。
    以下のAWSブログ記事の内容が、AWS Certified Solutions Architect - Associate (SAA-C03) の試験範囲に関連するか判定してください。
    
    記事内容:
    {content[:2000]}... (省略)

    回答は必ず "YES" か "NO" のみの単語で答えてください。余計な説明は不要です。
    """
    messages = [{"role": "user", "content": prompt}]
    response = invoke_bedrock(messages, max_tokens=10)
    return "YES" in response.upper()

def generate_question(content):
    """記事に基づいたSAA模擬問題を作成"""
    prompt = f"""
    あなたは優秀なAWS資格取得クラスの講師です。
    私はAWS Certified Solutions Architect - Associate (SAA-C03)の取得を目指しており、勉強開始5時間程度です。
    以下のブログ記事の内容に基づいて、本番ワークロードを構築・改善するような模擬問題を作成してください。

    記事内容:
    {content[:3000]}...

    要件:
    1. 日本語で出力すること。
    2. 4択問題（選択肢1〜4）であること。
    3. 以下のJSONフォーマットで出力すること（Markdownコードブロックは不要）。
    
    {{
        "question_text": "問題文...",
        "options": ["選択肢1の内容", "選択肢2の内容", "選択肢3の内容", "選択肢4の内容"],
        "correct_option_index": 1, 
        "explanation_correct": "正解の解説（1〜2行）",
        "explanation_others": "他の選択肢が間違いである理由（1〜2行）",
        "category": "第5分野：AWSブログ新着記事から出題"
    }}
    
    注意: correct_option_indexは1始まりの整数（1, 2, 3, 4）です。
    """
    messages = [{"role": "user", "content": prompt}]
    response_text = invoke_bedrock(messages, max_tokens=2000)
    
    # JSON部分を抽出（万が一Markdownが含まれていた場合用）
    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        json_str = response_text[start:end]
        return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None

def save_question(question_data, article_url):
    """問題をDynamoDBに保存"""
    question_id = str(uuid.uuid4())
    item = {
        'question_id': question_id,
        'article_url': article_url,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'question_text': question_data['question_text'],
        'options': question_data['options'],
        'correct_option_index': question_data['correct_option_index'],
        'explanation_correct': question_data['explanation_correct'],
        'explanation_others': question_data['explanation_others']
    }
    table.put_item(Item=item)
    return question_id

def create_question_blocks(question_data, question_id):
    """問題のSlack Blockを作成"""
    options_text = ""
    for i, opt in enumerate(question_data['options']):
        options_text += f"*{i+1}.* {opt}\n"

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "📝 SAA模擬問題チャレンジ"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{question_data['question_text']}*\n\n{options_text}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "1"},
                    "value": f"{question_id}:1",
                    "action_id": "option_1"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "2"},
                    "value": f"{question_id}:2",
                    "action_id": "option_2"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "3"},
                    "value": f"{question_id}:3",
                    "action_id": "option_3"
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "4"},
                    "value": f"{question_id}:4",
                    "action_id": "option_4"
                }
            ]
        }
    ]
    return blocks

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
        posts = get_latest_posts()
        recent_posts = [post for post in posts if is_within_last_24_hours(post)]
        
        if recent_posts:
            processed_articles = []
            for post in recent_posts:
                title = post.title
                if hasattr(post, 'content') and isinstance(post.content, list) and len(post.content) > 0 and hasattr(post.content[0], 'value'):
                    content = post.content[0].value
                else:
                    content = post.description
                link = post.link
                post_time = datetime(*post.published_parsed[:6], tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
                
                # 1. 要約
                summary = summarize_content(content)
                
                # 2. Slack投稿（記事）
                article_blocks = create_article_blocks(title, summary, link, post_time)
                post_to_slack(article_blocks)
                
                # 3. SAA関連チェック & 問題生成
                if check_saa_relevance(content):
                    print(f"Article '{title}' is relevant to SAA. Generating question...")
                    question_data = generate_question(content)
                    
                    if question_data:
                        # DynamoDBに保存
                        question_id = save_question(question_data, link)
                        
                        # Slack投稿（問題）
                        question_blocks = create_question_blocks(question_data, question_id)
                        post_to_slack(question_blocks)
                
                processed_articles.append({'title': title})
            
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Success', 'count': len(processed_articles)})
            }
        else:
            post_to_slack(create_no_updates_blocks())
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No new posts'})
            }
            
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
