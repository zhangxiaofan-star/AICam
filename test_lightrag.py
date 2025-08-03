#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LightRAG 测试脚本
"""

import asyncio
import os
import numpy as np
from lightrag import LightRAG, QueryParam
from lightrag.utils import EmbeddingFunc

async def test_lightrag():
    """测试LightRAG的基本功能"""
    
    # 创建工作目录
    working_dir = "./test_lightrag_cache"
    os.makedirs(working_dir, exist_ok=True)
    
    print("正在测试LightRAG...")
    
    try:
        # 定义简单的异步嵌入函数
        async def simple_embedding_func(texts):
            """简单的异步嵌入函数"""
            print(f"嵌入函数被调用，处理 {len(texts)} 个文本")
            embeddings = []
            for text in texts:
                # 创建简单的向量
                vector = np.random.rand(384).astype(np.float32)
                embeddings.append(vector)
            return np.array(embeddings)
        
        # 定义简单的LLM函数
        async def simple_llm_func(prompt, system_prompt=None, history_messages=[], **kwargs):
            """简单的LLM函数"""
            print(f"LLM函数被调用，提示: {prompt[:50]}...")
            return f"这是对提示的简单回答: {prompt[:100]}"
        
        # 测试1: 使用默认配置
        print("\n=== 测试1: 默认配置 ===")
        try:
            rag1 = LightRAG(working_dir=working_dir + "_default")
            print("✅ 默认配置初始化成功")
            
            # 测试插入
            await rag1.ainsert("这是一个测试文档。")
            print("✅ 默认配置插入成功")
            
        except Exception as e:
            print(f"❌ 默认配置失败: {e}")
        
        # 测试2: 自定义配置
        print("\n=== 测试2: 自定义配置 ===")
        try:
            rag2 = LightRAG(
                working_dir=working_dir + "_custom",
                llm_model_func=simple_llm_func,
                embedding_func=EmbeddingFunc(
                    embedding_dim=384,
                    max_token_size=8192,
                    func=simple_embedding_func
                )
            )
            print("✅ 自定义配置初始化成功")
            
            # 测试插入
            await rag2.ainsert("这是另一个测试文档。")
            print("✅ 自定义配置插入成功")
            
        except Exception as e:
            print(f"❌ 自定义配置失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
        
        # 测试3: 只使用自定义LLM
        print("\n=== 测试3: 只使用自定义LLM ===")
        try:
            rag3 = LightRAG(
                working_dir=working_dir + "_llm_only",
                llm_model_func=simple_llm_func
            )
            print("✅ 只使用自定义LLM初始化成功")
            
            # 测试插入
            await rag3.ainsert("这是第三个测试文档。")
            print("✅ 只使用自定义LLM插入成功")
            
        except Exception as e:
            print(f"❌ 只使用自定义LLM失败: {e}")
            import traceback
            print(f"详细错误: {traceback.format_exc()}")
            
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        print(f"详细错误: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_lightrag())