import json
import urllib.parse
import base64
import http.client
import urllib
import boto3

def lambda_handler(event, context):
    dynamodb = boto3.resource('dynamodb')
    userTable = dynamodb.Table('User')
    conversationTable = dynamodb.Table('Conversation')
    questionTable = dynamodb.Table('Question')

    MAX_QUESTION_NUMBER = 3

    # Helper Functions
    def append_message_to_conversation_db(phone_number, new_message_object):
        response = conversationTable.update_item(
            Key={'conversation_id': phone_number},
            UpdateExpression='SET #message = list_append(#message, :new_message)',
            ExpressionAttributeNames={'#message': 'message'},
            ExpressionAttributeValues={':new_message': [new_message_object]},
            ReturnValues='UPDATED_NEW'
        )
        return response

    def get_user(phone_number):
        try:
            response = userTable.get_item(Key={'phone_number': phone_number})
            return response.get('Item')
        except Exception as e:
            print(f"Error fetching user from User table: {e}")
            return None

    def get_question(question_number):
        try:
            response = questionTable.get_item(Key={'question_number': question_number})
            return response.get('Item')
        except Exception as e:
            print(f"Error fetching user from User table: {e}")
            return None

    def send_message(phone_number, message):
        data = json.dumps({"phoneNumber": phone_number, "message": message})
        headers = {"Content-Type": "application/json"}
        conn = http.client.HTTPSConnection("et8hcrv3lh.execute-api.us-east-2.amazonaws.com")
        conn.request("POST", "/default/smsSender-SmsHandleOutboundFunction-c1mnlkMhXvty", body=data, headers=headers)
        
        response = conn.getresponse()
        responseData = response.read().decode()
        print("Response:", responseData)

        conn.close()
    
    # main()
    if event.get('isBase64Encoded', False):
        body = base64.b64decode(event['body']).decode('utf-8')
    else:
        body = event.get('body', '')
        
    if not body:
        print("Empty body received")
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Empty body received'})
        }

    parsed_body = urllib.parse.parse_qs(body)
    
    parsed_body = {k: v[0] for k, v in parsed_body.items()}
    received_message = parsed_body.get('Body')
    phone_number = parsed_body.get('From')

    user = get_user(phone_number)
    if user.get('onboarding_process') == 'Completed' and user.get('meal_plan_generated'):
        # This means the user response is to meal plan reminder events.
        print("Do something")
    elif user.get('onboarding_process') == 'Completed' and not user.get('meal_plan_generated'):
        # This means user response is in invalid while waiting for a meal plan to be created, send a fallback message here.
        print("Do something")
    else:
        received_message_object = {
            'source': phone_number,
            'to': 'Telnyx',
            'message_content': received_message, 
        }
        append_message_to_conversation_db(phone_number, received_message_object)

        new_question_number = user.get('question_number') + 1

        if new_question_number > MAX_QUESTION_NUMBER:
            send_message(phone_number, "You have completed the onboarding process.")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Request processed successfully'})
            }
        else:
            question_item = get_question(new_question_number)
            question_content = question_item.get('question_content')

            send_message(phone_number, question_content)

            received_message_object = {
                'source': 'Telnyx',
                'to': phone_number,
                'message_content': question_content, 
            }
            append_message_to_conversation_db(phone_number, received_message_object)

            userTable.update_item(
                Key={'phone_number': phone_number},
                UpdateExpression='SET question_number = :new_question_number',
                ExpressionAttributeValues={':new_question_number': new_question_number},
                ReturnValues='UPDATED_NEW'
            )

            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Request processed successfully'})
            }