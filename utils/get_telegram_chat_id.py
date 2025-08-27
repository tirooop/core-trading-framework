import os
import requests
from dotenv import load_dotenv

def get_telegram_chat_id():
    """Get Telegram Chat ID from bot updates"""
    # Load environment variables
    load_dotenv()
    
    # Get bot token from environment
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env file")
        return None
    
    # Get updates from Telegram API
    url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
    try:
        response = requests.get(url)
        data = response.json()
        
        if not data.get('ok'):
            print(f"Error from Telegram API: {data.get('description')}")
            return None
            
        updates = data.get('result', [])
        if not updates:
            print("No updates found. Please send a message to your bot first.")
            return None
            
        # Get the latest update
        latest_update = updates[-1]
        message = latest_update.get('message', {})
        chat = message.get('chat', {})
        
        chat_id = chat.get('id')
        chat_type = chat.get('type')
        chat_title = chat.get('title', 'Private Chat')
        
        print(f"\nChat ID: {chat_id}")
        print(f"Chat Type: {chat_type}")
        print(f"Chat Title: {chat_title}")
        
        return chat_id
        
    except Exception as e:
        print(f"Error getting updates: {str(e)}")
        return None

if __name__ == "__main__":
    chat_id = get_telegram_chat_id()
    if chat_id:
        print("\nTo use this Chat ID, add it to your .env file:")
        print(f"TELEGRAM_CHAT_ID={chat_id}") 