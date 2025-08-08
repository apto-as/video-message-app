"""
Lambda function for auto-starting and stopping EC2 instances
コスト削減のための自動起動・停止Lambda関数
"""

import boto3
import os
from datetime import datetime

ec2 = boto3.client('ec2', region_name=os.environ.get('AWS_REGION', 'ap-northeast-1'))

def lambda_handler(event, context):
    """
    EC2インスタンスの自動起動・停止
    
    EventBridge (CloudWatch Events) から呼び出される
    event['action'] = 'start' または 'stop'
    """
    
    # 環境変数またはタグでインスタンスを特定
    instance_id = os.environ.get('INSTANCE_ID')
    
    if not instance_id:
        # タグでインスタンスを検索
        response = ec2.describe_instances(
            Filters=[
                {'Name': 'tag:AutoStop', 'Values': ['true']},
                {'Name': 'tag:Environment', 'Values': ['dev']},
                {'Name': 'instance-state-name', 'Values': ['running', 'stopped']}
            ]
        )
        
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append(instance['InstanceId'])
    else:
        instances = [instance_id]
    
    if not instances:
        return {
            'statusCode': 200,
            'body': 'No instances found to process'
        }
    
    # アクション実行
    action = event.get('action', 'stop')
    
    try:
        if action == 'stop':
            response = ec2.stop_instances(InstanceIds=instances)
            message = f"Stopped instances: {instances}"
            print(f"[{datetime.now()}] Stopping instances: {instances}")
            
        elif action == 'start':
            response = ec2.start_instances(InstanceIds=instances)
            message = f"Started instances: {instances}"
            print(f"[{datetime.now()}] Starting instances: {instances}")
            
        else:
            message = f"Unknown action: {action}"
            print(f"[{datetime.now()}] Error: {message}")
            return {
                'statusCode': 400,
                'body': message
            }
        
        # CloudWatch Logsに記録
        print(f"Response: {response}")
        
        return {
            'statusCode': 200,
            'body': message
        }
        
    except Exception as e:
        error_message = f"Error processing instances: {str(e)}"
        print(f"[{datetime.now()}] Error: {error_message}")
        
        return {
            'statusCode': 500,
            'body': error_message
        }