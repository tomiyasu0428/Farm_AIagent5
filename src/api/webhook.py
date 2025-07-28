"""LINE Webhook API endpoints."""

import hashlib
import hmac
import base64
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError, InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from src.config import settings
from src.agents.graph import process_user_message

logger = logging.getLogger(__name__)

# Initialize LINE SDK
line_bot_api = LineBotApi(settings.line_channel_access_token)
handler = WebhookHandler(settings.line_channel_secret)

webhook_router = APIRouter()


def verify_signature(body: bytes, signature: str) -> bool:
    """Verify LINE webhook signature."""
    hash = hmac.new(
        settings.line_channel_secret.encode('utf-8'),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(hash).decode()
    return hmac.compare_digest(signature, expected_signature)


@webhook_router.post("/webhook")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    """Handle LINE webhook events."""
    body = await request.body()
    
    # Verify signature
    if not x_line_signature or not verify_signature(body, x_line_signature):
        logger.warning("Invalid signature in webhook request")
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    try:
        # Process the webhook
        events = handler.parse(body.decode('utf-8'), x_line_signature)
        
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessage):
                await handle_text_message(event)
        
        return {"status": "success"}
        
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except LineBotApiError as e:
        logger.error(f"LINE Bot API error: {e}")
        raise HTTPException(status_code=500, detail="LINE Bot API error")
    except Exception as e:
        logger.error(f"Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def handle_text_message(event: MessageEvent):
    """Handle text message from LINE."""
    try:
        user_id = event.source.user_id
        user_message = event.message.text
        
        logger.info(f"Received message from {user_id}: {user_message}")
        
        # Process message through LangGraph
        response = await process_user_message(user_id, user_message)
        
        # Send response back to LINE
        reply_message = TextSendMessage(text=response)
        line_bot_api.reply_message(event.reply_token, reply_message)
        
        logger.info(f"Sent response to {user_id}: {response}")
        
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        # Send error message to user
        error_message = TextSendMessage(text="申し訳ございません。エラーが発生しました。もう一度お試しください。")
        try:
            line_bot_api.reply_message(event.reply_token, error_message)
        except LineBotApiError:
            logger.error("Failed to send error message to user")