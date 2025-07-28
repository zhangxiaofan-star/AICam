#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于LightRAG的加工工艺知识检索系统
"""

import os
import asyncio
import pandas as pd
from lightrag import LightRAG, QueryParam
from lightrag.llm import openai_complete_if_cache, openai_embedding
from lightrag.utils import EmbeddingFunc
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcessKnowledgeRetriever:
    def __init__(self):
        """初始化知识检索系统"""
        load_dotenv()
        
        # 配置参数
        self.working_dir = os.getenv('LIGHTRAG_WORKING_DIR', './lightrag_cache')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.openai_base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        if not self.openai_api_key:
            logger.warning("未设置OPENAI_API_KEY，请在.env文件中配置")
            
        # 确保工作目录存在
        os.makedirs(self.working_dir, exist_ok=True)
        
        # 初始化LightRAG
        self.rag = self._initialize_lightrag()
        
    def _initialize_lightrag(self):
        """初始化LightRAG实例"""
        try:
            rag = LightRAG(
                working_dir=self.working_dir,
                llm_model_func=openai_complete_if_cache,
                llm_model_name="gpt-3.5-turbo",
                llm_model_max_async=4,
                llm_model_max_token_size=32768,
                llm_model_kwargs={
                    "api_key": self.openai_api_key,
                    "base_url": self.openai_base_url,
                },
                embedding_func=EmbeddingFunc(
                    embedding_dim=1536,
                    max_token_size=8192,
                    func=lambda texts: openai_embedding(
                        texts,
                        model="text-embedding-ada-002",
                        api_key=self.openai_api_key,
                        base_url=self.openai_base_url
                    )
                )
            )
            logger.info("LightRAG初始化成功")
            return rag
        except Exception as e:
            logger.error(f"LightRAG初始化失败: {e}")
            return None
            
    def load_and_process_data(self, processes_csv_path, tools_csv_path):
        """加载并处理CSV数据为文本格式"""
        try:
            # 加载数据
            processes_df = pd.read_csv(processes_csv_path, encoding='utf-8')
            tools_df = pd.read_csv(tools_csv_path, encoding='utf-8')
            
            # 转换工艺数据为文本
            process_texts = []
            for _, row in processes_df.iterrows():
                text = f"""
工艺模板编号: {row['模板编号']}
特征ID: {row['特征ID']}
特征名称: {row['特征名称']}
组成面: {row['组成面']}
特征面: {row['特征面']}
面类型: {row['面类型']}
侧壁特征: {row['侧壁特征']}
余量: {row['余量']}
工序阶段: {row['工序阶段']}
工艺类型: {row['工艺类型']}

这是一个{row['特征名称']}的加工工艺，使用{row['工艺类型']}进行{row['工序阶段']}，
处理{row['面类型']}类型的{row['特征面']}，余量为{row['余量']}。
"""
                process_texts.append(text.strip())
                
            # 转换刀具数据为文本
            tool_texts = []
            for _, row in tools_df.iterrows():
                text = f"""
刀具ID: {row['刀具id']}
刀具名称: {row['刀具名称']}
直径: {row['直径']}mm
R角: {row['R角']}mm
刃数: {row['刃数']}
伸出长: {row['伸出长']}mm

这是一个直径为{row['直径']}mm的{row['刀具名称']}刀具，
R角为{row['R角']}mm，有{row['刃数']}个刃，伸出长度为{row['伸出长']}mm。
适用于相应直径和精度要求的加工任务。
"""
                tool_texts.append(text.strip())
                
            logger.info(f"成功处理{len(process_texts)}条工艺数据和{len(tool_texts)}条刀具数据")
            return process_texts + tool_texts
            
        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            return []
            
    async def build_knowledge_base(self, processes_csv_path, tools_csv_path):
        """构建知识库"""
        if not self.rag:
            logger.error("LightRAG未正确初始化")
            return False
            
        try:
            # 加载和处理数据
            texts = self.load_and_process_data(processes_csv_path, tools_csv_path)
            
            if not texts:
                logger.error("没有可用的文本数据")
                return False
                
            # 将所有文本合并为一个大文档
            combined_text = "\n\n".join(texts)
            
            # 插入到LightRAG
            await self.rag.ainsert(combined_text)
            
            logger.info("知识库构建完成")
            return True
            
        except Exception as e:
            logger.error(f"构建知识库时发生错误: {e}")
            return False
            
    async def query(self, question, mode="hybrid"):
        """查询知识库"""
        if not self.rag:
            logger.error("LightRAG未正确初始化")
            return None
            
        try:
            # 支持的查询模式
            valid_modes = ["naive", "local", "global", "hybrid"]
            if mode not in valid_modes:
                logger.warning(f"无效的查询模式: {mode}，使用默认模式: hybrid")
                mode = "hybrid"
                
            # 执行查询
            result = await self.rag.aquery(question, param=QueryParam(mode=mode))
            return result
            
        except Exception as e:
            logger.error(f"查询时发生错误: {e}")
            return None
            
    async def interactive_query(self):
        """交互式查询界面"""
        print("\n=== 加工工艺知识检索系统 ===")
        print("支持的查询模式: naive, local, global, hybrid")
        print("输入 'quit' 或 'exit' 退出系统")
        print("输入 'mode <模式名>' 切换查询模式")
        print("=" * 50)
        
        current_mode = "hybrid"
        
        while True:
            try:
                user_input = input(f"\n[{current_mode}模式] 请输入您的问题: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("感谢使用！再见！")
                    break
                    
                if user_input.startswith('mode '):
                    new_mode = user_input[5:].strip()
                    if new_mode in ["naive", "local", "global", "hybrid"]:
                        current_mode = new_mode
                        print(f"已切换到 {current_mode} 模式")
                    else:
                        print("无效的模式，支持的模式: naive, local, global, hybrid")
                    continue
                    
                if not user_input:
                    continue
                    
                print(f"\n正在查询中...")
                result = await self.query(user_input, mode=current_mode)
                
                if result:
                    print(f"\n回答:")
                    print("-" * 50)
                    print(result)
                    print("-" * 50)
                else:
                    print("抱歉，没有找到相关信息。")
                    
            except KeyboardInterrupt:
                print("\n\n感谢使用！再见！")
                break
            except Exception as e:
                logger.error(f"交互查询时发生错误: {e}")
                
    def get_sample_questions(self):
        """获取示例问题"""
        return [
            "什么是矩形凸台的加工工艺？",
            "精加工阶段适用哪些工艺类型？",
            "直径为10mm的刀具有哪些？",
            "底壁铣工艺的特点是什么？",
            "如何选择合适的刀具进行圆柱通孔加工？",
            "半精加工和精加工的区别是什么？",
            "哪些特征需要使用侧壁特征？",
            "R角为1mm的刀具适用于什么加工？"
        ]

async def main():
    """主函数"""
    # 数据文件路径
    processes_csv = "./dataset/processes.csv"
    tools_csv = "./dataset/tools.csv"
    
    # 创建知识检索系统
    retriever = ProcessKnowledgeRetriever()
    
    if not retriever.rag:
        logger.error("系统初始化失败，请检查配置")
        return
        
    # 检查知识库是否已存在
    knowledge_base_exists = os.path.exists(os.path.join(retriever.working_dir, "graph_chunk_entity_relation.json"))
    
    if not knowledge_base_exists:
        print("首次运行，正在构建知识库...")
        success = await retriever.build_knowledge_base(processes_csv, tools_csv)
        if not success:
            logger.error("知识库构建失败")
            return
        print("知识库构建完成！")
    else:
        print("检测到已有知识库，直接使用现有数据")
        
    # 显示示例问题
    print("\n示例问题:")
    for i, question in enumerate(retriever.get_sample_questions(), 1):
        print(f"{i}. {question}")
        
    # 启动交互式查询
    await retriever.interactive_query()

if __name__ == "__main__":
    asyncio.run(main())