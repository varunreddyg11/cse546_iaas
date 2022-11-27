from calendar import c
import boto3
import json
import os
import base64
import io

s3_input_bucket_name= "cse546-project1-group16-input"
s3_output_bucket_name="cse546-project1-group16-output"
sqs_request_queue_name = "cse546_project1_group16_sqs_input"
sqs_response_queue_name = "cse546_project1_group16_sqs_output"
sqs_request_queue_url = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_input'
sqs_response_queue_url = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_output'
local_image_folder = "/home/ubuntu/StoreImages"

sqs_request_queue = boto3.resource("sqs" ,endpoint_url='https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_input')
sqs_response_client= boto3.client("sqs", endpoint_url='https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_output')
sqs_request_client = boto3.client("sqs", endpoint_url='https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_input')

def get_image_sqs_input():

    request_queue = sqs_request_queue.get_queue_by_name(QueueName=sqs_request_queue_name)
    messages = request_queue.receive_messages(MaxNumberOfMessages=1, WaitTimeSeconds=20)
    content = ['no_message']
    if messages:
        for msg in messages:
            content = json.loads(msg.body)
            msg.delete()
    else:
        print("No messages in Queue")
    return content

def process_image_classify(file_name):
    s3 = boto3.client("s3")
    downloaded_image = local_image_folder + "/" + file_name
    image_result_file = local_image_folder + "/" + file_name.split(".")[0] + ".txt"

    os.system("python3 /home/ubuntu/classifier/image_classification.py " + downloaded_image + " > " + image_result_file)
    file_path = image_result_file
    result_content = open(file_path, "r").readline()
    result_content_update  = open(file_path, "w")
    result_content_update.write(file_name + ":" + result_content)
    result_content_update.close()
    message = {file_name : result_content}
    s3.put_object(Body=result_content, Bucket=s3_output_bucket_name, Key=file_name.replace(".JPEG",".txt"))
    response = sqs_response_client.send_message(QueueUrl=sqs_response_queue_url, MessageBody=json.dumps(message))
    return

def process_image_from_sqs(content):
    with open(local_image_folder+"/" + content[4], "wb") as file_to_save:
        msg1 = content[2].encode('utf-8')
        decode_image = base64.decodebytes(msg1)
        file_to_save.write(decode_image)
    file = io.open(local_image_folder+"/" + content[4], "rb", buffering = 0)
    try:
        file_name = content[4]
        s3 = boto3.client("s3")
        s3.upload_fileobj(io.BytesIO(file.read()), s3_input_bucket_name, str(file_name))
        process_image_classify(content[4])
    except Exception as e:
        print(e)
        response = sqs_request_client.send_message(QueueUrl=sqs_request_queue_url, MessageBody=json.dumps(content))
        print(response)

if __name__=="__main__":
    while True:
        content = get_image_sqs_input()
        if content[0] == "process":
            process_image_from_sqs(content)
        else:
            break