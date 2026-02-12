"""
调用示例 - 展示如何使用 pulumi_ec2_manager
注意：这不是主函数，只是示例代码
"""

from pulumi_ec2_manager import manage_ec2_sync, manage_ec2
import asyncio


# 示例 1: 同步调用创建实例
def example_create_sync():
    """同步方式创建 EC2 实例"""
    result = manage_ec2_sync(
        access_key="your-access-key",
        secret_key="your-secret-key",
        region="us-east-1",
        action="create",
        ami="ami-0c55b159cbfafe1f0",  # Amazon Linux 2
        instance_type="t2.micro",
        key_name="my-ssh-key",
        tags='{"Name": "TestInstance", "Environment": "Dev"}'
    )
    print(f"Create Result: {result}")
    return result


# 示例 2: 同步调用查询实例
def example_get_sync():
    """同步方式查询 EC2 实例"""
    result = manage_ec2_sync(
        access_key="your-access-key",
        secret_key="your-secret-key",
        region="us-east-1",
        action="get",
        instance_id="i-1234567890abcdef0"
    )
    print(f"Get Result: {result}")
    return result


# 示例 3: 同步调用删除实例
def example_delete_sync():
    """同步方式删除 EC2 实例"""
    result = manage_ec2_sync(
        access_key="your-access-key",
        secret_key="your-secret-key",
        region="us-east-1",
        action="delete",
        instance_id="i-1234567890abcdef0"
    )
    print(f"Delete Result: {result}")
    return result


# 示例 4: 自动推断操作
def example_auto_infer():
    """自动推断操作类型"""
    # 情况 1: 有 ami 无 instance_id -> create
    result_create = manage_ec2_sync(
        access_key="your-access-key",
        secret_key="your-secret-key",
        action="auto",  # 自动推断
        ami="ami-0c55b159cbfafe1f0",
        instance_type="t2.micro"
    )
    print(f"Auto inferred as: {result_create['action']}")
    
    # 情况 2: 有 instance_id 无 ami -> delete
    result_delete = manage_ec2_sync(
        access_key="your-access-key",
        secret_key="your-secret-key",
        action="auto",
        instance_id="i-1234567890abcdef0"
    )
    print(f"Auto inferred as: {result_delete['action']}")


# 示例 5: 异步调用（适用于支持 async 的调用器）
async def example_async():
    """异步方式调用"""
    result = await manage_ec2(
        access_key="your-access-key",
        secret_key="your-secret-key",
        region="us-east-1",
        action="create",
        ami="ami-0c55b159cbfafe1f0",
        instance_type="t2.micro",
        on_output=lambda msg: print(f"[Pulumi] {msg}")  # 实时输出
    )
    print(f"Async Result: {result}")
    return result


# 示例 6: 带安全组的复杂创建
def example_create_with_sg():
    """创建带安全组的实例"""
    result = manage_ec2_sync(
        access_key="your-access-key",
        secret_key="your-secret-key",
        region="us-east-1",
        action="create",
        ami="ami-0c55b159cbfafe1f0",
        instance_type="t2.micro",
        key_name="my-key",
        subnet_id="subnet-0123456789abcdef0",
        security_group_ids='["sg-0123456789abcdef0", "sg-0987654321fedcba0"]',
        tags='{"Name": "WebServer", "Project": "MyApp", "Team": "DevOps"}'
    )
    print(f"Create with SG Result: {result}")
    return result


if __name__ == "__main__":
    # 这个文件只是示例，不会直接运行
    # 实际调用由其他调用器执行
    pass
