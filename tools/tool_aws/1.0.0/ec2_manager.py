#!/usr/bin/env python3
"""
EC2 管理器 - 单一函数，全部参数写在入参里
所有逻辑在一个 def 里，不调用任何其他 py 文件，直接使用 boto3
"""
import json
from typing import Optional, Dict, Any
import boto3


def manage_ec2(
    access_key: str,
    secret_key: str,
    region: str,
    instance_id: Optional[str] = None,
    ami: Optional[str] = None,
    instance_type: str = "t2.micro",
    key_name: Optional[str] = None,
    subnet_id: Optional[str] = None,
    security_group_ids: Optional[str] = None,
    tags: Optional[str] = None,
    action: str = "auto"
) -> Dict[str, Any]:
    """
    EC2 管理统一入口 - 单一函数，全部参数写在入参里
    
    推断规则 (当 action="auto" 时):
        - 无 instance_id + 有 ami        -> create
        - 有 instance_id + 有 ami        -> update
        - 有 instance_id + 无 ami        -> delete
        - 有 instance_id + action="get"  -> get
        - 无 instance_id + 无 ami        -> get (查询所有)
    
    返回:
        {"success": bool, "action": str, "instance_id": str, 
         "instance_state": str, "outputs": dict, "error": str}
    """
    # ========== 推断操作类型 ==========
    if action and action != "auto":
        inferred_action = action.lower()
    else:
        has_instance_id = bool(instance_id)
        has_ami = bool(ami)
        
        if has_instance_id and has_ami:
            inferred_action = "update"
        elif has_instance_id and not has_ami:
            inferred_action = "delete"
        elif not has_instance_id and has_ami:
            inferred_action = "create"
        else:
            inferred_action = "get"
    
    # ========== 初始化 boto3 client ==========
    try:
        ec2 = boto3.client(
            'ec2',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
    except Exception as e:
        return {
            "success": False,
            "action": inferred_action,
            "instance_id": instance_id,
            "instance_state": None,
            "outputs": {},
            "error": f"Failed to create EC2 client: {str(e)}"
        }
    
    # ========== 解析可选参数 ==========
    try:
        sg_ids = json.loads(security_group_ids) if security_group_ids else None
        tag_dict = json.loads(tags) if tags else {"ManagedBy": "EC2Manager"}
    except json.JSONDecodeError as e:
        return {
            "success": False,
            "action": inferred_action,
            "instance_id": instance_id,
            "instance_state": None,
            "outputs": {},
            "error": f"Invalid JSON in parameters: {str(e)}"
        }
    
    # ========== 执行操作 ==========
    try:
        # -------- CREATE --------
        if inferred_action == "create":
            run_args = {
                'ImageId': ami,
                'InstanceType': instance_type,
                'MinCount': 1,
                'MaxCount': 1,
                'TagSpecifications': [{
                    'ResourceType': 'instance',
                    'Tags': [{'Key': k, 'Value': v} for k, v in tag_dict.items()]
                }]
            }
            
            if key_name:
                run_args['KeyName'] = key_name
            if subnet_id:
                run_args['SubnetId'] = subnet_id
            if sg_ids:
                run_args['SecurityGroupIds'] = sg_ids
            
            response = ec2.run_instances(**run_args)
            new_instance_id = response['Instances'][0]['InstanceId']
            
            # 等待运行
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[new_instance_id])
            
            # 获取详情
            response = ec2.describe_instances(InstanceIds=[new_instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            
            return {
                "success": True,
                "action": "create",
                "instance_id": new_instance_id,
                "instance_state": instance['State']['Name'],
                "outputs": {
                    "public_ip": instance.get('PublicIpAddress'),
                    "private_ip": instance.get('PrivateIpAddress'),
                    "ami": ami,
                    "instance_type": instance_type
                },
                "error": None
            }
        
        # -------- UPDATE --------
        elif inferred_action == "update":
            # 停止实例
            ec2.stop_instances(InstanceIds=[instance_id])
            waiter = ec2.get_waiter('instance_stopped')
            waiter.wait(InstanceIds=[instance_id])
            
            # 修改实例类型
            ec2.modify_instance_attribute(
                InstanceId=instance_id,
                InstanceType={'Value': instance_type}
            )
            
            # 启动实例
            ec2.start_instances(InstanceIds=[instance_id])
            waiter = ec2.get_waiter('instance_running')
            waiter.wait(InstanceIds=[instance_id])
            
            # 获取更新后的信息
            response = ec2.describe_instances(InstanceIds=[instance_id])
            instance = response['Reservations'][0]['Instances'][0]
            
            return {
                "success": True,
                "action": "update",
                "instance_id": instance_id,
                "instance_state": instance['State']['Name'],
                "outputs": {
                    "public_ip": instance.get('PublicIpAddress'),
                    "private_ip": instance.get('PrivateIpAddress'),
                    "instance_type": instance['InstanceType']
                },
                "error": None
            }
        
        # -------- DELETE --------
        elif inferred_action == "delete":
            ec2.terminate_instances(InstanceIds=[instance_id])
            
            waiter = ec2.get_waiter('instance_terminated')
            waiter.wait(InstanceIds=[instance_id])
            
            return {
                "success": True,
                "action": "delete",
                "instance_id": instance_id,
                "instance_state": "terminated",
                "outputs": {"message": "Instance deleted successfully"},
                "error": None
            }
        
        # -------- GET --------
        elif inferred_action == "get":
            if instance_id:
                # 查询特定实例
                response = ec2.describe_instances(InstanceIds=[instance_id])
                instances = []
                for r in response.get('Reservations', []):
                    for inst in r.get('Instances', []):
                        instances.append({
                            "instance_id": inst.get('InstanceId'),
                            "instance_type": inst.get('InstanceType'),
                            "state": inst.get('State', {}).get('Name'),
                            "ami": inst.get('ImageId'),
                            "public_ip": inst.get('PublicIpAddress'),
                            "private_ip": inst.get('PrivateIpAddress'),
                            "tags": {t['Key']: t['Value'] for t in inst.get('Tags', [])}
                        })
                
                return {
                    "success": True,
                    "action": "get",
                    "instance_id": instance_id if instances else None,
                    "instance_state": instances[0]['state'] if instances else None,
                    "outputs": {"instances": instances, "count": len(instances)},
                    "error": None if instances else f"Instance {instance_id} not found"
                }
            else:
                # 列出所有实例
                response = ec2.describe_instances()
                instances = []
                for r in response.get('Reservations', []):
                    for inst in r.get('Instances', []):
                        instances.append({
                            "instance_id": inst.get('InstanceId'),
                            "instance_type": inst.get('InstanceType'),
                            "state": inst.get('State', {}).get('Name'),
                            "ami": inst.get('ImageId'),
                            "public_ip": inst.get('PublicIpAddress'),
                            "private_ip": inst.get('PrivateIpAddress')
                        })
                
                return {
                    "success": True,
                    "action": "get",
                    "instance_id": None,
                    "instance_state": None,
                    "outputs": {"instances": instances, "count": len(instances)},
                    "error": None
                }
        
        # -------- 不支持的操作 --------
        else:
            return {
                "success": False,
                "action": inferred_action,
                "instance_id": instance_id,
                "instance_state": None,
                "outputs": {},
                "error": f"Unsupported action: {inferred_action}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "action": inferred_action,
            "instance_id": instance_id,
            "instance_state": None,
            "outputs": {},
            "error": str(e)
        }
