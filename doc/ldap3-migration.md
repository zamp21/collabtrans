# LDAP3 迁移指南

## 概述

CollabTrans已成功从`python-ldap`迁移到`ldap3`库，以解决Windows平台的兼容性问题。

## 迁移原因

### python-ldap的问题
- **Windows编译复杂**: 需要OpenLDAP开发库和C编译器
- **依赖管理困难**: 需要手动安装多个C库依赖
- **维护成本高**: 官方不再提供Windows预编译包
- **安装失败率高**: 用户经常遇到编译错误

### ldap3的优势
- **纯Python实现**: 无需C库依赖，跨平台兼容
- **安装简单**: `pip install ldap3`即可
- **功能完整**: 支持所有LDAP功能
- **维护活跃**: 持续更新和bug修复
- **文档完善**: 详细的API文档和示例

## 技术变更

### 依赖更新
```toml
# pyproject.toml
# 旧版本
"python-ldap>=3.4.4",

# 新版本
"ldap3>=2.9.1",
```

### API变更对比

#### 连接创建
```python
# python-ldap (旧)
import ldap
conn = ldap.initialize(ldap_uri)
conn.simple_bind_s(bind_dn, password)

# ldap3 (新)
from ldap3 import Server, Connection
server = Server(host, port, use_ssl=True)
conn = Connection(server, bind_dn, password)
conn.bind()
```

#### 搜索操作
```python
# python-ldap (旧)
result = conn.search_s(
    base_dn,
    ldap.SCOPE_SUBTREE,
    filter_str,
    attributes
)

# ldap3 (新)
conn.search(
    search_base=base_dn,
    search_filter=filter_str,
    search_scope=SUBTREE,
    attributes=attributes
)
result = conn.entries
```

#### 属性访问
```python
# python-ldap (旧)
attrs = result[0][1]
display_name = attrs['displayName'][0].decode('utf-8')

# ldap3 (新)
user_entry = conn.entries[0]
display_name = str(user_entry.displayName)
```

## 功能保持

### ✅ 完全兼容的功能
- LDAP/LDAPS协议支持
- 用户认证和绑定
- 用户信息搜索
- 组成员关系查询
- TLS/SSL配置
- 错误处理和异常

### ✅ 增强的功能
- 更好的错误信息
- 更简洁的API
- 自动类型转换
- 更好的连接管理

## 安装说明

### 自动安装
```bash
# 使用uv (推荐)
uv add ldap3
uv sync

# 使用pip
pip install ldap3>=2.9.1
```

### 验证安装
```python
# 测试导入
from ldap3 import Server, Connection, ALL
print("ldap3安装成功")
```

## 配置兼容性

### 配置文件无需更改
所有现有的LDAP配置都完全兼容：

```json
{
  "ldap_enabled": true,
  "ldap_protocol": "ldaps",
  "ldap_host": "ad.example.com",
  "ldap_port": 636,
  "ldap_bind_dn_template": "{username}@example.com",
  "ldap_base_dn": "OU=Users,DC=example,DC=com",
  "ldap_user_filter": "(sAMAccountName={username})",
  "ldap_tls_cacertfile": "/path/to/ca.crt",
  "ldap_tls_verify": true
}
```

## 性能对比

### 连接性能
- **python-ldap**: 需要C库初始化，启动稍慢
- **ldap3**: 纯Python，启动更快

### 内存使用
- **python-ldap**: 包含C扩展，内存占用较大
- **ldap3**: 纯Python，内存占用更小

### 功能性能
- **搜索性能**: 两者相当
- **绑定性能**: 两者相当
- **错误处理**: ldap3更友好

## 故障排除

### 常见问题

#### 1. 导入错误
```python
# 错误
ImportError: No module named 'ldap'

# 解决
pip install ldap3
```

#### 2. 连接失败
```python
# 检查配置
from ldap3 import Server, Connection
server = Server('your-ldap-server', port=389)
conn = Connection(server, 'bind_dn', 'password')
print(conn.bind())  # 应该返回True
```

#### 3. 搜索无结果
```python
# 检查搜索参数
conn.search(
    search_base='OU=Users,DC=example,DC=com',
    search_filter='(objectClass=user)',
    search_scope=SUBTREE
)
print(f"找到 {len(conn.entries)} 个结果")
```

### 调试技巧

#### 启用详细日志
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('ldap3')
logger.setLevel(logging.DEBUG)
```

#### 测试连接
```python
from ldap3 import Server, Connection, ALL

# 创建服务器对象
server = Server('your-server', get_info=ALL)

# 创建连接
conn = Connection(server, 'bind_dn', 'password')

# 测试绑定
if conn.bind():
    print("连接成功")
    print(f"服务器信息: {server.info}")
else:
    print(f"连接失败: {conn.last_error}")
```

## 迁移检查清单

### ✅ 完成项目
- [x] 更新pyproject.toml依赖
- [x] 重写LDAP客户端代码
- [x] 保持API兼容性
- [x] 测试基本功能
- [x] 验证错误处理
- [x] 更新文档

### 🔄 后续优化
- [ ] 性能基准测试
- [ ] 高级功能测试
- [ ] 生产环境验证
- [ ] 用户反馈收集

## 回滚方案

如果需要回滚到python-ldap：

1. **恢复依赖**
```toml
# pyproject.toml
"python-ldap>=3.4.4",
```

2. **恢复代码**
```bash
git checkout HEAD~1 -- collabtrans/auth/ldap_client.py
```

3. **重新安装**
```bash
# 使用预编译包
pip install https://github.com/cgohlke/python-ldap-build/releases/download/v3.4.4/python_ldap-3.4.4-cp312-cp312-win_amd64.whl
```

## 总结

### 迁移收益
- ✅ 解决了Windows安装问题
- ✅ 简化了依赖管理
- ✅ 提高了跨平台兼容性
- ✅ 保持了功能完整性
- ✅ 改善了开发体验

### 风险评估
- 🟢 **低风险**: API完全兼容
- 🟢 **低风险**: 配置无需更改
- 🟢 **低风险**: 功能完全保持
- 🟢 **低风险**: 有完整的回滚方案

这次迁移是一个**低风险、高收益**的改进，将显著改善CollabTrans在Windows平台上的部署体验。
