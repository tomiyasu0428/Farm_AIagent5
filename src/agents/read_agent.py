"""Read agent for data retrieval operations."""

import logging
from typing import Dict, Any, List
from langchain_core.messages import HumanMessage

from src.agents.base_agent import BaseAgent
from src.models.state import AgriAgentState
from src.database import get_database

logger = logging.getLogger(__name__)


class ReadAgent(BaseAgent):
    """Agent specialized in reading and retrieving data from the database."""
    
    def __init__(self):
        """Initialize read agent."""
        super().__init__("ReadAgent")
    
    async def process(self, state: AgriAgentState) -> Dict[str, Any]:
        """Process read requests and return relevant data."""
        try:
            user_message = self._extract_last_message(state)
            user_id = state.get("user_id")
            
            # Analyze what data the user is requesting
            query_type = await self._analyze_query(user_message)
            
            # Retrieve relevant data
            data_results = await self._retrieve_data(query_type, user_message, user_id)
            
            # Generate natural language response
            response = await self._generate_response(user_message, data_results)
            
            return {
                **self._format_response(response),
                "query_results": data_results,
                "extracted_data": {
                    "query_type": query_type,
                    "data_found": len(data_results) > 0
                }
            }
            
        except Exception as e:
            logger.error(f"Error in read agent processing: {e}")
            return self._format_response("データの取得中にエラーが発生しました。もう一度お試しください。")
    
    async def _analyze_query(self, message: str) -> str:
        """Analyze user query to determine what type of data to retrieve."""
        analysis_prompt = f"""
        以下のユーザーメッセージを分析し、どのような種類のデータが求められているかを判定してください。

        ユーザーメッセージ: "{message}"

        可能な分類:
        - field_info: 圃場情報、圃場の状態
        - work_history: 作業履歴、過去の作業記録
        - task_list: 予定されているタスク、今後の作業
        - material_info: 資材情報、農薬や肥料の詳細
        - crop_info: 作物情報、栽培情報
        - general_info: 一般的な情報、その他

        分類名のみを回答してください:
        """
        
        try:
            response = await self.invoke_llm(analysis_prompt)
            query_type = response.strip()
            logger.info(f"Query classified as: {query_type}")
            return query_type
            
        except Exception as e:
            logger.error(f"Error in query analysis: {e}")
            return "general_info"
    
    async def _retrieve_data(self, query_type: str, message: str, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve data from database based on query type."""
        database = get_database()
        results = []
        
        try:
            if query_type == "field_info":
                # Get field information for the user
                fields = await database.fields.find({"farmer_line_id": user_id}).to_list(10)
                results = fields
                
            elif query_type == "work_history":
                # Get recent work logs from work_logs collection (core collection)
                work_logs = await database.work_logs.find(
                    {"user_id": user_id},
                    sort=[("work_date", -1)]
                ).limit(10).to_list(10)
                results = work_logs
                
            elif query_type == "task_list":
                # Get pending tasks
                # First get user's fields, then find tasks for those fields
                user_fields = await database.fields.find(
                    {"farmer_line_id": user_id}, 
                    {"_id": 1}
                ).to_list(100)
                
                if user_fields:
                    field_ids = [field["_id"] for field in user_fields]
                    tasks = await database.tasks.find(
                        {
                            "field_id": {"$in": field_ids},
                            "status": {"$in": ["pending", "in_progress"]}
                        },
                        sort=[("scheduled_date", 1)]
                    ).limit(10).to_list(10)
                    results = tasks
                
            elif query_type == "material_info":
                # Get materials information
                materials = await database.materials.find({}).limit(10).to_list(10)
                results = materials
                
            elif query_type == "crop_info":
                # Get crops information
                crops = await database.crops.find({}).limit(10).to_list(10)
                results = crops
                
            elif query_type == "general_info":
                # For general queries, get recent farm data
                user_fields = await database.fields.find(
                    {"farmer_line_id": user_id}, 
                    {"_id": 1}
                ).to_list(100)
                
                if user_fields:
                    field_ids = [field["_id"] for field in user_fields]
                    farm_data = await database.farm_data.find(
                        {"field_id": {"$in": field_ids}},
                        sort=[("timestamp", -1)]
                    ).limit(5).to_list(5)
                    results = farm_data
            
            logger.info(f"Retrieved {len(results)} records for query type: {query_type}")
            return results
            
        except Exception as e:
            logger.error(f"Database query error: {e}")
            return []
    
    async def _generate_response(self, user_message: str, data_results: List[Dict[str, Any]]) -> str:
        """Generate natural language response based on retrieved data."""
        
        # Convert ObjectId and other non-serializable types to strings for the prompt
        sanitized_results = []
        for result in data_results[:3]:  # Limit to first 3 results for prompt
            sanitized_result = {}
            for key, value in result.items():
                if hasattr(value, '__str__'):
                    sanitized_result[key] = str(value)
                else:
                    sanitized_result[key] = value
            sanitized_results.append(sanitized_result)
        
        if not data_results:
            no_data_prompt = f"""
            ユーザーの質問: "{user_message}"
            
            該当するデータが見つかりませんでした。
            農家の方に親しみやすく、データが見つからなかったことを伝え、
            別の質問や作業記録の登録を提案してください。
            
            200文字以内で回答してください。
            """
            
            try:
                response = await self.invoke_llm(no_data_prompt)
                return response.strip()
            except Exception:
                return "該当するデータが見つかりませんでした。別の条件でお試しいただくか、作業記録の登録はいかがでしょうか？"
        
        response_prompt = f"""
        ユーザーの質問: "{user_message}"
        
        取得されたデータ:
        {sanitized_results}
        
        上記のデータを基に、ユーザーの質問に対して親しみやすく、実用的な回答を生成してください。
        農家の方が理解しやすい言葉で、必要な情報を整理して伝えてください。
        
        300文字以内で回答してください。
        """
        
        try:
            response = await self.invoke_llm(response_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "データを取得しましたが、回答の生成中にエラーが発生しました。詳細については後ほどお確かめください。"