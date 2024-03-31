import json
import urllib.parse
import base64
import http.client
import urllib

def lambda_handler(event, context):
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
    receivedMessage = parsed_body.get('Body')
    phoneNumber = parsed_body.get('From')



    print("Parsed body:", parsed_body)
    customMessage = "heyyyy lol"

    data = json.dumps({"phoneNumber": phoneNumber, "message": customMessage})
    headers = {"Content-Type": "application/json"}
    conn = http.client.HTTPSConnection("et8hcrv3lh.execute-api.us-east-2.amazonaws.com")
    conn.request("POST", "/default/smsSender-SmsHandleOutboundFunction-c1mnlkMhXvty", body=data, headers=headers)
    
    response = conn.getresponse()
    responseData = response.read().decode()
    
    print("Response from SMS API:", responseData)

    conn.close()


    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'Request processed successfully'})
    }