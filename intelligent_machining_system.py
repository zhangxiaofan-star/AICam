#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能加工决策系统
结合 LightRAG、大模型和加工决策模块，提供智能的工艺和刀具推荐
"""

import asyncio
import configparser
import logging
import json
import re
from typing import Dict, List, Any, Optional, Tuple
from lightrag_retrieval import IntelligentRetriever
from machining_advisor import MachiningAdvisor


class IntelligentMachiningSystem:
    """智能加工决策系统"""
    
    def __init__(self, config: configparser.ConfigParser):
        self.config = config
        self.logger = self._setup_logger()
        
        # 初始化子系统
        self.retriever = IntelligentRetriever(config)
        self.advisor = MachiningAdvisor(config)
        
        # 问题分析模式
        self.analysis_patterns = {
            'feature_extraction': [
                r'(圆柱通孔|圆形通孔|矩形通孔|圆柱凸台|矩形凹槽|圆形盲孔)',
                r'特征类型[是为](.+?)(?:[，,]|$)',
                r'特征[是为](.+?)(?:[，,]|$)',
                r'工件.*特征.*[是为](.+?)(?:[，,]|$)',
                r'有一个(.+?)(?:[，,]|$)'
            ],
            'dimension_extraction': [
                r'直径(?:是|为)?(\d+(?:\.\d+)?)mm',
                r'孔直径(?:是|为)?(\d+(?:\.\d+)?)mm',
                r'长度(?:是|为)?(\d+(?:\.\d+)?)mm',
                r'宽度(?:是|为)?(\d+(?:\.\d+)?)mm',
                r'高度(?:是|为)?(\d+(?:\.\d+)?)mm',
                r'深度(?:是|为)?(\d+(?:\.\d+)?)mm'
            ],
            'process_stage_extraction': [
                r'(粗加工|半精加工|精加工|清根)',
                r'需要(粗加工|半精加工|精加工|清根)',
                r'进行(粗加工|半精加工|精加工|清根)'
            ],
            'surface_type_extraction': [
                r'(平面|垂直面|圆柱面|锥面)',
                r'表面[是为](平面|垂直面|圆柱面|锥面)',
                r'面[是为](平面|垂直面|圆柱面|锥面)'
            ]
        }
    
    def _setup_logger(self) -> logging.Logger:
        """设置日志"""
        logger = logging.getLogger('IntelligentMachiningSystem')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    async def initialize(self) -> bool:
        """初始化系统"""
        try:
            self.logger.info("正在初始化智能加工决策系统...")
            
            # 初始化检索系统
            if not self.retriever.initialize():
                self.logger.error("LightRAG检索系统初始化失败")
                return False
            
            # 初始化加工决策系统
            if not self.advisor.connect_neo4j():
                self.logger.error("加工决策系统初始化失败")
                return False
            
            self.logger.info("✅ 智能加工决策系统初始化成功")
            return True
            
        except Exception as e:
            self.logger.error(f"系统初始化失败: {e}")
            return False
    
    def _extract_parameters_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取加工参数"""
        parameters = {
            'feature_name': None,
            'surface_type': None,
            'process_stage': None,
            'dimensions': {}
        }
        
        # 提取特征类型
        for pattern in self.analysis_patterns['feature_extraction']:
            match = re.search(pattern, text)
            if match:
                feature_name = match.group(1).strip()
                # 标准化特征名称
                feature_name = self._normalize_feature_name(feature_name)
                parameters['feature_name'] = feature_name
                break
        
        # 提取尺寸信息
        for pattern in self.analysis_patterns['dimension_extraction']:
            matches = re.findall(pattern, text)
            for match in matches:
                if '直径' in pattern:
                    parameters['dimensions']['diameter'] = float(match)
                elif '长度' in pattern:
                    parameters['dimensions']['length'] = float(match)
                elif '宽度' in pattern:
                    parameters['dimensions']['width'] = float(match)
                elif '高度' in pattern:
                    parameters['dimensions']['height'] = float(match)
                elif '深度' in pattern:
                    parameters['dimensions']['depth'] = float(match)
        
        # 提取工序阶段
        for pattern in self.analysis_patterns['process_stage_extraction']:
            match = re.search(pattern, text)
            if match:
                parameters['process_stage'] = match.group(1) if match.groups() else match.group(0)
                break
        
        # 提取表面类型
        for pattern in self.analysis_patterns['surface_type_extraction']:
            match = re.search(pattern, text)
            if match:
                parameters['surface_type'] = match.group(1) if match.groups() else match.group(0)
                break
        
        return parameters
    
    def _normalize_feature_name(self, feature_name: str) -> str:
        """标准化特征名称"""
        # 特征名称映射表 - 映射到数据库中存在的标准名称
        feature_mapping = {
            '圆形通孔': '圆柱通孔',
            '圆孔': '圆柱通孔',
            '圆形孔': '圆柱通孔',
            '矩形孔': '矩形通孔',
            '方孔': '矩形通孔',
            '圆台': '圆柱凸台',
            '矩形槽': '矩形凹槽',
            '方槽': '矩形凹槽',
            '凹槽': '矩形凹槽'
        }
        
        return feature_mapping.get(feature_name, feature_name)
    
    async def _analyze_question_with_llm(self, question: str) -> Dict[str, Any]:
        """使用大模型分析问题"""
        analysis_prompt = f"""
请分析以下加工问题，提取关键参数：

问题：{question}

请按照以下JSON格式返回分析结果：
{{
    "feature_name": "特征名称（如：圆形通孔、矩形凹槽、圆柱凸台等）",
    "surface_type": "表面类型（如：plane、垂直面、圆柱面等）",
    "process_stage": "工序阶段（如：粗加工、半精加工、精加工、清根）",
    "dimensions": {{
        "diameter": "直径值（数字）",
        "length": "长度值（数字）",
        "width": "宽度值（数字）",
        "height": "高度值（数字）",
        "depth": "深度值（数字）"
    }},
    "analysis_confidence": "分析置信度（0-1）",
    "missing_parameters": ["缺失的参数列表"]
}}

注意：
1. 如果某个参数无法从问题中提取，请设为null
2. 尺寸值只保留数字，不要单位
3. 特征名称要使用标准术语
4. 表面类型优先使用"plane"表示平面
"""
        
        try:
            # 使用LightRAG的LLM接口
            response = await self.retriever.llm_client.call_llm(analysis_prompt)
            
            # 尝试解析JSON响应
            if response and isinstance(response, str):
                # 提取JSON部分
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    analysis_result = json.loads(json_str)
                    return analysis_result
            
            self.logger.warning("LLM分析结果格式不正确，使用规则提取")
            return {}
            
        except Exception as e:
            self.logger.error(f"LLM分析失败: {e}")
            return {}
    
    def _infer_missing_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """推断缺失的参数"""
        # 如果有直径信息，可以推断长度和宽度
        if 'diameter' in parameters['dimensions'] and parameters['dimensions']['diameter']:
            diameter = parameters['dimensions']['diameter']
            if not parameters['dimensions'].get('length'):
                parameters['dimensions']['length'] = diameter
            if not parameters['dimensions'].get('width'):
                parameters['dimensions']['width'] = diameter
        
        # 默认工序阶段
        if not parameters['process_stage']:
            parameters['process_stage'] = '粗加工'  # 默认粗加工
        
        # 默认表面类型
        if not parameters['surface_type']:
            parameters['surface_type'] = 'plane'  # 默认平面
        
        # 默认深度/高度
        if not parameters['dimensions'].get('height') and not parameters['dimensions'].get('depth'):
            if 'diameter' in parameters['dimensions']:
                # 对于孔类特征，默认深度为直径的2倍
                parameters['dimensions']['height'] = parameters['dimensions']['diameter'] * 2
            else:
                parameters['dimensions']['height'] = 10.0  # 默认高度
        elif parameters['dimensions'].get('depth') and not parameters['dimensions'].get('height'):
            parameters['dimensions']['height'] = parameters['dimensions']['depth']
        
        return parameters
    
    async def _get_knowledge_context(self, question: str, parameters: Dict[str, Any]) -> str:
        """获取相关知识上下文"""
        try:
            # 构建知识查询
            knowledge_queries = []
            
            if parameters['feature_name']:
                knowledge_queries.append(f"{parameters['feature_name']}的加工工艺")
            
            if parameters['process_stage']:
                knowledge_queries.append(f"{parameters['process_stage']}工艺参数")
            
            # 查询相关知识
            all_context = []
            for query in knowledge_queries:
                context = await self.retriever._get_knowledge_context(query)
                if context:
                    all_context.append(context)
            
            return "\n\n".join(all_context)
            
        except Exception as e:
            self.logger.error(f"获取知识上下文失败: {e}")
            return ""
    
    async def process_machining_question(self, question: str) -> Dict[str, Any]:
        """处理加工问题的主要方法"""
        try:
            self.logger.info(f"开始处理问题: {question}")
            
            # 第一步：使用规则提取基本参数
            rule_parameters = self._extract_parameters_from_text(question)
            self.logger.info(f"规则提取参数: {rule_parameters}")
            
            # 第二步：使用LLM增强分析
            llm_parameters = await self._analyze_question_with_llm(question)
            self.logger.info(f"LLM分析参数: {llm_parameters}")
            
            # 第三步：合并和优化参数
            final_parameters = self._merge_parameters(rule_parameters, llm_parameters)
            final_parameters = self._infer_missing_parameters(final_parameters)
            self.logger.info(f"最终参数: {final_parameters}")
            
            # 第四步：获取知识上下文
            knowledge_context = await self._get_knowledge_context(question, final_parameters)
            
            # 第五步：使用加工决策系统获取推荐
            machining_recommendation = None
            if (final_parameters['feature_name'] and 
                final_parameters['dimensions'].get('length') and 
                final_parameters['dimensions'].get('width') and 
                final_parameters['dimensions'].get('height')):
                
                machining_recommendation = self.advisor.get_machining_recommendation(
                    feature_name=final_parameters['feature_name'],
                    surface_type=final_parameters['surface_type'],
                    process_stage=final_parameters['process_stage'],
                    length=final_parameters['dimensions']['length'],
                    width=final_parameters['dimensions']['width'],
                    height=final_parameters['dimensions']['height']
                )
            
            # 第六步：生成最终答案
            final_answer = await self._generate_intelligent_answer(
                question, final_parameters, knowledge_context, machining_recommendation
            )
            
            return final_answer
            
        except Exception as e:
            self.logger.error(f"处理问题失败: {e}")
            return {
                "answer": f"处理问题时发生错误: {str(e)}",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _merge_parameters(self, rule_params: Dict[str, Any], llm_params: Dict[str, Any]) -> Dict[str, Any]:
        """合并规则提取和LLM分析的参数"""
        merged = rule_params.copy()
        
        if llm_params:
            # LLM结果优先级更高
            for key in ['feature_name', 'surface_type', 'process_stage']:
                if llm_params.get(key) and not merged.get(key):
                    merged[key] = llm_params[key]
            
            # 合并尺寸信息
            if llm_params.get('dimensions'):
                for dim_key, dim_value in llm_params['dimensions'].items():
                    if dim_value and not merged['dimensions'].get(dim_key):
                        merged['dimensions'][dim_key] = float(dim_value)
        
        return merged
    
    async def _generate_intelligent_answer(self, question: str, parameters: Dict[str, Any], 
                                         knowledge_context: str, machining_recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """生成智能答案"""
        try:
            # 生成规范化的简洁答案
            answer = self._generate_standardized_answer(machining_recommendation)
            
            return {
                "answer": answer,
                "confidence": 0.85,
                "sources": ["LightRAG知识图谱", "加工决策系统", "派欧云LLM"],
                "parameters": parameters,
                "machining_recommendation": machining_recommendation,
                "knowledge_context": knowledge_context
            }
            
        except Exception as e:
            self.logger.error(f"生成智能答案失败: {e}")
            return {
                "answer": f"生成答案失败: {str(e)}",
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _generate_standardized_answer(self, machining_recommendation: Dict[str, Any]) -> str:
        """生成规范化的答案格式"""
        if not machining_recommendation:
            return "推荐模板ID：无  推荐加工工艺：无  推荐刀具ID：无"
        
        # 获取推荐模板ID
        process_templates = machining_recommendation.get('process_templates', [])
        template_id = process_templates[0].get('template_id') if process_templates else "无"
        
        # 获取推荐加工工艺
        process_type = process_templates[0].get('process_type') if process_templates else "无"
        
        # 获取推荐刀具ID
        suitable_tools = machining_recommendation.get('suitable_tools', [])
        tool_id = suitable_tools[0].get('tool_id') if suitable_tools else "无"
        
        return f"推荐模板ID：{template_id}  推荐加工工艺：{process_type}  推荐刀具ID：{tool_id}"
    
    def _generate_simple_id_answer(self, machining_recommendation: Dict[str, Any]) -> str:
        """生成简洁的ID答案"""
        if not machining_recommendation:
            return "❌ 无法提供推荐ID，未找到匹配的工艺和刀具。"
        
        answer_parts = []
        
        # 工艺模板ID
        process_templates = machining_recommendation.get('process_templates', [])
        if process_templates:
            template_ids = [t.get('template_id') for t in process_templates]
            answer_parts.append(f"**工艺模板ID**: {', '.join(template_ids)}")
        else:
            answer_parts.append("**工艺模板ID**: 未找到")
        
        # 刀具ID
        suitable_tools = machining_recommendation.get('suitable_tools', [])
        if suitable_tools:
            tool_id = suitable_tools[0].get('tool_id')
            answer_parts.append(f"**刀具ID**: {tool_id}")
        else:
            answer_parts.append("**刀具ID**: 未找到")
        
        return "\n".join(answer_parts)
    
    def close(self):
        """关闭系统"""
        if hasattr(self.retriever, 'neo4j_retriever'):
            self.retriever.neo4j_retriever.close()
        if hasattr(self.advisor, 'close'):
            self.advisor.close()


async def main():
    """主函数"""
    print("=" * 80)
    print("🤖 智能加工决策系统")
    print("=" * 80)
    print("结合 LightRAG、大模型和加工决策，提供智能的工艺和刀具推荐")
    print()
    
    # 加载配置
    config = configparser.ConfigParser()
    config.read("config.ini", encoding='utf-8')
    
    # 初始化系统
    system = IntelligentMachiningSystem(config)
    
    try:
        if not await system.initialize():
            print("❌ 系统初始化失败")
            return
        
        # 测试问题
        test_questions = [
            "我现在有一个工件，他的圆柱凸台精加工，直径12mm，高度6mm，用什么加工工艺和刀具？"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n{'='*60}")
            print(f"📋 测试问题 {i}")
            print(f"{'='*60}")
            print(f"问题: {question}")
            print("\n正在分析和处理...")
            
            result = await system.process_machining_question(question)
            
            print(f"\n🎯 回答:")
            print(result['answer'])
            print(f"\n📊 置信度: {result['confidence']}")
            print(f"📚 数据源: {', '.join(result.get('sources', []))}")
        
        print(f"\n{'='*80}")
        print("🎉 测试完成！")
        
    except Exception as e:
        print(f"❌ 系统运行错误: {e}")
    finally:
        system.close()


if __name__ == "__main__":
    asyncio.run(main())