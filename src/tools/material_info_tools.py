"""LangChain tools for material information retrieval with self-correction."""

import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json

from src.database import get_database

logger = logging.getLogger(__name__)


class MaterialQueryInput(BaseModel):
    """Input schema for material query tool."""

    query_type: str = Field(
        description="Type of material query: 'all', 'by_name', 'by_type', 'by_stock_status', 'low_stock', 'by_usage'"
    )
    search_value: Optional[str] = Field(
        default=None, 
        description="Search value: material_name, material_type, stock_status, or usage_purpose"
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximum number of results to return (1-50)",
    )


class MaterialInfoTool(BaseTool):
    """Dynamic material information retrieval tool with self-correction capability."""

    name: str = "get_material_information"
    description: str = """
資材情報を柔軟に検索するツールです。以下の検索タイプに対応：
- 'all': 全資材を取得
- 'by_name': 資材名での部分一致検索
- 'by_type': 資材種別での検索 (農薬/肥料/種子/農具など)
- 'by_stock_status': 在庫状況での検索
- 'low_stock': 在庫少ない資材の検索
- 'by_usage': 用途・使用目的での検索

例：{'query_type': 'by_name', 'search_value': '農薬', 'limit': 10}
例：{'query_type': 'low_stock', 'limit': 15}
例：{'query_type': 'by_type', 'search_value': '肥料', 'limit': 20}
    """
    args_schema: type[BaseModel] = MaterialQueryInput

    async def _arun(
        self, 
        query_type: str, 
        search_value: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """Execute material query with self-correction mechanism."""
        try:
            logger.info(f"MaterialInfoTool called with: query_type={query_type}, search_value={search_value}, limit={limit}")
            
            # Input validation and correction
            corrected_params = await self._validate_and_correct_input(query_type, search_value, limit)

            # Execute query with correction loop
            result = await self._execute_with_correction(**corrected_params)

            # Format results for LLM consumption
            return await self._format_results(result, corrected_params)

        except Exception as e:
            logger.error(f"Material info tool error: {e}", exc_info=True)
            return f"資材情報の取得中にエラーが発生しました。別の条件でお試しください。"

    def _run(
        self, 
        query_type: str, 
        search_value: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """Synchronous version (not implemented for async database)."""
        return "このツールは非同期実行のみサポートしています。"

    async def _validate_and_correct_input(
        self, 
        query_type: str, 
        search_value: Optional[str], 
        limit: int
    ) -> Dict[str, Any]:
        """Validate and auto-correct input parameters."""

        # Correct query_type
        valid_types = ["all", "by_name", "by_type", "by_stock_status", "low_stock", "by_usage"]
        if query_type not in valid_types:
            query_type_lower = query_type.lower()
            if "名前" in query_type_lower or "name" in query_type_lower:
                query_type = "by_name"
            elif "種別" in query_type_lower or "タイプ" in query_type_lower or "type" in query_type_lower:
                query_type = "by_type"
            elif "在庫" in query_type_lower or "stock" in query_type_lower:
                if "少ない" in query_type_lower or "不足" in query_type_lower or "low" in query_type_lower:
                    query_type = "low_stock"
                else:
                    query_type = "by_stock_status"
            elif "用途" in query_type_lower or "使用" in query_type_lower or "usage" in query_type_lower:
                query_type = "by_usage"
            else:
                query_type = "all"  # Default fallback

        # Correct limit
        if limit < 1:
            limit = 1
        elif limit > 50:
            limit = 50

        # Validate search_value requirement
        if query_type in ["by_name", "by_type", "by_stock_status", "by_usage"] and (
            not search_value or str(search_value).strip() == ""
        ):
            logger.info(f"search_value が空のため 'all' クエリへフォールバック: search_value={search_value}")
            query_type = "all"
            search_value = None
        else:
            logger.info(f"search_value validation passed: {search_value}")

        logger.info(
            f"Corrected parameters: query_type={query_type}, search_value={search_value}, limit={limit}"
        )

        return {"query_type": query_type, "search_value": search_value, "limit": limit}

    async def _execute_with_correction(
        self, 
        query_type: str, 
        search_value: Optional[str], 
        limit: int, 
        retry_count: int = 0
    ) -> List[Dict[str, Any]]:
        """Execute database query with automatic error correction."""

        max_retries = 3
        database = get_database()

        try:
            # Build MongoDB query based on type
            query = {}
            sort = [("material_name", 1)]  # Default sort by name

            if query_type == "all":
                query = {}

            elif query_type == "by_name":
                if search_value and search_value.strip():
                    # 部分一致検索
                    query = {"material_name": {"$regex": search_value, "$options": "i"}}

            elif query_type == "by_type":
                if search_value and search_value.strip():
                    # 資材種別検索（農薬、肥料、種子、農具など）
                    type_mapping = {
                        "農薬": ["農薬", "殺虫剤", "殺菌剤", "除草剤"],
                        "肥料": ["肥料", "化成肥料", "有機肥料", "液肥"],
                        "種子": ["種子", "種", "苗"],
                        "農具": ["農具", "道具", "機械", "器具"],
                        "資材": ["資材", "マルチ", "支柱", "ネット"]
                    }
                    
                    # Exact match first, then category match
                    search_terms = [search_value]
                    for category, terms in type_mapping.items():
                        if search_value.lower() in [t.lower() for t in terms]:
                            search_terms.extend(terms)
                    
                    query = {
                        "$or": [
                            {"material_type": {"$regex": term, "$options": "i"}} 
                            for term in search_terms
                        ]
                    }

            elif query_type == "by_stock_status":
                if search_value and search_value.strip():
                    # 在庫状況検索
                    status_mapping = {
                        "充分": {"$gte": 100},
                        "十分": {"$gte": 100},
                        "普通": {"$gte": 50, "$lt": 100},
                        "少ない": {"$gt": 0, "$lt": 50},
                        "不足": {"$gt": 0, "$lt": 20},
                        "切れ": {"$lte": 0},
                        "在庫切れ": {"$lte": 0}
                    }
                    
                    stock_condition = status_mapping.get(search_value.lower())
                    if stock_condition:
                        query = {"current_stock": stock_condition}
                    else:
                        # Try direct search in stock_status field if exists
                        query = {"stock_status": {"$regex": search_value, "$options": "i"}}

            elif query_type == "low_stock":
                # 在庫が少ない資材を検索（閾値以下）
                query = {
                    "$or": [
                        {"current_stock": {"$lt": 20}},  # 20個未満
                        {"stock_status": {"$regex": "少ない|不足|低", "$options": "i"}}
                    ]
                }
                sort = [("current_stock", 1)]  # 在庫少ない順

            elif query_type == "by_usage":
                if search_value and search_value.strip():
                    # 用途・使用目的での検索
                    query = {
                        "$or": [
                            {"usage_purpose": {"$regex": search_value, "$options": "i"}},
                            {"application": {"$regex": search_value, "$options": "i"}},
                            {"target_crops": {"$regex": search_value, "$options": "i"}}
                        ]
                    }

            # Execute query
            logger.info(f"Executing MongoDB query: {query}")
            results = await database.materials.find(query).sort(sort).limit(limit).to_list(limit)

            logger.info(f"Query successful: {len(results)} results returned")
            return results

        except Exception as e:
            logger.warning(f"Query failed (attempt {retry_count + 1}): {e}")

            if retry_count < max_retries:
                # Self-correction strategies
                if "stock" in str(e).lower():
                    # Stock-related error, try all materials
                    return await self._execute_with_correction(
                        "all", None, limit, retry_count + 1
                    )
                elif "type" in str(e).lower():
                    # Type-related error, try by name
                    return await self._execute_with_correction(
                        "by_name", search_value, limit, retry_count + 1
                    )
                else:
                    # Generic error, try basic query
                    return await self._execute_with_correction(
                        "all", None, min(limit, 10), retry_count + 1
                    )
            else:
                logger.error(f"Max retries exceeded for material query")
                return []

    async def _format_results(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> str:
        """Format query results for LLM consumption."""

        # Create structured summary
        summary = {
            "total_count": len(results), 
            "query_type": params["query_type"], 
            "materials": []
        }

        for material in results:
            # Handle stock status
            current_stock = material.get("current_stock", 0)
            stock_status = "不明"
            if isinstance(current_stock, (int, float)):
                if current_stock <= 0:
                    stock_status = "在庫切れ"
                elif current_stock < 20:
                    stock_status = "少ない"
                elif current_stock < 50:
                    stock_status = "普通"
                else:
                    stock_status = "充分"

            material_info = {
                "material_name": material.get("material_name", "資材名不明"),
                "material_type": material.get("material_type", "種別不明"),
                "current_stock": current_stock,
                "stock_status": stock_status,
                "unit": material.get("unit", "個"),
                "price_per_unit": material.get("price_per_unit", "価格不明"),
                "supplier": material.get("supplier", "供給元不明"),
                "usage_purpose": material.get("usage_purpose", "用途不明"),
                "application_method": material.get("application_method", "使用方法不明"),
                "target_crops": material.get("target_crops", []),
                "safety_notes": material.get("safety_notes", ""),
                "expiry_date": material.get("expiry_date", "期限不明"),
                "storage_conditions": material.get("storage_conditions", "保管条件不明")
            }

            summary["materials"].append(material_info)

        # Format as natural language for LLM
        result_text = f"資材情報検索結果: {len(results)}件の資材が見つかりました。\n\n"

        for i, material in enumerate(summary["materials"], 1):
            result_text += f"{i}. {material['material_name']}\n"
            result_text += f"   種別: {material['material_type']}\n"
            result_text += f"   在庫: {material['current_stock']}{material['unit']} ({material['stock_status']})\n"
            
            if material['price_per_unit'] and material['price_per_unit'] != "価格不明":
                result_text += f"   価格: {material['price_per_unit']}円/{material['unit']}\n"
            
            if material['supplier'] and material['supplier'] != "供給元不明":
                result_text += f"   供給元: {material['supplier']}\n"
            
            if material['usage_purpose'] and material['usage_purpose'] != "用途不明":
                result_text += f"   用途: {material['usage_purpose']}\n"
            
            if material['application_method'] and material['application_method'] != "使用方法不明":
                result_text += f"   使用方法: {material['application_method'][:50]}{'...' if len(material['application_method']) > 50 else ''}\n"
            
            if material['target_crops'] and len(material['target_crops']) > 0:
                crops = ", ".join([str(c) for c in material['target_crops'][:3]])  # First 3 crops
                result_text += f"   対象作物: {crops}\n"
            
            if material['expiry_date'] and material['expiry_date'] != "期限不明":
                result_text += f"   期限: {material['expiry_date']}\n"
            
            if material['safety_notes'] and material['safety_notes'].strip():
                result_text += f"   安全注意: {material['safety_notes'][:50]}{'...' if len(material['safety_notes']) > 50 else ''}\n"
            
            # Stock alert
            if material['current_stock'] < 20:
                result_text += f"   ⚠️ 在庫少ない - 補充を検討してください\n"
            
            result_text += "\n"

        # Add structured data for further processing
        result_text += f"\n--- 構造化データ ---\n{json.dumps(summary, ensure_ascii=False, indent=2)}"

        return result_text