#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加工工艺和刀具决策系统
根据工件特征、尺寸等参数，智能推荐加工工艺和刀具
"""

import logging
import configparser
from typing import Dict, List, Tuple, Optional
from neo4j import GraphDatabase


class MachiningAdvisor:
    """加工工艺和刀具决策顾问"""
    
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
        except Exception as e:
            self.logger.error(f"Neo4j连接失败: {e}")
            return False
    
    def find_suitable_tools(self, diameter_limit: float, height: float) -> List[Dict]:
        """
            根据尺寸限制查找合适的刀具

            Args:
                diameter_limit: 直径限制（长宽最小值）
                height: 工件高度

            Returns:
                符合条件的刀具列表
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                # 查找符合条件的刀具：直径 <= diameter_limit 且 伸出长 > height
                query = """
                    MATCH (t:Tool)
                    WHERE t.diameter <= $diameter_limit AND t.extension_length > $height
                    RETURN t.id as tool_id, t.name as tool_name, 
                           t.diameter as diameter, t.extension_length as extension_length,
                           t.r_angle as r_angle, t.flute_count as flute_count
                    ORDER BY t.diameter DESC, t.extension_length ASC
                """
                
                result = session.run(query, 
                                   diameter_limit=diameter_limit, 
                                   height=height)
                
                tools = []
                for record in result:
                    tool_info = {
                        'tool_id': record['tool_id'],
                        'tool_name': record['tool_name'],
                        'diameter': record['diameter'],
                        'extension_length': record['extension_length'],
                        'r_angle': record['r_angle'],
                        'flute_count': record['flute_count']
                    }
                    tools.append(tool_info)
                
                self.logger.info(f"找到 {len(tools)} 个符合条件的刀具")
                return tools
                
        except Exception as e:
            self.logger.error(f"查找刀具失败: {e}")
            return []
    
    def find_process_template(self, feature_name: str, surface_type: str, 
                            process_stage: str) -> List[Dict]:
        """
            根据特征名称、特征面和工序阶段查找工艺模板

            Args:
                feature_name: 特征名称（如：矩形通孔、圆柱凸台等）
                surface_type: 特征面类型（如：平面、垂直面等）
                process_stage: 工序阶段（如：粗加工、半精加工、精加工等）

            Returns:
                匹配的工艺模板列表
        """
        if not self.driver:
            return []
        
        try:
            with self.driver.session() as session:
                # 精确匹配查询
                query = """
                    MATCH (f:Feature)-[:HAS_PROCESS]->(p:Process)
                    WHERE f.name = $feature_name 
                    AND (p.surface_type = $surface_type OR p.feature_surface = $surface_type)
                    AND p.process_stage = $process_stage
                    RETURN  p.template_id as template_id, p.process_type as process_type,
                            p.feature_surface as feature_surface, p.surface_type as surface_type,
                            p.process_stage as process_stage, p.component_surface as component_surface,
                            f.name as feature_name
                    ORDER BY p.template_id
                """
                
                result = session.run(query, 
                                    feature_name=feature_name,
                                    surface_type=surface_type,
                                    process_stage=process_stage)
                
                processes = []
                for record in result:
                    process_info = {
                        'template_id': record['template_id'],
                        'process_type': record['process_type'],
                        'feature_surface': record['feature_surface'],
                        'surface_type': record['surface_type'],
                        'process_stage': record['process_stage'],
                        'component_surface': record['component_surface'],
                        'feature_name': record['feature_name']
                    }
                    processes.append(process_info)
                
                self.logger.info(f"找到 {len(processes)} 个匹配的工艺模板")
                return processes
                
        except Exception as e:
            self.logger.error(f"查找工艺模板失败: {e}")
            return []
    
    def get_machining_recommendation(self, feature_name: str, surface_type: str, 
                                    process_stage: str, length: float, width: float, 
                                    height: float) -> Dict:
        """
            获取完整的加工推荐方案

            Args:
                feature_name: 特征名称
                surface_type: 特征面类型
                process_stage: 工序阶段
                length: 长度
                width: 宽度
                height: 高度

            Returns:
                包含工艺模板和刀具推荐的完整方案
        """
        # 计算尺寸限制
        diameter_limit = min(length, width)
        
        # 查找工艺模板
        process_templates = self.find_process_template(feature_name, surface_type, process_stage)
        
        # 查找合适的刀具
        suitable_tools = self.find_suitable_tools(diameter_limit, height)
        
        # 构建推荐结果
        recommendation = {
            'input_parameters': {
                'feature_name': feature_name,
                'surface_type': surface_type,
                'process_stage': process_stage,
                'dimensions': {
                    'length': length,
                    'width': width,
                    'height': height,
                    'diameter_limit': diameter_limit
                }
            },
            'process_templates': process_templates,
            'suitable_tools': suitable_tools,
            'recommendation_summary': self._generate_recommendation_summary(
                process_templates, suitable_tools, diameter_limit, height
            )
        }
        
        return recommendation
    
    def _generate_recommendation_summary(self, process_templates: List[Dict], 
                                       suitable_tools: List[Dict], 
                                       diameter_limit: float, height: float) -> str:
        """生成推荐摘要"""
        summary = []
        
        # 工艺推荐摘要
        if process_templates:
            if len(process_templates) == 1:
                template = process_templates[0]
                summary.append(f"推荐工艺模板：{template['template_id']} ({template['process_type']})")
            else:
                template_ids = [p['template_id'] for p in process_templates]
                summary.append(f"找到 {len(process_templates)} 个匹配的工艺模板：{', '.join(template_ids)}")
        else:
            summary.append("未找到匹配的工艺模板")
        
        # 刀具推荐摘要
        if suitable_tools:
            best_tool = suitable_tools[0]  # 按直径降序、伸出长升序排列，第一个是最优的
            summary.append(f"推荐刀具：{best_tool['tool_id']} ({best_tool['tool_name']})")
            summary.append(f"刀具直径：{best_tool['diameter']}mm (限制：≤{diameter_limit}mm)")
            summary.append(f"伸出长：{best_tool['extension_length']}mm (要求：>{height}mm)")
            
            if len(suitable_tools) > 1:
                summary.append(f"共有 {len(suitable_tools)} 个刀具符合条件")
        else:
            summary.append(f"未找到符合条件的刀具 (需要：直径≤{diameter_limit}mm，伸出长>{height}mm)")
        
        return "\n".join(summary)
    
    def get_decision_rules_prompt(self) -> str:
        """获取决策规则的系统提示"""
        return """
            你是一个专业的加工工艺顾问。请根据以下决策规则为用户提供加工工艺和刀具推荐：

            ## 工艺模板决策规则：
            1. 根据特征名称（如：矩形通孔、圆柱凸台、矩形凹槽等）进行初步筛选
            2. 根据特征面类型（如：平面、垂直面等）进行精确匹配
            3. 根据工序阶段（如：粗加工、半精加工、精加工、清根等）确定唯一模板
            4. 输出格式：模板ID（如：P001）和工艺类型（如：底壁铣、平面轮廓铣等）

            ## 刀具选择决策规则：
            1. 直径限制：刀具直径 ≤ min(长度, 宽度)
            2. 伸出长限制：刀具伸出长 > 工件高度
            3. 优选原则：在满足条件的刀具中，优先选择直径较大的刀具（加工效率高）
            4. 输出格式：刀具ID（如：T001）

            ## 回答要求：
            1. 严格按照上述规则进行决策
            2. 如果找到唯一匹配，直接给出推荐
            3. 如果有多个选择，说明原因并给出最优推荐
            4. 如果没有找到匹配，说明具体原因
            5. 使用中文回答，格式简洁明确
        """
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j连接已关闭")


def load_config():
    """加载配置文件"""
    config = configparser.ConfigParser()
    config_file = "config.ini"
    
    try:
        config.read(config_file, encoding='utf-8')
        print(f"✅ 配置文件加载成功: {config_file}")
        return config
    except Exception as e:
        print(f"❌ 配置文件加载失败: {e}")
        return None


async def main():
    """测试主函数"""
    print("=== 加工工艺和刀具决策系统测试 ===")
    
    # 加载配置
    config = load_config()
    if not config:
        return
    
    # 创建决策顾问
    advisor = MachiningAdvisor(config)
    
    # 连接数据库
    if not advisor.connect_neo4j():
        print("❌ 数据库连接失败")
        return
    
    print("✅ 系统初始化成功")
    
    # 测试案例
    test_cases = [
        {
            'feature_name': '圆柱通孔',
            'surface_type': '平面',
            'process_stage': '精加工',
            'length': 10.0,
            'width': 10.0,
            'height': 5.0
        },
        {
            'feature_name': '矩形凸台',
            'surface_type': '垂直面',
            'process_stage': '半精加工',
            'length': 20.0,
            'width': 15.0,
            'height': 8.0
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n--- 测试案例 {i} ---")
        print(f"特征名称：{case['feature_name']}")
        print(f"特征面：{case['surface_type']}")
        print(f"工序阶段：{case['process_stage']}")
        print(f"尺寸：{case['length']}×{case['width']}×{case['height']}mm")
        
        recommendation = advisor.get_machining_recommendation(**case)
        
        print("\n推荐结果：")
        print(recommendation['recommendation_summary'])
    
    advisor.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())