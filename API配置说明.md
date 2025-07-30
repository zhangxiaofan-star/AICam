# API配置说明

## 配置步骤

### 1. 选择API服务商

你可以选择以下任一API服务商：

#### OpenAI官方 (推荐，但需要海外网络)
- 注册地址: https://platform.openai.com/
- 获取API密钥: https://platform.openai.com/account/api-keys
- 配置示例:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
EMBEDDING_MODEL=text-embedding-ada-002
```

#### 智谱AI (国内，支持GLM模型)
- 注册地址: https://open.bigmodel.cn/
- 获取API密钥: 控制台 -> API密钥管理
- 配置示例:
```
OPENAI_API_KEY=your_zhipu_api_key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
OPENAI_MODEL=glm-4
EMBEDDING_MODEL=embedding-2
```

#### 阿里云百炼 (国内，支持通义千问)
- 注册地址: https://dashscope.aliyun.com/
- 获取API密钥: 控制台 -> API-KEY管理
- 配置示例:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
OPENAI_MODEL=qwen-turbo
EMBEDDING_MODEL=text-embedding-v1
```

#### 硅基流动 (国内，免费额度较多)
- 注册地址: https://siliconflow.cn/
- 获取API密钥: 控制台 -> API密钥
- 配置示例:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_MODEL=Qwen/Qwen2.5-7B-Instruct
EMBEDDING_MODEL=BAAI/bge-m3
```

#### 月之暗面 (Kimi)
- 注册地址: https://platform.moonshot.cn/
- 获取API密钥: 控制台 -> API Key
- 配置示例:
```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.moonshot.cn/v1
OPENAI_MODEL=moonshot-v1-8k
EMBEDDING_MODEL=moonshot-v1-8k
```

### 2. 配置.env文件

1. 打开项目根目录下的 `.env` 文件
2. 找到你选择的API服务商对应的配置部分
3. 取消注释（删除行首的 `#`）
4. 将 `your_xxx_api_key` 替换为你的实际API密钥

### 3. 验证配置

运行测试脚本验证配置是否正确：

```bash
python test_lightrag_updated.py
```

如果看到 "✅ 查询成功" 的提示，说明配置正确。

## 注意事项

1. **API密钥安全**: 不要将API密钥提交到版本控制系统中
2. **费用控制**: 建议在API服务商控制台设置使用限额
3. **网络环境**: 国外API服务可能需要稳定的网络环境
4. **模型选择**: 不同服务商的模型能力和费用不同，请根据需求选择

## 推荐配置

对于国内用户，推荐使用以下配置：

### 硅基流动 (免费额度多，适合测试)
```
OPENAI_API_KEY=你的硅基流动API密钥
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_MODEL=Qwen/Qwen2.5-7B-Instruct
EMBEDDING_MODEL=BAAI/bge-m3
```

### 智谱AI (模型质量好，适合生产)
```
OPENAI_API_KEY=你的智谱AI密钥
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
OPENAI_MODEL=glm-4
EMBEDDING_MODEL=embedding-2
```

配置完成后，你就可以正常使用LightRAG知识图谱检索系统了！