import boto3
import os
import json

def generate_arn(template, event, resource_id):
    """ Helper function to generate ARN string. """
    account = event['account']
    region = event['region']
    return template.replace('@region@', region).replace('@account@', account).replace('@resourceId@', resource_id)

def aws_ec2(event):
    arnList = []
    ec2ArnTemplate = 'arn:aws:ec2:@region@:@account@:instance/@instanceId@'
    volumeArnTemplate = 'arn:aws:ec2:@region@:@account@:volume/@volumeId@'
    
    if event['detail']['eventName'] == 'RunInstances':
        print("Tagging for new EC2...")
        for item in event['detail']['responseElements']['instancesSet']['items']:
            instance_id = item['instanceId']
            arnList.append(generate_arn(ec2ArnTemplate, event, instance_id))
            
            ec2_resource = boto3.resource('ec2')
            instance = ec2_resource.Instance(instance_id)
            for volume in instance.volumes.all():
                arnList.append(generate_arn(volumeArnTemplate, event, volume.id))
    
    elif event['detail']['eventName'] == 'CreateVolume':
        print("Tagging for new EBS volume...")
        volume_id = event['detail']['responseElements']['volumeId']
        arnList.append(generate_arn(volumeArnTemplate, event, volume_id))
    
    return arnList

def aws_vpc(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateVpc':
        print("Tagging for new VPC...")
        vpc_id = event['detail']['responseElements']['vpc']['vpcId']
        arnList.append(generate_arn('arn:aws:ec2:@region@:@account@:vpc/@resourceId@', event, vpc_id))
    return arnList

def aws_subnet(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateSubnet':
        print("Tagging for new Subnet...")
        subnet_id = event['detail']['responseElements']['subnet']['subnetId']
        arnList.append(generate_arn('arn:aws:ec2:@region@:@account@:subnet/@resourceId@', event, subnet_id))
    return arnList

def aws_nat_gateway(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateNatGateway':
        print("Tagging for new NAT Gateway...")
        nat_gateway_id = event['detail']['responseElements']['natGateway']['natGatewayId']
        arnList.append(generate_arn('arn:aws:ec2:@region@:@account@:natGateway/@resourceId@', event, nat_gateway_id))
    return arnList

def aws_elasticip(event):
    arnList = []
    if event['detail']['eventName'] == 'AllocateAddress':
        print("Tagging for new Elastic IP...")
        allocation_id = event['detail']['responseElements']['allocationId']
        arnList.append(generate_arn('arn:aws:ec2:@region@:@account@:elastic-ip/@resourceId@', event, allocation_id))
    return arnList

def aws_elasticloadbalancing(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateLoadBalancer':
        print("Tagging for new LoadBalancer...")
        for lb in event['detail']['responseElements']['loadBalancers']:
            arnList.append(lb['loadBalancerArn'])
    return arnList

def aws_rds(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateDBInstance':
        print("Tagging for new RDS instance...")
        arnList.append(event['detail']['responseElements']['dBInstanceArn'])
    return arnList

def aws_s3(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateBucket':
        print("Tagging for new S3 bucket...")
        bucket_name = event['detail']['requestParameters']['bucketName']
        arnList.append(f'arn:aws:s3:::{bucket_name}')
    return arnList

def aws_lambda(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateFunction20150331':
        print("Tagging for new Lambda function...")
        function_arn = event['detail']['responseElements']['functionArn']
        arnList.append(function_arn)
    return arnList

def aws_dynamodb(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateTable':
        print("Tagging for new DynamoDB table...")
        table_arn = event['detail']['responseElements']['tableDescription']['tableArn']
        arnList.append(table_arn)
    return arnList

def aws_kms(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateKey':
        print("Tagging for new KMS key...")
        arnList.append(event['detail']['responseElements']['keyMetadata']['arn'])
    return arnList

def aws_sns(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateTopic':
        print("Tagging for new SNS topic...")
        topic_name = event['detail']['requestParameters']['name']
        arnList.append(generate_arn('arn:aws:sns:@region@:@account@:@topicName@', event, topic_name))
    return arnList

def aws_sqs(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateQueue':
        print("Tagging for new SQS queue...")
        queue_name = event['detail']['requestParameters']['queueName']
        arnList.append(generate_arn('arn:aws:sqs:@region@:@account@:@queueName@', event, queue_name))
    return arnList

def aws_elasticfilesystem(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateMountTarget':
        print("Tagging for new EFS mount target...")
        file_system_id = event['detail']['responseElements']['fileSystemId']
        arnList.append(generate_arn('arn:aws:elasticfilesystem:@region@:@account@:file-system/@fileSystemId@', event, file_system_id))
    return arnList

def aws_route53(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateHostedZone':
        print("Tagging for new Route 53 hosted zone...")
        hosted_zone_id = event['detail']['responseElements']['hostedZone']['Id'].split('/')[-1]
        arnList.append(generate_arn('arn:aws:route53:@region@:@account@:@hostedZoneId@', event, hosted_zone_id))
    return arnList

def aws_msk(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateCluster':
        print("Tagging for new MSK cluster...")
        cluster_name = event['detail']['responseElements']['clusterArn'].split(':')[-1]
        arnList.append(generate_arn('arn:aws:kafka:@region@:@account@:@clusterName@', event, cluster_name))
    return arnList

def get_identity(event):
    print("Getting user identity...")
    user_id = event['detail']['userIdentity']['arn'].split('/')[-1]
    
    if event['detail']['userIdentity']['type'] == 'AssumedRole':
        role_id = event['detail']['userIdentity']['arn'].split('/')[-2]
        return user_id, role_id
    return user_id, None

def main(event, context):
    print(f"Input event: {event}")
    print("Event source:", event['source'])
    method = event['source'].replace('.', "_")

    res_arns = globals()[method](event)
    print("Resource ARNs:", res_arns)

    tags = json.loads(os.environ['tags'])
    identity_recording = os.environ['identityRecording']

    if identity_recording == 'true':
        user_id, role_id = get_identity(event)
        if role_id:
            tags['roleId'] = role_id
        tags['userId'] = user_id

    print("Tags to apply:", tags)

    client = boto3.client('resourcegroupstaggingapi')
    for arn in res_arns:
        response = client.tag_resources(
            ResourceARNList=[arn],
            Tags=tags
        )

    return {
        'statusCode': 200,
        'body': json.dumps('Finished tagging resources')
    }
