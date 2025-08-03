#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo4j + 派欧云API 知识图谱检索系统
基于Neo4j知识库和派欧云API的智能问答系统
"""

import os
import sys
import asyncio
import configparser
import logging
from neo4j import GraphDatabase


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
    log_file_path = os.path.join(log_dir, "neo4j_retrieval.log")
    
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
    
    def get_all_features(self):
        """获取所有特征类型"""
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                query = """
                    MATCH (f:Feature)
                    RETURN DISTINCT f.name as feature_name, f.id as feature_id
                    ORDER BY f.name
                """
                
                result = session.run(query)
                features = []
                
                for record in result:
                    features.append({
                        'name': record['feature_name'],
                        'id': record['feature_id']
                    })
                
                return features
        except Exception as e:
            self.logger.error(f"获取特征类型失败: {e}")
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


class IntelligentRetriever:
    """智能检索系统 - Neo4j + 派欧云API"""
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.neo4j_retriever = Neo4jKnowledgeRetriever(config)
        self.llm_client = PaiyunLLMClient(config)
    
    def initialize(self):
        """初始化检索系统"""
        try:
            # 连接Neo4j数据库
            if not self.neo4j_retriever.connect_neo4j():
                self.logger.error("Neo4j数据库连接失败")
                return False
            
            self.logger.info("智能检索系统初始化成功")
            return True
        except Exception as e:
            self.logger.error(f"检索系统初始化失败: {e}")
            return False
    
    async def query(self, question: str) -> str:
        """智能查询"""
        try:
            self.logger.info(f"收到查询: {question}")
            
            # 获取知识上下文
            knowledge_context = ""
            
            # 获取所有知识作为上下文
            all_knowledge = self.neo4j_retriever.get_all_knowledge()
            if all_knowledge:
                # 取前15条知识作为上下文
                knowledge_context = "\n".join(all_knowledge[:15])
                self.logger.info(f"获取到 {len(all_knowledge)} 条知识，使用前15条作为上下文")
            
            # 搜索特定特征
            features = self.neo4j_retriever.search_features(question)
            if features:
                feature_info = "相关特征信息：\n"
                for feature in features[:8]:  # 限制为前8个特征
                    feature_info += f"- {feature['name']} (ID: {feature['id']})\n"
                    if feature['process_types']:
                        feature_info += f"  工艺类型: {', '.join(feature['process_types'])}\n"
                    if feature['surface_types']:
                        feature_info += f"  面类型: {', '.join(feature['surface_types'])}\n"
                knowledge_context = feature_info + "\n" + knowledge_context
            
            # 使用派欧云API进行智能回答
            if knowledge_context:
                try:
                    system_prompt = """你是一个加工工艺专家。请基于提供的知识库信息回答用户问题。
                    要求：
                    1. 严格基于提供的知识库内容回答
                    2. 回答要准确、简洁、结构化
                    3. 如果知识库中没有相关信息，请明确说明
                    4. 使用中文回答
                    5. 对于特征类型问题，请列出所有相关的特征类型"""
                    
                    prompt = f"知识库内容：\n{knowledge_context}\n\n用户问题：{question}\n\n请基于上述知识库内容回答问题："
                    
                    answer = await self.llm_client.call_llm(prompt, system_prompt)
                    if answer and len(answer.strip()) > 10:
                        return answer
                except Exception as api_error:
                    self.logger.error(f"派欧云API调用失败: {api_error}")
            
            # 如果API调用失败，返回基于Neo4j的结构化答案
            return self._generate_structured_answer(question)
            
        except Exception as e:
            self.logger.error(f"查询失败: {e}")
            return "抱歉，查询系统暂时不可用。"
    
    def _generate_structured_answer(self, question: str) -> str:
        """生成结构化答案"""
        try:
            # 特征类型相关问题
            if "特征类型" in question or "特征" in question:
                features = self.neo4j_retriever.get_all_features()
                if features:
                    result = "根据知识库，加工工艺中的特征类型包括：\n\n"
                    
                    # 按特征名称分组
                    feature_dict = {}
                    for feature in features:
                        name = feature['name']
                        feature_id = feature['id']
                        if name not in feature_dict:
                            feature_dict[name] = []
                        feature_dict[name].append(feature_id)
                    
                    # 输出特征类型
                    for i, (name, ids) in enumerate(sorted(feature_dict.items()), 1):
                        result += f"{i}. **{name}**\n"
                        result += f"   - 特征ID: {', '.join(map(str, ids))}\n\n"
                    
                    result += f"共发现 {len(feature_dict)} 种不同的特征类型，{len(features)} 个具体特征实例。"
                    return result
            
            # 工艺相关问题
            elif "工艺" in question:
                all_knowledge = self.neo4j_retriever.get_all_knowledge()
                if all_knowledge:
                    # 提取工艺类型信息
                    process_types = set()
                    process_stages = set()
                    
                    for knowledge in all_knowledge:
                        if "工艺类型:" in knowledge:
                            process_type = knowledge.split("工艺类型:")[1].split("\n")[0].strip()
                            if process_type and process_type != "未知":
                                process_types.add(process_type)
                        
                        if "工序阶段:" in knowledge:
                            process_stage = knowledge.split("工序阶段:")[1].split("\n")[0].strip()
                            if process_stage and process_stage != "未知":
                                process_stages.add(process_stage)
                    
                    result = "根据知识库，加工工艺信息包括：\n\n"
                    
                    if process_types:
                        result += "**工艺类型：**\n"
                        for i, ptype in enumerate(sorted(process_types), 1):
                            result += f"{i}. {ptype}\n"
                        result += "\n"
                    
                    if process_stages:
                        result += "**工序阶段：**\n"
                        for i, stage in enumerate(sorted(process_stages), 1):
                            result += f"{i}. {stage}\n"
                        result += "\n"
                    
                    result += f"基于 {len(all_knowledge)} 条知识记录分析得出。"
                    return result
            
            # 默认回答
            return "根据知识库内容，我可以为您提供加工工艺特征类型、工艺流程等相关信息。请具体询问您想了解的内容。"
            
        except Exception as e:
            self.logger.error(f"生成结构化答案失败: {e}")
            return "抱歉，无法生成答案。"


async def main():
    """主函数"""
    print("=== Neo4j + 派欧云API 知识图谱检索系统 ===")
    
    # 加载配置
    config = load_config()
    logger = configure_logging(config)
    
    # 显示配置信息
    print(f"Neo4j URI: {config.get('neo4j', 'uri')}")
    print(f"派欧云模型: {config.get('paiyun_api', 'model')}")
    print("=" * 50)
    
    retriever = IntelligentRetriever(config)
    question = 'V形通槽的工艺类型是什么？'
    try:
        # 初始化检索系统
        print("正在初始化检索系统...")
        if not retriever.initialize():
            print("❌ 检索系统初始化失败")
            return
        
        print("✅ Neo4j + 派欧云API 检索系统初始化成功")
        print("✅ 系统已就绪，可以开始查询！")
        

        if question:
            print(f"\n问题: {question}")
            print("回答:")
            answer = await retriever.query(question)
            print(answer)
            return
        
        # # 交互式查询模式
        # print("\n" + "="*50)
        # print("进入交互式查询模式 (输入 'quit' 退出)")
        # print("="*50)
        
        # while True:
        #     try:
        #         question = input("\n请输入您的问题: ").strip()
                
        #         if question.lower() in ['quit', 'exit', '退出', 'q']:
        #             break
                
        #         if not question:
        #             continue
                
        #         print(f"\n问题: {question}")
        #         print("正在查询...")
                
        #         answer = await retriever.query(question)
                
        #         print("回答:")
        #         print(answer)
                
        #     except EOFError:
        #         break
        #     except KeyboardInterrupt:
        #         print("\n\n用户中断查询")
        #         break
    
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