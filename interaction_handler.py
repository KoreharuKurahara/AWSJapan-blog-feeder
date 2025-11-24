import json
import os
import boto3
import urllib.parse
from datetime import datetime

# Initialize DynamoDB client
dynamodb = boto3.resource('dynamodb')
TABLE_NAME = 'SaaQuestions'
table = dynamodb.Table(TABLE_NAME)

def lambda_handler(event, context):
    """
    Handle Slack interactive components (Button clicks)
    """
    try:
        # Parse the body
        # Slack sends data as application/x-www-form-urlencoded
        body = event.get('body', '')
        if event.get('isBase64Encoded', False):
            import base64
            body = base64.b64decode(body).decode('utf-8')
            
        # Parse query string parameters
        params = urllib.parse.parse_qs(body)
        
        if 'payload' not in params:
            return {
                'statusCode': 400,
                'body': 'Missing payload'
            }
            
        payload = json.loads(params['payload'][0])
        
        # Check if it's a block action
        if payload['type'] == 'block_actions':
            action = payload['actions'][0]
            action_id = action['action_id']
            value = action['value'] # This should contain the question_id and selected option
            
            # Value format: "question_id:selected_option_index"
            try:
                question_id, selected_index = value.split(':')
                selected_index = int(selected_index)
            except ValueError:
                return {'statusCode': 400, 'body': 'Invalid action value'}
            
            # Fetch question from DynamoDB
            response = table.get_item(Key={'question_id': question_id})
            if 'Item' not in response:
                return {'statusCode': 404, 'body': 'Question not found'}
                
            item = response['Item']
            correct_index = int(item['correct_option_index'])
            explanation_correct = item['explanation_correct']
            explanation_others = item['explanation_others']
            
            # Determine if correct
            is_correct = (selected_index == correct_index)
            
            # Build response message
            if is_correct:
                result_text = "✅ *正解です！*"
                explanation = explanation_correct
            else:
                result_text = "❌ *不正解です...*"
                explanation = explanation_others
                
            # Create ephemeral response
            response_blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"{result_text}\n\n{explanation}"
                    }
                }
            ]
            
            # Return JSON to Slack to update the message or send ephemeral
            # For interaction, we usually use response_url to send a message, 
            # but returning JSON with 'response_type': 'ephemeral' works for immediate feedback
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'response_type': 'ephemeral',
                    'replace_original': False,
                    'blocks': response_blocks
                })
            }
            
        return {
            'statusCode': 200,
            'body': 'OK'
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
