#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CSV数据转Neo4j知识图谱
将dataset目录下的CSV文件转换为Neo4j知识图谱数据库
"""

import os
import sys
import pandas as pd
import configparser
import logging
from typing import Dict, List, Any

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
    log_file_path = os.path.join(log_dir, "csv_to_neo4j.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

class CSVToNeo4jConverter:
    """CSV转Neo4j转换器"""
    
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
    
    def clear_database(self):
        """清空数据库"""
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                # 删除所有节点和关系
                session.run("MATCH (n) DETACH DELETE n")
                self.logger.info("数据库清空完成")
                return True
        except Exception as e:
            self.logger.error(f"清空数据库失败: {e}")
            return False
    
    def load_processes_data(self):
        """加载工艺数据"""
        processes_file = "dataset/processes.csv"
        if not os.path.exists(processes_file):
            self.logger.error(f"工艺数据文件不存在: {processes_file}")
            return None
        
        try:
            df = pd.read_csv(processes_file)
            self.logger.info(f"加载工艺数据: {len(df)} 条记录")
            return df
        except Exception as e:
            self.logger.error(f"加载工艺数据失败: {e}")
            return None
    
    def load_tools_data(self):
        """加载刀具数据"""
        tools_file = "dataset/tools.csv"
        if not os.path.exists(tools_file):
            self.logger.error(f"刀具数据文件不存在: {tools_file}")
            return None
        
        try:
            df = pd.read_csv(tools_file)
            self.logger.info(f"加载刀具数据: {len(df)} 条记录")
            return df
        except Exception as e:
            self.logger.error(f"加载刀具数据失败: {e}")
            return None
    
    def create_feature_nodes(self, processes_df):
        """创建特征节点"""
        if not self.driver or processes_df is None:
            return False
        
        try:
            with self.driver.session() as session:
                # 获取唯一的特征
                features = processes_df[['特征ID', '特征名称']].drop_duplicates()
                
                for _, row in features.iterrows():
                    feature_id = row['特征ID']
                    feature_name = row['特征名称']
                    
                    # 创建特征节点
                    query = """
                    MERGE (f:Feature {id: $feature_id, name: $feature_name})
                    """
                    session.run(query, feature_id=feature_id, feature_name=feature_name)
                
                self.logger.info(f"创建特征节点: {len(features)} 个")
                return True
        except Exception as e:
            self.logger.error(f"创建特征节点失败: {e}")
            return False
    
    def create_process_nodes(self, processes_df):
        """创建工艺节点"""
        if not self.driver or processes_df is None:
            return False
        
        try:
            with self.driver.session() as session:
                for _, row in processes_df.iterrows():
                    # 创建工艺节点
                    query = """
                    CREATE (p:Process {
                        template_id: $template_id,
                        feature_id: $feature_id,
                        feature_name: $feature_name,
                        component_surface: $component_surface,
                        feature_surface: $feature_surface,
                        surface_type: $surface_type,
                        sidewall_feature: $sidewall_feature,
                        allowance: $allowance,
                        process_stage: $process_stage,
                        process_type: $process_type
                    })
                    """
                    session.run(query,
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
                
                self.logger.info(f"创建工艺节点: {len(processes_df)} 个")
                return True
        except Exception as e:
            self.logger.error(f"创建工艺节点失败: {e}")
            return False
    
    def create_tool_nodes(self, tools_df):
        """创建刀具节点"""
        if not self.driver or tools_df is None:
            return False
        
        try:
            with self.driver.session() as session:
                for _, row in tools_df.iterrows():
                    # 创建刀具节点
                    query = """
                    CREATE (t:Tool {
                        id: $tool_id,
                        name: $tool_name,
                        diameter: $diameter,
                        r_angle: $r_angle,
                        flute_count: $flute_count,
                        extension_length: $extension_length
                    })
                    """
                    session.run(query,
                        tool_id=row['刀具id'],
                        tool_name=row['刀具名称'],
                        diameter=row['直径'],
                        r_angle=row['R角'],
                        flute_count=row['刃数'],
                        extension_length=row['伸出长']
                    )
                
                self.logger.info(f"创建刀具节点: {len(tools_df)} 个")
                return True
        except Exception as e:
            self.logger.error(f"创建刀具节点失败: {e}")
            return False
    
    def create_relationships(self, processes_df):
        """创建关系"""
        if not self.driver or processes_df is None:
            return False
        
        try:
            with self.driver.session() as session:
                # 创建特征-工艺关系
                for _, row in processes_df.iterrows():
                    query = """
                    MATCH (f:Feature {id: $feature_id})
                    MATCH (p:Process {template_id: $template_id})
                    MERGE (f)-[:HAS_PROCESS]->(p)
                    """
                    session.run(query,
                        feature_id=row['特征ID'],
                        template_id=row['模板编号']
                    )
                
                # 创建工艺类型分组关系
                process_types = processes_df['工艺类型'].dropna().unique()
                for process_type in process_types:
                    # 创建工艺类型节点
                    query = """
                    MERGE (pt:ProcessType {name: $process_type})
                    """
                    session.run(query, process_type=process_type)
                    
                    # 连接工艺到工艺类型
                    query = """
                    MATCH (pt:ProcessType {name: $process_type})
                    MATCH (p:Process {process_type: $process_type})
                    MERGE (p)-[:BELONGS_TO]->(pt)
                    """
                    session.run(query, process_type=process_type)
                
                self.logger.info("创建关系完成")
                return True
        except Exception as e:
            self.logger.error(f"创建关系失败: {e}")
            return False
    
    def create_indexes(self):
        """创建索引"""
        if not self.driver:
            return False
        
        try:
            with self.driver.session() as session:
                # 创建索引
                indexes = [
                    "CREATE INDEX IF NOT EXISTS FOR (f:Feature) ON (f.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (f:Feature) ON (f.name)",
                    "CREATE INDEX IF NOT EXISTS FOR (p:Process) ON (p.template_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (p:Process) ON (p.feature_id)",
                    "CREATE INDEX IF NOT EXISTS FOR (t:Tool) ON (t.id)",
                    "CREATE INDEX IF NOT EXISTS FOR (t:Tool) ON (t.name)",
                    "CREATE INDEX IF NOT EXISTS FOR (pt:ProcessType) ON (pt.name)"
                ]
                
                for index_query in indexes:
                    session.run(index_query)
                
                self.logger.info("创建索引完成")
                return True
        except Exception as e:
            self.logger.error(f"创建索引失败: {e}")
            return False
    
    def get_statistics(self):
        """获取统计信息"""
        if not self.driver:
            return None
        
        try:
            with self.driver.session() as session:
                stats = {}
                
                # 节点统计
                result = session.run("MATCH (n:Feature) RETURN count(n) as count")
                stats['features'] = result.single()['count']
                
                result = session.run("MATCH (n:Process) RETURN count(n) as count")
                stats['processes'] = result.single()['count']
                
                result = session.run("MATCH (n:Tool) RETURN count(n) as count")
                stats['tools'] = result.single()['count']
                
                result = session.run("MATCH (n:ProcessType) RETURN count(n) as count")
                stats['process_types'] = result.single()['count']
                
                # 关系统计
                result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
                stats['relationships'] = result.single()['count']
                
                return stats
        except Exception as e:
            self.logger.error(f"获取统计信息失败: {e}")
            return None
    
    def convert(self):
        """执行转换"""
        self.logger.info("开始CSV到Neo4j转换...")
        
        # 连接数据库
        if not self.connect_neo4j():
            return False
        
        # 清空数据库
        print("正在清空数据库...")
        if not self.clear_database():
            return False
        
        # 加载数据
        print("正在加载CSV数据...")
        processes_df = self.load_processes_data()
        tools_df = self.load_tools_data()
        
        if processes_df is None:
            return False
        
        # 创建节点
        print("正在创建特征节点...")
        if not self.create_feature_nodes(processes_df):
            return False
        
        print("正在创建工艺节点...")
        if not self.create_process_nodes(processes_df):
            return False
        
        if tools_df is not None:
            print("正在创建刀具节点...")
            if not self.create_tool_nodes(tools_df):
                return False
        
        # 创建关系
        print("正在创建关系...")
        if not self.create_relationships(processes_df):
            return False
        
        # 创建索引
        print("正在创建索引...")
        if not self.create_indexes():
            return False
        
        # 获取统计信息
        stats = self.get_statistics()
        if stats:
            print("\n=== 转换完成统计 ===")
            print(f"特征节点: {stats['features']} 个")
            print(f"工艺节点: {stats['processes']} 个")
            print(f"刀具节点: {stats['tools']} 个")
            print(f"工艺类型节点: {stats['process_types']} 个")
            print(f"关系: {stats['relationships']} 个")
            print("=====================")
        
        self.logger.info("CSV到Neo4j转换完成")
        return True
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j连接已关闭")

def main():
    """主函数"""
    print("=== CSV数据转Neo4j知识图谱 ===")
    
    # 加载配置
    config = load_config()
    logger = configure_logging(config)
    
    # 显示配置信息
    print(f"Neo4j URI: {config.get('neo4j', 'uri')}")
    print(f"用户名: {config.get('neo4j', 'username')}")
    print("=" * 40)
    
    converter = CSVToNeo4jConverter(config)
    
    try:
        success = converter.convert()
        if success:
            print("✅ 转换成功完成！")
        else:
            print("❌ 转换失败！")
    except Exception as e:
        logger.error(f"转换过程出错: {e}")
        print(f"❌ 转换过程出错: {e}")
    finally:
        converter.close()

if __name__ == "__main__":
    main()