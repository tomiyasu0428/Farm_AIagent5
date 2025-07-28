"""LangChain tools for task management with self-correction."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json

from src.database import get_database

logger = logging.getLogger(__name__)


class TaskQueryInput(BaseModel):
    """Input schema for task query tool."""

    query_type: str = Field(
        description="Type of task query: 'upcoming', 'overdue', 'by_status', 'by_field', 'by_priority', 'by_date_range'"
    )
    search_value: Optional[str] = Field(
        default=None, 
        description="Search value: status, field_name, priority, or date (YYYY-MM-DD format)"
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


class TaskManagementTool(BaseTool):
    """Dynamic task management tool with self-correction capability."""

    name: str = "get_task_information"
    description: str = """
タスク・予定を柔軟に検索するツールです。以下の検索タイプに対応：
- 'upcoming': 今後予定されているタスク
- 'overdue': 期限切れのタスク
- 'by_status': ステータス別検索 (pending/in_progress/completed/cancelled)
- 'by_field': 特定圃場のタスク
- 'by_priority': 優先度別検索 (high/medium/low)
- 'by_date_range': 日付範囲での検索

例：{'query_type': 'upcoming', 'limit': 10}
例：{'query_type': 'by_status', 'search_value': 'pending', 'limit': 15}
例：{'query_type': 'by_field', 'search_value': '橋前', 'limit': 10}
    """
    args_schema: type[BaseModel] = TaskQueryInput

    async def _arun(
        self, 
        query_type: str, 
        search_value: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 20
    ) -> str:
        """Execute task query with self-correction mechanism."""
        try:
            logger.info(f"TaskManagementTool called with: query_type={query_type}, search_value={search_value}, start_date={start_date}, end_date={end_date}, limit={limit}")
            
            # Input validation and correction
            corrected_params = await self._validate_and_correct_input(
                query_type, search_value, start_date, end_date, limit
            )

            # Execute query with correction loop
            result = await self._execute_with_correction(**corrected_params)

            # Format results for LLM consumption
            return await self._format_results(result, corrected_params)

        except Exception as e:
            logger.error(f"Task management tool error: {e}", exc_info=True)
            return f"タスク情報の取得中にエラーが発生しました。別の条件でお試しください。"

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
        valid_types = ["upcoming", "overdue", "by_status", "by_field", "by_priority", "by_date_range"]
        if query_type not in valid_types:
            query_type_lower = query_type.lower()
            if "今後" in query_type_lower or "予定" in query_type_lower or "upcoming" in query_type_lower:
                query_type = "upcoming"
            elif "期限切れ" in query_type_lower or "遅延" in query_type_lower or "overdue" in query_type_lower:
                query_type = "overdue"
            elif "ステータス" in query_type_lower or "状態" in query_type_lower or "status" in query_type_lower:
                query_type = "by_status"
            elif "圃場" in query_type_lower or "field" in query_type_lower:
                query_type = "by_field"
            elif "優先度" in query_type_lower or "priority" in query_type_lower:
                query_type = "by_priority"
            elif "日付" in query_type_lower or "期間" in query_type_lower or "date" in query_type_lower:
                query_type = "by_date_range"
            else:
                query_type = "upcoming"  # Default fallback

        # Correct limit
        if limit < 1:
            limit = 1
        elif limit > 50:
            limit = 50

        # Validate date formats and ranges
        if query_type == "by_date_range":
            start_date, end_date = self._validate_date_range(start_date, end_date)

        # Validate search_value requirement
        if query_type in ["by_status", "by_field", "by_priority"] and (
            not search_value or str(search_value).strip() == ""
        ):
            logger.info(f"search_value が空のため 'upcoming' クエリへフォールバック: search_value={search_value}")
            query_type = "upcoming"
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
            # Default to next 30 days if no dates provided
            if not start_date and not end_date:
                start_date = datetime.now().strftime("%Y-%m-%d")
                end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            elif not start_date:
                # If only end_date provided, set start_date to today
                start_date = datetime.now().strftime("%Y-%m-%d")
            elif not end_date:
                # If only start_date provided, set end_date to 30 days after start
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_date = (start_dt + timedelta(days=30)).strftime("%Y-%m-%d")

            # Validate date format
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")

            # Ensure start_date <= end_date
            if start_date > end_date:
                start_date, end_date = end_date, start_date

            return start_date, end_date

        except ValueError as e:
            logger.warning(f"Invalid date format, using default range: {e}")
            start_date = datetime.now().strftime("%Y-%m-%d")
            end_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
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
            sort = [("scheduled_date", 1)]  # Default sort by earliest first

            today = datetime.now().strftime("%Y-%m-%d")

            if query_type == "upcoming":
                # Get upcoming tasks (future dates, not completed)
                query = {
                    "scheduled_date": {"$gte": today},
                    "status": {"$in": ["pending", "in_progress"]}
                }

            elif query_type == "overdue":
                # Get overdue tasks (past dates, not completed)
                query = {
                    "scheduled_date": {"$lt": today},
                    "status": {"$in": ["pending", "in_progress"]}
                }
                sort = [("scheduled_date", 1)]  # Oldest overdue first

            elif query_type == "by_status":
                if search_value and search_value.strip():
                    # Normalize status values
                    status_mapping = {
                        "pending": "pending",
                        "待機": "pending",
                        "未開始": "pending",
                        "in_progress": "in_progress",
                        "進行中": "in_progress",
                        "実行中": "in_progress",
                        "completed": "completed",
                        "完了": "completed",
                        "終了": "completed",
                        "cancelled": "cancelled",
                        "キャンセル": "cancelled",
                        "中止": "cancelled"
                    }
                    status = status_mapping.get(search_value.lower(), search_value.lower())
                    query = {"status": status}

            elif query_type == "by_field":
                if search_value and search_value.strip():
                    # Search by field name or field_code
                    query = {
                        "$or": [
                            {"field_name": {"$regex": search_value, "$options": "i"}},
                            {"field_code": {"$regex": search_value, "$options": "i"}}
                        ]
                    }

            elif query_type == "by_priority":
                if search_value and search_value.strip():
                    # Normalize priority values
                    priority_mapping = {
                        "high": "high",
                        "高": "high",
                        "緊急": "high",
                        "medium": "medium",
                        "中": "medium",
                        "普通": "medium",
                        "low": "low",
                        "低": "low",
                        "後回し": "low"
                    }
                    priority = priority_mapping.get(search_value.lower(), search_value.lower())
                    query = {"priority": priority}

            elif query_type == "by_date_range":
                if start_date and end_date:
                    query = {
                        "scheduled_date": {
                            "$gte": start_date,
                            "$lte": end_date
                        }
                    }

            # Execute query
            logger.info(f"Executing MongoDB query: {query}")
            results = await database.tasks.find(query).sort(sort).limit(limit).to_list(limit)

            logger.info(f"Query successful: {len(results)} results returned")
            return results

        except Exception as e:
            logger.warning(f"Query failed (attempt {retry_count + 1}): {e}")

            if retry_count < max_retries:
                # Self-correction strategies
                if "field" in str(e).lower():
                    # Field-related error, try upcoming query
                    return await self._execute_with_correction(
                        "upcoming", None, None, None, limit, retry_count + 1
                    )
                elif "date" in str(e).lower():
                    # Date-related error, try upcoming query
                    return await self._execute_with_correction(
                        "upcoming", None, None, None, limit, retry_count + 1
                    )
                else:
                    # Generic error, try basic query
                    return await self._execute_with_correction(
                        "upcoming", None, None, None, min(limit, 10), retry_count + 1
                    )
            else:
                logger.error(f"Max retries exceeded for task query")
                return []

    async def _format_results(self, results: List[Dict[str, Any]], params: Dict[str, Any]) -> str:
        """Format query results for LLM consumption."""

        # Create structured summary
        summary = {
            "total_count": len(results), 
            "query_type": params["query_type"], 
            "tasks": []
        }

        for task in results:
            # Convert dates and handle missing fields
            scheduled_date = task.get("scheduled_date", "日付不明")
            if isinstance(scheduled_date, str):
                try:
                    # Try to format date nicely
                    dt = datetime.strptime(scheduled_date, "%Y-%m-%d")
                    scheduled_date = dt.strftime("%Y年%m月%d日")
                except:
                    pass

            # Status translation
            status_translation = {
                "pending": "待機中",
                "in_progress": "進行中", 
                "completed": "完了",
                "cancelled": "キャンセル"
            }
            status = status_translation.get(task.get("status", "unknown"), task.get("status", "不明"))

            # Priority translation
            priority_translation = {
                "high": "高",
                "medium": "中",
                "low": "低"
            }
            priority = priority_translation.get(task.get("priority", "medium"), task.get("priority", "中"))

            task_info = {
                "scheduled_date": scheduled_date,
                "task_name": task.get("task_name", "タスク名不明"),
                "field_name": task.get("field_name", "圃場不明"),
                "field_code": task.get("field_code", "コード不明"),
                "work_type": task.get("work_type", "作業種別不明"),
                "description": task.get("description", "詳細なし"),
                "status": status,
                "priority": priority,
                "estimated_duration": task.get("estimated_duration", "時間不明"),
                "assigned_to": task.get("assigned_to", "担当者不明"),
                "materials_needed": task.get("materials_needed", []),
                "notes": task.get("notes", "")
            }

            summary["tasks"].append(task_info)

        # Format as natural language for LLM
        result_text = f"タスク検索結果: {len(results)}件のタスクが見つかりました。\n\n"

        for i, task in enumerate(summary["tasks"], 1):
            result_text += f"{i}. {task['scheduled_date']} - {task['task_name']}\n"
            result_text += f"   圃場: {task['field_name']} ({task['field_code']})\n"
            result_text += f"   作業: {task['work_type']}\n"
            result_text += f"   状態: {task['status']} | 優先度: {task['priority']}\n"
            
            if task['description'] and task['description'] != "詳細なし":
                result_text += f"   詳細: {task['description']}\n"
            
            if task['estimated_duration'] and task['estimated_duration'] != "時間不明":
                result_text += f"   予想時間: {task['estimated_duration']}\n"
            
            if task['assigned_to'] and task['assigned_to'] != "担当者不明":
                result_text += f"   担当者: {task['assigned_to']}\n"
            
            if task['materials_needed'] and len(task['materials_needed']) > 0:
                materials = ", ".join([str(m) for m in task['materials_needed'][:3]])  # First 3 materials
                result_text += f"   必要資材: {materials}\n"
            
            if task['notes'] and task['notes'].strip():
                result_text += f"   備考: {task['notes'][:50]}{'...' if len(task['notes']) > 50 else ''}\n"
            
            result_text += "\n"

        # Add structured data for further processing
        result_text += f"\n--- 構造化データ ---\n{json.dumps(summary, ensure_ascii=False, indent=2)}"

        return result_text