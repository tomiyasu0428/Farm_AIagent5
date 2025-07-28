"""LangChain tools for field information retrieval with self-correction."""

import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json

from src.database import get_database

logger = logging.getLogger(__name__)


class FieldQueryInput(BaseModel):
    """Input schema for field query tool."""

    query_type: str = Field(
        description="Type of field query: 'all', 'by_name', 'by_code', 'by_crop', 'active_only'"
    )
    search_value: Optional[str] = Field(
        default=None, description="Search value when using 'by_name', 'by_code', or 'by_crop' query types"
    )
    limit: Optional[int] = Field(
        default=30,  # Default limit set to 30 for balanced breadth and precision
        description="Maximum number of results to return (1-50)",
    )


class FieldRetrievalTool(BaseTool):
    """Dynamic field information retrieval tool with self-correction capability."""

    name: str = "get_field_information"
    description: str = """
圃場情報を検索するツールです。以下のパラメーターを使用：
- query_type: 検索タイプ ('all', 'by_name', 'by_code', 'by_crop', 'active_only')
- search_value: 検索値（圃場名や圃場コードなど）
- limit: 取得件数（デフォルト30件）

例：{'query_type': 'by_name', 'search_value': '橋前', 'limit': 30}
    """
    args_schema: type[BaseModel] = FieldQueryInput

    async def _arun(self, query_type: str, search_value: Optional[str] = None, limit: int = 30) -> str:
        """Execute field query with self-correction mechanism."""
        try:
            # Input validation and correction
            corrected_params = await self._validate_and_correct_input(query_type, search_value, limit)

            # Execute query with correction loop
            result = await self._execute_with_correction(**corrected_params)

            # Format results for LLM consumption
            return await self._format_results(result, corrected_params)

        except Exception as e:
            logger.error(f"Field retrieval tool error: {e}", exc_info=True)
            return f"圃場情報の取得中にエラーが発生しました。別の条件でお試しください。"

    def _run(self, query_type: str, search_value: Optional[str] = None, limit: int = 10) -> str:
        """Synchronous version (not implemented for async database)."""
        return "このツールは非同期実行のみサポートしています。"

    async def _validate_and_correct_input(
        self, query_type: str, search_value: Optional[str], limit: int
    ) -> Dict[str, Any]:
        """Validate and auto-correct input parameters."""

        # Correct query_type
        valid_types = ["all", "by_name", "by_code", "by_crop", "active_only"]
        if query_type not in valid_types:
            # Try to infer correct type
            query_type_lower = query_type.lower()
            if "名前" in query_type_lower or "name" in query_type_lower:
                query_type = "by_name"
            elif "コード" in query_type_lower or "code" in query_type_lower:
                query_type = "by_code"
            elif "作物" in query_type_lower or "crop" in query_type_lower:
                query_type = "by_crop"
            elif "アクティブ" in query_type_lower or "active" in query_type_lower:
                query_type = "active_only"
            else:
                query_type = "all"  # Default fallback

        # Correct limit
        if limit < 1:
            limit = 1
        elif limit > 50:
            limit = 50

        # Validate search_value requirement
        if query_type in ["by_name", "by_code", "by_crop"] and (
            not search_value or str(search_value).strip() == ""
        ):
            # Self-correction: search_value が無い場合は安全に全件検索へフォールバック
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
        self, query_type: str, search_value: Optional[str], limit: int, retry_count: int = 0
    ) -> List[Dict[str, Any]]:
        """Execute database query with automatic error correction."""

        max_retries = 3
        database = get_database()

        try:
            # Build MongoDB query based on type
            query = {}
            sort = [("name", 1)]  # Default sort

            if query_type == "all":
                query = {}

            elif query_type == "by_name":
                if search_value and search_value.strip():
                    # 部分一致検索を強化（大文字小文字無視、ひらがなカタカナも考慮する場合は別途）
                    query = {"name": {"$regex": search_value, "$options": "i"}}

            elif query_type == "by_code":
                if search_value and search_value.strip():
                    query = {"field_code": {"$regex": search_value, "$options": "i"}}

            elif query_type == "by_crop":
                if search_value:
                    query = {"current_cultivation.crop_name": {"$regex": search_value, "$options": "i"}}

            elif query_type == "active_only":
                query = {"current_cultivation": {"$exists": True, "$ne": None}}

            # Execute query
            logger.info(f"Executing MongoDB query: {query}")
            results = await database.fields.find(query).sort(sort).limit(limit).to_list(limit)

            logger.info(f"Query successful: {len(results)} results returned")
            return results

        except Exception as e:
            logger.warning(f"Query failed (attempt {retry_count + 1}): {e}")

            if retry_count < max_retries:
                # Self-correction: try simpler query
                if query_type != "all":
                    logger.info("Attempting self-correction with simplified query")
                    return await self._execute_with_correction("all", None, limit, retry_count + 1)

            # Final fallback
            logger.error(f"All query attempts failed: {e}")
            return []

    async def _format_results(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> str:
        """Format results for natural language consumption by LLM."""

        if not results:
            return f"検索条件「{params['query_type']}」に該当する圃場が見つかりませんでした。"

        # Create structured summary
        summary = {"total_count": len(results), "query_type": params["query_type"], "fields": []}

        for field in results:
            # Convert area from ㎡ to ha for structured data - handle missing area field
            area_sqm = field.get("area", 0)
            if not isinstance(area_sqm, (int, float)):
                area_sqm = 0
            area_ha = area_sqm / 10000 if area_sqm > 0 else None
            
            field_info = {
                "name": field.get("name", "名前不明"),
                "field_code": field.get("field_code", "コード不明"),
                "area_ha": round(area_ha, 1) if area_ha else "面積不明",
                "area_sqm": area_sqm if isinstance(area_sqm, (int, float)) else "面積不明",
                "soil_type": field.get("soil_type", "土壌不明"),
                "current_crop": None,
                "location": field.get("location", {}),
            }

            # Extract current cultivation info
            if field.get("current_cultivation"):
                cultivation = field["current_cultivation"]
                field_info["current_crop"] = {
                    "crop_name": cultivation.get("crop_name", "作物不明"),
                    "variety": cultivation.get("variety", "品種不明"),
                    "growth_stage": cultivation.get("growth_stage", "成長段階不明"),
                }

            summary["fields"].append(field_info)

        # Format as natural language for LLM
        result_text = f"圃場検索結果: {len(results)}件の圃場が見つかりました。\n\n"

        for i, field in enumerate(summary["fields"], 1):
            result_text += f"{i}. {field['name']}"
            if field["field_code"] != "コード不明":
                result_text += f" ({field['field_code']})"
            
            # Convert area from ㎡ to ha for display
            area_ha = field.get('area_ha', 0)
            area_sqm = field.get('area_sqm', 0)
            if area_ha and isinstance(area_ha, (int, float)) and area_ha > 0:
                result_text += f"\n   面積: {area_ha}ha ({area_sqm:,.0f}㎡), 土壌: {field['soil_type']}\n"
            else:
                result_text += f"\n   面積: 面積不明, 土壌: {field['soil_type']}\n"

            if field["current_crop"]:
                crop = field["current_crop"]
                result_text += (
                    f"   現在栽培: {crop['crop_name']}({crop['variety']}) - {crop['growth_stage']}\n"
                )

            result_text += "\n"

        # Add structured data for further processing
        result_text += f"\n--- 構造化データ ---\n{json.dumps(summary, ensure_ascii=False, indent=2)}"

        return result_text
