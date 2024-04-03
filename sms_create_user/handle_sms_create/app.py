import json
import boto3
from datetime import datetime
import http.client

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')

    userTable = dynamodb.Table('User')
    questionTable = dynamodb.Table('Question')
    conversationTable = dynamodb.Table('Conversation')

    try:
        body = json.loads(event.get('body', '{}'))
    except json.JSONDecodeError:
        print("Error decoding JSON from event body")
        return {'statusCode': 400, 'body': json.dumps({'message': 'Invalid request body'})}

    phone_number = '+1' + body.get('phoneNumber')

    try:
        user_response = userTable.get_item(Key={'phone_number': phone_number})
        if 'Item' in user_response:
            print(f"User with phone number {phone_number} already exists.")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'User already exists'})
            }
    except Exception as e:
        print(f"Error accessing User table: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Error accessing User table'})}

    try:
        response = questionTable.get_item(Key={'question_number': 0})
        question = response.get('Item')
        if not question:
            raise ValueError("Question not found")
    except Exception as e:
        print(f"Error fetching question from DB: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Error fetching question'})}

    question_content = question.get('question_content', 'Sorry, an error has occurred.')

    try:
        user = {
            'phone_number': phone_number,
            'first_name': body.get('firstName'),
            'opted_in': body.get('terms'),
            'timezone': body.get('userTimezone'),
            'created_at': datetime.now().isoformat(),
            'question_number': 0,
            'days_on_plan': 0,
            'onboarding_status': 'In Progress',
            'preliminary_meal_plan_generated': False,
            'approved_meal_plan_generated': False,
        }
        response = userTable.put_item(Item=user)
    except Exception as e:
        print(f"Error adding user to DB: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Error adding user'})}

    try:
        conversation = {
            'conversation_id': phone_number,
            'message': [{
                'source': 'telnyx',
                'to': phone_number,
                'message_content': question_content, 
            }]
        }
        response = conversationTable.put_item(Item=conversation)
    except Exception as e:
        print(f"Error adding conversation to DB: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Error adding conversation'})}

    try:
        data = json.dumps({"phoneNumber": phone_number, "message": question_content})
        headers = {"Content-Type": "application/json"}
        conn = http.client.HTTPSConnection("aqwgmthqlk.execute-api.us-east-2.amazonaws.com")
        conn.request("POST", "/default/smsSender-SmsHandleOutboundFunction-c1mnlkMhXvty", body=data, headers=headers)
        
        response = conn.getresponse()
        responseData = response.read().decode()
        print("Response sending message:", responseData)

        conn.close()

        if response.status != 200:
            raise ValueError("SMS sending failed")
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return {'statusCode': 500, 'body': json.dumps({'message': 'Error sending SMS'})}

    return {
        "statusCode": 200,
        "body": json.dumps({'message': 'Operation successful'}),
    }