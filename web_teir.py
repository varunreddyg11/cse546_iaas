from flask import Flask, request, redirect
import json
import boto3
import time
import base64
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './StoreImages/'

s3_input_bucket_name= "cse546-project1-group16-input"
s3_output_bucket_name="cse546-project1-group16-output"
sqs_queue_name_input = "cse546_project1_group16_sqs_input"
sqs_queue_name_output = "cse546_project1_group16_sqs_output"
sqs_queue_url_input = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_input'
sqs_queue_url_output = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_output'


def push_image(file_path, file_name):
    sqs = boto3.client("sqs", endpoint_url=sqs_queue_url_input)
    file_binary = open(file_path, 'rb').read()
    encoded= base64.b64encode(file_binary)

    message_body = json.dumps(["process",s3_input_bucket_name, encoded.decode('utf-8'), "", file_name])
    sqs.send_message(QueueUrl=sqs_queue_url_input, MessageBody=message_body)
    return


my_dict = {}


@app.route('/upload_image', methods=['POST'])
def upload_image():
    sqs_response = boto3.client("sqs", endpoint_url=sqs_queue_url_output)
    global my_dict
    file_name = ""
    for file in request.files.getlist('myfile'):
        file_name = file.filename
        if file:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            push_image(app.config['UPLOAD_FOLDER']+filename, file.filename)
    print( "File Uploaded!" , filename)
    while file_name not in my_dict: 
        messages = sqs_response.receive_message(QueueUrl=sqs_queue_url_output,MaxNumberOfMessages=1, WaitTimeSeconds=20)
        if 'Messages' in messages:
            messages = messages['Messages']
            for each_message in messages:
                content = json.loads(each_message['Body'])
                receipt_handle = each_message['ReceiptHandle']
                print(content)
                sqs_response.delete_message(QueueUrl=sqs_queue_url_output,ReceiptHandle=receipt_handle)
                my_dict[list(content.keys())[0]] = list(content.values())[0]
        else:
            print("waiting for output")
            time.sleep(5)
    response_string = my_dict[file_name]
    my_dict.pop(file_name)
    return response_string

if __name__=="__main__":
    app.run(host='0.0.0.0',port=8080, debug=True)