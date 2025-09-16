# 敏感配置管理

DocuTranslate 使用分离的配置文件来管理敏感信息，确保API密钥等敏感数据不会被提交到代码仓库。

## 配置文件结构

### 1. 公共配置文件（提交到git）
- `global_config.json` - 全局配置，不包含敏感信息
- `auth_config.json` - 认证配置，不包含敏感信息

### 2. 敏感配置文件（不提交到git）
- `local_secrets.json` - 本地敏感配置，包含API密钥等
- `local_secrets.json.template` - 配置模板文件

## 首次部署配置

### 方法1：使用初始化脚本（推荐）

```bash
# 运行配置初始化脚本
python3 setup_secrets.py
```

脚本会引导您配置：
- 各平台的API密钥
- MinerU令牌
- 默认管理员密码
- 会话密钥
- Redis密码（可选）

### 方法2：手动配置

1. 复制模板文件：
```bash
cp local_secrets.json.template local_secrets.json
```

2. 编辑 `local_secrets.json`，填入真实的API密钥：
```json
{
  "platform_api_keys": {
    "openai": "sk-your-openai-api-key-here",
    "deepseek": "sk-your-deepseek-api-key-here",
    "anthropic": "sk-your-anthropic-api-key-here"
  },
  "translator_mineru_token": "your-mineru-token-here",
  "auth_secrets": {
    "default_password": "your-secure-admin-password",
    "session_secret_key": "your-very-long-random-session-secret-key",
    "redis_password": "your-redis-password-if-needed"
  }
}
```

## 配置说明

### API密钥配置
支持以下平台的API密钥：
- `openai` - OpenAI API
- `azure` - Azure OpenAI
- `anthropic` - Anthropic Claude
- `google` - Google Gemini
- `mistral` - Mistral AI
- `cohere` - Cohere
- `xai` - xAI Grok
- `groq` - Groq
- `together` - Together AI
- `deepseek` - DeepSeek
- `dashscope` - 阿里云通义千问
- `volcengine_ark` - 字节跳动豆包
- `siliconflow` - SiliconFlow
- `zhipu` - 智谱AI
- `dmxapi` - DMX API
- `custom` - 自定义平台

### 认证配置
- `default_password` - 默认管理员密码
- `session_secret_key` - 会话加密密钥（建议使用随机字符串）
- `redis_password` - Redis密码（如果使用密码保护）

## 安全注意事项

1. **文件权限**：确保 `local_secrets.json` 文件权限设置为仅所有者可读写：
   ```bash
   chmod 600 local_secrets.json
   ```

2. **备份安全**：备份时不要包含敏感配置文件

3. **环境变量**：生产环境建议使用环境变量覆盖敏感配置：
   ```bash
   export OPENAI_API_KEY="your-key-here"
   export DEEPSEEK_API_KEY="your-key-here"
   ```

4. **定期轮换**：定期更换API密钥和会话密钥

## Web界面配置

管理员登录后，可以在Web界面的"登入设置"中：
- 查看当前配置状态
- 更新API密钥（会保存到 `local_secrets.json`）
- 修改认证相关设置

## 故障排除

### 配置文件不存在
如果 `local_secrets.json` 不存在，系统会使用默认配置。建议运行初始化脚本创建配置文件。

### 权限问题
确保应用有权限读取 `local_secrets.json` 文件：
```bash
ls -la local_secrets.json
```

### 配置不生效
1. 检查配置文件格式是否正确（JSON格式）
2. 重启应用服务
3. 查看应用日志确认配置加载状态

## 迁移现有配置

如果您已有包含敏感信息的配置文件，可以按以下步骤迁移：

1. 备份现有配置
2. 运行初始化脚本或手动创建 `local_secrets.json`
3. 将敏感信息从旧配置文件复制到新文件
4. 更新 `.gitignore` 确保敏感文件不被提交
5. 删除旧配置文件中的敏感信息
