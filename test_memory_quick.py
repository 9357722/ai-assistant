"""
记忆管理系统快速测试
跳过 Redis 连接测试，只验证核心功能
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_quick():
    """快速测试"""
    print("=" * 60)
    print("记忆管理系统快速测试")
    print("=" * 60)
    
    results = []
    
    # 1. 测试模块导入
    print("\n1. 测试模块导入...")
    try:
        import memory_config
        from services.memory_manager import MemoryManager
        from routes.memory import router
        print("   ✓ 所有模块导入成功")
        results.append(("模块导入", True))
    except Exception as e:
        print(f"   ✗ 模块导入失败: {e}")
        results.append(("模块导入", False))
    
    # 2. 测试配置
    print("\n2. 测试配置文件...")
    try:
        from memory_config import WORKING_MEMORY_TTL, CONFIDENCE_THRESHOLD
        print(f"   ✓ 工作记忆 TTL: {WORKING_MEMORY_TTL}秒")
        print(f"   ✓ 置信度阈值: {CONFIDENCE_THRESHOLD}")
        results.append(("配置文件", True))
    except Exception as e:
        print(f"   ✗ 配置测试失败: {e}")
        results.append(("配置文件", False))
    
    # 3. 测试路由定义
    print("\n3. 测试 API 路由...")
    try:
        from routes.memory import router
        print(f"   ✓ 路由前缀: {router.prefix}")
        
        # 列出所有端点
        print("   API 端点:")
        for route in router.routes:
            if hasattr(route, 'methods'):
                methods = ', '.join(route.methods)
                print(f"     {methods:8s} {route.path}")
        
        # 验证必需端点（注意：FastAPI 的 route.path 包含完整路径）
        endpoints = [route.path for route in router.routes if hasattr(route, 'path')]
        required_suffixes = ['/profile', '/list', '/search', '/clear', '/stats']
        missing = [suffix for suffix in required_suffixes if not any(ep.endswith(suffix) for ep in endpoints)]
        
        if missing:
            print(f"   ⚠️  缺少端点: {missing}")
            results.append(("API 路由", False))
        else:
            print("   ✓ 所有 API 端点都已定义")
            results.append(("API 路由", True))
    except Exception as e:
        print(f"   ✗ 路由测试失败: {e}")
        results.append(("API 路由", False))
    
    # 4. 测试数据库表结构
    print("\n4. 测试数据库表结构...")
    try:
        with open("init.sql", "r", encoding="utf-8") as f:
            sql = f.read()
        
        tables = ["user_profiles", "memory_logs", "user_memory_vectors"]
        all_exist = all(f"CREATE TABLE IF NOT EXISTS {t}" in sql for t in tables)
        
        if all_exist:
            print("   ✓ 所有记忆相关表都已定义")
            for t in tables:
                print(f"     - {t}")
            results.append(("数据库表", True))
        else:
            print("   ✗ 部分表定义缺失")
            results.append(("数据库表", False))
    except Exception as e:
        print(f"   ✗ 数据库表测试失败: {e}")
        results.append(("数据库表", False))
    
    # 5. 测试记忆管理器实例化
    print("\n5. 测试记忆管理器...")
    try:
        from services.memory_manager import MemoryManager
        
        # 模拟 pool
        class MockPool:
            def acquire(self):
                return self
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
        
        manager = MemoryManager(MockPool())
        print("   ✓ MemoryManager 实例化成功")
        print("   ✓ 核心类结构正确")
        results.append(("记忆管理器", True))
    except Exception as e:
        print(f"   ✗ 记忆管理器测试失败: {e}")
        results.append(("记忆管理器", False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name:15s} {status}")
    
    print(f"\n通过率: {passed}/{total} ({passed/total*100:.0f}%)")
    
    if passed == total:
        print("\n" + "🎉" * 20)
        print("\n✅ 所有测试通过！")
        print("\n" + "🎉" * 20)
        
        print("\n📝 注意事项：")
        print("  1. Redis 服务需要启动才能使用工作记忆功能")
        print("  2. 需要执行 init.sql 创建数据库表")
        print("  3. 需要配置 DeepSeek API Key 用于记忆提取")
        print("\n🚀 启动服务：")
        print("  docker compose up -d")
        print("\n📖 查看文档：")
        print("  MEMORY_SYSTEM_README.md")
        
        return True
    else:
        print(f"\n❌ 有 {total-passed} 项测试失败")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_quick())
    sys.exit(0 if success else 1)
