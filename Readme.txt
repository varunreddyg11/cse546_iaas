Group 16
Group Members: Varun Kumar Reddy Gunnreddy

# credentails for aws, loginto_webteir.pem for accessing through ssh  
AWS credentials are requried for scripts
also attaching aws/credentails


Url : http://35.174.89.85:8080/upload_image
EIP : 35.174.89.85

SQS:
sqs_queue_name_input = "cse546_project1_group16_sqs_input"
sqs_queue_name_output = "cse546_project1_group16_sqs_output"
sqs_queue_url_input = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_input'
sqs_queue_url_output = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_output'

S3: 

s3_input_bucket_name= "cse546-project1-group16-input"
s3_output_bucket_name="cse546-project1-group16-output"

 curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
