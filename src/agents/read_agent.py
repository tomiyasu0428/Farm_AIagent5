"""Read agent for data retrieval operations with LangChain tools."""

import logging
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain.agents import create_react_agent, AgentExecutor

from src.agents.base_agent import BaseAgent
from src.models.state import AgriAgentState
from src.database import get_database
from src.tools.field_tools import FieldRetrievalTool
from src.tools.work_history_tools import WorkHistoryRetrievalTool
from src.tools.task_management_tools import TaskManagementTool
from src.tools.material_info_tools import MaterialInfoTool

logger = logging.getLogger(__name__)


class ReadAgent(BaseAgent):
    """Agent specialized in reading and retrieving data from the database."""

    def __init__(self):
        """Initialize read agent with LangChain tools."""
        super().__init__("ReadAgent")

        # Initialize all tools
        self.field_tool = FieldRetrievalTool()
        self.work_history_tool = WorkHistoryRetrievalTool()
        self.task_tool = TaskManagementTool()
        self.material_tool = MaterialInfoTool()
        
        self.tools = [
            self.field_tool,
            self.work_history_tool, 
            self.task_tool,
            self.material_tool
        ]

        # Create ReAct agent prompt using the hub template
        from langchain import hub
        
        try:
            # Use the standard ReAct prompt from LangChain Hub
            self.prompt = hub.pull("hwchase17/react")
        except:
            # Fallback to manual ReAct prompt if hub access fails
            from langchain_core.prompts import PromptTemplate
            
            self.prompt = PromptTemplate.from_template("""
あなたは農業管理AIの読み取り専門エージェントです。
農家の方からの質問に対して、利用可能なツールを使って適切な情報を取得し、
親しみやすく実用的な回答を提供してください。

利用可能なツール:
{tools}

ツール使用のガイドライン:
- get_field_information: 圃場情報、面積、土壌、栽培状況
- get_work_history: 作業履歴、過去の農作業記録
- get_task_information: 予定タスク、今後の作業計画
- get_material_information: 資材情報、在庫状況、農薬・肥料データ

回答は300文字以内で、農家の方が理解しやすい言葉で答えてください。

Use the following format:

Question: the input question you must answer  
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}""")

        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,
            early_stopping_method="generate",
            handle_parsing_errors=True,
        )

    async def process(self, state: AgriAgentState) -> Dict[str, Any]:
        """Process read requests using LangChain tools."""
        try:
            user_message = self._extract_last_message(state)
            user_id = state.get("user_id")

            logger.info(f"Processing read request with tools: {user_message}")

            # Check if this query can be handled by LangChain tools
            if await self._should_use_tools(user_message):
                # Use LangChain tool-calling agent
                result = await self.agent_executor.ainvoke({"input": user_message})

                response = result.get("output", "申し訳ございません。回答の生成に失敗しました。")

                return {
                    **self._format_response(response),
                    "query_results": [{"tools_used": "langchain_agent", "success": True}],
                    "extracted_data": {
                        "query_type": "langchain_tools",
                        "data_found": True,
                        "tools_available": ["get_field_information", "get_work_history", "get_task_information", "get_material_information"],
                    },
                }
            else:
                # Fallback to direct database access for other queries
                return await self._process_non_field_query(user_message, user_id)

        except Exception as e:
            logger.error(f"Error in read agent processing: {e}")
            return self._format_response("データの取得中にエラーが発生しました。もう一度お試しください。")

    async def _should_use_tools(self, message: str) -> bool:
        """Determine if the message should be handled by LangChain tools."""
        message_lower = message.lower()
        
        # Field-related keywords
        field_keywords = ["圃場", "畑", "田", "ハウス", "field", "場所", "土地", "栽培", "作物", "面積", "ha", "ヘクタール", "平米", "㎡"]
        
        # Work history keywords
        work_keywords = ["作業", "履歴", "記録", "実施", "実行", "過去", "前回", "work", "history", "やった", "した"]
        
        # Task/schedule keywords  
        task_keywords = ["予定", "タスク", "計画", "今度", "次", "今後", "予約", "スケジュール", "task", "schedule", "予定", "する予定"]
        
        # Material keywords
        material_keywords = ["資材", "農薬", "肥料", "種子", "在庫", "材料", "material", "stock", "薬", "肥", "種"]
        
        # Check for any tool-related keywords
        all_keywords = field_keywords + work_keywords + task_keywords + material_keywords
        if any(keyword in message_lower for keyword in all_keywords):
            return True
            
        # Check for actual field names from database (common field names)
        common_field_names = ["橋前", "橋向こう", "登山道前", "豊緑", "toyomidori", "若菜"]
        if any(field_name in message_lower for field_name in common_field_names):
            return True
            
        # Check for question patterns that suggest data retrieval
        question_patterns = ["教えて", "知りたい", "確認", "見せて", "どう", "どこ", "いつ", "何", "どの", "どれ"]
        if any(pattern in message_lower for pattern in question_patterns):
            return True
            
        return False

    async def _is_field_query(self, message: str) -> bool:
        """Legacy method - determine if the message is asking about field information."""
        field_keywords = ["圃場", "畑", "田", "ハウス", "field", "場所", "土地", "栽培", "作物", "面積", "ha", "ヘクタール", "平米", "㎡"]
        message_lower = message.lower()
        
        # Check for field keywords
        if any(keyword in message_lower for keyword in field_keywords):
            return True
            
        # Check for actual field names from database (common field names)
        common_field_names = ["橋前", "橋向こう", "登山道前", "豊緑", "toyomidori"]
        if any(field_name in message_lower for field_name in common_field_names):
            return True
            
        return False

    async def _process_non_field_query(self, user_message: str, user_id: str) -> Dict[str, Any]:
        """Process non-field queries using direct database access (legacy method)."""
        try:
            # Analyze what data the user is requesting
            query_type = await self._analyze_query(user_message)

            # Retrieve relevant data (excluding field_info which now uses tools)
            data_results = await self._retrieve_data(query_type, user_message, user_id)

            # Generate natural language response
            response = await self._generate_response(user_message, data_results)

            return {
                **self._format_response(response),
                "query_results": data_results,
                "extracted_data": {"query_type": query_type, "data_found": len(data_results) > 0},
            }

        except Exception as e:
            logger.error(f"Error in non-field query processing: {e}")
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

        # Default limit for query results
        LIMIT_DEFAULT = 30

        try:
            if query_type == "field_info":
                # Try to extract potential field name or code from user message
                extracted_key = None
                # Heuristic: take first continuous Kanji/Katakana/Hiragana/Alnum sequence
                import re

                candidates = re.findall(r"[\w一-龥ぁ-んァ-ヶー]+", message)
                if candidates:
                    # Select the longest token as probable name/code
                    extracted_key = max(candidates, key=len)

                if extracted_key and len(extracted_key) >= 2:
                    query = {
                        "$or": [
                            {"name": {"$regex": extracted_key, "$options": "i"}},
                            {"field_code": {"$regex": extracted_key, "$options": "i"}},
                        ]
                    }
                    logger.info(f"Field info search query built: {query}")
                    fields = await database.fields.find(query).limit(LIMIT_DEFAULT).to_list(LIMIT_DEFAULT)
                else:
                    # Fallback: return all (limited)
                    fields = await database.fields.find({}).limit(LIMIT_DEFAULT).to_list(LIMIT_DEFAULT)

                results = fields

            elif query_type == "work_history":
                # Get recent work logs from work_logs collection (core collection)
                work_logs = (
                    await database.work_logs.find({"user_id": user_id}, sort=[("work_date", -1)])
                    .limit(LIMIT_DEFAULT)
                    .to_list(LIMIT_DEFAULT)
                )
                results = work_logs

            elif query_type == "task_list":
                # Get pending tasks - for now get all tasks (would need user-task assignment in production)
                tasks = (
                    await database.tasks.find(
                        {"status": {"$in": ["pending", "in_progress"]}}, sort=[("scheduled_date", 1)]
                    )
                    .limit(LIMIT_DEFAULT)
                    .to_list(LIMIT_DEFAULT)
                )
                results = tasks

            elif query_type == "material_info":
                # Get materials information
                materials = await database.materials.find({}).limit(LIMIT_DEFAULT).to_list(LIMIT_DEFAULT)
                results = materials

            elif query_type == "crop_info":
                # Get crops information
                crops = await database.crops.find({}).limit(LIMIT_DEFAULT).to_list(LIMIT_DEFAULT)
                results = crops

            elif query_type == "general_info":
                # For general queries, get recent farm data from all fields
                farm_data = (
                    await database.farm_data.find({}, sort=[("timestamp", -1)]).limit(5).to_list(5)
                )  # farm_data は直近 5 件で十分
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
                if hasattr(value, "__str__"):
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
