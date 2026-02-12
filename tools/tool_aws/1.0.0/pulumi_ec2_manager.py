"""
Pulumi AWS EC2 管理模块
支持 Create/Read/Update/Delete EC2 实例
通过参数控制操作类型
"""

import os
import json
import asyncio
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from pulumi import automation as auto
import pulumi_aws as aws


@dataclass
class EC2Config:
    """EC2 实例配置"""
    # AWS 凭证
    access_key: str
    secret_key: str
    region: str = "us-east-1"
    
    # 实例配置
    ami: Optional[str] = None
    instance_type: str = "t2.micro"
    key_name: Optional[str] = None
    subnet_id: Optional[str] = None
    security_group_ids: Optional[list] = None
    
    # 可选标签
    tags: Dict[str, str] = field(default_factory=lambda: {"ManagedBy": "Pulumi"})
    
    # 操作标识（create/update/delete/get）
    action: str = "create"
    
    # 实例 ID（用于 update/delete/get）
    instance_id: Optional[str] = None
    
    # Pulumi 项目配置
    project_name: str = "aws-ec2-manager"
    stack_name: str = "dev"


@dataclass
class OperationResult:
    """操作结果"""
    success: bool
    action: str
    instance_id: Optional[str] = None
    instance_state: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


def _infer_action(config: EC2Config) -> str:
    """
    根据参数自动推断操作类型
    
    推断规则：
    - 有 instance_id + 有 ami -> update (更新实例配置)
    - 有 instance_id + 无 ami -> delete (删除实例)
    - 无 instance_id + 有 ami -> create (创建实例)
    - 有 instance_id + action=get -> get (查询实例)
    """
    if config.action and config.action != "auto":
        return config.action.lower()
    
    has_instance_id = bool(config.instance_id)
    has_ami = bool(config.ami)
    
    if has_instance_id and has_ami:
        return "update"
    elif has_instance_id and not has_ami:
        return "delete"
    elif not has_instance_id and has_ami:
        return "create"
    else:
        return "get"  # 默认查询操作


def _pulumi_program(config: EC2Config):
    """
    Pulumi 基础设施程序
    根据 action 执行不同的资源定义
    """
    action = _infer_action(config)
    
    if action == "create":
        # 创建 EC2 实例
        instance_args = {
            "ami": config.ami,
            "instance_type": config.instance_type,
            "tags": config.tags,
        }
        
        if config.key_name:
            instance_args["key_name"] = config.key_name
        if config.subnet_id:
            instance_args["subnet_id"] = config.subnet_id
        if config.security_group_ids:
            instance_args["vpc_security_group_ids"] = config.security_group_ids
        
        instance = aws.ec2.Instance("ec2-instance", **instance_args)
        
        # 导出输出
        return {
            "instance_id": instance.id,
            "public_ip": instance.public_ip,
            "private_ip": instance.private_ip,
            "instance_state": instance.instance_state,
        }
    
    elif action == "update":
        # 更新现有实例（通过导入方式）
        instance_args = {
            "ami": config.ami,
            "instance_type": config.instance_type,
            "tags": config.tags,
        }
        
        if config.key_name:
            instance_args["key_name"] = config.key_name
        if config.subnet_id:
            instance_args["subnet_id"] = config.subnet_id
        if config.security_group_ids:
            instance_args["vpc_security_group_ids"] = config.security_group_ids
        
        # 使用 import_ 参数来管理现有资源
        instance = aws.ec2.Instance(
            "ec2-instance",
            opts=auto.ResourceOptions(import_=config.instance_id),
            **instance_args
        )
        
        return {
            "instance_id": instance.id,
            "public_ip": instance.public_ip,
            "private_ip": instance.private_ip,
            "instance_state": instance.instance_state,
        }
    
    elif action == "delete":
        # 删除操作：不创建任何资源，destroy 时会清理
        # 为了删除，我们需要先导入然后销毁
        instance = aws.ec2.Instance(
            "ec2-instance",
            ami="",  # 占位，实际需要查询获取
            instance_type=config.instance_type,
            opts=auto.ResourceOptions(import_=config.instance_id)
        )
        return {
            "instance_id": instance.id,
            "message": "Instance marked for deletion"
        }
    
    else:  # get
        # 查询操作：获取现有实例信息
        # 使用 aws.get_instance 数据源
        instance = aws.ec2.get_instance(instance_id=config.instance_id)
        return {
            "instance_id": instance.id,
            "ami": instance.ami,
            "instance_type": instance.instance_type,
            "public_ip": instance.public_ip,
            "private_ip": instance.private_ip,
            "instance_state": instance.state,
            "tags": instance.tags,
        }


class PulumiEC2Manager:
    """Pulumi AWS EC2 管理器"""
    
    def __init__(self, config: EC2Config):
        self.config = config
        self._stack: Optional[auto.Stack] = None
    
    def _setup_env(self):
        """设置 AWS 环境变量"""
        os.environ["AWS_ACCESS_KEY_ID"] = self.config.access_key
        os.environ["AWS_SECRET_ACCESS_KEY"] = self.config.secret_key
        os.environ["AWS_DEFAULT_REGION"] = self.config.region
    
    async def _get_or_create_stack(self) -> auto.Stack:
        """获取或创建 Pulumi Stack"""
        work_dir = f"/tmp/pulumi-workspace/{self.config.project_name}"
        os.makedirs(work_dir, exist_ok=True)
        
        # 创建 Pulumi.yaml
        pulumi_yaml = f"""name: {self.config.project_name}
runtime: python
description: AWS EC2 Manager
"""
        with open(f"{work_dir}/Pulumi.yaml", "w") as f:
            f.write(pulumi_yaml)
        
        # 定义程序函数
        def program():
            return _pulumi_program(self.config)
        
        # 创建或选择 stack
        stack = await auto.create_or_select_stack_async(
            stack_name=self.config.stack_name,
            project_name=self.config.project_name,
            program=program,
            work_dir=work_dir,
        )
        
        # 配置 AWS Provider
        await stack.set_config_async("aws:region", auto.ConfigValue(self.config.region))
        
        return stack
    
    async def execute(self, on_output: Optional[Callable[[str], None]] = None) -> OperationResult:
        """
        执行操作
        
        参数:
            on_output: 输出回调函数
            
        返回:
            OperationResult: 操作结果
        """
        try:
            self._setup_env()
            action = _infer_action(self.config)
            
            if action == "get":
                # 查询操作不需要 stack，直接使用 AWS API
                return await self._do_get()
            
            self._stack = await self._get_or_create_stack()
            
            if action == "create":
                return await self._do_create(on_output)
            elif action == "update":
                return await self._do_update(on_output)
            elif action == "delete":
                return await self._do_delete(on_output)
            else:
                return OperationResult(
                    success=False,
                    action=action,
                    error=f"Unknown action: {action}"
                )
                
        except Exception as e:
            return OperationResult(
                success=False,
                action=_infer_action(self.config),
                error=str(e)
            )
    
    async def _do_create(self, on_output: Optional[Callable[[str], None]] = None) -> OperationResult:
        """创建 EC2 实例"""
        result = await self._stack.up_async(on_output=on_output)
        
        outputs = result.outputs
        return OperationResult(
            success=True,
            action="create",
            instance_id=outputs.get("instance_id", {}).get("value"),
            instance_state=outputs.get("instance_state", {}).get("value"),
            outputs={
                "public_ip": outputs.get("public_ip", {}).get("value"),
                "private_ip": outputs.get("private_ip", {}).get("value"),
            }
        )
    
    async def _do_update(self, on_output: Optional[Callable[[str], None]] = None) -> OperationResult:
        """更新 EC2 实例"""
        result = await self._stack.up_async(on_output=on_output)
        
        outputs = result.outputs
        return OperationResult(
            success=True,
            action="update",
            instance_id=outputs.get("instance_id", {}).get("value"),
            instance_state=outputs.get("instance_state", {}).get("value"),
            outputs={
                "public_ip": outputs.get("public_ip", {}).get("value"),
                "private_ip": outputs.get("private_ip", {}).get("value"),
            }
        )
    
    async def _do_delete(self, on_output: Optional[Callable[[str], None]] = None) -> OperationResult:
        """删除 EC2 实例"""
        result = await self._stack.destroy_async(on_output=on_output)
        
        return OperationResult(
            success=True,
            action="delete",
            instance_id=self.config.instance_id,
            outputs={"message": "Instance deleted successfully"}
        )
    
    async def _do_get(self) -> OperationResult:
        """查询 EC2 实例信息"""
        # 使用 boto3 直接查询，无需 Pulumi stack
        import boto3
        
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=self.config.access_key,
            aws_secret_access_key=self.config.secret_key,
            region_name=self.config.region
        )
        
        if not self.config.instance_id:
            # 列出所有实例
            response = ec2.describe_instances()
            instances = []
            for reservation in response.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    instances.append({
                        "instance_id": inst.get("InstanceId"),
                        "instance_type": inst.get("InstanceType"),
                        "state": inst.get("State", {}).get("Name"),
                        "public_ip": inst.get("PublicIpAddress"),
                        "private_ip": inst.get("PrivateIpAddress"),
                    })
            return OperationResult(
                success=True,
                action="get",
                outputs={"instances": instances, "count": len(instances)}
            )
        else:
            # 查询特定实例
            response = ec2.describe_instances(InstanceIds=[self.config.instance_id])
            
            for reservation in response.get("Reservations", []):
                for inst in reservation.get("Instances", []):
                    return OperationResult(
                        success=True,
                        action="get",
                        instance_id=inst.get("InstanceId"),
                        instance_state=inst.get("State", {}).get("Name"),
                        outputs={
                            "ami": inst.get("ImageId"),
                            "instance_type": inst.get("InstanceType"),
                            "public_ip": inst.get("PublicIpAddress"),
                            "private_ip": inst.get("PrivateIpAddress"),
                            "tags": inst.get("Tags", []),
                            "launch_time": str(inst.get("LaunchTime")) if inst.get("LaunchTime") else None,
                        }
                    )
            
            return OperationResult(
                success=False,
                action="get",
                error=f"Instance {self.config.instance_id} not found"
            )


# ============================================================================
# 对外接口函数（供外部调用器使用）
# ============================================================================

async def manage_ec2(
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
    action: str = "auto",  # auto/create/update/delete/get
    instance_id: Optional[str] = None,
    ami: Optional[str] = None,
    instance_type: str = "t2.micro",
    key_name: Optional[str] = None,
    subnet_id: Optional[str] = None,
    security_group_ids: Optional[str] = None,  # JSON 字符串列表
    tags: Optional[str] = None,  # JSON 字符串字典
    project_name: str = "aws-ec2-manager",
    stack_name: str = "dev",
    on_output: Optional[Callable[[str], None]] = None
) -> Dict[str, Any]:
    """
    管理 AWS EC2 实例的统一入口
    
    参数:
        access_key: AWS Access Key
        secret_key: AWS Secret Key
        region: AWS 区域，默认 us-east-1
        action: 操作类型 - auto(自动推断)/create/update/delete/get
        instance_id: EC2 实例 ID（update/delete/get 时需要）
        ami: AMI ID（create/update 时需要）
        instance_type: 实例类型，默认 t2.micro
        key_name: SSH 密钥对名称
        subnet_id: 子网 ID
        security_group_ids: 安全组 ID 列表（JSON 字符串）
        tags: 标签（JSON 字符串字典）
        project_name: Pulumi 项目名称
        stack_name: Pulumi Stack 名称
        on_output: 输出回调函数
    
    返回:
        操作结果字典
    
    使用示例:
        # 创建实例
        result = await manage_ec2(
            access_key="AKIA...",
            secret_key="...",
            action="create",
            ami="ami-12345678",
            instance_type="t2.micro"
        )
        
        # 删除实例
        result = await manage_ec2(
            access_key="AKIA...",
            secret_key="...",
            action="delete",
            instance_id="i-1234567890abcdef0"
        )
        
        # 自动推断（根据参数自动判断）
        # 有 ami 无 instance_id -> create
        # 有 ami 有 instance_id -> update
        # 无 ami 有 instance_id -> delete
    """
    # 解析 JSON 参数
    sg_ids = json.loads(security_group_ids) if security_group_ids else None
    tag_dict = json.loads(tags) if tags else {"ManagedBy": "Pulumi"}
    
    config = EC2Config(
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        ami=ami,
        instance_type=instance_type,
        key_name=key_name,
        subnet_id=subnet_id,
        security_group_ids=sg_ids,
        tags=tag_dict,
        action=action,
        instance_id=instance_id,
        project_name=project_name,
        stack_name=stack_name,
    )
    
    manager = PulumiEC2Manager(config)
    result = await manager.execute(on_output=on_output)
    
    return {
        "success": result.success,
        "action": result.action,
        "instance_id": result.instance_id,
        "instance_state": result.instance_state,
        "outputs": result.outputs,
        "error": result.error,
    }


def manage_ec2_sync(
    access_key: str,
    secret_key: str,
    region: str = "us-east-1",
    action: str = "auto",
    instance_id: Optional[str] = None,
    ami: Optional[str] = None,
    instance_type: str = "t2.micro",
    key_name: Optional[str] = None,
    subnet_id: Optional[str] = None,
    security_group_ids: Optional[str] = None,
    tags: Optional[str] = None,
    project_name: str = "aws-ec2-manager",
    stack_name: str = "dev"
) -> Dict[str, Any]:
    """
    同步版本的 EC2 管理接口（供不支持 async 的调用器使用）
    参数同 manage_ec2
    """
    return asyncio.run(manage_ec2(
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        action=action,
        instance_id=instance_id,
        ami=ami,
        instance_type=instance_type,
        key_name=key_name,
        subnet_id=subnet_id,
        security_group_ids=security_group_ids,
        tags=tags,
        project_name=project_name,
        stack_name=stack_name,
    ))
