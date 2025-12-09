# LightRAG 加工工艺和刀具推荐系统使用说明

## 系统架构

本系统完全基于 **LightRAG** 架构，整合了大语言模型（LLM）和 Neo4j 知识图谱，实现智能的加工工艺和刀具推荐。

## 核心流程

### 1. 特征信息提取（LLM）
使用大模型从用户的自然语言问题中提取：
- **特征类型**：如"圆柱通孔"、"矩形凸台"等
- **特征面**：如"孔"、"平面"、"曲面"等
- **尺寸信息**：直径、长度、宽度、高度等

### 2. 知识图谱检索（Neo4j）
根据提取的特征信息，在 Neo4j 知识图谱中检索：
- 匹配的工艺模板
- 相关联的刀具信息
- 工艺阶段和类型

### 3. 智能选择（LLM + 知识图谱）
使用 LLM 结合知识图谱中的候选方案，智能选择最佳匹配：
- 特征类型匹配
- 特征面匹配
- 尺寸约束满足
- 工序阶段适配

### 4. 结果格式化
返回标准化的结果：
```json
{
    "process_template_id": "工艺模板ID",
    "tool_id": "刀具ID"
}
```

## 使用示例

### 代码调用

```python
import asyncio
from lightrag_retrieval import IntelligentRetriever, load_config

async def example():
    # 加载配置
    config = load_config()

    # 创建检索器
    retriever = IntelligentRetriever(config)
    retriever.initialize()

    # 提出问题
    question = '我现在有一个工件，他的特征类型是圆柱通孔，其中带孔的面中，孔直径是5mm，我想知道使用什么加工工艺和刀具进行加工？只需要给我一个工艺模板ID和刀具ID即可'

    # 获取推荐
    result = await retriever.query_machining_process_and_tool(question)

    # 输出结果
    print(f"工艺模板ID: {result['process_template_id']}")
    print(f"刀具ID: {result['tool_id']}")
    print(f"理由: {result['reason']}")

# 运行
asyncio.run(example())
```

### 运行脚本

```bash
python lightrag_retrieval.py
```

## 输出格式

### 详细输出
```json
{
    "process_template_id": "P001",
    "tool_id": "T123",
    "feature_info": {
        "feature_type": "圆柱通孔",
        "feature_surface": "孔",
        "dimensions": {
            "diameter": 5,
            "length": null,
            "width": null,
            "height": null
        }
    },
    "reason": "该方案最适合圆柱通孔的加工，特征面为孔，刀具直径满足尺寸要求",
    "all_candidates": [...]
}
```

### 简化输出
```json
{
    "process_template_id": "P001",
    "tool_id": "T123"
}
```

## 核心方法

### `query_machining_process_and_tool(question: str)`

主方法，完成整个 LightRAG 流程。

**参数**：
- `question`: 用户的自然语言问题

**返回**：
- `process_template_id`: 推荐的工艺模板ID
- `tool_id`: 推荐的刀具ID
- `feature_info`: 提取的特征信息
- `reason`: 选择理由
- `all_candidates`: 所有候选方案

### `extract_feature_info(question: str)`

从问题中提取特征信息（步骤1）。

### `lightrag_search_in_neo4j(...)`

在知识图谱中检索候选方案（步骤2）。

### `lightrag_select_best_match(...)`

使用 LLM 选择最佳匹配（步骤3）。

## 配置要求

需要在 `config.ini` 中配置：

```ini
[neo4j]
uri = bolt://localhost:7687
username = neo4j
password = your_password

[paiyun_api]
api_key = your_api_key
base_url = https://api.paiyun.com/v1
model = your_model_name

[system]
log_dir = ./logs
```

## 技术特点

1. **完全基于 LightRAG**：不使用硬编码规则，全部通过 LLM + 知识图谱实现
2. **自然语言理解**：支持各种表述方式的问题
3. **智能推理**：LLM 结合知识图谱进行推理决策
4. **可解释性**：提供选择理由和候选方案
5. **灵活扩展**：易于添加新的特征类型和工艺规则

## 注意事项

1. 确保 Neo4j 数据库已启动并包含工艺和刀具数据
2. 确保派欧云 API 密钥有效
3. 问题描述越详细，推荐结果越准确
4. 系统会自动记录日志到 `logs` 目录
