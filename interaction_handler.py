import json
import os
import boto3
import urllib.parse
import requests
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'SaaQuestions'
table = dynamodb.Table(TABLE_NAME)

# Helper class to convert DynamoDB Decimal to float/int for JSON serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super(DecimalEncoder, self).default(obj)

def lambda_handler(event, context):
    """
    Handle Slack interactive components (Button clicks)
    """
    
    try:
        # Parse the body
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            import base64
            body = base64.b64decode(body).decode('utf-8')
        
        # Parse query string parameters
        params = urllib.parse.parse_qs(body)
        
        if 'payload' not in params:
            print("Error: Missing payload")
            return {'statusCode': 200, 'body': ''}
            
        payload = json.loads(params['payload'][0])
        
        # Check if it's a block action
        if payload['type'] == 'block_actions':
            # Extract response_url
            response_url = payload.get('response_url')
            if not response_url:
                print("Error: No response_url found")
                return {'statusCode': 200, 'body': ''}

            action = payload['actions'][0]
            value = action['value']
            
            # Value format: "question_id:selected_option_index"
            try:
                question_id, selected_index = value.split(':')
                selected_index = int(selected_index)
            except ValueError:
                print(f"Error: Invalid action value: {value}")
                requests.post(response_url, json={
                    'response_type': 'ephemeral',
                    'text': 'エラーが発生しました（不正なデータ形式）'
                })
                return {'statusCode': 200, 'body': ''}
            
            # Fetch question from DynamoDB
            try:
                response = table.get_item(Key={'question_id': question_id})
            except Exception as e:
                print(f"DynamoDB Error: {e}")
                requests.post(response_url, json={
                    'response_type': 'ephemeral',
                    'text': 'データベースエラーが発生しました'
                })
                return {'statusCode': 200, 'body': ''}

            if 'Item' not in response:
                requests.post(response_url, json={
                    'response_type': 'ephemeral',
                    'text': '問題データが見つかりませんでした'
                })
                return {'statusCode': 200, 'body': ''}
                
            item = response['Item']
            correct_index = int(item['correct_option_index'])
            explanation_correct = item.get('explanation_correct', '解説がありません')
            explanation_others = item.get('explanation_others', '解説がありません')
            
            # Determine if correct
            is_correct = (selected_index == correct_index)
            
            # Build response message
            if is_correct:
                result_text = "✅ *正解です！*"
                explanation = explanation_correct
            else:
                result_text = "❌ *不正解です...*"
                explanation = explanation_others
                
            response_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{result_text}\n\n{explanation}"
                    }
                }
            ]
            
            response_body = {
                'response_type': 'ephemeral',
                'replace_original': False,
                'text': result_text,
                'blocks': response_blocks
            }
            
            # Send message back to Slack via response_url
            requests.post(
                response_url, 
                data=json.dumps(response_body, cls=DecimalEncoder),
                headers={'Content-Type': 'application/json'}
            )
            
        # Always return 200 OK immediately to acknowledge the interaction
        return {
            'statusCode': 200,
            'body': ''
        }
        
    except Exception as e:
        print(f"Unhandled Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 200,
            'body': ''
        }
