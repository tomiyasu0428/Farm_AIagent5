"""LINE Webhook API endpoints."""

import hashlib
import hmac
import base64
import json
import logging
from fastapi import APIRouter, Request, HTTPException, Header
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import LineBotApiError, InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from src.config import settings
from src.agents.graph import process_user_message
from src.utils.langsmith_config import session_tracker

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


@webhook_router.post("/webhook/line")
async def line_webhook(request: Request, x_line_signature: str = Header(None)):
    """Handle LINE webhook events."""
    body = await request.body()
    
    # Debug signature header
    if not x_line_signature:
        logger.error("Signature header missing")
        raise HTTPException(status_code=400, detail="Missing signature header")
    
    logger.info(f"Webhook received: signature={x_line_signature}, body_length={len(body)}")
    
    try:
        # Process the webhook - temporarily skip signature validation in handler
        body_str = body.decode('utf-8')
        logger.info(f"Body content: {body_str}")
        
        # Parse without signature validation for debugging
        webhook_data = json.loads(body_str)
        
        # Manual event processing instead of handler.parse()
        if 'events' in webhook_data:
            for event_data in webhook_data['events']:
                if (event_data.get('type') == 'message' and 
                    event_data.get('message', {}).get('type') == 'text'):
                    
                    # Create a mock event object
                    user_id = event_data['source']['userId']
                    message_text = event_data['message']['text']
                    reply_token = event_data['replyToken']
                    
                    logger.info(f"Processing text message from {user_id}: {message_text}")
                    
                    # Process message and send reply
                    await handle_text_message_direct(user_id, message_text, reply_token)
        
        return {"status": "success"}
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in webhook body: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
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


async def handle_text_message_direct(user_id: str, message_text: str, reply_token: str):
    """Handle text message from LINE with direct parameters."""
    try:
        logger.info(f"Received message from {user_id}: {message_text}")
        
        # Update session tracking for LangSmith
        session_tracker.update_session(user_id)
        
        # Process message through LangGraph
        response = await process_user_message(user_id, message_text)
        
        # Send response back to LINE
        reply_message = TextSendMessage(text=response)
        line_bot_api.reply_message(reply_token, reply_message)
        
        logger.info(f"Sent response to {user_id}: {response}")
        
    except Exception as e:
        logger.error(f"Error handling text message: {e}")
        # Send error message to user
        error_message = TextSendMessage(text="申し訳ございません。エラーが発生しました。もう一度お試しください。")
        try:
            line_bot_api.reply_message(reply_token, error_message)
        except LineBotApiError:
            logger.error("Failed to send error message to user")