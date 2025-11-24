import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def create_table():
    dynamodb = boto3.client('dynamodb')
    table_name = 'SaaQuestions'
    
    try:
        print(f"Creating table {table_name}...")
        response = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'question_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'question_id',
                    'AttributeType': 'S'
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"Table {table_name} creation initiated. Status: {response['TableDescription']['TableStatus']}")
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print(f"Table {table_name} already exists.")
        else:
            print(f"Error creating table: {e}")

if __name__ == "__main__":
    create_table()
