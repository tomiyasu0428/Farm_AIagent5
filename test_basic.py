#!/usr/bin/env python3
"""Basic test script to verify the system setup."""

import sys
import os
import asyncio

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.agents.graph import process_user_message


async def test_basic_flow():
    """Test basic message processing flow."""
    print("Testing basic Agricultural AI Agent flow...")
    
    # Test messages
    test_messages = [
        "こんにちは",
        "今日の圃場の状況は？",
        "トマトの作業履歴を教えて",
    ]
    
    test_user_id = "test_user_123"
    
    for message in test_messages:
        print(f"\n--- Testing message: '{message}' ---")
        try:
            response = await process_user_message(test_user_id, message)
            print(f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")
    
    print("\n--- Basic test completed ---")


if __name__ == "__main__":
    asyncio.run(test_basic_flow())