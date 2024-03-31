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

    print(body)

    phone_number = '+1' + body.get('phoneNumber')

    response = questionTable.get_item(
        Key={
            'question_number': 0
        }
    )
    question = response.get('Item', None)
    question_content = question.get('question_content', 'Sorry, an error has occured.')

    data = json.dumps({"phoneNumber": phone_number, "message": question_content})
    headers = {"Content-Type": "application/json"}
    conn = http.client.HTTPSConnection("et8hcrv3lh.execute-api.us-east-2.amazonaws.com")
    conn.request("POST", "/default/smsSender-SmsHandleOutboundFunction-c1mnlkMhXvty", body=data, headers=headers)
    
    response = conn.getresponse()
    responseData = response.read().decode()
    responseData = json.loads(responseData) 

    print("Response from SMS API:", responseData)

    conn.close()

    user = {
        'phone_number': '+1' + body.get('phoneNumber'),
        'first_name': body.get('firstName'),
        'opted_in': body.get('terms'),
        'timezone': body.get('userTimezone'),
        'created_at': datetime.now().isoformat(),
        'question_number': 0
    }

    conversation = {
        # TODO Later when more coaches/admins/other come onboard, make it phone_number + '_' + coach_id.
        'conversation_id': phone_number,
        'message': {
            'from': 'telnyx',
            'to': phone_number,
            'message': question_content,
            'timestamp': responseData.get('data', {}).get('received_at', datetime.now().isoformat())
        }
    }

    response = userTable.put_item(Item=user)
    response = conversationTable.put_item(Item=conversation)

    return {
        "statusCode": 200,
        "body": json.dumps({
        }),
    }
