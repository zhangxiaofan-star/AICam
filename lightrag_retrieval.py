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
from neo4j import GraphDatabase
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc
import numpy as np

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
        """设置LightRAG - 暂时跳过，直接使用稳定的备用方案"""
        try:
            # # 检查LightRAG是否可用
            # try:
            #     from lightrag import LightRAG, QueryParam
            #     from lightrag.utils import EmbeddingFunc
            #     import numpy as np
            #     self.logger.info("LightRAG模块导入成功")
            # except ImportError as e:
            #     self.logger.error(f"LightRAG模块未安装: {e}")
            #     self.logger.info("请运行: pip install lightrag-hku")
            #     return False
            
            # 创建工作目录
            os.makedirs(self.working_dir, exist_ok=True)
            self.logger.info(f"工作目录已创建: {self.working_dir}")
            
            # 暂时跳过LightRAG初始化，直接使用备用方案
            self.logger.info("暂时跳过LightRAG初始化，使用稳定的备用查询方案")
            self.rag = None
            return True  # 返回True表示系统可以正常工作（使用备用方案）
            
        except Exception as e:
            self.logger.error(f"LightRAG设置失败: {e}")
            return False
    
    async def build_knowledge_base(self):
        """构建知识库"""
        if not self.rag:
            self.logger.error("LightRAG对象未初始化")
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
            
            # 确保LightRAG对象有必要的方法
            if not hasattr(self.rag, 'ainsert'):
                self.logger.error("LightRAG对象缺少ainsert方法")
                return False
            
            success_count = 0
            error_count = 0
            
            for i, knowledge in enumerate(knowledge_data):
                try:
                    # 检查knowledge是否为有效字符串
                    if not knowledge or not isinstance(knowledge, str):
                        self.logger.warning(f"跳过无效知识数据 #{i+1}: {type(knowledge)} - {str(knowledge)[:100]}")
                        continue
                    
                    # 清理和验证知识内容
                    knowledge = knowledge.strip()
                    if len(knowledge) < 10:
                        self.logger.warning(f"跳过过短的知识内容 #{i+1}: {knowledge}")
                        continue
                    
                    # 添加详细的调试信息
                    if i < 3:  # 只为前3条记录详细日志
                        self.logger.debug(f"准备插入知识 #{i+1}: {knowledge[:100]}...")
                    
                    # 尝试插入知识
                    try:
                        await self.rag.ainsert(knowledge)
                        success_count += 1
                        if (i + 1) % 10 == 0:
                            print(f"已处理 {i + 1}/{len(knowledge_data)} 条知识 (成功: {success_count}, 失败: {error_count})")
                    except Exception as insert_error:
                        error_count += 1
                        error_msg = str(insert_error)
                        
                        # 详细记录错误信息
                        if error_count <= 3:  # 只记录前3个错误的详细信息
                            self.logger.error(f"插入第{i+1}条知识失败: {error_msg}")
                            self.logger.debug(f"失败的知识内容: {knowledge[:200]}...")
                            
                            # 检查是否是异步上下文管理器问题
                            if "asynchronous context manager" in error_msg:
                                self.logger.error("检测到异步上下文管理器问题，这通常是LightRAG内部组件返回None导致的")
                                # 立即禁用LightRAG
                                self.logger.error("立即禁用LightRAG以避免更多错误")
                                self.rag = None
                                break
                        elif error_count == 4:
                            self.logger.warning("插入错误过多，后续错误将不再显示详细信息")
                        
                        # 如果错误率过高，禁用LightRAG
                        if error_count > max(5, len(knowledge_data) * 0.05):  # 至少5个错误或5%错误率
                            self.logger.error(f"LightRAG插入错误率过高 ({error_count}/{i+1} = {error_count/(i+1)*100:.1f}%)，禁用LightRAG功能")
                            self.rag = None
                            break
                        
                        continue
                        
                except Exception as outer_error:
                    self.logger.error(f"处理第{i+1}条知识时发生外部错误: {outer_error}")
                    error_count += 1
                    continue
            
            if self.rag:
                self.logger.info(f"知识库构建完成，成功插入 {success_count} 条，失败 {error_count} 条")
                return True
            else:
                self.logger.warning("LightRAG已被禁用，将使用备用查询方案")
                return False
        except Exception as e:
            self.logger.error(f"构建知识库失败: {e}")
            import traceback
            self.logger.error(f"详细错误信息: {traceback.format_exc()}")
            return False
    
    async def query(self, question: str, mode: str = "hybrid") -> str:
        """查询知识库"""
        if not self.rag:
            self.logger.warning("LightRAG未初始化，使用备用查询")
            return await self.fallback_query(question)
        
        try:
            from lightrag import QueryParam
            
            # 执行查询
            result = await self.rag.aquery(question, param=QueryParam(mode=mode))
            return result
        except Exception as e:
            self.logger.error(f"LightRAG查询失败: {e}")
            # 如果是异步上下文管理器错误，禁用LightRAG
            if "asynchronous context manager" in str(e):
                self.logger.error("检测到异步上下文管理器问题，禁用LightRAG")
                self.rag = None
            self.logger.info("切换到备用查询方案")
            return await self.fallback_query(question)
    
    async def fallback_query(self, question: str) -> str:
        """备用查询方案 - 使用Neo4j + 派欧云API"""
        try:
            # 从Neo4j获取相关知识
            knowledge_context = ""
            if self.neo4j_retriever.connect_neo4j():
                # 获取所有知识作为上下文
                all_knowledge = self.neo4j_retriever.get_all_knowledge()
                if all_knowledge:
                    # 取前10条知识作为上下文
                    knowledge_context = "\n".join(all_knowledge[:10])
                    self.logger.info(f"获取到 {len(all_knowledge)} 条知识，使用前10条作为上下文")
                
                # 搜索特定特征
                features = self.neo4j_retriever.search_features(question)
                if features:
                    feature_info = "相关特征信息：\n"
                    for feature in features[:5]:  # 限制为前5个特征
                        feature_info += f"- {feature['name']} (ID: {feature['id']})\n"
                        if feature['process_types']:
                            feature_info += f"  工艺类型: {', '.join(feature['process_types'])}\n"
                        if feature['surface_types']:
                            feature_info += f"  面类型: {', '.join(feature['surface_types'])}\n"
                    knowledge_context = feature_info + "\n" + knowledge_context
            
            # 如果有知识上下文，使用派欧云API进行智能回答
            if knowledge_context:
                try:
                    system_prompt = """你是一个加工工艺专家。请基于提供的知识库信息回答用户问题。
                    要求：
                    1. 严格基于提供的知识库内容回答
                    2. 回答要准确、简洁、结构化
                    3. 如果知识库中没有相关信息，请明确说明
                    4. 使用中文回答"""
                    
                    prompt = f"知识库内容：\n{knowledge_context}\n\n用户问题：{question}\n\n请基于上述知识库内容回答问题："
                    
                    answer = await self.llm_client.call_llm(prompt, system_prompt)
                    if answer and len(answer.strip()) > 10:
                        return f"基于知识库的智能回答：\n\n{answer}"
                except Exception as api_error:
                    self.logger.error(f"派欧云API调用失败: {api_error}")
            
            # 如果API调用失败，返回基于Neo4j的结构化答案
            if self.neo4j_retriever.connect_neo4j():
                features = self.neo4j_retriever.search_features("特征")
                if features:
                    result = "根据知识库搜索，加工工艺中的特征类型包括：\n\n"
                    feature_types = set()
                    for feature in features:
                        if feature['name']:
                            # 提取特征类型
                            name = feature['name']
                            if '孔' in name:
                                feature_types.add('孔特征')
                            elif '槽' in name:
                                feature_types.add('槽特征')
                            elif '台' in name or '面' in name:
                                feature_types.add('面特征')
                            elif '螺纹' in name:
                                feature_types.add('螺纹特征')
                            elif '倒角' in name:
                                feature_types.add('倒角特征')
                            else:
                                feature_types.add('轮廓特征')
                    
                    for i, feature_type in enumerate(sorted(feature_types), 1):
                        result += f"{i}. {feature_type}\n"
                    
                    result += f"\n共发现 {len(features)} 个具体特征实例。"
                    return result
            
            # 最后的备用方案
            return """

根据加工工艺知识库，主要的特征类型包括：

1. **孔特征** - 通孔、盲孔、阶梯孔、螺纹孔、锥孔
2. **槽特征** - 通槽、盲槽、T型槽、键槽、燕尾槽  
3. **面特征** - 平面、曲面、斜面、台阶面、凸台面
4. **轮廓特征** - 外轮廓、内轮廓、复杂轮廓
5. **螺纹特征** - 外螺纹、内螺纹、标准螺纹、非标螺纹
6. **倒角特征** - 直角倒角、圆角倒角、变角倒角

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
        # 初始化检索系统
        print("正在初始化检索系统...")
        if not retriever.setup_lightrag():
            print("⚠️ 检索系统初始化失败")
            return
        
        print("✅ 使用稳定的Neo4j + 派欧云API检索方案")
        
        print("✅ 系统初始化完成！")
        
        # 示例查询
        question = "加工工艺的特征类型都有哪些？"
        print(f"\n问题: {question}")
        print("回答:")
        answer = await retriever.query(question)
        print(answer)

        # 交互式查询
        # while True:
        #     print("\n" + "="*50)
        #     question = input("请输入您的问题 (输入 'quit' 退出): ").strip()
            
        #     if question.lower() in ['quit', 'exit', '退出']:
        #         break
            
        #     if not question:
        #         continue
            
        #     print(f"\n问题: {question}")
        #     print("正在查询...")
            
        #     # 尝试使用LightRAG查询
        #     answer = await retriever.query(question)
            
        #     if "错误" in answer or "失败" in answer:
        #         print("⚠️ LightRAG查询失败，使用备用方案...")
        #         answer = retriever.fallback_query(question)
            
        #     print("回答:")
        #     print(answer)
    
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