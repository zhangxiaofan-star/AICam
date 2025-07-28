# 加工工艺知识图谱系统使用说明

## 系统概述

本系统包含两个主要组件：
1. **CSV转Neo4j知识图谱** (`csv_to_neo4j.py`) - 将工艺和刀具数据转换为Neo4j图数据库
2. **LightRAG知识检索** (`lightrag_retrieval.py`) - 基于LightRAG的智能问答检索系统

## 环境准备

### 1. Python环境
已创建conda虚拟环境 `py310`，包含所需依赖：
- neo4j==5.28.1
- pandas==2.3.1
- lightrag==0.1.0b6
- openai==1.97.1
- python-dotenv==1.1.1

### 2. Neo4j数据库
需要安装并启动Neo4j数据库：
- 下载地址：https://neo4j.com/download/
- 默认端口：7687
- 默认用户名：neo4j
- 需要设置密码

### 3. OpenAI API
LightRAG需要OpenAI API进行文本处理：
- 获取API Key：https://platform.openai.com/
- 在`.env`文件中配置

## 配置文件

编辑 `.env` 文件，配置以下参数：

```env
# Neo4j数据库配置
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password

# OpenAI API配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_BASE_URL=https://api.openai.com/v1

# LightRAG配置
LIGHTRAG_WORKING_DIR=./lightrag_cache
```

## 使用步骤

### 步骤1：启动Neo4j数据库
1. 启动Neo4j Desktop或Neo4j服务
2. 确保数据库运行在 `bolt://localhost:7687`
3. 记录用户名和密码

### 步骤2：构建Neo4j知识图谱
```bash
# 激活conda环境
conda activate py310

# 运行知识图谱构建脚本
python csv_to_neo4j.py
```

该脚本将：
- 读取 `dataset/processes.csv` 和 `dataset/tools.csv`
- 创建节点：Process（工艺）、Tool（刀具）、Feature（特征）、Surface（面）、ProcessType（工艺类型）、ProcessStage（工序阶段）
- 建立关系：工艺-特征、工艺-面类型、工艺-工艺类型、工艺-工序阶段、刀具-工艺推荐
- 输出统计信息

### 步骤3：使用LightRAG检索系统
```bash
# 运行检索系统
python lightrag_retrieval.py
```

首次运行会构建知识库，后续运行直接使用已有数据。

## 功能特性

### Neo4j知识图谱功能
- **节点类型**：
  - Process：工艺模板
  - Tool：刀具
  - Feature：加工特征
  - Surface：面类型
  - ProcessType：工艺类型
  - ProcessStage：工序阶段

- **关系类型**：
  - PROCESSES：工艺处理特征
  - USES_SURFACE：工艺使用面类型
  - HAS_TYPE：工艺具有类型
  - IN_STAGE：工艺属于阶段
  - RECOMMENDED_FOR：刀具推荐用于工艺

### LightRAG检索功能
- **查询模式**：
  - `naive`：简单检索
  - `local`：局部图检索
  - `global`：全局图检索
  - `hybrid`：混合模式（推荐）

- **示例查询**：
  - "什么是矩形凸台的加工工艺？"
  - "精加工阶段适用哪些工艺类型？"
  - "直径为10mm的刀具有哪些？"
  - "如何选择合适的刀具进行圆柱通孔加工？"

## 数据结构

### 工艺数据 (processes.csv)
- 模板编号：工艺模板唯一标识
- 特征ID：加工特征标识
- 特征名称：特征类型名称
- 组成面：特征组成面信息
- 特征面：特征面信息
- 面类型：面的几何类型
- 侧壁特征：是否有侧壁特征
- 余量：加工余量
- 工序阶段：粗加工/半精加工/精加工
- 工艺类型：具体工艺方法

### 刀具数据 (tools.csv)
- 刀具id：刀具唯一标识
- 刀具名称：刀具型号名称
- 直径：刀具直径(mm)
- R角：刀具圆角半径(mm)
- 刃数：刀具刃数
- 伸出长：刀具伸出长度(mm)

## 故障排除

### 常见问题
1. **Neo4j连接失败**
   - 检查Neo4j服务是否启动
   - 验证连接参数（URI、用户名、密码）
   - 确认防火墙设置

2. **OpenAI API错误**
   - 检查API Key是否正确
   - 验证账户余额
   - 确认网络连接

3. **数据加载失败**
   - 检查CSV文件路径
   - 验证文件编码（UTF-8）
   - 确认数据格式

### 日志信息
系统会输出详细的日志信息，帮助诊断问题：
- INFO：正常操作信息
- WARNING：警告信息
- ERROR：错误信息

## 扩展功能

### 自定义查询
可以在Neo4j Browser中执行Cypher查询：
```cypher
// 查询所有精加工工艺
MATCH (p:Process)-[:IN_STAGE]->(ps:ProcessStage {name: '精加工'})
RETURN p

// 查询推荐刀具
MATCH (t:Tool)-[:RECOMMENDED_FOR]->(p:Process)
RETURN t.name, p.template_id
```

### 添加新数据
1. 更新CSV文件
2. 重新运行 `csv_to_neo4j.py`
3. 重新构建LightRAG知识库

## 技术架构

```
CSV数据 → Neo4j知识图谱 ← Cypher查询
    ↓
LightRAG知识库 → 向量检索 → 智能问答
    ↑
OpenAI API
```

## 联系支持

如有问题，请检查：
1. 环境配置是否正确
2. 依赖包是否完整安装
3. 服务是否正常运行
4. 日志错误信息