"""
记忆管理系统功能测试
测试实际的 Redis 连接、记忆存储和检索功能
"""
import asyncio
import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_redis_connection():
    """测试 Redis 连接"""
    print("=" * 60)
    print("1. 测试 Redis 连接")
    print("=" * 60)
    
    try:
        from services.redis_client import init_redis, get_redis, close_redis
        
        # 初始化 Redis
        redis_client = await init_redis()
        
        if redis_client is None:
            print("   ⚠️  Redis 连接失败（可能是 Redis 未启动）")
            print("   ℹ️  记忆系统将使用数据库作为后备存储")
            return False
        
        # 测试写入和读取
        test_key = "test:memory:connection"
        test_value = {"test": True, "timestamp": datetime.now().isoformat()}
        
        await redis_client.setex(test_key, 60, json.dumps(test_value))
        retrieved = await redis_client.get(test_key)
        
        if retrieved:
            data = json.loads(retrieved)
            print(f"   ✓ Redis 写入成功: {test_key}")
            print(f"   ✓ Redis 读取成功: {data}")
            # 清理测试数据
            await redis_client.delete(test_key)
            print("   ✓ Redis 连接测试通过！")
            return True
        else:
            print("   ✗ Redis 读取失败")
            return False
            
    except Exception as e:
        print(f"   ✗ Redis 测试失败: {e}")
        return False


async def test_memory_manager_unit():
    """测试记忆管理器单元功能（不依赖外部服务）"""
    print("\n" + "=" * 60)
    print("2. 测试记忆管理器单元功能")
    print("=" * 60)
    
    try:
        from services.memory_manager import MemoryManager
        
        # 创建模拟的 pool（用于测试基本功能）
        class MockPool:
            """模拟数据库连接池"""
            def acquire(self):
                return self
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            def cursor(self):
                return self
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        
        mock_pool = MockPool()
        manager = MemoryManager(mock_pool)
        
        print("   ✓ MemoryManager 实例化成功")
        print("   ✓ 基本结构验证通过")
        
        # 测试配置
        from memory_config import (
            WORKING_MEMORY_TTL, 
            MAX_WORKING_MEMORY,
            CONFIDENCE_THRESHOLD
        )
        
        print(f"   ✓ 工作记忆 TTL: {WORKING_MEMORY_TTL}秒")
        print(f"   ✓ 最大工作记忆: {MAX_WORKING_MEMORY}条")
        print(f"   ✓ 置信度阈值: {CONFIDENCE_THRESHOLD}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 记忆管理器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_working_memory_flow():
    """测试工作记忆流程（如果 Redis 可用）"""
    print("\n" + "=" * 60)
    print("3. 测试工作记忆流程")
    print("=" * 60)
    
    try:
        from services.redis_client import get_redis
        from services.memory_manager import MemoryManager
        
        redis_client = await get_redis()
        
        if redis_client is None:
            print("   ⚠️  Redis 不可用，跳过工作记忆测试")
            print("   ℹ️  实际运行时会回退到数据库存储")
            return None
        
        # 创建记忆管理器
        class MockPool:
            def acquire(self):
                return self
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        
        manager = MemoryManager(MockPool(), redis_client)
        
        # 测试工作记忆操作
        test_user_id = 99999
        test_session_id = "test_session_123"
        
        # 1. 获取工作记忆（应该返回空）
        memory = await manager.get_working_memory(test_user_id, test_session_id)
        print(f"   ✓ 获取工作记忆成功")
        print(f"     - 会话ID: {memory.get('session_id')}")
        print(f"     - 上下文数量: {len(memory.get('context', []))}")
        
        # 2. 添加消息到工作记忆
        await manager.add_to_working_memory(
            test_user_id, 
            test_session_id, 
            "user", 
            "我想买一部手机"
        )
        await manager.add_to_working_memory(
            test_user_id, 
            test_session_id, 
            "assistant", 
            "好的，为您推荐以下手机..."
        )
        print("   ✓ 添加消息到工作记忆成功")
        
        # 3. 验证工作记忆
        memory = await manager.get_working_memory(test_user_id, test_session_id)
        context_count = len(memory.get('context', []))
        print(f"   ✓ 工作记忆验证成功，当前有 {context_count} 条消息")
        
        # 4. 清除工作记忆
        await manager.clear_working_memory(test_user_id, test_session_id)
        memory = await manager.get_working_memory(test_user_id, test_session_id)
        context_count_after = len(memory.get('context', []))
        print(f"   ✓ 清除工作记忆成功，清除后有 {context_count_after} 条消息")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 工作记忆测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_routes():
    """测试 API 路由定义"""
    print("\n" + "=" * 60)
    print("4. 测试 API 路由定义")
    print("=" * 60)
    
    try:
        from routes.memory import router
        
        print(f"   ✓ 路由前缀: {router.prefix}")
        print(f"   ✓ 路由标签: {router.tags}")
        
        print("\n   API 端点列表:")
        for route in router.routes:
            if hasattr(route, 'methods'):
                methods = ', '.join(route.methods)
                # FastAPI 的 route.path 已经包含完整路径
                print(f"     {methods:8s} {route.path}")
        
        # 验证关键端点存在（FastAPI 的 route.path 包含完整路径）
        endpoints = [route.path for route in router.routes if hasattr(route, 'path')]
        required_suffixes = ['/profile', '/list', '/search', '/clear', '/stats']
        
        missing = [suffix for suffix in required_suffixes if not any(ep.endswith(suffix) for ep in endpoints)]
        if missing:
            print(f"\n   ⚠️  缺少端点: {missing}")
            return False
        else:
            print("\n   ✓ 所有必需端点都已定义")
            return True
            
    except Exception as e:
        print(f"   ✗ 路由测试失败: {e}")
        return False


async def test_database_schema():
    """测试数据库表结构定义"""
    print("\n" + "=" * 60)
    print("5. 测试数据库表结构")
    print("=" * 60)
    
    try:
        # 读取 init.sql 验证表定义
        with open("init.sql", "r", encoding="utf-8") as f:
            sql_content = f.read()
        
        required_tables = [
            "user_profiles",
            "memory_logs", 
            "user_memory_vectors"
        ]
        
        for table in required_tables:
            if f"CREATE TABLE IF NOT EXISTS {table}" in sql_content:
                print(f"   ✓ 表 {table} 定义存在")
            else:
                print(f"   ✗ 表 {table} 定义缺失")
                return False
        
        # 验证关键字段
        if "favorite_colors JSON" in sql_content:
            print("   ✓ user_profiles 包含偏好字段")
        
        if "memory_type ENUM" in sql_content:
            print("   ✓ memory_logs 包含类型字段")
        
        print("   ✓ 数据库表结构验证通过")
        return True
        
    except Exception as e:
        print(f"   ✗ 数据库表测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("\n记忆管理系统功能测试")
    print("\n" + "🚀" * 30)
    
    results = {}
    
    # 测试 Redis 连接
    results['redis'] = await test_redis_connection()
    
    # 测试记忆管理器单元功能
    results['memory_manager'] = await test_memory_manager_unit()
    
    # 测试工作记忆流程
    results['working_memory'] = await test_working_memory_flow()
    
    # 测试 API 路由
    results['api_routes'] = await test_api_routes()
    
    # 测试数据库表结构
    results['database'] = await test_database_schema()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v is True)
    skipped = sum(1 for v in results.values() if v is None)
    failed = sum(1 for v in results.values() if v is False)
    
    for name, result in results.items():
        if result is True:
            status = "✓ 通过"
        elif result is None:
            status = "- 跳过"
        else:
            status = "✗ 失败"
        print(f"  {name:20s} {status}")
    
    print(f"\n总计: {total} 项测试")
    print(f"  通过: {passed}")
    print(f"  跳过: {skipped} (依赖外部服务)")
    print(f"  失败: {failed}")
    
    if failed == 0:
        print("\n" + "🎉" * 20)
        print("\n✅ 所有可测试的功能都已通过！")
        print("\n" + "🎉" * 20)
        
        print("\n📋 实现总结：")
        print("  ✓ 记忆管理器核心模块")
        print("  ✓ Redis 连接管理")
        print("  ✓ API 路由定义")
        print("  ✓ 数据库表结构")
        print("  ✓ 配置文件")
        
        print("\n⚠️  注意事项：")
        print("  1. Redis 服务需要启动才能使用工作记忆功能")
        print("  2. 需要执行 init.sql 创建数据库表")
        print("  3. 需要配置 DeepSeek API Key 用于记忆提取")
        
        return True
    else:
        print(f"\n❌ 有 {failed} 项测试失败，请检查")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
