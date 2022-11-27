import boto3
import json
import paramiko
import threading
from time import sleep
from botocore.exceptions import ClientError


used_master_instances = ["i-00d6564a61cbdaa2f","i-0b8486e7cd644a41f"]
s3_input_bucket_name= "cse546-project1-group16-input"
s3_output_bucket_name="cse546-project1-group16-output"
sqs_request_queue_name = "cse546_project1_group16_sqs_input"
sqs_response_queue_name = "cse546_project1_group16_sqs_output"
sqs_request_queue_url = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_input'
sqs_response_queue_url = 'https://sqs.us-east-1.amazonaws.com/116211720936/cse546_project1_group16_sqs_output'
config = [
            {
                'DeviceName': '/dev/xvda',
                'Ebs': {

                    'DeleteOnTermination': True,
                    'VolumeSize': 8,
                    'VolumeType': 'gp2'
                },
            },
        ]

instance_state_maps = {"running" : ["running", "pending","inservice"],"stopped":["stopped"]}

list_of_instance_ids = list()
count_of_intsances = 0
list_of_threads = list()
list_of_processing_instances = list()
ec2_client = boto3.resource("ec2")
sqs_request_client = boto3.client("sqs",endpoint_url=sqs_request_queue_url)
max_instances = 19

def start_new_instances(no_of_instances,count_of_running_instances_fortagging):
    ec2_client_start = boto3.client('ec2')
    for i in range(no_of_instances):
        start_instance = ec2_client_start.run_instances(
                BlockDeviceMappings=config,
                ImageId='ami-0aae5a8e3e77bb3c0',
                InstanceType='t2.micro',
                KeyName='loginto_webteir',
                MinCount=1,
                MaxCount=1,
                Monitoring={
                    'Enabled': False
                },
                SecurityGroupIds=[
                    "sg-00e963fb19d393189"
                ],
            )
        instance = start_instance["Instances"][0]
        try:
            ec2_client_start.create_tags(Resources=[instance["InstanceId"]], Tags=[{'Key':'Name', 'Value':'app_tier '+str(i + count_of_running_instances_fortagging)}])
        except ClientError as e:
            print(e)
        print(start_instance)

def get_list_of_instance(instancestate):
    list_of_instance_ids = list()
    instances = ec2_client.instances.filter(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': instance_state_maps[instancestate]
                }
            ]
        )
    for instance in instances:
        if instance.id not in used_master_instances:
            list_of_instance_ids.append(instance.id)
    return list_of_instance_ids

def trigger_app_tier_script(ec2_client, instance_id):
    ssh_key = paramiko.RSAKey.from_private_key_file('/home/ec2-user/app_teir_master/loginto_webteir.pem')
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    instance = [i for i in ec2_client.instances.filter(InstanceIds=[instance_id])][0]
    while True:
        try:
            client.connect(hostname=instance.public_ip_address, username="ubuntu", pkey=ssh_key, timeout=45)
            client.exec_command('python3 /home/ubuntu/app_tier_service.py')
            sleep(5)
            client.close()
            break
        except Exception as e:
            print("Reattempting to connect "+str(e))
            sleep(10)



def execute_instance_thread():
    global list_of_threads
    for instance_id in get_list_of_instance("running"):
        if instance_id not in list_of_processing_instances:
            thread = threading.Thread(name=instance_id, target=trigger_app_tier_script, args=(ec2_client, instance_id))
            list_of_threads.append(thread)
            list_of_processing_instances.append(instance_id)
            thread.start()
            sleep(5)
    new_thread_list = []
    for each_thread in list_of_threads:
        if not each_thread.is_alive():
            list_of_processing_instances.remove(each_thread.getName())
        else:
            new_thread_list.append(each_thread)
    list_of_threads = new_thread_list


if __name__=="__main__":

    while True:
        
        list_of_running_instances = get_list_of_instance("running")
        list_of_stopped_instances = get_list_of_instance("stopped")
        no_of_running_instances = len(list_of_running_instances)
        no_of_stopped_instances = len(list_of_stopped_instances)
        queue = sqs_request_client.get_queue_attributes(QueueUrl=sqs_request_queue_url, AttributeNames=['ApproximateNumberOfMessages',])
        messages_in_queue = int(queue['Attributes']['ApproximateNumberOfMessages'])

        stopped_instances = list_of_stopped_instances

        if messages_in_queue > no_of_stopped_instances:
            no_of_new_instances_to_start = min(max_instances - (no_of_running_instances + no_of_stopped_instances), messages_in_queue - no_of_stopped_instances)
            if no_of_new_instances_to_start > 0:
                try:
                    start_new_instances(no_of_new_instances_to_start, no_of_running_instances + no_of_stopped_instances)
                except ClientError as e:
                    print(e)
            if len(stopped_instances) > 0:
                try:
                    ec2_client.instances.filter(InstanceIds=stopped_instances).start()
                except ClientError as e:
                    print(e)
            sleep(45)

        else:
            no_of_instances_to_start = min(no_of_stopped_instances, messages_in_queue - (no_of_running_instances - len(list_of_processing_instances)))
            if no_of_instances_to_start > 0:
                try:
                    ec2_client.instances.filter(InstanceIds=stopped_instances[:no_of_instances_to_start]).start()
                except ClientError as e:
                    print(e)   
                sleep(40)

        execute_instance_thread()

        idle_instances = list()
        for id in get_list_of_instance("running"):
            if id not in list_of_processing_instances:
                idle_instances.append(id)

        if len(idle_instances) > 0:
            print("Stopping Idle Instances: ", idle_instances)
            ec2_client.instances.filter(InstanceIds=idle_instances).stop()
            sleep(40)
            

        sleep(20)
