#!/usr/bin/env python3
"""Quick database connection test."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def quick_test():
    """Quick database connection test."""
    from src.database import init_database, get_database
    
    print('🔍 データベース接続テスト...')
    try:
        await init_database()
        database = get_database()
        
        collections = await database.list_collection_names()
        print(f'✅ 接続成功! コレクション数: {len(collections)}')
        
        if collections:
            for col in sorted(collections):
                count = await database[col].count_documents({})
                print(f'  📄 {col}: {count} documents')
        else:
            print('  ⚠️  コレクションがありません')
            
    except Exception as e:
        print(f'❌ エラー: {e}')


if __name__ == "__main__":
    asyncio.run(quick_test())