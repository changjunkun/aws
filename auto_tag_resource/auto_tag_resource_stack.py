from aws_cdk import (
    CfnParameter,
    Duration,
    Stack,
    Aws,
    aws_iam as _iam,
    aws_events as _events,
    aws_events_targets as _targets,
    aws_lambda as _lambda
)
from constructs import Construct

class AutoTagResourceStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # example resource
        # queue = sqs.Queue(
        #     self, "AutoTagResourceQueue",
        #     visibility_timeout=Duration.seconds(300),
        # )

        # set parameters
        tags = CfnParameter(self, "tags", type="String", description="tag name and value with json format.")
        identityRecording = CfnParameter(self, "identityRecording", type="String", default="false", description="Defines if the tool records the requester identity as a tag.")

        # create role for lambda function
        lambda_role = _iam.Role(self, "lambda_role",
            role_name = f"resource-tagging-role-{Aws.REGION}",
            assumed_by=_iam.ServicePrincipal("lambda.amazonaws.com"))

        # Add permissions for tagging various AWS resources
        lambda_role.add_to_policy(_iam.PolicyStatement(
            effect=_iam.Effect.ALLOW,
            resources=["*"],
            actions=[
                "dynamodb:TagResource", "dynamodb:DescribeTable",
                "lambda:TagResource", "lambda:ListTags",
                "s3:GetBucketTagging", "s3:PutBucketTagging", 
                "ec2:CreateTags", "ec2:DescribeNatGateways", "ec2:DescribeInternetGateways", 
                "ec2:DescribeVolumes", "ec2:DescribeSubnets", "ec2:DescribeVpcs", "ec2:DescribeRouteTables", 
                "rds:AddTagsToResource", "rds:DescribeDBInstances",
                "sns:TagResource", "sqs:ListQueueTags", "sqs:TagQueue", 
                "es:AddTags", "kms:ListResourceTags", "kms:TagResource", 
                "elasticfilesystem:TagResource", "elasticfilesystem:CreateTags", 
                "elasticfilesystem:DescribeTags", "elasticloadbalancing:AddTags",
                "tag:getResources", "tag:getTagKeys", "tag:getTagValues", 
                "tag:TagResources", "tag:UntagResources", 
                "cloudformation:DescribeStacks", "cloudformation:ListStackResources", 
                "elasticache:DescribeReplicationGroups", "elasticache:DescribeCacheClusters", 
<<<<<<< HEAD
                "elasticache:AddTagsToResource", "elasticache:Describe*", 
                "GameLift:TagResource", "kafka:TagResource", "kafka:UntagResource",
                "docdb:ListTagsForResource", "docdb:AddTagsToResource", "docdb:RemoveTagsFromResource", 
                "workspaces:TagResource", "workspaces:*","workspaces:UntagResource", "workspaces:DescribeWorkspaces",
                "route53:ListTagsForResource", "route53:TagResource", "route53:UntagResource",
                "msk:TagResource", "msk:UntagResource", "kafka:*", "resource-groups:*", "kafka:AddTagsToResource", "kafka:*", "ds:*"
=======
                "elasticache:AddTagsToResource", "resource-groups:*", 
                "GameLift:TagResource", "kafka:TagResource", "kafka:UntagResource","kafka:List*","kafka:Describe*",
                "docdb:ListTagsForResource", "docdb:AddTagsToResource", "docdb:RemoveTagsFromResource", 
                "workspaces:TagResource", "workspaces:UntagResource", "workspaces:DescribeWorkspaces", "workspaces:Describe*", "workspaces:List*",
                "route53:ListTagsForResource", "route53:TagResource", "route53:UntagResource",
                "msk:TagResource", "msk:UntagResource", "ec2:DescribeNetworkInterfaces",
                "ds:Describe*", "ds:ListTagsForResource", "ds:AddTagsToResource", "ds:CreateTags",
                "workspaces:CreateTags"
>>>>>>> d49ad03bca15aa652579d1493d33ba60652e86a7
            ]
        ))

        # create lambda function
        tagging_function = _lambda.Function(self, "resource_tagging_automation_function",
            runtime=_lambda.Runtime.PYTHON_3_10,
            memory_size=128,
            timeout=Duration.seconds(600),
            handler="lambda-handler.main",
            code=_lambda.Code.from_asset("./lambda"),
            function_name="resource-tagging-automation-function",
            role=lambda_role,
            environment={
                "tags": tags.value_as_string,
                "identityRecording": identityRecording.value_as_string
            }
        )

        # Define event rule for resource creation events
        _eventRule = _events.Rule(self, "resource-tagging-automation-rule",
            event_pattern=_events.EventPattern(
                source=["aws.ec2", "aws.elasticloadbalancing", "aws.rds", "aws.lambda", "aws.s3", 
<<<<<<< HEAD
                        "aws.dynamodb", "aws.elasticfilesystem", "aws.es", "aws.sqs", "aws.sns", 
                        "aws.kms", "aws.elasticache", "aws.gamelift", "aws.msk", "aws.route53", "aws.workspaces", "aws.eks"],
=======
                        "aws.dynamodb", "aws.elasticfilesystem", "aws.es", "aws.sqs", "aws.sns", "aws.eks",
                        "aws.kms", "aws.elasticache", "aws.gamelift", "aws.msk", "aws.route53","aws.workspaces"],
>>>>>>> d49ad03bca15aa652579d1493d33ba60652e86a7
                detail_type=["AWS API Call via CloudTrail"],
                detail={
                    "eventSource": [
                        "ec2.amazonaws.com", "elasticloadbalancing.amazonaws.com", "s3.amazonaws.com", 
<<<<<<< HEAD
                        "rds.amazonaws.com", "lambda.amazonaws.com", "dynamodb.amazonaws.com", 
                        "elasticfilesystem.amazonaws.com", "es.amazonaws.com", "sqs.amazonaws.com", 
                        "sns.amazonaws.com", "kms.amazonaws.com", "elasticache.amazonaws.com", 
                        "gamelift.amazonaws.com", "dms.amazonaws.com", "kafka.amazonaws.com", "route53.amazonaws.com", "eks.amazonaws.com", "workspaces.amazonaws.com"
                    ],
                    "eventName": [
                        "RunInstances", "CreateFunction20150331", "CreateBucket", "CreateDBInstance", 
                        "CreateTable", "CreateVolume", "CreateLoadBalancer", "CreateMountTarget", 
                        "CreateDomain", "CreateQueue", "CreateTopic", "CreateKey", "CreateReplicationGroup", 
                        "CreateCacheCluster", "ModifyReplicationGroupShardConfiguration", "CreateFleet",
                        "CreateNatGateway", "CreateSubnet", "CreateVpc", "CreateRoute", "CreateHostedZone", 
                        "CreateCluster", "AllocateAddress", "DeregisterWorkspaceDirectory", "workspaceId", "CreateDirectory", "CreateInternetGateway", "CreateVpcEndpoint", "CreateTransitGateway", "CreateReplicationInstance", "CreateReplicationGroup", "ModifyCluster", "CreateWorkspaces", "ChangeResourceRecordSets", "CreateServerlessCache", "CreateCacheCluster", "CreateReplicationGroup", "CopyServerlessCacheSnapshot", "CopySnapshot", "CreateCacheParameterGroup", "CreateCacheSecurityGroup", "CreateCacheSubnetGroup", "CreateServerlessCacheSnapshot", "CreateSnapshot", "CreateUserGroup", "CreateUser", "PurchaseReservedCacheNodesOffering", "CreateRecordSet", "CreateInboundEndpoint", "CreateHostedZone", "UpdateCluster", "CreateStream", "UpdateStream", "CreateWorkspace", "CreateVpcPeeringConnection", "DeleteVpcPeeringConnection", "CreateTags"
                    ]
=======
                        "rds.amazonaws.com", "lambda.amazonaws.com", "dynamodb.amazonaws.com", "eks.amazonaws.com",
                        "elasticfilesystem.amazonaws.com", "es.amazonaws.com", "sqs.amazonaws.com", "skylight.amazonaws.com",
                        "sns.amazonaws.com", "kms.amazonaws.com", "elasticache.amazonaws.com", "workspaces.amazonaws.com",
                        "gamelift.amazonaws.com", "kafka.amazonaws.com", "route53.amazonaws.com"
                    ],
                    "eventName": ["RunInstances", "CreateFunction20150331", "CreateBucket", "DeregisterWorkspaceDirectory", "CreateDBInstance", "workspaceId", "CreateDirectory", "CreateTable", "CreateVolume", "CreateLoadBalancer", "CreateMountTarget", "CreateDomain", "CreateQueue", "CreateTopic", "CreateKey", "CreateVpc", "CreateInternetGateway", "CreateNatGateway", "AllocateAddress", "CreateVpcEndpoint", "CreateTransitGateway", "CreateReplicationInstance", "CreateReplicationGroup", "CreateCluster", "ModifyCluster", "CreateWorkspaces", "CreateHostedZone", "ChangeResourceRecordSets", "CreateServerlessCache", "CreateCacheCluster", "CreateReplicationGroup", "CopyServerlessCacheSnapshot", "CopySnapshot", "CreateCacheParameterGroup", "CreateCacheSecurityGroup", "CreateCacheSubnetGroup", "CreateServerlessCacheSnapshot", "CreateSnapshot", "CreateUserGroup", "CreateUser", "PurchaseReservedCacheNodesOffering", "CreateRecordSet", "CreateInboundEndpoint", "CreateHostedZone", "CreateCluster", "UpdateCluster", "DeleteCluster", "CreateStream", "UpdateStream", "DeleteStream", "CreateWorkspace", "TerminateWorkspace", "CreateVpcPeeringConnection", "DeleteVpcPeeringConnection", "CreateHealthCheck", "CreateTags", "UpdateHealthCheck", "DeleteHealthCheck"]
>>>>>>> d49ad03bca15aa652579d1493d33ba60652e86a7
                }
            )
        )

        # Add Lambda function as the target for the event rule
        _eventRule.add_target(_targets.LambdaFunction(tagging_function, retry_attempts=2))
