import json
import requests
import os

def lambda_handler(event, context):
    TELNYX_API_KEY = os.environ.get('TELNYX_API_KEY')
    authorization_header = f"Bearer KEY{TELNYX_API_KEY}"

    try:
        body = json.loads(event.get('body', ''))
    except json.JSONDecodeError:
        print("Error decoding JSON from event body")
        return {'statusCode': 400, 'body': json.dumps({'message': 'Invalid request body'})}

    phoneNumber = body.get('phoneNumber')
    message = body.get('message')

    if not phoneNumber:
        return {'statusCode': 400, 'body': json.dumps({'message': 'phoneNumber is required'})}

    url = "https://api.telnyx.com/v2/messages"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": authorization_header
    }

    data = {
        "from": "+18447281313",
        "to": phoneNumber,
        "text": message,  
        "media_urls": []  
    }

    try:
        response = requests.post(url, headers=headers, json=data)
        response_data = response.json()

        print("Response from Telnyx API:", response_data)

        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Request sent successfully', 'response': response_data})
        }
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

        return {
            'statusCode': 500,
            'body': json.dumps({'message': 'Failed to send request'})
        }
