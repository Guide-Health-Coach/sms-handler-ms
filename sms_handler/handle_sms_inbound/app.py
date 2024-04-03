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

    CHAPTER_1_QUESTIONS = 7
    CHAPTER_2_QUESTIONS = 15

    # --- Helper Functions ---
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
        print(f"Fetching user with phone_number: {phone_number}")  # Enhanced logging
        try:
            response = userTable.get_item(Key={'phone_number': phone_number})
            item = response.get('Item')
            if not item:
                print(f"No user found with phone_number: {phone_number}")
            return item
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

    def get_meal_plan(phone_number, meal_plan_type):
        print("Requesting meal plan for:", phone_number)
        data = json.dumps({"phone_number": phone_number, "meal_plan_type": meal_plan_type})
        headers = {"Content-Type": "application/json"}
        conn = http.client.HTTPSConnection("ww57rlfsei.execute-api.us-east-2.amazonaws.com")
        try:
            conn.request("POST", "/default/mealplan-MealPlanFunction-o765SZ4skYlJ", body=data, headers=headers)
            response = conn.getresponse()
            if response.status == 200:
                responseData = response.read().decode()
                responseJson = json.loads(responseData)

                meal_plan = responseJson.get('meal_plan', 'No meal plan found')
                print("Response getting meal plan:", responseData)
                return meal_plan
            else:
                print("Failed to get meal plan:", response.status, response.reason)
        finally:
            conn.close()

    def send_message(phone_number, message):
        data = json.dumps({"phoneNumber": phone_number, "message": message})
        headers = {"Content-Type": "application/json"}
        conn = http.client.HTTPSConnection("aqwgmthqlk.execute-api.us-east-2.amazonaws.com")
        try:
            conn.request("POST", "/default/smsSender-SmsHandleOutboundFunction-c1mnlkMhXvty", body=data, headers=headers)
            response = conn.getresponse()
            if response.status == 200:
                responseData = response.read().decode()
                print("Response sending message:", responseData)
            else:
                print("Failed to send message:", response.status, response.reason)
        finally:
            conn.close()

    
    # --- main() ---
    user_agent = event['headers'].get('User-Agent')
    if user_agent == 'telnyx-webhooks':
        print("Message from Telnyx received; ignoring.")
        return {
            'statusCode': 200,
            'body': 'Ignored Telnyx message'
        }
    print("Received event:", event)  # Log the raw event
    is_base64_encoded = event.get('isBase64Encoded', False)
    body = event.get('body', '')

    if not body:
        print("Empty body received")
        return {
            'statusCode': 400,
            'body': json.dumps({'message': 'Empty body received'})
        }

    try:
        if is_base64_encoded:
            body = base64.b64decode(body).decode('utf-8')
    except Exception as e:
        print(f"Error decoding base64 content: {e}")

    try:
        parsed_body = urllib.parse.parse_qs(body)
        parsed_body = {k: v[0] for k, v in parsed_body.items()}
    except Exception as e:
        print(f"Error parsing form-urlencoded content: {e}")

    received_message = parsed_body.get('Body')
    phone_number = parsed_body.get('From')
    
    print(received_message)
    print(phone_number)
    user = get_user(phone_number)

    if user.get('onboarding_status') == 'Completed' and user.get('approved_meal_plan_generated'):
        # This means the user response is to meal plan reminder events or anything that's not onboarding related.
        print("You completed the onboarding, and you have no current reminders!  Your start day is on Monday!")
        print("You are now responding to reminder {'Breakfast'}")
    else:
        received_message_object = {
            'source': phone_number,
            'to': 'Telnyx',
            'message_content': received_message, 
        }
        append_message_to_conversation_db(phone_number, received_message_object)

        new_question_number = user.get('question_number') + 1

        if new_question_number > CHAPTER_1_QUESTIONS and not user.get('preliminary_meal_plan'):
            meal_plan = get_meal_plan(phone_number, 'preliminary')
            print(meal_plan)
            send_message(phone_number, meal_plan)
            userTable.update_item(
                Key={'phone_number': phone_number},
                UpdateExpression='SET question_number = :new_question_number',
                ExpressionAttributeValues={':new_question_number': new_question_number},
                ReturnValues='UPDATED_NEW'
            )
            userTable.update_item(
                Key={'phone_number': phone_number},
                UpdateExpression='SET preliminary_meal_plan_generated = :new_preliminary_meal_plan_generated',
                ExpressionAttributeValues={':new_preliminary_meal_plan_generated': True},
                ReturnValues='UPDATED_NEW'
            )
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'Request processed successfully'})
            }

        elif new_question_number > CHAPTER_2_QUESTIONS and not user.get('approved_meal_plan'):
            send_message(phone_number, "This is the end of the demo.  Later we will have an approved meal plan from the last set of questions and also set reminders for users, with interactivity to also tailor their plan every week.  The user is going to be able to interact throughout the week by talking about what they liked, disliked, etc.")
            # userTable.update_item(
            #     Key={'phone_number': phone_number},
            #     UpdateExpression='SET question_number = :new_question_number',
            #     ExpressionAttributeValues={':new_question_number': new_question_number},
            #     ReturnValues='UPDATED_NEW'
            # )
            # Generate New meal plan here.
            # Send another message.
            # Update the approved_meal_plan_generate to True
            # set user onboarding_process to "completed"
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