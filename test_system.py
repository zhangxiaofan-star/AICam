#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统测试脚本
用于验证环境配置和基本功能
"""

import os
import sys
import pandas as pd
from dotenv import load_dotenv

def test_environment():
    """测试环境配置"""
    print("=== 环境测试 ===")
    
    # 测试Python版本
    print(f"Python版本: {sys.version}")
    
    # 测试必要的包
    required_packages = ['pandas', 'neo4j', 'lightrag', 'openai', 'python-dotenv']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} 已安装")
        except ImportError:
            print(f"✗ {package} 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n缺少以下包: {', '.join(missing_packages)}")
        print("请运行: pip install " + " ".join(missing_packages))
        return False
    
    return True

def test_data_files():
    """测试数据文件"""
    print("\n=== 数据文件测试 ===")
    
    files_to_check = [
        "./dataset/processes.csv",
        "./dataset/tools.csv"
    ]
    
    all_files_exist = True
    
    for file_path in files_to_check:
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path, encoding='utf-8')
                print(f"✓ {file_path} 存在，包含 {len(df)} 行数据")
            except Exception as e:
                print(f"✗ {file_path} 读取失败: {e}")
                all_files_exist = False
        else:
            print(f"✗ {file_path} 不存在")
            all_files_exist = False
    
    return all_files_exist

def test_config():
    """测试配置文件"""
    print("\n=== 配置文件测试 ===")
    
    if not os.path.exists('.env'):
        print("✗ .env 文件不存在")
        print("请创建 .env 文件并配置必要参数")
        return False
    
    load_dotenv()
    
    required_configs = [
        'NEO4J_URI',
        'NEO4J_USERNAME', 
        'NEO4J_PASSWORD',
        'OPENAI_API_KEY'
    ]
    
    missing_configs = []
    
    for config in required_configs:
        value = os.getenv(config)
        if value and value != 'your_openai_api_key_here' and value != 'password':
            print(f"✓ {config} 已配置")
        else:
            print(f"✗ {config} 未配置或使用默认值")
            missing_configs.append(config)
    
    if missing_configs:
        print(f"\n需要配置: {', '.join(missing_configs)}")
        return False
    
    return True

def test_neo4j_connection():
    """测试Neo4j连接"""
    print("\n=== Neo4j连接测试 ===")
    
    try:
        from neo4j import GraphDatabase
        load_dotenv()
        
        uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
        username = os.getenv('NEO4J_USERNAME', 'neo4j')
        password = os.getenv('NEO4J_PASSWORD', 'password')
        
        driver = GraphDatabase.driver(uri, auth=(username, password))
        
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]
            
        driver.close()
        
        if test_value == 1:
            print("✓ Neo4j连接成功")
            return True
        else:
            print("✗ Neo4j连接测试失败")
            return False
            
    except Exception as e:
        print(f"✗ Neo4j连接失败: {e}")
        print("请确保Neo4j服务正在运行，并检查连接配置")
        return False

def test_openai_api():
    """测试OpenAI API"""
    print("\n=== OpenAI API测试 ===")
    
    try:
        import openai
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        
        if not api_key or api_key == 'your_openai_api_key_here':
            print("✗ OpenAI API Key未配置")
            return False
        
        # 简单的API测试（不实际调用，避免费用）
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        print("✓ OpenAI客户端初始化成功")
        print("注意：未进行实际API调用测试以避免费用")
        return True
        
    except Exception as e:
        print(f"✗ OpenAI API测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("加工工艺知识图谱系统 - 环境测试")
    print("=" * 50)
    
    tests = [
        ("环境配置", test_environment),
        ("数据文件", test_data_files),
        ("配置文件", test_config),
        ("Neo4j连接", test_neo4j_connection),
        ("OpenAI API", test_openai_api)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"✗ {test_name}测试出错: {e}")
            results[test_name] = False
    
    # 总结
    print("\n" + "=" * 50)
    print("测试结果总结:")
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"  {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 所有测试通过！系统已准备就绪。")
        print("\n下一步:")
        print("1. 运行 python csv_to_neo4j.py 构建知识图谱")
        print("2. 运行 python lightrag_retrieval.py 启动检索系统")
    else:
        print("❌ 部分测试失败，请根据上述信息修复问题。")
        print("\n常见解决方案:")
        print("1. 安装缺失的Python包")
        print("2. 启动Neo4j数据库服务")
        print("3. 配置.env文件中的参数")
        print("4. 检查网络连接")

if __name__ == "__main__":
    main()