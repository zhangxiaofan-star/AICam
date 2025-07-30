# LightRAG + Neo4j 知识图谱系统

## 项目概述

本项目包含两个核心功能：
1. **CSV转Neo4j知识图谱** - 将dataset目录下的CSV文件转换为Neo4j知识图谱
2. **LightRAG检索系统** - 通过LightRAG从Neo4j知识库中检索并回答问题

## 文件说明

- `csv_to_neo4j.py` - CSV数据转Neo4j知识图谱转换器
- `lightrag_retrieval.py` - LightRAG + Neo4j 检索系统
- `config.ini` - 系统配置文件
- `dataset/` - CSV数据文件目录
  - `processes.csv` - 工艺数据
  - `tools.csv` - 刀具数据

## 配置说明

编辑 `config.ini` 文件，配置以下参数：

### Neo4j数据库配置
```ini
[neo4j]
uri = bolt://localhost:7687
username = neo4j
password = your_password
```

### 派欧云API配置
```ini
[paiyun_api]
api_key = your_api_key
base_url = https://api.ppinfra.com/v1
model = qwen/qwen3-32b-fp8
```

## 使用方法

### 1. 转换CSV到Neo4j

```bash
python csv_to_neo4j.py
```

这将：
- 连接到Neo4j数据库
- 清空现有数据
- 读取dataset目录下的CSV文件
- 创建特征、工艺、刀具节点
- 建立节点间的关系
- 创建索引优化查询性能

### 2. 运行检索系统

```bash
python lightrag_retrieval.py
```

这将：
- 初始化LightRAG系统
- 从Neo4j加载知识数据
- 构建知识库
- 提供交互式问答界面

## 系统特性

- **多层备用方案**: 当LightRAG或Neo4j连接失败时，自动切换到备用方案
- **配置化管理**: 所有关键参数通过config.ini统一管理
- **完整日志**: 详细的操作日志记录在logs目录下
- **错误处理**: 完善的异常处理和错误提示

## 依赖包

```bash
pip install pandas neo4j lightrag aiohttp configparser
```

## 注意事项

1. 确保Neo4j服务正在运行
2. 确保dataset目录下有processes.csv和tools.csv文件
3. 配置正确的派欧云API密钥
4. 首次运行时会清空Neo4j数据库

## 故障排除

- **Neo4j连接失败**: 检查Neo4j服务状态和配置
- **API调用失败**: 检查派欧云API密钥和网络连接
- **依赖包缺失**: 运行pip install安装所需包
- **CSV文件不存在**: 确保dataset目录下有正确的CSV文件