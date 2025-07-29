#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
加工工艺知识图谱构建器
将CSV数据转换为Neo4j知识图谱
"""

import pandas as pd
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcessKnowledgeGraphBuilder:
    def __init__(self):
        """初始化知识图谱构建器"""
        load_dotenv()
        
        # Neo4j连接配置
        self.uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        self.username = os.getenv('NEO4J_USERNAME', 'neo4j')
        self.password = os.getenv('NEO4J_PASSWORD', 'zxfneo4j')
        
        # 初始化Neo4j驱动
        self.driver = None
        self.connect_to_neo4j()
        
    def connect_to_neo4j(self):
        """连接到Neo4j数据库"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("成功连接到Neo4j数据库")
        except Exception as e:
            logger.error(f"连接Neo4j失败: {e}")
            logger.info("请确保Neo4j服务正在运行，并检查连接配置")
            
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            
    def clear_database(self):
        """清空数据库（可选）"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("数据库已清空")
        
    def create_constraints_and_indexes(self):
        """创建约束和索引"""
        with self.driver.session() as session:
            # 创建唯一性约束
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Process) REQUIRE p.template_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Tool) REQUIRE t.tool_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (f:Feature) REQUIRE f.feature_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Surface) REQUIRE s.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (pt:ProcessType) REQUIRE pt.name IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (ps:ProcessStage) REQUIRE ps.name IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"创建约束: {constraint}")
                except Exception as e:
                    logger.warning(f"约束可能已存在: {e}")
                    
    def load_processes_data(self, csv_path):
        """加载工艺数据"""
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            logger.info(f"成功加载工艺数据，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"加载工艺数据失败: {e}")
            return None
            
    def load_tools_data(self, csv_path):
        """加载刀具数据"""
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            logger.info(f"成功加载刀具数据，共{len(df)}条记录")
            return df
        except Exception as e:
            logger.error(f"加载刀具数据失败: {e}")
            return None
            
    def create_process_nodes(self, processes_df):
        """创建工艺节点"""
        with self.driver.session() as session:
            for _, row in processes_df.iterrows():
                # 创建工艺模板节点
                session.run("""
                    MERGE (p:Process {template_id: $template_id})
                    SET p.feature_id = $feature_id,
                        p.feature_name = $feature_name,
                        p.component_surface = $component_surface,
                        p.feature_surface = $feature_surface,
                        p.surface_type = $surface_type,
                        p.sidewall_feature = $sidewall_feature,
                        p.allowance = $allowance,
                        p.process_stage = $process_stage,
                        p.process_type = $process_type
                """, 
                template_id=row['模板编号'],
                feature_id=row['特征ID'],
                feature_name=row['特征名称'],
                component_surface=row['组成面'],
                feature_surface=row['特征面'],
                surface_type=row['面类型'],
                sidewall_feature=row['侧壁特征'],
                allowance=row['余量'],
                process_stage=row['工序阶段'],
                process_type=row['工艺类型']
                )
                
                # 创建特征节点
                session.run("""
                    MERGE (f:Feature {feature_id: $feature_id})
                    SET f.name = $feature_name
                """, 
                feature_id=row['特征ID'],
                feature_name=row['特征名称']
                )
                
                # 创建面类型节点
                if pd.notna(row['面类型']):
                    session.run("""
                        MERGE (s:Surface {name: $surface_type})
                    """, surface_type=row['面类型'])
                
                # 创建工艺类型节点
                if pd.notna(row['工艺类型']):
                    session.run("""
                        MERGE (pt:ProcessType {name: $process_type})
                    """, process_type=row['工艺类型'])
                
                # 创建工序阶段节点
                if pd.notna(row['工序阶段']):
                    session.run("""
                        MERGE (ps:ProcessStage {name: $process_stage})
                    """, process_stage=row['工序阶段'])
                    
        logger.info("工艺节点创建完成")
        
    def create_tool_nodes(self, tools_df):
        """创建刀具节点"""
        with self.driver.session() as session:
            for _, row in tools_df.iterrows():
                session.run("""
                    MERGE (t:Tool {tool_id: $tool_id})
                    SET t.name = $tool_name,
                        t.diameter = $diameter,
                        t.r_angle = $r_angle,
                        t.flute_count = $flute_count,
                        t.extension_length = $extension_length
                """,
                tool_id=row['刀具id'],
                tool_name=row['刀具名称'],
                diameter=row['直径'],
                r_angle=row['R角'],
                flute_count=row['刃数'],
                extension_length=row['伸出长']
                )
                
        logger.info("刀具节点创建完成")
        
    def create_relationships(self, processes_df):
        """创建关系"""
        with self.driver.session() as session:
            for _, row in processes_df.iterrows():
                # 工艺-特征关系
                session.run("""
                    MATCH (p:Process {template_id: $template_id})
                    MATCH (f:Feature {feature_id: $feature_id})
                    MERGE (p)-[:PROCESSES]->(f)
                """,
                template_id=row['模板编号'],
                feature_id=row['特征ID']
                )
                
                # 工艺-面类型关系
                if pd.notna(row['面类型']):
                    session.run("""
                        MATCH (p:Process {template_id: $template_id})
                        MATCH (s:Surface {name: $surface_type})
                        MERGE (p)-[:USES_SURFACE]->(s)
                    """,
                    template_id=row['模板编号'],
                    surface_type=row['面类型']
                    )
                
                # 工艺-工艺类型关系
                if pd.notna(row['工艺类型']):
                    session.run("""
                        MATCH (p:Process {template_id: $template_id})
                        MATCH (pt:ProcessType {name: $process_type})
                        MERGE (p)-[:HAS_TYPE]->(pt)
                    """,
                    template_id=row['模板编号'],
                    process_type=row['工艺类型']
                    )
                
                # 工艺-工序阶段关系
                if pd.notna(row['工序阶段']):
                    session.run("""
                        MATCH (p:Process {template_id: $template_id})
                        MATCH (ps:ProcessStage {name: $process_stage})
                        MERGE (p)-[:IN_STAGE]->(ps)
                    """,
                    template_id=row['模板编号'],
                    process_stage=row['工序阶段']
                    )
                    
        logger.info("关系创建完成")
        
    def create_tool_process_relationships(self):
        """创建刀具和工艺的推荐关系（基于规则）"""
        with self.driver.session() as session:
            # 示例：为不同的工艺类型推荐合适的刀具
            # 这里可以根据实际的工艺知识来定义规则
            
            # 底壁铣推荐平底刀具
            session.run("""
                MATCH (p:Process)-[:HAS_TYPE]->(pt:ProcessType {name: '底壁铣'})
                MATCH (t:Tool) WHERE t.name CONTAINS 'D'
                MERGE (t)-[:RECOMMENDED_FOR]->(p)
            """)
            
            # 平面轮廓铣推荐球头刀具
            session.run("""
                MATCH (p:Process)-[:HAS_TYPE]->(pt:ProcessType {name: '平面轮廓铣'})
                MATCH (t:Tool) WHERE t.name CONTAINS 'B'
                MERGE (t)-[:RECOMMENDED_FOR]->(p)
            """)
            
        logger.info("刀具-工艺推荐关系创建完成")
        
    def build_knowledge_graph(self, processes_csv_path, tools_csv_path, clear_db=False):
        """构建完整的知识图谱"""
        try:
            if clear_db:
                self.clear_database()
                
            # 创建约束和索引
            self.create_constraints_and_indexes()
            
            # 加载数据
            processes_df = self.load_processes_data(processes_csv_path)
            tools_df = self.load_tools_data(tools_csv_path)
            
            if processes_df is None or tools_df is None:
                logger.error("数据加载失败，无法构建知识图谱")
                return False
                
            # 创建节点
            self.create_process_nodes(processes_df)
            self.create_tool_nodes(tools_df)
            
            # 创建关系
            self.create_relationships(processes_df)
            self.create_tool_process_relationships()
            
            logger.info("知识图谱构建完成！")
            return True
            
        except Exception as e:
            logger.error(f"构建知识图谱时发生错误: {e}")
            return False
            
    def get_graph_statistics(self):
        """获取图谱统计信息"""
        with self.driver.session() as session:
            # 节点统计
            node_counts = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """).data()
            
            # 关系统计
            rel_counts = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as relationship, count(r) as count
                ORDER BY count DESC
            """).data()
            
            logger.info("=== 知识图谱统计信息 ===")
            logger.info("节点统计:")
            for item in node_counts:
                logger.info(f"  {item['label']}: {item['count']}")
                
            logger.info("关系统计:")
            for item in rel_counts:
                logger.info(f"  {item['relationship']}: {item['count']}")

def main():
    """主函数"""
    # 数据文件路径
    processes_csv = "./dataset/processes.csv"
    tools_csv = "./dataset/tools.csv"
    
    # 创建知识图谱构建器
    builder = ProcessKnowledgeGraphBuilder()
    
    try:
        # 构建知识图谱
        success = builder.build_knowledge_graph(
            processes_csv_path=processes_csv,
            tools_csv_path=tools_csv,
            clear_db=True  # 设置为True会清空现有数据
        )
        
        if success:
            # 显示统计信息
            builder.get_graph_statistics()
        else:
            logger.error("知识图谱构建失败")
            
    finally:
        # 关闭连接
        builder.close()

if __name__ == "__main__":
    main()