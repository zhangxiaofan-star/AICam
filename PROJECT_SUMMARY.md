# LightRAG + Neo4j 知识图谱项目

## 项目概述
本项目实现了两个核心功能：
1. 将 `dataset` 目录下的 CSV 文件转换为 Neo4j 知识图谱
2. 通过 LightRAG 检索方式从 Neo4j 知识库中检索并回答问题

## 项目文件结构
```
ZCW-ZQG/
├── dataset/                    # 数据源目录
│   ├── processes.csv          # 工艺数据
│   └── tools.csv              # 刀具数据
├── config.ini                 # 统一配置文件
├── csv_to_neo4j.py           # CSV转Neo4j功能
├── lightrag_retrieval.py     # LightRAG检索功能
└── PROJECT_SUMMARY.md        # 项目说明
```

## 核心功能

### 1. CSV转Neo4j知识图谱 (`csv_to_neo4j.py`)
- 读取 `dataset/processes.csv` 和 `dataset/tools.csv`
- 创建特征、工艺、刀具、工艺类型节点
- 建立节点间的关系
- 创建索引优化查询性能

**使用方法：**
```bash
python csv_to_neo4j.py
```

### 2. LightRAG检索系统 (`lightrag_retrieval.py`)
- 连接Neo4j知识图谱
- 使用派欧云大模型进行推理
- 支持自然语言问答
- 提供备用查询方案

**使用方法：**
```bash
echo "特征类型都有哪些？" | python lightrag_retrieval.py
```

## 配置说明 (`config.ini`)

### Neo4j数据库配置
```ini
[neo4j]
uri = bolt://localhost:7687
username = neo4j
password = zxfneo4j
```

### 派欧云API配置
```ini
[paiyun_api]
api_key = your_api_key_here
base_url = https://api.ppinfra.com/v1
model = qwen/qwen3-32b-fp8
```

### 嵌入模型配置
```ini
[embedding]
api_key = your_embedding_api_key
base_url = https://api.siliconflow.cn/v1
model = BAAI/bge-m3
```

### 系统配置
```ini
[system]
lightrag_working_dir = ./lightrag_storage
log_dir = ./logs
log_max_bytes = 10485760
log_backup_count = 5
verbose_debug = false
```

## 数据结构

### 知识图谱节点类型
- **Feature**: 特征节点（如矩形凸台、圆柱凸台等）
- **Process**: 工艺节点（包含工序阶段、面类型等信息）
- **Tool**: 刀具节点（包含直径、R角、刃数等信息）
- **ProcessType**: 工艺类型节点（如粗加工、精加工等）

### 关系类型
- `HAS_PROCESS`: 特征与工艺的关系
- `USES_TOOL`: 工艺与刀具的关系
- `BELONGS_TO`: 工艺与工艺类型的关系

## 运行要求
- Python 3.8+
- Neo4j数据库
- 网络连接（用于API调用）
- 必要的Python包（系统会自动安装）

## 成功运行示例
1. CSV转换成功：创建了28个特征节点、270个工艺节点、13个刀具节点
2. 检索系统成功回答问题，提供了完整的特征类型分类

## 注意事项
- 确保Neo4j数据库正在运行
- 配置正确的API密钥
- 系统具备自动容错和备用方案