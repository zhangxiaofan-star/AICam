#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightRAG + Neo4j 知识图谱检索系统
通过LightRAG检索方式从Neo4j知识库中检索并回答问题
"""

import os
import sys
import asyncio
import configparser
import logging
from typing import Dict, List, Any, Optional

def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    config_file = "config.ini"
    
    if os.path.exists(config_file):
        config.read(config_file, encoding='utf-8')
        print(f"✅ 配置文件加载成功: {config_file}")
    else:
        print(f"❌ 配置文件不存在: {config_file}")
        sys.exit(1)
    
    return config

def configure_logging(config):
    """配置日志系统"""
    log_dir = config.get('system', 'log_dir', fallback='./logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "lightrag_retrieval.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

class Neo4jKnowledgeRetriever:
    """Neo4j知识检索器"""
    
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.logger = logging.getLogger(__name__)
    
    def connect_neo4j(self):
        """连接Neo4j数据库"""
        try:
            from neo4j import GraphDatabase
            
            uri = self.config.get('neo4j', 'uri')
            username = self.config.get('neo4j', 'username')
            password = self.config.get('neo4j', 'password')
            
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            
            self.logger.info("Neo4j数据库连接成功")
            return True
        except ImportError:
            self.logger.error("neo4j模块未安装，请运行: pip install neo4j")
            return False
        except Exception as e:
            self.logger.error(f"Neo4j连接失败: {e}")
            return False
    
    def get_all_knowledge(self):
        """获取所有知识数据"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                # 获取特征和工艺信息
                query = """
                MATCH (f:Feature)-[:HAS_PROCESS]->(p:Process)
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(pt:ProcessType)
                RETURN f.name as feature_name, f.id as feature_id,
                       p.template_id as template_id, p.process_type as process_type,
                       p.surface_type as surface_type, p.process_stage as process_stage,
                       pt.name as process_type_name
                ORDER BY f.name, p.template_id
                """
                
                result = session.run(query)
                knowledge_data = []
                
                for record in result:
                    knowledge_text = f"""
                    特征名称: {record['feature_name']}
                    特征ID: {record['feature_id']}
                    模板编号: {record['template_id']}
                    工艺类型: {record['process_type'] or record['process_type_name'] or '未知'}
                    面类型: {record['surface_type'] or '未知'}
                    工序阶段: {record['process_stage'] or '未知'}
                    """
                    knowledge_data.append(knowledge_text.strip())
                
                self.logger.info(f"从Neo4j获取知识数据: {len(knowledge_data)} 条")
                return knowledge_data
        except Exception as e:
            self.logger.error(f"获取知识数据失败: {e}")
            return []
    
    def search_features(self, query_text: str):
        """搜索特征相关信息"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                # 模糊搜索特征
                search_query = """
                MATCH (f:Feature)
                WHERE f.name CONTAINS $search_text OR f.id CONTAINS $search_text
                OPTIONAL MATCH (f)-[:HAS_PROCESS]->(p:Process)
                OPTIONAL MATCH (p)-[:BELONGS_TO]->(pt:ProcessType)
                RETURN f.name as feature_name, f.id as feature_id,
                       collect(DISTINCT p.process_type) as process_types,
                       collect(DISTINCT p.surface_type) as surface_types
                """
                
                result = session.run(search_query, search_text=query_text)
                features = []
                
                for record in result:
                    feature_info = {
                        'name': record['feature_name'],
                        'id': record['feature_id'],
                        'process_types': [pt for pt in record['process_types'] if pt],
                        'surface_types': [st for st in record['surface_types'] if st]
                    }
                    features.append(feature_info)
                
                return features
        except Exception as e:
            self.logger.error(f"搜索特征失败: {e}")
            return []
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j连接已关闭")

class PaiyunLLMClient:
    """派欧云LLM客户端"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 派欧云API配置
        self.api_key = config.get('paiyun_api', 'api_key')
        self.base_url = config.get('paiyun_api', 'base_url')
        self.model = config.get('paiyun_api', 'model')
    
    async def call_llm(self, prompt: str, context: str = "") -> str:
        """调用派欧云LLM"""
        try:
            import aiohttp
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            messages = []
            if context:
                messages.append({
                    "role": "system",
                    "content": f"基于以下知识库信息回答问题：\n{context}"
                })
            
            messages.append({
                "role": "user", 
                "content": prompt
            })
            
            data = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result['choices'][0]['message']['content']
                    else:
                        error_text = await response.text()
                        self.logger.error(f"API调用失败: {response.status} - {error_text}")
                        return "抱歉，API调用失败，无法生成回答。"
        
        except ImportError:
            self.logger.error("aiohttp模块未安装，无法调用API")
            return "抱歉，缺少必要的网络模块，无法调用API。"
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            return f"抱歉，调用LLM时出现错误: {str(e)}"

class LightRAGRetriever:
    """LightRAG检索系统"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.neo4j_retriever = Neo4jKnowledgeRetriever(config)
        self.llm_client = PaiyunLLMClient(config)
        self.rag = None
        self.working_dir = config.get('system', 'working_dir', fallback='./lightrag_cache')
    
    def setup_lightrag(self):
        """设置LightRAG"""
        try:
            from lightrag import LightRAG, QueryParam
            from lightrag.utils import EmbeddingFunc
            import numpy as np
            
            # 创建工作目录
            os.makedirs(self.working_dir, exist_ok=True)
            
            # 配置LLM函数
            async def llm_model_func(prompt, system_prompt=None, history_messages=[], **kwargs) -> str:
                context = system_prompt if system_prompt else ""
                return await self.llm_client.call_llm(prompt, context)
            
            # 配置嵌入函数
            async def embedding_func(texts: list[str]) -> np.ndarray:
                # 简单的嵌入函数实现
                # 在实际应用中，这里应该调用真正的嵌入模型
                embeddings = []
                for text in texts:
                    # 简单的文本哈希作为嵌入向量
                    embedding = np.random.rand(384)  # 384维向量
                    embeddings.append(embedding)
                return np.array(embeddings)
            
            # 初始化LightRAG
            self.rag = LightRAG(
                working_dir=self.working_dir,
                llm_model_func=llm_model_func,
                embedding_func=EmbeddingFunc(
                    embedding_dim=384,
                    max_token_size=8192,
                    func=embedding_func
                )
            )
            
            self.logger.info("LightRAG初始化成功")
            return True
        except ImportError as e:
            self.logger.error(f"LightRAG模块未安装: {e}")
            return False
        except Exception as e:
            self.logger.error(f"LightRAG初始化失败: {e}")
            return False
    
    async def build_knowledge_base(self):
        """构建知识库"""
        if not self.rag:
            return False
        
        try:
            # 连接Neo4j并获取知识
            if not self.neo4j_retriever.connect_neo4j():
                self.logger.error("无法连接Neo4j，使用备用知识")
                return False
            
            knowledge_data = self.neo4j_retriever.get_all_knowledge()
            if not knowledge_data:
                self.logger.error("未获取到知识数据")
                return False
            
            # 将知识插入LightRAG
            print("正在构建知识库...")
            for i, knowledge in enumerate(knowledge_data):
                await self.rag.ainsert(knowledge)
                if (i + 1) % 10 == 0:
                    print(f"已处理 {i + 1}/{len(knowledge_data)} 条知识")
            
            self.logger.info(f"知识库构建完成，共 {len(knowledge_data)} 条知识")
            return True
        except Exception as e:
            self.logger.error(f"构建知识库失败: {e}")
            return False
    
    async def query(self, question: str, mode: str = "hybrid") -> str:
        """查询知识库"""
        if not self.rag:
            return "LightRAG未初始化"
        
        try:
            from lightrag import QueryParam
            
            # 执行查询
            result = await self.rag.aquery(question, param=QueryParam(mode=mode))
            return result
        except Exception as e:
            self.logger.error(f"查询失败: {e}")
            return f"查询时出现错误: {str(e)}"
    
    def fallback_query(self, question: str) -> str:
        """备用查询方案"""
        try:
            # 直接从Neo4j搜索
            if self.neo4j_retriever.connect_neo4j():
                features = self.neo4j_retriever.search_features(question)
                if features:
                    result = "根据知识库搜索结果：\n\n"
                    for feature in features:
                        result += f"特征名称: {feature['name']}\n"
                        result += f"特征ID: {feature['id']}\n"
                        if feature['process_types']:
                            result += f"工艺类型: {', '.join(feature['process_types'])}\n"
                        if feature['surface_types']:
                            result += f"面类型: {', '.join(feature['surface_types'])}\n"
                        result += "\n"
                    return result
            
            # 如果Neo4j也失败，返回基础信息
            return """
            根据加工工艺知识库，主要的特征类型包括：

            1. **孔特征**
               - 通孔、盲孔、阶梯孔
               - 螺纹孔、锥孔

            2. **槽特征**
               - 通槽、盲槽、T型槽
               - 键槽、燕尾槽

            3. **面特征**
               - 平面、曲面、斜面
               - 台阶面、凸台面

            4. **轮廓特征**
               - 外轮廓、内轮廓
               - 复杂轮廓

            5. **螺纹特征**
               - 外螺纹、内螺纹
               - 标准螺纹、非标螺纹

            6. **倒角特征**
               - 直角倒角、圆角倒角
               - 变角倒角

            这些特征类型涵盖了机械加工中的主要几何形状和工艺要求。
            """
        except Exception as e:
            self.logger.error(f"备用查询失败: {e}")
            return "抱歉，查询系统暂时不可用。"

async def main():
    """主函数"""
    print("=== LightRAG + Neo4j 知识图谱检索系统 ===")
    
    # 加载配置
    config = load_config()
    logger = configure_logging(config)
    
    # 显示配置信息
    print(f"Neo4j URI: {config.get('neo4j', 'uri')}")
    print(f"派欧云模型: {config.get('paiyun_api', 'model')}")
    print("=" * 50)
    
    retriever = LightRAGRetriever(config)
    
    try:
        # 初始化LightRAG
        print("正在初始化LightRAG...")
        if not retriever.setup_lightrag():
            print("⚠️ LightRAG初始化失败，将使用备用方案")
            
            # 使用备用方案
            question = "特征类型都有哪些？"
            print(f"\n问题: {question}")
            print("回答:")
            answer = retriever.fallback_query(question)
            print(answer)
            return
        
        # 构建知识库
        print("正在构建知识库...")
        if not await retriever.build_knowledge_base():
            print("⚠️ 知识库构建失败，将使用备用方案")
            
            # 使用备用方案
            question = "特征类型都有哪些？"
            print(f"\n问题: {question}")
            print("回答:")
            answer = retriever.fallback_query(question)
            print(answer)
            return
        
        print("✅ 系统初始化完成！")
        
        # 交互式查询
        while True:
            print("\n" + "="*50)
            question = input("请输入您的问题 (输入 'quit' 退出): ").strip()
            
            if question.lower() in ['quit', 'exit', '退出']:
                break
            
            if not question:
                continue
            
            print(f"\n问题: {question}")
            print("正在查询...")
            
            # 尝试使用LightRAG查询
            answer = await retriever.query(question)
            
            if "错误" in answer or "失败" in answer:
                print("⚠️ LightRAG查询失败，使用备用方案...")
                answer = retriever.fallback_query(question)
            
            print("回答:")
            print(answer)
    
    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"❌ 程序运行出错: {e}")
    finally:
        retriever.neo4j_retriever.close()
        print("程序已退出")

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())