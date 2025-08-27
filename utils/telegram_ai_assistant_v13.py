"""
Telegram AI Assistant (v13 compatible)
Provides a Telegram interface for interacting with the trading system using AI.
Compatible with python-telegram-bot version 13.x
"""
import os
import logging
import json
from typing import Dict, Any, List, Optional, Callable
from telegram import Update, Bot
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    Dispatcher
)

# Import our AI chat agent
from api.ai_chat_agent import DeepSeekChatAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramAIAssistant:
    """
    Telegram bot that provides an AI interface to the trading system.
    Uses DeepSeek for NLP understanding and strategy generation.
    Compatible with python-telegram-bot v13.x
    """
    
    def __init__(self, 
                token: Optional[str] = None,
                ai_agent: Optional[DeepSeekChatAgent] = None,
                command_handlers: Optional[Dict[str, Callable]] = None):
        """
        Initialize the Telegram AI assistant.
        
        Args:
            token: Telegram bot token, defaults to environment variable
            ai_agent: DeepSeek AI agent instance
            command_handlers: Dictionary mapping commands to handler functions
        """
        self.token = token or os.environ.get("TELEGRAM_TOKEN")
        if not self.token:
            raise ValueError("Telegram token not provided and not found in environment variables")
        
        # Initialize AI agent if not provided
        self.ai_agent = ai_agent or DeepSeekChatAgent()
        
        # Command handlers
        self.command_handlers = command_handlers or {}
        
        # Authorized users (for security)
        auth_users = os.environ.get("TELEGRAM_AUTHORIZED_USERS", "")
        self.authorized_users = set(map(int, auth_users.split(","))) if auth_users else set()
        if not self.authorized_users:
            logger.warning("No authorized users set. Bot will respond to anyone.")
        
        # Chat history for context
        self.chat_history = {}
        
        # Setup updater and dispatcher
        self.updater = Updater(token=self.token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        
        # Register handlers
        self._register_handlers()
        
        logger.info("Initialized Telegram AI Assistant (v13)")
    
    def _register_handlers(self):
        """Register command and message handlers."""
        # Add command handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start_command))
        self.dispatcher.add_handler(CommandHandler("help", self.help_command))
        self.dispatcher.add_handler(CommandHandler("status", self.status_command))
        self.dispatcher.add_handler(CommandHandler("generate", self.generate_command))
        self.dispatcher.add_handler(CommandHandler("analyze", self.analyze_command))
        self.dispatcher.add_handler(CommandHandler("optimize", self.optimize_command))
        self.dispatcher.add_handler(CommandHandler("train", self.train_command))
        
        # Add message handler for chat interactions
        self.dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, self.handle_message))
        
        # Add error handler
        self.dispatcher.add_error_handler(self._error_handler)
    
    def start_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /start command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        message = (
            f"ðŸ‘‹ Hello {update.effective_user.first_name}!\n\n"
            "I'm your AI Trading Assistant. I can help you with:\n"
            "- Generating trading strategies\n"
            "- Analyzing strategy performance\n"
            "- Monitoring your portfolio\n"
            "- Automating trading tasks\n\n"
            "Try asking me to generate a strategy, or use commands like /status or /help."
        )
        update.message.reply_text(message)
    
    def help_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /help command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        message = (
            "ðŸ¤– *AI Trading Assistant Help*\n\n"
            "*Available Commands:*\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check system status\n"
            "/generate - Generate a new strategy\n"
            "/optimize - Optimize portfolio\n"
            "/analyze - Analyze a strategy\n"
            "/train - Train a strategy\n\n"
            
            "*Natural Language Examples:*\n"
            "- 'Generate a mean reversion strategy'\n"
            "- 'What's the status of my portfolio?'\n"
            "- 'Analyze the performance of strategy X'\n"
            "- 'How is strategy Y performing?'\n"
            "- 'Train all strategies'\n"
        )
        update.message.reply_text(message, parse_mode='Markdown')
    
    def status_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /status command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        # Get status information
        status_handler = self.command_handlers.get("status")
        if status_handler:
            status_info = status_handler()
            update.message.reply_text(status_info)
        else:
            update.message.reply_text("Status command not implemented.")
    
    def generate_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /generate command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        # Get parameters from message
        params = ' '.join(context.args) if context.args else "mean reversion"
        
        update.message.reply_text(f"Generating {params} strategy... this may take a moment.")
        
        try:
            # Call AI to generate strategy
            strategy_code = self.ai_agent.generate_strategy(params)
            
            # Check if strategy is too long for Telegram
            if len(strategy_code) > 4000:
                # Split into chunks
                chunks = [strategy_code[i:i+4000] for i in range(0, len(strategy_code), 4000)]
                for i, chunk in enumerate(chunks):
                    header = f"Strategy (part {i+1}/{len(chunks)}):\n\n" if i == 0 else ""
                    update.message.reply_text(f"{header}```python\n{chunk}\n```", parse_mode='Markdown')
            else:
                update.message.reply_text(f"Generated strategy:\n\n```python\n{strategy_code}\n```", parse_mode='Markdown')
            
            # Save strategy (if handler provided)
            save_handler = self.command_handlers.get("save_strategy")
            if save_handler:
                filename = save_handler(strategy_code, params)
                update.message.reply_text(f"Strategy saved as: {filename}")
            
        except Exception as e:
            error_msg = f"Error generating strategy: {str(e)}"
            logger.error(error_msg)
            update.message.reply_text(f"Sorry, there was an error: {error_msg}")
    
    def analyze_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /analyze command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        # Get parameters from message
        if not context.args:
            update.message.reply_text("Please specify a strategy name to analyze.")
            return
        
        strategy_name = context.args[0]
        update.message.reply_text(f"Analyzing strategy '{strategy_name}'... this may take a moment.")
        
        # Call handler if provided
        analyze_handler = self.command_handlers.get("analyze_strategy")
        if analyze_handler:
            try:
                analysis = analyze_handler(strategy_name)
                update.message.reply_text(f"Analysis for {strategy_name}:\n\n{analysis}")
            except Exception as e:
                error_msg = f"Error analyzing strategy: {str(e)}"
                logger.error(error_msg)
                update.message.reply_text(f"Sorry, there was an error: {error_msg}")
        else:
            update.message.reply_text("Analysis command not implemented.")
    
    def optimize_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /optimize command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        update.message.reply_text("Optimizing portfolio... this may take a moment.")
        
        # Call handler if provided
        optimize_handler = self.command_handlers.get("optimize_portfolio")
        if optimize_handler:
            try:
                result = optimize_handler()
                update.message.reply_text(f"Portfolio optimization results:\n\n{result}")
            except Exception as e:
                error_msg = f"Error optimizing portfolio: {str(e)}"
                logger.error(error_msg)
                update.message.reply_text(f"Sorry, there was an error: {error_msg}")
        else:
            update.message.reply_text("Optimization command not implemented.")
    
    def train_command(self, update: Update, context: CallbackContext) -> None:
        """Handle the /train command."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        # Get parameters from message
        strategy_name = context.args[0] if context.args else "all"
        
        if strategy_name.lower() == "all":
            update.message.reply_text("Training all strategies... this may take a while.")
        else:
            update.message.reply_text(f"Training strategy '{strategy_name}'... this may take a moment.")
        
        # Call handler if provided
        train_handler = self.command_handlers.get("train_strategy")
        if train_handler:
            try:
                result = train_handler(strategy_name)
                update.message.reply_text(f"Training completed for {strategy_name}:\n\n{result}")
            except Exception as e:
                error_msg = f"Error starting training: {str(e)}"
                logger.error(error_msg)
                update.message.reply_text(f"Sorry, there was an error: {error_msg}")
        else:
            update.message.reply_text("Training command not implemented.")
    
    def handle_message(self, update: Update, context: CallbackContext) -> None:
        """Handle free-form text messages using AI."""
        user_id = update.effective_user.id
        if not self._is_authorized(user_id):
            update.message.reply_text("Sorry, you are not authorized to use this bot.")
            return
        
        message_text = update.message.text
        logger.info(f"Received message: {message_text}")
        
        # Store in chat history
        if user_id not in self.chat_history:
            self.chat_history[user_id] = []
        
        self.chat_history[user_id].append({
            "role": "user",
            "content": message_text
        })
        
        # Use AI to interpret and respond
        try:
            # First try to interpret as command
            interpreted = self.ai_agent.interpret_user_request(message_text)
            command = interpreted.get("command", "unknown")
            
            if command != "unknown" and command in self.command_handlers:
                # Handle as command
                handler = self.command_handlers[command]
                parameters = interpreted.get("parameters", {})
                
                update.message.reply_text(f"I understand you want to {command}. Processing...")
                
                result = handler(**parameters)
                update.message.reply_text(str(result))
                
            else:
                # Handle as general chat
                system_prompt = """You are an AI trading assistant helping with quantitative trading strategies.
Provide concise, accurate responses about trading, strategy development, market analysis and portfolio management.
Keep responses under 4000 characters to fit in Telegram messages."""
                
                # Create message history for context
                messages = self.chat_history[user_id][-5:]  # Last 5 messages
                
                # Add system prompt
                full_messages = [{"role": "system", "content": system_prompt}] + messages
                
                # Get AI response
                chat_result = self.ai_agent.chat(full_messages)
                
                if chat_result["success"]:
                    response = chat_result["response"]
                    
                    # Store in chat history
                    self.chat_history[user_id].append({
                        "role": "assistant",
                        "content": response
                    })
                    
                    # Send response (handle long messages)
                    if len(response) > 4000:
                        chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
                        for chunk in chunks:
                            update.message.reply_text(chunk)
                    else:
                        update.message.reply_text(response)
                else:
                    error = chat_result.get("error", "Unknown error")
                    logger.error(f"AI chat error: {error}")
                    update.message.reply_text(f"Sorry, I encountered an error: {error}")
                
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(error_msg)
            update.message.reply_text(f"Sorry, there was an error processing your message: {error_msg}")
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if a user is authorized to use the bot."""
        if not self.authorized_users:
            return True  # No restrictions if no authorized users specified
        return user_id in self.authorized_users
    
    def _error_handler(self, update: object, context: CallbackContext) -> None:
        """Handle errors in the telegram bot."""
        logger.error(f"Update {update} caused error: {context.error}")
        if update and hasattr(update, 'effective_message') and update.effective_message:
            update.effective_message.reply_text(
                "Sorry, an error occurred while processing your request."
            )
    
    def run(self):
        """Run the Telegram bot."""
        # Send startup notification
        self.updater.bot.send_message(
            chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            text="ðŸš€ AI Strategy Evolution system is now online and ready!"
        )
        
        # Start the Bot
        logger.info("Starting Telegram bot...")
        self.updater.start_polling()
        
        # Run the bot until the user presses Ctrl-C
        self.updater.idle()

# Example usage
if __name__ == "__main__":
    # Mock command handlers for demonstration
    mock_handlers = {
        "status": lambda: "System Status: Online, 3 strategies running",
        "save_strategy": lambda code, params: f"strategy_{params.replace(' ', '_')}.py",
        "analyze_strategy": lambda name: f"Strategy {name} analysis: Sharpe ratio 1.2",
        "optimize_portfolio": lambda: "Portfolio optimized: 40% Strategy A, 60% Strategy B",
        "train_strategy": lambda name: f"Training complete for {name}, accuracy 85%"
    }
    
    # Create and run bot
    try:
        bot = TelegramAIAssistant(command_handlers=mock_handlers)
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {str(e)}") 