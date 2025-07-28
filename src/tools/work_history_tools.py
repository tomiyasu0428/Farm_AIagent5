"""LangChain tools for work history retrieval with self-correction."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json

from src.database import get_database

logger = logging.getLogger(__name__)


class WorkHistoryQueryInput(BaseModel):
    """Input schema for work history query tool."""

    query_type: str = Field(
        description="Type of work history query: 'recent', 'by_date_range', 'by_field', 'by_work_type', 'by_user'"
    )
    search_value: Optional[str] = Field(
        default=None, 
        description="Search value: field_name, work_type, user_id, or date (YYYY-MM-DD format)"
    )
    start_date: Optional[str] = Field(
        default=None, 
        description="Start date for date range queries (YYYY-MM-DD format)"
    )
    end_date: Optional[str] = Field(
        default=None, 
        description="End date for date range queries (YYYY-MM-DD format)"
    )
    limit: Optional[int] = Field(
        default=20,
        description="Maximum number of results to return (1-50)",
    )


class WorkHistoryRetrievalTool(BaseTool):
    """Dynamic work history retrieval tool with self-correction capability."""

    name: str = "get_work_history"
    description: str = """
作業履歴を柔軟に検索するツールです。以下の検索タイプに対応：
- 'recent': 最近の作業履歴を取得
- 'by_date_range': 日付範囲での検索
- 'by_field': 特定圃場での作業履歴
- 'by_work_type': 作業種別での検索
- 'by_user': 特定ユーザーの作業履歴

例：{'query_type': 'by_field', 'search_value': '橋前', 'limit': 10}
例：{'query_type': 'by_date_range', 'start_date': '2025-07-01', 'end_date': '2025-07-28', 'limit': 20}
    """
    args_schema: type[BaseModel] = WorkHistoryQueryInput

    async def _arun(
        self, 
        query_type: str, 
        search_value: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """Execute work history query with self-correction mechanism."""
        try:
            logger.info(f"WorkHistoryRetrievalTool called with: query_type={query_type}, search_value={search_value}, start_date={start_date}, end_date={end_date}, limit={limit}")
            
            # Input validation and correction
            corrected_params = await self._validate_and_correct_input(
                query_type, search_value, start_date, end_date, limit
            )

            # Execute query with correction loop
            result = await self._execute_with_correction(**corrected_params)

            # Format results for LLM consumption
            return await self._format_results(result, corrected_params)

        except Exception as e:
            logger.error(f"Work history retrieval tool error: {e}", exc_info=True)
            return f"作業履歴の取得中にエラーが発生しました。別の条件でお試しください。"

    def _run(
        self, 
        query_type: str, 
        search_value: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """Synchronous version (not implemented for async database)."""
        return "このツールは非同期実行のみサポートしています。"

    async def _validate_and_correct_input(
        self, 
        query_type: str, 
        search_value: Optional[str], 
        start_date: Optional[str],
        end_date: Optional[str],
        limit: int
    ) -> Dict[str, Any]:
        """Validate and auto-correct input parameters."""

        # Correct query_type
        valid_types = ["recent", "by_date_range", "by_field", "by_work_type", "by_user"]
        if query_type not in valid_types:
            query_type_lower = query_type.lower()
            if "最近" in query_type_lower or "recent" in query_type_lower:
                query_type = "recent"
            elif "日付" in query_type_lower or "期間" in query_type_lower or "date" in query_type_lower:
                query_type = "by_date_range"
            elif "圃場" in query_type_lower or "field" in query_type_lower:
                query_type = "by_field"
            elif "作業" in query_type_lower or "work" in query_type_lower:
                query_type = "by_work_type"
            elif "ユーザー" in query_type_lower or "user" in query_type_lower:
                query_type = "by_user"
            else:
                query_type = "recent"  # Default fallback

        # Correct limit
        if limit < 1:
            limit = 1
        elif limit > 50:
            limit = 50

        # Validate date formats and ranges
        if query_type == "by_date_range":
            start_date, end_date = self._validate_date_range(start_date, end_date)

        # Validate search_value requirement
        if query_type in ["by_field", "by_work_type", "by_user"] and (
            not search_value or str(search_value).strip() == ""
        ):
            logger.info(f"search_value が空のため 'recent' クエリへフォールバック: search_value={search_value}")
            query_type = "recent"
            search_value = None
        else:
            logger.info(f"search_value validation passed: {search_value}")

        logger.info(
            f"Corrected parameters: query_type={query_type}, search_value={search_value}, start_date={start_date}, end_date={end_date}, limit={limit}"
        )

        return {
            "query_type": query_type, 
            "search_value": search_value, 
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit
        }

    def _validate_date_range(self, start_date: Optional[str], end_date: Optional[str]) -> tuple:
        """Validate and correct date range."""
        try:
            # Default to last 30 days if no dates provided
            if not start_date and not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            elif not start_date:
                # If only end_date provided, set start_date to 30 days before
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                start_date = (end_dt - timedelta(days=30)).strftime("%Y-%m-%d")
            elif not end_date:
                # If only start_date provided, set end_date to today
                end_date = datetime.now().strftime("%Y-%m-%d")

            # Validate date format
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")

            # Ensure start_date <= end_date
            if start_date > end_date:
                start_date, end_date = end_date, start_date

            return start_date, end_date

        except ValueError as e:
            logger.warning(f"Invalid date format, using default range: {e}")
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            return start_date, end_date

    async def _execute_with_correction(
        self, 
        query_type: str, 
        search_value: Optional[str], 
        start_date: Optional[str],
        end_date: Optional[str],
        limit: int, 
        retry_count: int = 0
    ) -> List[Dict[str, Any]]:
        """Execute database query with automatic error correction."""

        max_retries = 3
        database = get_database()

        try:
            # Build MongoDB query based on type
            query = {}
            sort = [("work_date", -1)]  # Default sort by most recent

            if query_type == "recent":
                # Get recent work logs (last 30 days)
                recent_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
                query = {"work_date": {"$gte": recent_date}}

            elif query_type == "by_date_range":
                if start_date and end_date:
                    query = {
                        "work_date": {
                            "$gte": start_date,
                            "$lte": end_date
                        }
                    }

            elif query_type == "by_field":
                if search_value and search_value.strip():
                    # Search by field name or field_code
                    query = {
                        "$or": [
                            {"field_name": {"$regex": search_value, "$options": "i"}},
                            {"field_code": {"$regex": search_value, "$options": "i"}}
                        ]
                    }

            elif query_type == "by_work_type":
                if search_value and search_value.strip():
                    query = {"work_type": {"$regex": search_value, "$options": "i"}}

            elif query_type == "by_user":
                if search_value and search_value.strip():
                    query = {"user_id": search_value}

            # Execute query
            logger.info(f"Executing MongoDB query: {query}")
            results = await database.work_logs.find(query).sort(sort).limit(limit).to_list(limit)

            logger.info(f"Query successful: {len(results)} results returned")
            return results

        except Exception as e:
            logger.warning(f"Query failed (attempt {retry_count + 1}): {e}")

            if retry_count < max_retries:
                # Self-correction strategies
                if "field" in str(e).lower():
                    # Field-related error, try simpler query
                    return await self._execute_with_correction(
                        "recent", None, None, None, limit, retry_count + 1
                    )
                elif "date" in str(e).lower():
                    # Date-related error, try recent query
                    return await self._execute_with_correction(
                        "recent", None, None, None, limit, retry_count + 1
                    )
                else:
                    # Generic error, try basic query
                    return await self._execute_with_correction(
                        "recent", None, None, None, min(limit, 10), retry_count + 1
                    )
            else:
                logger.error(f"Max retries exceeded for work history query")
                return []

    async def _format_results(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> str:
        """Format query results for LLM consumption."""

        # Create structured summary
        summary = {
            "total_count": len(results), 
            "query_type": params["query_type"], 
            "work_logs": []
        }

        for work_log in results:
            # Convert dates and handle missing fields
            work_date = work_log.get("work_date", "日付不明")
            if isinstance(work_date, str):
                try:
                    # Try to format date nicely
                    dt = datetime.strptime(work_date, "%Y-%m-%d")
                    work_date = dt.strftime("%Y年%m月%d日")
                except:
                    pass

            work_info = {
                "work_date": work_date,
                "field_name": work_log.get("field_name", "圃場不明"),
                "field_code": work_log.get("field_code", "コード不明"),
                "work_type": work_log.get("work_type", "作業種別不明"),
                "description": work_log.get("description", "詳細なし"),
                "duration_hours": work_log.get("duration_hours", "時間不明"),
                "worker_name": work_log.get("worker_name", "作業者不明"),
                "materials_used": work_log.get("materials_used", []),
                "notes": work_log.get("notes", "")
            }

            summary["work_logs"].append(work_info)

        # Format as natural language for LLM
        result_text = f"作業履歴検索結果: {len(results)}件の作業記録が見つかりました。\n\n"

        for i, work in enumerate(summary["work_logs"], 1):
            result_text += f"{i}. {work['work_date']} - {work['field_name']}\n"
            result_text += f"   作業: {work['work_type']}\n"
            
            if work['description'] and work['description'] != "詳細なし":
                result_text += f"   詳細: {work['description']}\n"
            
            if work['duration_hours'] and work['duration_hours'] != "時間不明":
                result_text += f"   作業時間: {work['duration_hours']}時間\n"
            
            if work['worker_name'] and work['worker_name'] != "作業者不明":
                result_text += f"   作業者: {work['worker_name']}\n"
            
            if work['materials_used'] and len(work['materials_used']) > 0:
                materials = ", ".join([str(m) for m in work['materials_used'][:3]])  # First 3 materials
                result_text += f"   使用資材: {materials}\n"
            
            if work['notes'] and work['notes'].strip():
                result_text += f"   備考: {work['notes'][:50]}{'...' if len(work['notes']) > 50 else ''}\n"
            
            result_text += "\n"

        # Add structured data for further processing
        result_text += f"\n--- 構造化データ ---\n{json.dumps(summary, ensure_ascii=False, indent=2)}"

        return result_text