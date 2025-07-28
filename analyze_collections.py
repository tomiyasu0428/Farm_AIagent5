#!/usr/bin/env python3
"""Analyze current collections for consolidation."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def analyze_collections():
    """Analyze all collections in detail."""
    from src.database import init_database, get_database
    
    await init_database()
    database = get_database()
    
    collections = await database.list_collection_names()
    print('📊 現在のコレクション詳細分析:')
    print('=' * 60)
    
    collection_analysis = {}
    
    for col in sorted(collections):
        count = await database[col].count_documents({})
        sample = await database[col].find_one({})
        
        print(f'\n📄 {col}: {count}件')
        
        if sample:
            fields = list(sample.keys())
            print(f'   全フィールド: {fields}')
            
            # Show sample data structure
            print('   サンプルデータ構造:')
            for key, value in list(sample.items())[:3]:
                if key != '_id':
                    print(f'     {key}: {type(value).__name__} = {str(value)[:50]}...')
        else:
            print('   ⚠️ 空のコレクション')
            
        collection_analysis[col] = {
            'count': count,
            'fields': list(sample.keys()) if sample else [],
            'has_data': count > 0
        }
    
    print('\n\n🔍 重複・統合候補の分析:')
    print('=' * 60)
    
    # Find potential duplicates
    role_groups = {
        'ユーザー管理': [],
        '圃場・作業管理': [],
        'タスク・スケジュール': [], 
        'データ・ログ': [],
        'マスター・参照': [],
        'システム管理': []
    }
    
    for col, data in collection_analysis.items():
        if 'farmer' in col or 'worker' in col or 'user' in col:
            role_groups['ユーザー管理'].append(col)
        elif 'field' in col or 'work' in col:
            role_groups['圃場・作業管理'].append(col)
        elif 'task' in col or 'schedule' in col:
            role_groups['タスク・スケジュール'].append(col)
        elif 'data' in col or 'log' in col or 'record' in col:
            role_groups['データ・ログ'].append(col)
        elif 'crop' in col or 'material' in col:
            role_groups['マスター・参照'].append(col)
        else:
            role_groups['システム管理'].append(col)
    
    for role, collections in role_groups.items():
        if collections:
            print(f'\n{role}:')
            for col in collections:
                print(f'  • {col} ({collection_analysis[col]["count"]}件)')


if __name__ == "__main__":
    asyncio.run(analyze_collections())