# AWS EC2 Pulumi 管理工具

使用 Pulumi Automation API 管理 AWS EC2 实例，支持 CRUD 全生命周期管理。

## 功能特性

- ✅ **Create** - 创建 EC2 实例
- ✅ **Read/Get** - 查询 EC2 实例信息
- ✅ **Update** - 更新 EC2 实例配置
- ✅ **Delete** - 删除 EC2 实例
- 🔄 **自动识别** - 根据参数自动推断操作类型
- 🔐 **安全凭证** - AK/SK 通过参数传入，不存储在代码中

## 输入参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| access_key | string | ✅ | AWS Access Key ID |
| secret_key | string | ✅ | AWS Secret Access Key |
| region | string | ❌ | AWS 区域，默认 `us-east-1` |
| action | string | ❌ | 操作类型：`auto`/`create`/`update`/`delete`/`get`，默认 `auto` |
| instance_id | string | 条件 | EC2 实例 ID（update/delete/get 时必填） |
| ami | string | 条件 | AMI ID（create/update 时必填） |
| instance_type | string | ❌ | 实例类型，默认 `t2.micro` |
| key_name | string | ❌ | SSH 密钥对名称 |
| subnet_id | string | ❌ | 子网 ID |
| security_group_ids | string | ❌ | 安全组 ID 列表（JSON 数组字符串） |
| tags | string | ❌ | 标签（JSON 对象字符串） |
| project_name | string | ❌ | Pulumi 项目名称 |
| stack_name | string | ❌ | Pulumi Stack 名称 |

## Action 自动识别规则

当 `action=auto` 时，根据以下规则自动推断操作：

| instance_id | ami | 推断操作 |
|-------------|-----|----------|
| 无 | 有 | create |
| 有 | 有 | update |
| 有 | 无 | delete |
| 无 | 无 | get（查询所有实例） |

## 调用示例

### 创建实例

```python
result = manage_ec2_sync(
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    action="create",
    ami="ami-0c55b159cbfafe1f0",
    instance_type="t2.micro",
    key_name="my-key",
    tags='{"Name": "MyInstance", "Env": "Dev"}'
)
```

### 查询实例

```python
result = manage_ec2_sync(
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    action="get",
    instance_id="i-1234567890abcdef0"
)
```

### 删除实例

```python
result = manage_ec2_sync(
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    action="delete",
    instance_id="i-1234567890abcdef0"
)
```

### 自动推断（创建）

```python
# 有 ami 无 instance_id -> 自动识别为 create
result = manage_ec2_sync(
    access_key="AKIAIOSFODNN7EXAMPLE",
    secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    ami="ami-0c55b159cbfafe1f0",
    instance_type="t2.micro"
)
```

## 输出结果

```json
{
    "success": true,
    "action": "create",
    "instance_id": "i-1234567890abcdef0",
    "instance_state": "running",
    "outputs": {
        "public_ip": "52.1.2.3",
        "private_ip": "10.0.1.2"
    },
    "error": null
}
```

## 依赖安装

```bash
pip install pulumi pulumi-aws boto3
```

## 注意事项

1. 确保 AWS 账号有操作 EC2 的权限
2. 首次运行会自动下载 Pulumi 引擎（约 100MB）
3. 临时工作目录位于 `/tmp/pulumi-workspace/`
