#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo4j + 派欧云API + LightRAG 知识图谱检索系统
基于Neo4j知识库和派欧云API的智能问答系统,完全使用LightRAG架构
"""

import os
import sys
import asyncio
import configparser
import logging
import re
import json
from typing import Dict, List, Any, Optional
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
    """智能检索系统 - 完全基于LightRAG架构"""

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

    async def extract_feature_info(self, question: str) -> Dict[str, Any]:
        """
        步骤1: 使用大模型从用户问题中提取特征信息

        Args:
            question: 用户问题

        Returns:
            提取的特征信息字典，包含：
            - feature_type: 特征类型（如：圆柱通孔、矩形凸台）
            - feature_surface: 特征面（如：孔、平面、曲面）
            - dimensions: 尺寸信息字典（可能包含：diameter, length, width, height等）
        """
        try:
            extraction_prompt = f"""
请从以下用户问题中提取加工特征信息，并以JSON格式返回。

用户问题：{question}

请提取以下信息：
1. feature_type（特征类型）：如"圆柱通孔"、"矩形凸台"、"V形通槽"等
2. feature_surface（特征面）：如"孔"、"平面"、"曲面"、"垂直面"等
3. dimensions（尺寸信息）：提取所有提到的尺寸参数，如：
   - diameter（直径）
   - length（长度）
   - width（宽度）
   - height（高度/深度）
   - radius（半径）

请严格按照以下JSON格式返回，不要添加任何其他文字：
{{
    "feature_type": "提取的特征类型",
    "feature_surface": "提取的特征面",
    "dimensions": {{
        "diameter": 数值或null,
        "length": 数值或null,
        "width": 数值或null,
        "height": 数值或null
    }}
}}

注意：
- 如果问题中没有明确提到某个信息，对应字段返回null
- 尺寸数值只保留数字，单位默认为mm
- 只返回JSON，不要有其他解释文字
"""

            self.logger.info("步骤1: 开始使用大模型提取特征信息...")
            response = await self.llm_client.call_llm(extraction_prompt, "")

            # 解析JSON响应
            response_clean = self._clean_json_response(response)
            feature_info = json.loads(response_clean)
            self.logger.info(f"提取的特征信息: {feature_info}")

            return feature_info

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}, 原始响应: {response}")
            return {
                "feature_type": None,
                "feature_surface": None,
                "dimensions": {}
            }
        except Exception as e:
            self.logger.error(f"提取特征信息失败: {str(e)}")
            return {
                "feature_type": None,
                "feature_surface": None,
                "dimensions": {}
            }

    def _clean_json_response(self, response: str) -> str:
        """清理LLM返回的JSON响应"""
        response_clean = response.strip()
        if response_clean.startswith("```json"):
            response_clean = response_clean[7:]
        if response_clean.startswith("```"):
            response_clean = response_clean[3:]
        if response_clean.endswith("```"):
            response_clean = response_clean[:-3]
        return response_clean.strip()

    async def lightrag_search_in_neo4j(self, feature_type: str, feature_surface: str,
                                       dimensions: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        步骤2: 使用LightRAG在Neo4j知识图谱中搜索候选结果

        Args:
            feature_type: 特征类型
            feature_surface: 特征面
            dimensions: 尺寸信息

        Returns:
            候选工艺和刀具列表
        """
        if not self.neo4j_retriever.driver:
            return []

        try:
            with self.neo4j_retriever.driver.session() as session:
                # 构建查询语句，根据特征类型查找工艺和刀具
                query = """
                MATCH (f:Feature)-[:HAS_PROCESS]->(p:Process)
                WHERE f.name CONTAINS $feature_type
                OPTIONAL MATCH (p)-[:USES_TOOL]->(t:Tool)
                RETURN DISTINCT
                    f.name as feature_name,
                    f.id as feature_id,
                    p.template_id as process_template_id,
                    p.process_type as process_type,
                    p.surface_type as surface_type,
                    p.process_stage as process_stage,
                    p.feature_surface as feature_surface,
                    collect(DISTINCT {
                        tool_id: t.id,
                        tool_name: t.name,
                        diameter: t.diameter,
                        extension_length: t.extension_length
                    }) as tools
                ORDER BY p.template_id
                LIMIT 10
                """

                result = session.run(query, feature_type=feature_type)
                records = list(result)

                if not records:
                    self.logger.warning(f"未找到特征类型 '{feature_type}' 的相关工艺和刀具")
                    return []

                # 构建候选列表
                candidates = []
                for record in records:
                    tools = record['tools']
                    # 过滤掉空的tool记录
                    valid_tools = [t for t in tools if t['tool_id'] is not None]

                    candidate = {
                        "feature_name": record['feature_name'],
                        "feature_id": record['feature_id'],
                        "process_template_id": record['process_template_id'],
                        "process_type": record['process_type'],
                        "surface_type": record['surface_type'],
                        "process_stage": record['process_stage'],
                        "feature_surface": record['feature_surface'],
                        "tools": valid_tools
                    }
                    candidates.append(candidate)

                self.logger.info(f"步骤2: 从Neo4j检索到 {len(candidates)} 个候选方案")
                return candidates

        except Exception as e:
            self.logger.error(f"在Neo4j中搜索失败: {str(e)}")
            return []

    async def lightrag_select_best_match(self, question: str, feature_info: Dict[str, Any],
                                        candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        步骤3: 使用LightRAG（LLM+知识图谱）从候选中选择最佳匹配

        Args:
            question: 原始问题
            feature_info: 提取的特征信息
            candidates: 候选方案列表

        Returns:
            最佳匹配的工艺模板ID和刀具ID
        """
        if not candidates:
            return {
                "process_template_id": None,
                "tool_id": None,
                "reason": "未找到匹配的候选方案"
            }

        try:
            # 构建选择提示
            selection_prompt = f"""
请根据用户需求，从以下候选方案中选择最合适的工艺模板和刀具。

用户问题：{question}

提取的特征信息：
- 特征类型: {feature_info.get('feature_type')}
- 特征面: {feature_info.get('feature_surface')}
- 尺寸信息: {json.dumps(feature_info.get('dimensions', {}), ensure_ascii=False)}

候选方案（共{len(candidates)}个）：
{json.dumps(candidates, ensure_ascii=False, indent=2)}

选择规则：
1. 特征类型必须匹配
2. 特征面类型要匹配（如问题提到"孔"，优先选择feature_surface或surface_type包含"孔"或"平面"的）
3. 刀具选择：如果有尺寸限制，刀具直径要小于等于最小尺寸；刀具伸出长要大于工件高度
4. 优先选择最适合的工序阶段（如精加工、半精加工等）

请严格按照以下JSON格式返回，不要添加任何其他文字：
{{
    "process_template_id": "选中的工艺模板ID",
    "tool_id": "选中的刀具ID",
    "reason": "选择理由（简要说明为什么选择这个方案）"
}}

注意：只返回JSON，不要有其他解释文字
"""

            self.logger.info("步骤3: 使用LLM选择最佳匹配...")
            response = await self.llm_client.call_llm(selection_prompt, "")

            # 清理并解析响应
            response_clean = self._clean_json_response(response)
            selection = json.loads(response_clean)
            self.logger.info(f"选择的工艺和刀具: {selection}")

            return selection

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析失败: {e}, 原始响应: {response}")
            # 返回第一个候选结果作为默认
            if candidates and candidates[0]['tools']:
                first = candidates[0]
                return {
                    "process_template_id": first['process_template_id'],
                    "tool_id": first['tools'][0]['tool_id'] if first['tools'] else None,
                    "reason": "由于解析失败，返回第一个匹配结果"
                }
            return {
                "process_template_id": candidates[0]['process_template_id'] if candidates else None,
                "tool_id": None,
                "reason": "由于解析失败，返回第一个匹配结果（无刀具信息）"
            }
        except Exception as e:
            self.logger.error(f"选择最佳匹配失败: {str(e)}")
            return {
                "process_template_id": None,
                "tool_id": None,
                "reason": f"选择失败: {str(e)}"
            }

    async def query_machining_process_and_tool(self, question: str) -> Dict[str, Any]:
        """
        完整的LightRAG流程：从问题中提取信息 -> 检索 -> 选择最佳匹配

        Args:
            question: 用户问题（如：我现在有一个工件，他的特征类型是圆柱通孔，其中带孔的面中，
                     孔直径是5mm，我想知道使用什么加工工艺和刀具进行加工？）

        Returns:
            包含工艺模板ID和刀具ID的字典，格式如：
            {
                "process_template_id": "P001",
                "tool_id": "T001",
                "feature_info": {...},
                "reason": "选择理由",
                "all_candidates": [...]
            }
        """
        try:
            self.logger.info(f"开始处理问题: {question}")

            # 步骤1: 使用大模型提取特征信息
            feature_info = await self.extract_feature_info(question)

            if not feature_info.get('feature_type'):
                return {
                    "error": "无法从问题中提取特征类型",
                    "process_template_id": None,
                    "tool_id": None,
                    "feature_info": feature_info
                }

            # 步骤2: 在Neo4j中搜索候选结果
            candidates = await self.lightrag_search_in_neo4j(
                feature_type=feature_info.get('feature_type'),
                feature_surface=feature_info.get('feature_surface'),
                dimensions=feature_info.get('dimensions', {})
            )

            if not candidates:
                return {
                    "error": f"未找到特征类型 '{feature_info.get('feature_type')}' 的相关工艺和刀具",
                    "process_template_id": None,
                    "tool_id": None,
                    "feature_info": feature_info,
                    "all_candidates": []
                }

            # 步骤3: 使用LLM选择最佳匹配
            selection = await self.lightrag_select_best_match(question, feature_info, candidates)

            # 步骤4: 格式化输出结果
            result = {
                "process_template_id": selection.get('process_template_id'),
                "tool_id": selection.get('tool_id'),
                "feature_info": feature_info,
                "reason": selection.get('reason'),
                "all_candidates": candidates
            }

            self.logger.info(f"最终推荐结果: process_template_id={result['process_template_id']}, tool_id={result['tool_id']}")
            return result

        except Exception as e:
            self.logger.error(f"查询加工工艺和刀具失败: {str(e)}")
            return {
                "error": str(e),
                "process_template_id": None,
                "tool_id": None
            }
    


async def main():
    """主函数"""
    print("=== Neo4j + 派欧云API + LightRAG 知识图谱检索系统 ===")

    # 加载配置
    config = load_config()
    logger = configure_logging(config)

    # 显示配置信息
    print(f"Neo4j URI: {config.get('neo4j', 'uri')}")
    print(f"派欧云模型: {config.get('paiyun_api', 'model')}")
    print("=" * 50)

    retriever = IntelligentRetriever(config)

    # 测试问题
    question = '我现在有一个工件，他的特征类型是圆柱通孔，其中带孔的面中，孔直径是5mm，我想知道使用什么加工工艺和刀具进行加工？只需要给我一个工艺模板ID和刀具ID即可'

    try:
        # 初始化检索系统
        print("正在初始化检索系统...")
        if not retriever.initialize():
            print("❌ 检索系统初始化失败")
            return

        print("✅ LightRAG检索系统初始化成功")
        print("✅ 系统已就绪，可以开始查询！")

        if question:
            print(f"\n问题: {question}")
            print("\n" + "="*50)
            print("开始LightRAG流程...")
            print("="*50)

            # 调用新的LightRAG方法
            result = await retriever.query_machining_process_and_tool(question)

            print("\n" + "="*50)
            print("查询结果:")
            print("="*50)

            if 'error' in result:
                print(f"❌ 错误: {result['error']}")
            else:
                print(f"✅ 工艺模板ID: {result['process_template_id']}")
                print(f"✅ 刀具ID: {result['tool_id']}")
                print(f"\n选择理由: {result.get('reason', '无')}")

                print(f"\n提取的特征信息:")
                feature_info = result.get('feature_info', {})
                print(f"  - 特征类型: {feature_info.get('feature_type')}")
                print(f"  - 特征面: {feature_info.get('feature_surface')}")
                print(f"  - 尺寸信息: {feature_info.get('dimensions')}")

                # 显示所有候选方案
                candidates = result.get('all_candidates', [])
                if candidates:
                    print(f"\n共找到 {len(candidates)} 个候选方案")

            # 格式化最终输出
            print("\n" + "="*50)
            print("格式化输出:")
            print("="*50)
            final_output = {
                "process_template_id": result.get('process_template_id'),
                "tool_id": result.get('tool_id')
            }
            print(json.dumps(final_output, ensure_ascii=False, indent=2))

            return

    except KeyboardInterrupt:
        print("\n用户中断程序")
    except Exception as e:
        logger.error(f"程序运行出错: {e}")
        print(f"❌ 程序运行出错: {e}")
    finally:
        retriever.neo4j_retriever.close()
        print("\n程序已退出")


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())