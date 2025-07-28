"""Supervisor agent for routing and orchestration."""

import logging
from typing import Dict, Any
from langchain_core.messages import HumanMessage

from src.agents.base_agent import BaseAgent
from src.models.state import AgriAgentState

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Supervisor agent that routes user requests to appropriate specialist agents."""
    
    def __init__(self):
        """Initialize supervisor agent."""
        super().__init__("Supervisor")
        
        # Available agents for routing
        self.available_agents = [
            "ReadAgent",
            "WriteAgent", 
            "RecommendationAgent",
            "NotificationAgent"
        ]
    
    async def process(self, state: AgriAgentState) -> Dict[str, Any]:
        """Process user message and route to appropriate agent."""
        try:
            user_message = self._extract_last_message(state)
            
            # Route based on message content
            next_agent = await self._route_message(user_message)
            
            # If it's a simple greeting or general query, handle directly
            if next_agent == "Supervisor":
                response = await self._handle_direct_response(user_message)
                return self._format_response(response)
            
            # Route to specialist agent
            return {
                "next_agent": next_agent,
                "agent_data": {
                    "routed_by": self.name,
                    "routing_reason": f"Message classified for {next_agent}"
                }
            }
            
        except Exception as e:
            logger.error(f"Error in supervisor processing: {e}")
            return self._format_response("申し訳ございません。エラーが発生しました。もう一度お試しください。")
    
    async def _route_message(self, message: str) -> str:
        """Route message to appropriate agent based on content analysis."""
        routing_prompt = f"""
        あなたは農業AIシステムの司令塔です。以下のユーザーメッセージを分析し、最適なエージェントに振り分けてください。

        ユーザーメッセージ: "{message}"

        利用可能なエージェント:
        - ReadAgent: データの読み取り、検索、参照（作業履歴、圃場情報、資材情報など）
        - WriteAgent: データの書き込み、作業記録の登録、タスクの作成
        - RecommendationAgent: 作業提案、最適化提案、分析結果の提供
        - NotificationAgent: 通知、リマインダー、アラートの設定
        - Supervisor: 一般的な挨拶、システム説明、簡単な質問

        以下の形式で回答してください（エージェント名のみ）:
        ReadAgent
        """
        
        try:
            response = await self.invoke_llm(routing_prompt)
            agent_name = response.strip()
            
            # Validate agent name
            if agent_name in self.available_agents + ["Supervisor"]:
                logger.info(f"Routed message to {agent_name}")
                return agent_name
            else:
                logger.warning(f"Invalid agent name: {agent_name}, defaulting to ReadAgent")
                return "ReadAgent"
                
        except Exception as e:
            logger.error(f"Error in message routing: {e}")
            return "ReadAgent"  # Default fallback
    
    async def _handle_direct_response(self, message: str) -> str:
        """Handle messages that don't need routing to specialist agents."""
        direct_response_prompt = f"""
        あなたは農業管理AIアシスタントです。農家の方との会話において、親しみやすく、専門的で、実用的な回答を提供してください。

        ユーザーメッセージ: "{message}"

        以下のような場合は直接回答してください:
        - 挨拶や一般的な質問
        - システムの使い方の説明
        - 簡単な農業知識の質問

        回答は200文字以内で、温かみのある敬語で答えてください。
        """
        
        try:
            response = await self.invoke_llm(direct_response_prompt)
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error in direct response: {e}")
            return "こんにちは！農業管理AIアシスタントです。作業記録の確認や登録、作業提案など、お気軽にお声かけください。"