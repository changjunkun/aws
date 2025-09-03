import boto3
import os
import json
import time
from botocore.exceptions import ClientError

def check_and_manage_tags(resource_arn, region, required_tags):
    client = boto3.client('resourcegroupstaggingapi', region_name=region)
    try:
        response = client.get_resources(ResourceARNList=[resource_arn])

        if not response.get('ResourceTagMappingList'):
            client.tag_resources(ResourceARNList=[resource_arn], Tags=required_tags)
            return

        existing_tags = response['ResourceTagMappingList'][0].get('Tags', [])
        existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}

        tags_to_remove = []
        tags_to_add = {}

        for key, value in required_tags.items():
            if key in existing_tag_dict:
                if existing_tag_dict[key] != value:
                    tags_to_remove.append(key)
                    tags_to_add[key] = value
            else:
                tags_to_add[key] = value

        if tags_to_remove:
            client.untag_resources(ResourceARNList=[resource_arn], TagKeys=tags_to_remove)

        if tags_to_add:
            client.tag_resources(ResourceARNList=[resource_arn], Tags=tags_to_add)

    except Exception as e:
        print(f"Error processing {resource_arn}: {e}")

def get_all_resources_in_region(region):
    client = boto3.client('resourcegroupstaggingapi', region_name=region)
    all_resources = []

    try:
        paginator = client.get_paginator('get_resources')
        for page in paginator.paginate():
            all_resources.extend(page.get('ResourceTagMappingList', []))
    except Exception as e:
        print(f"Error getting resources: {e}")

    return [resource['ResourceARN'] for resource in all_resources]

def aws_ec2(event):
    arnList = []
    _account = event['account']
    _region = event['region']
    ec2ArnTemplate = 'arn:aws:ec2:@region@:@account@:instance/@instanceId@'
    volumeArnTemplate = 'arn:aws:ec2:@region@:@account@:volume/@volumeId@'
    resourceArnTemplate = 'arn:aws:ec2:@region@:@account@:resourceName/@resourceId@'

    if event['detail']['eventName'] == 'RunInstances':
        print("tagging for new EC2...")
        _instanceId = event['detail']['responseElements']['instancesSet']['items'][0]['instanceId']
        arnList.append(ec2ArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('@instanceId@', _instanceId))

        ec2_resource = boto3.resource('ec2')
        _instance = ec2_resource.Instance(_instanceId)
        for volume in _instance.volumes.all():
            arnList.append(volumeArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('@volumeId@', volume.id))
        
        # 遍历所有EC2资源并打标签
        try:
            ec2_client = boto3.client('ec2', region_name=_region)
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            # 处理实例
            instances = ec2_client.describe_instances()
            for reservation in instances['Reservations']:
                for instance in reservation['Instances']:
                    try:
                        existing_tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
                        needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                        if needs_update:
                            tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                            ec2_client.create_tags(Resources=[instance['InstanceId']], Tags=tag_list)
                    except Exception as e:
                        print(f"Error processing EC2 instance {instance['InstanceId']}: {e}")
            
            # 处理卷
            volumes = ec2_client.describe_volumes()
            for volume in volumes['Volumes']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in volume.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[volume['VolumeId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing EBS volume {volume['VolumeId']}: {e}")
            
            # 处理快照
            snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])
            for snapshot in snapshots['Snapshots']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in snapshot.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[snapshot['SnapshotId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing snapshot {snapshot['SnapshotId']}: {e}")
            
            # 处理AMI
            images = ec2_client.describe_images(Owners=['self'])
            for image in images['Images']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in image.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[image['ImageId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing AMI {image['ImageId']}: {e}")
            
            # 处理VPC
            vpcs = ec2_client.describe_vpcs()
            for vpc in vpcs['Vpcs']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in vpc.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[vpc['VpcId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing VPC {vpc['VpcId']}: {e}")
            
            # 处理子网
            subnets = ec2_client.describe_subnets()
            for subnet in subnets['Subnets']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in subnet.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[subnet['SubnetId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing subnet {subnet['SubnetId']}: {e}")
            
            # 处理路由表
            route_tables = ec2_client.describe_route_tables()
            for rt in route_tables['RouteTables']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in rt.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[rt['RouteTableId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing route table {rt['RouteTableId']}: {e}")
            
            # 处理互联网网关
            igws = ec2_client.describe_internet_gateways()
            for igw in igws['InternetGateways']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in igw.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[igw['InternetGatewayId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing IGW {igw['InternetGatewayId']}: {e}")
            
            # 处理NAT网关
            nat_gws = ec2_client.describe_nat_gateways()
            for nat_gw in nat_gws['NatGateways']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in nat_gw.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[nat_gw['NatGatewayId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing NAT Gateway {nat_gw['NatGatewayId']}: {e}")
            
            # 处理弹性IP
            addresses = ec2_client.describe_addresses()
            for address in addresses['Addresses']:
                if 'AllocationId' in address:
                    try:
                        existing_tags = {tag['Key']: tag['Value'] for tag in address.get('Tags', [])}
                        needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                        if needs_update:
                            tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                            ec2_client.create_tags(Resources=[address['AllocationId']], Tags=tag_list)
                    except Exception as e:
                        print(f"Error processing EIP {address['AllocationId']}: {e}")
            
            # 处理传输网关
            tgws = ec2_client.describe_transit_gateways()
            for tgw in tgws['TransitGateways']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in tgw.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[tgw['TransitGatewayId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing TGW {tgw['TransitGatewayId']}: {e}")
                    
        except Exception as e:
            print(f"Error processing EC2 resources: {e}")

    elif event['detail']['eventName'] == 'CreateVolume':
        print("tagging for new EBS...")
        _volumeId = event['detail']['responseElements']['volumeId']
        arnList.append(volumeArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('@volumeId@', _volumeId))
        
    elif event['detail']['eventName'] == 'CreateVpc':
        print("tagging for new VPC...")
        _vpcId = event['detail']['responseElements']['vpc']['vpcId']
        arnList.append(resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'vpc').replace('@resourceId@', _vpcId))
        
    elif event['detail']['eventName'] == 'CreateSubnet':
        print("tagging for new Subnet...")
        _subnetId = event['detail']['responseElements']['subnet']['subnetId']
        arnList.append(resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'subnet').replace('@resourceId@', _subnetId))
        
    elif event['detail']['eventName'] == 'CreateRouteTable':
        print("tagging for new Route Table...")
        _routeTableId = event['detail']['responseElements']['routeTable']['routeTableId']
        arnList.append(resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'route-table').replace('@resourceId@', _routeTableId))
        
    elif event['detail']['eventName'] == 'CreateInternetGateway':
        print("tagging for new IGW...")
        _igwId = event['detail']['responseElements']['internetGateway']['internetGatewayId']
        arnList.append(resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'internet-gateway').replace('@resourceId@', _igwId))

    elif event['detail']['eventName'] == 'CreateNatGateway':
        print("Processing NAT Gateway creation...")
        _natgwResponse = event['detail']['responseElements'].get('CreateNatGatewayResponse', {})
        if 'natGateway' in _natgwResponse:
            _natgwId = _natgwResponse['natGateway'].get('natGatewayId')
            if _natgwId:
                print(f"Found NAT Gateway ID: {_natgwId}")
                arn = resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'natgateway').replace('@resourceId@', _natgwId)
                arnList.append(arn)
            else:
                print("NAT Gateway ID not found immediately, polling for status...")
                retries = 5
                while retries > 0:
                    print(f"Retrying... {retries} attempts left.")
                    time.sleep(10)
                    status = check_nat_gateway_status(_region, _natgwId)
                    if status == 'available':
                        print(f"NAT Gateway {_natgwId} is now available.")
                        arn = resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'natgateway').replace('@resourceId@', _natgwId)
                        arnList.append(arn)
                        break
                    retries -= 1
                if retries == 0:
                    print(f"Failed to get NAT Gateway ID for {_natgwId} after retries.")
        else:
            print("NAT Gateway creation failed or did not include the expected information.")

    elif event['detail']['eventName'] == 'AllocateAddress':
        print("tagging for new EIP...")
        _allocationId = event['detail']['responseElements']['allocationId']
        arnList.append(resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'elastic-ip').replace('@resourceId@', _allocationId))

    elif event['detail']['eventName'] == 'CreateVpcEndpoint':
        print("tagging for new VPC Endpoint...")
        _vpceId = event['detail']['responseElements']['CreateVpcEndpointResponse']['vpcEndpoint']['vpcEndpointId']
        arnList.append(resourceArnTemplate.replace('@region@', _region).replace('@account@', _account).replace('resourceName', 'vpc-endpoint').replace('@resourceId@', _vpceId))

        vpc_endpoint = event['detail']['responseElements']['CreateVpcEndpointResponse']['vpcEndpoint']
        tag_set = vpc_endpoint.get('tagSet')
        if tag_set is not None:
            tag_items = tag_set.get('item')
            if isinstance(tag_items, dict):
                if tag_items.get('key') == 'ClusterArn':
                    msk_arn = tag_items.get('value')
                    arnList.append(msk_arn)
                    print(f"Extracted MSK Cluster ARN: {msk_arn}")
            elif isinstance(tag_items, list):
                for tag in tag_items:
                    if isinstance(tag, dict):
                        if tag.get('key') == 'ClusterArn':
                            msk_arn = tag.get('value')
                            arnList.append(msk_arn)
                            print(f"Extracted MSK Cluster ARN: {msk_arn}")
        
        # 遍历所有VPC端点并打标签
        try:
            ec2_client = boto3.client('ec2', region_name=_region)
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            vpc_endpoints = ec2_client.describe_vpc_endpoints()
            for endpoint in vpc_endpoints['VpcEndpoints']:
                try:
                    existing_tags = {tag['Key']: tag['Value'] for tag in endpoint.get('Tags', [])}
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        ec2_client.create_tags(Resources=[endpoint['VpcEndpointId']], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing VPC endpoint {endpoint['VpcEndpointId']}: {e}")
                    
        except Exception as e:
            print(f"Error processing VPC endpoints: {e}")

    elif event['detail']['eventName'] == 'CreateTransitGateway':
        print("tagging for new Transit Gateway...")
        arnList.append(event['detail']['responseElements']['CreateTransitGatewayResponse']['transitGateway']['transitGatewayArn'])

    return arnList

def aws_kafka(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    kafka_client = boto3.client('kafka')
    tags_env = os.getenv('tags', '{}')
    new_tags = json.loads(tags_env)
    
    # 处理新创建的资源
    if event_name == 'CreateClusterV2':
        arnList.append(event['detail']['responseElements']['clusterArn'])
    elif event_name == 'CreateCluster':
        arnList.append(event['detail']['responseElements']['clusterArn'])
    elif event_name == 'CreateConfiguration':
        arnList.append(event['detail']['responseElements']['arn'])
    
    # 扫描并处理所有现有MSK资源
    try:
        # 处理MSK集群（传统和无服务器）
        try:
            next_token = None
            while True:
                if next_token:
                    response = kafka_client.list_clusters_v2(NextToken=next_token)
                else:
                    response = kafka_client.list_clusters_v2()
                
                for cluster in response.get('ClusterInfoList', []):
                    cluster_arn = cluster['ClusterArn']
                    try:
                        existing_tags = kafka_client.list_tags_for_resource(ResourceArn=cluster_arn)['Tags']
                        
                        needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            kafka_client.tag_resource(ResourceArn=cluster_arn, Tags=new_tags)
                    except Exception as e:
                        print(f"Error processing MSK cluster {cluster_arn}: {e}")
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
        except Exception as e:
            print(f"Error listing MSK clusters: {e}")
        
        # 处理MSK配置
        try:
            next_token = None
            while True:
                if next_token:
                    response = kafka_client.list_configurations(NextToken=next_token)
                else:
                    response = kafka_client.list_configurations()
                
                for config in response.get('Configurations', []):
                    config_arn = config['Arn']
                    try:
                        existing_tags = kafka_client.list_tags_for_resource(ResourceArn=config_arn)['Tags']
                        
                        needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            kafka_client.tag_resource(ResourceArn=config_arn, Tags=new_tags)
                    except Exception as e:
                        print(f"Error processing MSK configuration {config_arn}: {e}")
                
                next_token = response.get('NextToken')
                if not next_token:
                    break
        except Exception as e:
            print(f"Error listing MSK configurations: {e}")
            
    except Exception as e:
        print(f"Error processing MSK resources: {e}")
    
    return arnList

def aws_rds(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    rds_client = boto3.client('rds')
    tags_env = os.getenv('tags', '{}')
    new_tags = json.loads(tags_env)
    
    # 处理新创建的资源
    if event_name == 'CreateDBInstance':
        arnList.append(event['detail']['responseElements']['dBInstanceArn'])
    elif event_name == 'CreateDBCluster':
        arnList.append(event['detail']['responseElements']['dBCluster']['dBClusterArn'])
    elif event_name == 'CreateDBSubnetGroup':
        arnList.append(event['detail']['responseElements']['dBSubnetGroup']['dBSubnetGroupArn'])
    elif event_name == 'CreateDBParameterGroup':
        arnList.append(event['detail']['responseElements']['dBParameterGroup']['dBParameterGroupArn'])
    elif event_name == 'CreateOptionGroup':
        arnList.append(event['detail']['responseElements']['optionGroup']['optionGroupArn'])
    elif event_name == 'CreateDBClusterParameterGroup':
        arnList.append(event['detail']['responseElements']['dBClusterParameterGroup']['dBClusterParameterGroupArn'])
    elif event_name == 'CreateDBSnapshot':
        arnList.append(event['detail']['responseElements']['dBSnapshot']['dBSnapshotArn'])
    elif event_name == 'CreateDBClusterSnapshot':
        arnList.append(event['detail']['responseElements']['dBClusterSnapshot']['dBClusterSnapshotArn'])
    
    # 只有在数据库创建事件时才扫描所有RDS资源
    if event_name in ['CreateDBInstance', 'CreateDBCluster']:
        try:
            # 处理DB实例（传统和无服务器）
            instances = rds_client.describe_db_instances()
            for instance in instances['DBInstances']:
                instance_arn = instance['DBInstanceArn']
                try:
                    existing_tags = rds_client.list_tags_for_resource(ResourceName=instance_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        rds_client.add_tags_to_resource(ResourceName=instance_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing RDS instance {instance_arn}: {e}")
            
            # 处理DB集群（传统和无服务器）
            clusters = rds_client.describe_db_clusters()
            for cluster in clusters['DBClusters']:
                cluster_arn = cluster['DBClusterArn']
                try:
                    existing_tags = rds_client.list_tags_for_resource(ResourceName=cluster_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        rds_client.add_tags_to_resource(ResourceName=cluster_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing RDS cluster {cluster_arn}: {e}")
            
            # 处理DB子网组
            subnet_groups = rds_client.describe_db_subnet_groups()
            for subnet_group in subnet_groups['DBSubnetGroups']:
                subnet_group_arn = subnet_group['DBSubnetGroupArn']
                try:
                    existing_tags = rds_client.list_tags_for_resource(ResourceName=subnet_group_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        rds_client.add_tags_to_resource(ResourceName=subnet_group_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing RDS subnet group {subnet_group_arn}: {e}")
            
            # 处理DB参数组
            parameter_groups = rds_client.describe_db_parameter_groups()
            for param_group in parameter_groups['DBParameterGroups']:
                param_group_arn = param_group['DBParameterGroupArn']
                try:
                    existing_tags = rds_client.list_tags_for_resource(ResourceName=param_group_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        rds_client.add_tags_to_resource(ResourceName=param_group_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing RDS parameter group {param_group_arn}: {e}")
            
            # 处理DB集群参数组
            cluster_parameter_groups = rds_client.describe_db_cluster_parameter_groups()
            for cluster_param_group in cluster_parameter_groups['DBClusterParameterGroups']:
                cluster_param_group_arn = cluster_param_group['DBClusterParameterGroupArn']
                try:
                    existing_tags = rds_client.list_tags_for_resource(ResourceName=cluster_param_group_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        rds_client.add_tags_to_resource(ResourceName=cluster_param_group_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing RDS cluster parameter group {cluster_param_group_arn}: {e}")
            
            # 处理DB快照
            try:
                snapshots = rds_client.describe_db_snapshots(SnapshotType='manual')
                for snapshot in snapshots['DBSnapshots']:
                    snapshot_arn = snapshot['DBSnapshotArn']
                    try:
                        existing_tags = rds_client.list_tags_for_resource(ResourceName=snapshot_arn)['TagList']
                        existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                        
                        needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                            rds_client.add_tags_to_resource(ResourceName=snapshot_arn, Tags=tag_list)
                    except Exception as e:
                        print(f"Error processing RDS snapshot {snapshot_arn}: {e}")
                
                # 处理DB集群快照
                cluster_snapshots = rds_client.describe_db_cluster_snapshots(SnapshotType='manual')
                for cluster_snapshot in cluster_snapshots['DBClusterSnapshots']:
                    cluster_snapshot_arn = cluster_snapshot['DBClusterSnapshotArn']
                    try:
                        existing_tags = rds_client.list_tags_for_resource(ResourceName=cluster_snapshot_arn)['TagList']
                        existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                        
                        needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                            rds_client.add_tags_to_resource(ResourceName=cluster_snapshot_arn, Tags=tag_list)
                    except Exception as e:
                        print(f"Error processing RDS cluster snapshot {cluster_snapshot_arn}: {e}")
            except Exception as e:
                print(f"Error listing RDS snapshots: {e}")
            
            # 处理DB选项组
            try:
                option_groups = rds_client.describe_option_groups()
                for option_group in option_groups['OptionGroupsList']:
                    option_group_arn = option_group['OptionGroupArn']
                    try:
                        existing_tags = rds_client.list_tags_for_resource(ResourceName=option_group_arn)['TagList']
                        existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                        
                        needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                            rds_client.add_tags_to_resource(ResourceName=option_group_arn, Tags=tag_list)
                    except Exception as e:
                        print(f"Error processing RDS option group {option_group_arn}: {e}")
            except Exception as e:
                print(f"Error listing RDS option groups: {e}")
                        
        except Exception as e:
            print(f"Error processing RDS resources: {e}")
    
    return arnList

def aws_elasticache(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    elasticache_client = boto3.client('elasticache')
    tags_env = os.getenv('tags', '{}')
    new_tags = json.loads(tags_env)
    
    # 处理新创建的资源
    if event_name == 'CreateServerlessCache':
        arnList.append(event['detail']['responseElements']['serverlessCache']['aRN'])
    elif event_name == 'CreateReplicationGroup':
        arnList.append(event['detail']['responseElements']['replicationGroup']['aRN'])
    elif event_name == 'CreateCacheCluster':
        arnList.append(event['detail']['responseElements']['cacheCluster']['aRN'])
    elif event_name == 'CreateCacheSubnetGroup':
        arnList.append(event['detail']['responseElements']['aRN'])
    elif event_name == 'CreateCacheParameterGroup':
        arnList.append(event['detail']['responseElements']['aRN'])
    elif event_name == 'CreateSnapshot':
        arnList.append(event['detail']['responseElements']['snapshot']['aRN'])
    elif event_name == 'CreateUser':
        arnList.append(event['detail']['responseElements']['aRN'])
    
    # 扫描并处理所有现有ElastiCache资源
    try:
        # 处理无服务器缓存
        try:
            serverless_caches = elasticache_client.describe_serverless_caches()
            for cache in serverless_caches['ServerlessCaches']:
                cache_arn = cache['ARN']
                try:
                    existing_tags = elasticache_client.list_tags_for_resource(ResourceName=cache_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        elasticache_client.add_tags_to_resource(ResourceName=cache_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing serverless cache {cache_arn}: {e}")
        except Exception as e:
            print(f"Error listing serverless caches: {e}")
        
        # 处理复制组（集群模式）
        replication_groups = elasticache_client.describe_replication_groups()
        for rg in replication_groups['ReplicationGroups']:
            rg_arn = rg['ARN']
            try:
                existing_tags = elasticache_client.list_tags_for_resource(ResourceName=rg_arn)['TagList']
                existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                
                needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                
                if needs_update:
                    tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                    elasticache_client.add_tags_to_resource(ResourceName=rg_arn, Tags=tag_list)
            except Exception as e:
                print(f"Error processing replication group {rg_arn}: {e}")
        
        # 处理缓存集群（非集群模式）
        cache_clusters = elasticache_client.describe_cache_clusters()
        for cluster in cache_clusters['CacheClusters']:
            cluster_arn = cluster['ARN']
            try:
                existing_tags = elasticache_client.list_tags_for_resource(ResourceName=cluster_arn)['TagList']
                existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                
                needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                
                if needs_update:
                    tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                    elasticache_client.add_tags_to_resource(ResourceName=cluster_arn, Tags=tag_list)
            except Exception as e:
                print(f"Error processing cache cluster {cluster_arn}: {e}")
        
        # 处理子网组
        subnet_groups = elasticache_client.describe_cache_subnet_groups()
        for sg in subnet_groups['CacheSubnetGroups']:
            sg_arn = sg['ARN']
            try:
                existing_tags = elasticache_client.list_tags_for_resource(ResourceName=sg_arn)['TagList']
                existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                
                needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                
                if needs_update:
                    tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                    elasticache_client.add_tags_to_resource(ResourceName=sg_arn, Tags=tag_list)
            except Exception as e:
                print(f"Error processing subnet group {sg_arn}: {e}")
        
        # 处理参数组
        parameter_groups = elasticache_client.describe_cache_parameter_groups()
        for pg in parameter_groups['CacheParameterGroups']:
            pg_arn = pg['ARN']
            try:
                existing_tags = elasticache_client.list_tags_for_resource(ResourceName=pg_arn)['TagList']
                existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                
                needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                
                if needs_update:
                    tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                    elasticache_client.add_tags_to_resource(ResourceName=pg_arn, Tags=tag_list)
            except Exception as e:
                print(f"Error processing parameter group {pg_arn}: {e}")
        
        # 处理快照
        try:
            snapshots = elasticache_client.describe_snapshots()
            for snapshot in snapshots['Snapshots']:
                snapshot_arn = snapshot['ARN']
                try:
                    existing_tags = elasticache_client.list_tags_for_resource(ResourceName=snapshot_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        elasticache_client.add_tags_to_resource(ResourceName=snapshot_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing snapshot {snapshot_arn}: {e}")
        except Exception as e:
            print(f"Error listing snapshots: {e}")
        
        # 处理用户和用户组
        try:
            users = elasticache_client.describe_users()
            for user in users['Users']:
                user_arn = user['ARN']
                try:
                    existing_tags = elasticache_client.list_tags_for_resource(ResourceName=user_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        elasticache_client.add_tags_to_resource(ResourceName=user_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing user {user_arn}: {e}")
        except Exception as e:
            print(f"Error listing users: {e}")
            
    except Exception as e:
        print(f"Error processing ElastiCache resources: {e}")
    
    return arnList

def aws_memorydb(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    if event_name == 'CreateCluster':
        arnList.append(event['detail']['responseElements']['cluster']['aRN'])
        
        # 遍历所有MemoryDB资源并打标签
        try:
            memorydb_client = boto3.client('memorydb')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            # 处理集群
            clusters = memorydb_client.describe_clusters()
            for cluster in clusters['Clusters']:
                cluster_arn = cluster['ARN']
                try:
                    existing_tags = memorydb_client.list_tags(ResourceArn=cluster_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        memorydb_client.tag_resource(ResourceArn=cluster_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing MemoryDB cluster {cluster_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing MemoryDB resources: {e}")
            
    elif event_name == 'CreateUser':
        arnList.append(event['detail']['responseElements']['user']['aRN'])
    
    return arnList

def aws_eks(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    if event_name == 'CreateCluster':
        arnList.append(event['detail']['responseElements']['cluster']['arn'])
        
        # 遍历所有EKS集群并打标签
        try:
            eks_client = boto3.client('eks')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            clusters = eks_client.list_clusters()
            for cluster_name in clusters['clusters']:
                try:
                    cluster_info = eks_client.describe_cluster(name=cluster_name)
                    cluster_arn = cluster_info['cluster']['arn']
                    existing_tags = cluster_info['cluster'].get('tags', {})
                    
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        eks_client.tag_resource(resourceArn=cluster_arn, tags=new_tags)
                        
                    # 处理节点组
                    nodegroups = eks_client.list_nodegroups(clusterName=cluster_name)
                    for ng_name in nodegroups['nodegroups']:
                        try:
                            ng_info = eks_client.describe_nodegroup(clusterName=cluster_name, nodegroupName=ng_name)
                            ng_arn = ng_info['nodegroup']['nodegroupArn']
                            ng_tags = ng_info['nodegroup'].get('tags', {})
                            
                            ng_needs_update = any(key not in ng_tags or ng_tags[key] != value for key, value in new_tags.items())
                            
                            if ng_needs_update:
                                eks_client.tag_resource(resourceArn=ng_arn, tags=new_tags)
                        except Exception as e:
                            print(f"Error processing EKS nodegroup {ng_name}: {e}")
                            
                except Exception as e:
                    print(f"Error processing EKS cluster {cluster_name}: {e}")
                    
        except Exception as e:
            print(f"Error processing EKS resources: {e}")
            
    elif event_name == 'CreateNodegroup':
        arnList.append(event['detail']['responseElements']['nodegroup']['nodegroupArn'])
    
    return arnList

def aws_s3(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateBucket':
        _bucketName = event['detail']['requestParameters']['bucketName']
        arnList.append(f'arn:aws:s3:::{_bucketName}')
        
        # 遍历所有S3存储桶并打标签
        try:
            s3_client = boto3.client('s3')
            # 获取环境变量中的标签
            try:
                tags_env = os.getenv('tags', '{}')  # Retrieve 'tags' environment variable
                new_tags = json.loads(tags_env)  # Parse JSON string into Python dictionary
            except json.JSONDecodeError as e:
                print(f"Error parsing 'tags' environment variable: {e}")
                new_tags = {'map-migrated': 'DefaultMigration'}  # Default value
            
            buckets = s3_client.list_buckets()
            
            for bucket in buckets['Buckets']:
                bucket_name = bucket['Name']
                if bucket_name != _bucketName:
                    try:
                        try:
                            tags_response = s3_client.get_bucket_tagging(Bucket=bucket_name)
                            existing_tags = {tag['Key']: tag['Value'] for tag in tags_response['TagSet']}
                        except ClientError as e:
                            existing_tags = {} if e.response['Error']['Code'] == 'NoSuchTagSet' else {}
                        
                        needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            updated_tags = {**existing_tags, **new_tags}
                            tag_set = [{'Key': k, 'Value': v} for k, v in updated_tags.items()]
                            s3_client.put_bucket_tagging(Bucket=bucket_name, Tagging={'TagSet': tag_set})
                    except Exception as e:
                        print(f"Error processing bucket {bucket_name}: {e}")
        except Exception as e:
            print(f"Error listing buckets: {e}")
    return arnList

def aws_lambda(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateFunction20150331':
        arnList.append(event['detail']['responseElements']['functionArn'])
        
        # 遍历所有Lambda函数并打标签
        try:
            lambda_client = boto3.client('lambda')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            functions = lambda_client.list_functions()
            for function in functions['Functions']:
                function_arn = function['FunctionArn']
                try:
                    existing_tags = lambda_client.list_tags(Resource=function_arn)['Tags']
                    
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        lambda_client.tag_resource(Resource=function_arn, Tags=new_tags)
                except Exception as e:
                    print(f"Error processing Lambda function {function_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing Lambda functions: {e}")
            
    return arnList

def aws_dynamodb(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    dynamodb_client = boto3.client('dynamodb')
    tags_env = os.getenv('tags', '{}')
    new_tags = json.loads(tags_env)
    
    # 处理新创建的资源
    if event_name == 'CreateTable':
        arnList.append(event['detail']['responseElements']['tableDescription']['tableArn'])
    
    # 扫描并处理所有现有DynamoDB资源
    try:
        # 处理DynamoDB表
        tables = dynamodb_client.list_tables()
        for table_name in tables['TableNames']:
            try:
                table_info = dynamodb_client.describe_table(TableName=table_name)
                table_arn = table_info['Table']['TableArn']
                
                existing_tags = dynamodb_client.list_tags_of_resource(ResourceArn=table_arn)['Tags']
                existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                
                needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                
                if needs_update:
                    tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                    dynamodb_client.tag_resource(ResourceArn=table_arn, Tags=tag_list)
            except Exception as e:
                print(f"Error processing DynamoDB table {table_name}: {e}")
                
    except Exception as e:
        print(f"Error processing DynamoDB tables: {e}")
        
    return arnList

def aws_sns(event):
    arnList = []
    _account = event['account']
    _region = event['region']
    
    if event['detail']['eventName'] == 'CreateTopic':
        _topicName = event['detail']['requestParameters']['name']
        arnList.append(f'arn:aws:sns:{_region}:{_account}:{_topicName}')
        
        # 遍历所有SNS主题并打标签
        try:
            sns_client = boto3.client('sns')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            topics = sns_client.list_topics()
            for topic in topics['Topics']:
                topic_arn = topic['TopicArn']
                try:
                    existing_tags = sns_client.list_tags_for_resource(ResourceArn=topic_arn)['Tags']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        sns_client.tag_resource(ResourceArn=topic_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing SNS topic {topic_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing SNS topics: {e}")
            
    return arnList

def aws_sqs(event):
    arnList = []
    _account = event['account']
    _region = event['region']
    
    if event['detail']['eventName'] == 'CreateQueue':
        _queueName = event['detail']['requestParameters']['queueName']
        arnList.append(f'arn:aws:sqs:{_region}:{_account}:{_queueName}')
        
        # 遍历所有SQS队列并打标签
        try:
            sqs_client = boto3.client('sqs')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            queues = sqs_client.list_queues()
            for queue_url in queues.get('QueueUrls', []):
                try:
                    existing_tags = sqs_client.list_queue_tags(QueueUrl=queue_url)['Tags']
                    
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        sqs_client.tag_queue(QueueUrl=queue_url, Tags=new_tags)
                except Exception as e:
                    print(f"Error processing SQS queue {queue_url}: {e}")
                    
        except Exception as e:
            print(f"Error processing SQS queues: {e}")
            
    return arnList

def aws_elasticfilesystem(event):
    arnList = []
    _account = event['account']
    _region = event['region']
    
    if event['detail']['eventName'] == 'CreateFileSystem':
        _efsId = event['detail']['responseElements']['fileSystemId']
        arnList.append(f'arn:aws:elasticfilesystem:{_region}:{_account}:file-system/{_efsId}')
        
        # 遍历所有EFS文件系统并打标签
        try:
            efs_client = boto3.client('efs')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            filesystems = efs_client.describe_file_systems()
            for fs in filesystems['FileSystems']:
                fs_arn = fs['FileSystemArn']
                try:
                    existing_tags = efs_client.describe_tags(FileSystemId=fs['FileSystemId'])['Tags']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        efs_client.tag_resource(ResourceId=fs['FileSystemId'], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing EFS {fs_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing EFS resources: {e}")
            
    return arnList

def aws_opensearch(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateDomain':
        arnList.append(event['detail']['responseElements']['domainStatus']['domainArn'])
        
        # 遍历所有OpenSearch域并打标签
        try:
            opensearch_client = boto3.client('opensearch')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            domains = opensearch_client.list_domain_names()
            for domain in domains['DomainNames']:
                domain_name = domain['DomainName']
                try:
                    domain_info = opensearch_client.describe_domain(DomainName=domain_name)
                    domain_arn = domain_info['DomainStatus']['ARN']
                    
                    existing_tags = opensearch_client.list_tags(ARN=domain_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        opensearch_client.add_tags(ARN=domain_arn, TagList=tag_list)
                except Exception as e:
                    print(f"Error processing OpenSearch domain {domain_name}: {e}")
                    
        except Exception as e:
            print(f"Error processing OpenSearch domains: {e}")
            
    return arnList

def aws_kms(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateKey':
        arnList.append(event['detail']['responseElements']['keyMetadata']['arn'])
        
        # 遍历所有KMS密钥并打标签
        try:
            kms_client = boto3.client('kms')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            keys = kms_client.list_keys()
            for key in keys['Keys']:
                key_id = key['KeyId']
                try:
                    key_info = kms_client.describe_key(KeyId=key_id)
                    if key_info['KeyMetadata']['KeyManager'] == 'CUSTOMER':
                        key_arn = key_info['KeyMetadata']['Arn']
                        
                        existing_tags = kms_client.list_resource_tags(KeyId=key_id)['Tags']
                        existing_tag_dict = {tag['TagKey']: tag['TagValue'] for tag in existing_tags}
                        
                        needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            tag_list = [{'TagKey': k, 'TagValue': v} for k, v in new_tags.items()]
                            kms_client.tag_resource(KeyId=key_id, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing KMS key {key_id}: {e}")
                    
        except Exception as e:
            print(f"Error processing KMS keys: {e}")
            
    return arnList

def aws_elasticloadbalancing(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateLoadBalancer':
        lbs = event['detail']['responseElements']
        for lb in lbs['loadBalancers']:
            arnList.append(lb['loadBalancerArn'])
            
        # 遍历所有负载均衡器并打标签
        try:
            elb_client = boto3.client('elbv2')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            load_balancers = elb_client.describe_load_balancers()
            for lb in load_balancers['LoadBalancers']:
                lb_arn = lb['LoadBalancerArn']
                try:
                    existing_tags = elb_client.describe_tags(ResourceArns=[lb_arn])['TagDescriptions'][0]['Tags']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        elb_client.add_tags(ResourceArns=[lb_arn], Tags=tag_list)
                except Exception as e:
                    print(f"Error processing ELB {lb_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing ELB resources: {e}")
            
    return arnList

def aws_dms(event):
    arnList = []
    if event['detail']['eventName'] == 'CreateReplicationInstance':
        arnList.append(event['detail']['responseElements']['replicationInstance']['replicationInstanceArn'])
        
        # 遍历所有DMS实例并打标签
        try:
            dms_client = boto3.client('dms')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            instances = dms_client.describe_replication_instances()
            for instance in instances['ReplicationInstances']:
                instance_arn = instance['ReplicationInstanceArn']
                try:
                    existing_tags = dms_client.list_tags_for_resource(ResourceArn=instance_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        dms_client.add_tags_to_resource(ResourceArn=instance_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing DMS instance {instance_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing DMS instances: {e}")
            
    return arnList

def aws_mq(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    if event_name == 'CreateBroker':
        arnList.append(event['detail']['responseElements']['brokerArn'])
        
        # 遍历所有MQ代理并打标签
        try:
            mq_client = boto3.client('mq')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            brokers = mq_client.list_brokers()
            for broker in brokers['BrokerSummaries']:
                broker_arn = broker['BrokerArn']
                try:
                    existing_tags = mq_client.list_tags(ResourceArn=broker_arn)['Tags']
                    
                    needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        mq_client.create_tags(ResourceArn=broker_arn, Tags=new_tags)
                except Exception as e:
                    print(f"Error processing MQ broker {broker_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing MQ brokers: {e}")
            
    return arnList

def aws_docdb(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    docdb_client = boto3.client('docdb')
    docdb_elastic_client = boto3.client('docdb-elastic')
    tags_env = os.getenv('tags', '{}')
    new_tags = json.loads(tags_env)
    
    # 处理新创建的资源
    if event_name == 'CreateDBCluster':
        arnList.append(event['detail']['responseElements']['dBCluster']['dBClusterArn'])
    elif event_name == 'CreateDBInstance':
        arnList.append(event['detail']['responseElements']['dBInstanceArn'])
    elif event_name == 'CreateDBClusterSnapshot':
        arnList.append(event['detail']['responseElements']['dBClusterSnapshot']['dBClusterSnapshotArn'])
    elif event_name == 'CreateDBSubnetGroup':
        arnList.append(event['detail']['responseElements']['dBSubnetGroup']['dBSubnetGroupArn'])
    elif event_name == 'CreateDBClusterParameterGroup':
        arnList.append(event['detail']['responseElements']['dBClusterParameterGroup']['dBClusterParameterGroupArn'])
    elif event_name == 'CreateCluster':
        arnList.append(event['detail']['responseElements']['cluster']['clusterArn'])
    
    # 只有在集群创建事件时才扫描所有DocumentDB资源
    if event_name in ['CreateDBCluster', 'CreateCluster']:
        try:
            # 处理DocumentDB集群
            clusters = docdb_client.describe_db_clusters()
            for cluster in clusters['DBClusters']:
                cluster_arn = cluster['DBClusterArn']
                try:
                    existing_tags = docdb_client.list_tags_for_resource(ResourceName=cluster_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        docdb_client.add_tags_to_resource(ResourceName=cluster_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing DocumentDB cluster {cluster_arn}: {e}")
            
            # 处理DocumentDB弹性集群
            try:
                elastic_clusters = docdb_elastic_client.list_clusters()
                for elastic_cluster in elastic_clusters['clusters']:
                    elastic_cluster_arn = elastic_cluster['clusterArn']
                    try:
                        existing_tags = docdb_elastic_client.list_tags_for_resource(resourceArn=elastic_cluster_arn)['tags']
                        
                        needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            docdb_elastic_client.tag_resource(resourceArn=elastic_cluster_arn, tags=new_tags)
                    except Exception as e:
                        print(f"Error processing DocumentDB elastic cluster {elastic_cluster_arn}: {e}")
            except Exception as e:
                print(f"Error listing DocumentDB elastic clusters: {e}")
            
            # 处理DocumentDB实例
            instances = docdb_client.describe_db_instances()
            for instance in instances['DBInstances']:
                instance_arn = instance['DBInstanceArn']
                try:
                    existing_tags = docdb_client.list_tags_for_resource(ResourceName=instance_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        docdb_client.add_tags_to_resource(ResourceName=instance_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing DocumentDB instance {instance_arn}: {e}")
            
            # 处理DocumentDB子网组
            subnet_groups = docdb_client.describe_db_subnet_groups()
            for subnet_group in subnet_groups['DBSubnetGroups']:
                subnet_group_arn = subnet_group['DBSubnetGroupArn']
                try:
                    existing_tags = docdb_client.list_tags_for_resource(ResourceName=subnet_group_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        docdb_client.add_tags_to_resource(ResourceName=subnet_group_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing DocumentDB subnet group {subnet_group_arn}: {e}")
            
            # 处理DocumentDB集群参数组
            cluster_parameter_groups = docdb_client.describe_db_cluster_parameter_groups()
            for cluster_param_group in cluster_parameter_groups['DBClusterParameterGroups']:
                cluster_param_group_arn = cluster_param_group['DBClusterParameterGroupArn']
                try:
                    existing_tags = docdb_client.list_tags_for_resource(ResourceName=cluster_param_group_arn)['TagList']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        docdb_client.add_tags_to_resource(ResourceName=cluster_param_group_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing DocumentDB cluster parameter group {cluster_param_group_arn}: {e}")
            
            # 处理DocumentDB集群快照
            try:
                cluster_snapshots = docdb_client.describe_db_cluster_snapshots(SnapshotType='manual')
                for cluster_snapshot in cluster_snapshots['DBClusterSnapshots']:
                    cluster_snapshot_arn = cluster_snapshot['DBClusterSnapshotArn']
                    try:
                        existing_tags = docdb_client.list_tags_for_resource(ResourceName=cluster_snapshot_arn)['TagList']
                        existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                        
                        needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                            docdb_client.add_tags_to_resource(ResourceName=cluster_snapshot_arn, Tags=tag_list)
                    except Exception as e:
                        print(f"Error processing DocumentDB cluster snapshot {cluster_snapshot_arn}: {e}")
            except Exception as e:
                print(f"Error listing DocumentDB snapshots: {e}")
            
            # 处理DocumentDB弹性集群快照
            try:
                elastic_snapshots = docdb_elastic_client.list_cluster_snapshots()
                for elastic_snapshot in elastic_snapshots['snapshots']:
                    elastic_snapshot_arn = elastic_snapshot['snapshotArn']
                    try:
                        existing_tags = docdb_elastic_client.list_tags_for_resource(resourceArn=elastic_snapshot_arn)['tags']
                        
                        needs_update = any(key not in existing_tags or existing_tags[key] != value for key, value in new_tags.items())
                        
                        if needs_update:
                            docdb_elastic_client.tag_resource(resourceArn=elastic_snapshot_arn, tags=new_tags)
                    except Exception as e:
                        print(f"Error processing DocumentDB elastic snapshot {elastic_snapshot_arn}: {e}")
            except Exception as e:
                print(f"Error listing DocumentDB elastic snapshots: {e}")
                    
        except Exception as e:
            print(f"Error processing DocumentDB resources: {e}")
        
    return arnList

def aws_route53resolver(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    if event_name == 'CreateResolverEndpoint':
        arnList.append(event['detail']['responseElements']['resolverEndpoint']['arn'])
        
        # 遍历所有Route53 Resolver端点并打标签
        try:
            resolver_client = boto3.client('route53resolver')
            tags_env = os.getenv('tags', '{}')
            new_tags = json.loads(tags_env)
            
            endpoints = resolver_client.list_resolver_endpoints()
            for endpoint in endpoints['ResolverEndpoints']:
                endpoint_arn = endpoint['Arn']
                try:
                    existing_tags = resolver_client.list_tags_for_resource(ResourceArn=endpoint_arn)['Tags']
                    existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                    
                    needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                    
                    if needs_update:
                        tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                        resolver_client.tag_resource(ResourceArn=endpoint_arn, Tags=tag_list)
                except Exception as e:
                    print(f"Error processing Route53 Resolver endpoint {endpoint_arn}: {e}")
                    
        except Exception as e:
            print(f"Error processing Route53 Resolver endpoints: {e}")
            
    return arnList

def aws_workspaces(event):
    arnList = []
    event_name = event['detail']['eventName']
    
    ws_client = boto3.client('workspaces')
    ds_client = boto3.client('ds')
    tags_env = os.getenv('tags', '{}')
    new_tags = json.loads(tags_env)
    
    # 处理新创建的资源
    if event_name == 'CreateWorkspaces':
        for workspace in event['detail']['responseElements']['workspaces']:
            arnList.append(workspace['workspaceArn'])
    elif event_name == 'CreateDirectory':
        arnList.append(event['detail']['responseElements']['directoryId'])
    
    # 扫描并处理所有现有WorkSpaces资源
    try:
        # 处理WorkSpaces实例
        workspaces = ws_client.describe_workspaces()
        for workspace in workspaces['Workspaces']:
            workspace_id = workspace['WorkspaceId']
            try:
                existing_tags = ws_client.describe_tags(ResourceId=workspace_id)['TagList']
                existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                
                needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                
                if needs_update:
                    tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                    ws_client.create_tags(ResourceId=workspace_id, Tags=tag_list)
            except Exception as e:
                print(f"Error processing WorkSpace {workspace_id}: {e}")
        
        # 处理Directory Service目录
        directories = ds_client.describe_directories()
        for directory in directories['DirectoryDescriptions']:
            directory_id = directory['DirectoryId']
            try:
                existing_tags = ds_client.list_tags_for_resource(ResourceId=directory_id)['Tags']
                existing_tag_dict = {tag['Key']: tag['Value'] for tag in existing_tags}
                
                needs_update = any(key not in existing_tag_dict or existing_tag_dict[key] != value for key, value in new_tags.items())
                
                if needs_update:
                    tag_list = [{'Key': k, 'Value': v} for k, v in new_tags.items()]
                    ds_client.add_tags_to_resource(ResourceId=directory_id, Tags=tag_list)
            except Exception as e:
                print(f"Error processing Directory {directory_id}: {e}")
                
    except Exception as e:
        print(f"Error processing WorkSpaces resources: {e}")
        
    return arnList

def main(event, context):
    try:
        _method = event['source'].replace('.', "_")
        _res_tags = json.loads(os.environ['tags'])
        _region = event['region']

        event_name = event.get('detail', {}).get('eventName', '')
        is_create_event = any(create_keyword in event_name.lower() for create_keyword in
                            ['create', 'run', 'allocate'])

        if is_create_event:
            all_resource_arns = get_all_resources_in_region(_region)
            for arn in all_resource_arns:
                check_and_manage_tags(arn, _region, _res_tags)

        if _method in globals():
            resARNs = globals()[_method](event)
            if resARNs:
                for arn in resARNs:
                    check_and_manage_tags(arn, _region, _res_tags)

            return {
                'statusCode': 200,
                'body': json.dumps(f"Successfully processed resources")
            }

        return {
            'statusCode': 400,
            'body': json.dumps("Invalid event source")
        }

    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Internal error: {e}")
        }
