#!/usr/bin/env python


"""


Telegram Bot - Telegram integration for WarMachine platform





This module provides Telegram bot functionality for the WarMachine trading platform,


allowing users to interact with the platform through Telegram commands.


"""





import os


import logging


import json


import time


import asyncio


from datetime import datetime


from typing import Dict, Any, Optional, List, Union


from pathlib import Path





from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup


from telegram.ext import (


    Application, 


    CommandHandler, 


    ContextTypes, 


    MessageHandler, 


    CallbackQueryHandler,


    filters


)





# Set up logging


logger = logging.getLogger(__name__)





class TelegramBot:


    """Telegram bot for WarMachine platform"""


    


    def __init__(self, config: Dict[str, Any], ai_model_router=None, community_manager=None, unified_notifier=None):


        """


        Initialize the Telegram bot


        


        Args:


            config: Configuration dictionary


            ai_model_router: AI Model Router instance


            community_manager: Community Manager instance


            unified_notifier: Unified Notifier instance


        """


        self.config = config


        self.telegram_config = config.get("telegram", {})


        self.token = self.telegram_config.get("token", "")


        self.admin_chat_id = self.telegram_config.get("admin_chat_id", "")


        self.report_channel_id = self.telegram_config.get("report_channel_id", "")


        self.allowed_users = self.telegram_config.get("allowed_users", [])


        


        # Store platform components


        self.ai_model_router = ai_model_router


        self.community_manager = community_manager


        self.unified_notifier = unified_notifier


        


        # Initialize application


        self.application = None


        self.initialized = False


        


        if self.token:


            self.initialized = True


            logger.info("Telegram bot initialized")


        else:


            logger.warning("Telegram bot not initialized: Missing token")


            


    async def setup(self):


        """Set up the Telegram bot application"""


        if not self.initialized:


            logger.warning("Cannot set up Telegram bot: Not initialized")


            return False


            


        try:


            # Create application


            self.application = Application.builder().token(self.token).build()


            


            # Register command handlers


            self.application.add_handler(CommandHandler("start", self.cmd_start))


            self.application.add_handler(CommandHandler("help", self.cmd_help))


            self.application.add_handler(CommandHandler("status", self.cmd_status))


            self.application.add_handler(CommandHandler("positions", self.cmd_positions))


            self.application.add_handler(CommandHandler("portfolio", self.cmd_portfolio))


            self.application.add_handler(CommandHandler("chart", self.cmd_chart))


            self.application.add_handler(CommandHandler("analyze", self.cmd_analyze))


            self.application.add_handler(CommandHandler("buy", self.cmd_buy))


            self.application.add_handler(CommandHandler("sell", self.cmd_sell))


            self.application.add_handler(CommandHandler("alert", self.cmd_alert))


            self.application.add_handler(CommandHandler("news", self.cmd_news))


            self.application.add_handler(CommandHandler("predict", self.cmd_predict))


            


            # Handle unknown commands


            self.application.add_handler(MessageHandler(filters.COMMAND, self.unknown_command))


            


            # Handle callback queries


            self.application.add_handler(CallbackQueryHandler(self.handle_callback))


            


            logger.info("Telegram bot application set up")


            return True


            


        except Exception as e:


            logger.error(f"Failed to set up Telegram bot: {str(e)}")


            return False


            


    async def run(self):


        """Run the Telegram bot"""


        if not self.initialized:


            logger.warning("Cannot run Telegram bot: Not initialized")


            return


            


        try:


            # Set up the application


            success = await self.setup()


            


            if not success:


                logger.error("Failed to set up Telegram bot application")


                return


                


            # Start polling


            await self.application.initialize()


            await self.application.start_polling()


            


            logger.info("Telegram bot started")


            


            # Keep the bot running


            try:


                await self.application.updater.start_polling()


            except Exception as e:


                logger.error(f"Error in polling: {str(e)}")


                


        except Exception as e:


            logger.error(f"Failed to run Telegram bot: {str(e)}")


            


    def run_in_thread(self):


        """Run the Telegram bot in a non-blocking thread"""


        if not self.initialized:


            logger.warning("Cannot run Telegram bot: Not initialized")


            return None


            


        try:


            import threading


            


            def bot_thread():


                asyncio.run(self.run())


                


            thread = threading.Thread(target=bot_thread, daemon=True)


            thread.start()


            


            logger.info("Telegram bot started in thread")


            return thread


            


        except Exception as e:


            logger.error(f"Failed to run Telegram bot in thread: {str(e)}")


            return None


            


    async def send_message(self, chat_id: str, text: str, parse_mode: str = "Markdown", reply_markup=None):


        """


        Send a message to a Telegram chat


        


        Args:


            chat_id: Chat ID


            text: Message text


            parse_mode: Parse mode (Markdown, HTML)


            reply_markup: Inline keyboard markup


            


        Returns:


            Success status


        """


        if not self.initialized or not self.application:


            logger.warning("Cannot send message: Bot not initialized")


            return False


            


        try:


            await self.application.bot.send_message(


                chat_id=chat_id,


                text=text,


                parse_mode=parse_mode,


                reply_markup=reply_markup


            )


            


            return True


            


        except Exception as e:


            logger.error(f"Failed to send Telegram message: {str(e)}")


            return False


            


    async def send_photo(self, chat_id: str, photo_path: str, caption: str = "", parse_mode: str = "Markdown"):


        """


        Send a photo to a Telegram chat


        


        Args:


            chat_id: Chat ID


            photo_path: Path to photo file


            caption: Photo caption


            parse_mode: Parse mode (Markdown, HTML)


            


        Returns:


            Success status


        """


        if not self.initialized or not self.application:


            logger.warning("Cannot send photo: Bot not initialized")


            return False


            


        try:


            with open(photo_path, "rb") as photo_file:


                await self.application.bot.send_photo(


                    chat_id=chat_id,


                    photo=photo_file,


                    caption=caption,


                    parse_mode=parse_mode


                )


                


            return True


            


        except Exception as e:


            logger.error(f"Failed to send Telegram photo: {str(e)}")


            return False


            


    async def send_audio(self, chat_id: str, audio_path: str, caption: str = "", parse_mode: str = "Markdown"):


        """


        Send an audio file to a Telegram chat


        


        Args:


            chat_id: Chat ID


            audio_path: Path to audio file


            caption: Audio caption


            parse_mode: Parse mode (Markdown, HTML)


            


        Returns:


            Success status


        """


        if not self.initialized or not self.application:


            logger.warning("Cannot send audio: Bot not initialized")


            return False


            


        try:


            with open(audio_path, "rb") as audio_file:


                await self.application.bot.send_audio(


                    chat_id=chat_id,


                    audio=audio_file,


                    caption=caption,


                    parse_mode=parse_mode


                )


                


            return True


            


        except Exception as e:


            logger.error(f"Failed to send Telegram audio: {str(e)}")


            return False


            


    async def broadcast(self, text: str, level: str = "free", parse_mode: str = "Markdown"):


        """


        Broadcast a message to all users of a specific level


        


        Args:


            text: Message text


            level: Minimum user level (free, trader, pro_trader, vip)


            parse_mode: Parse mode (Markdown, HTML)


            


        Returns:


            Number of messages sent


        """


        if not self.initialized or not self.application or not self.community_manager:


            logger.warning("Cannot broadcast: Bot not initialized or missing community manager")


            return 0


            


        try:


            # Get channel subscribers


            subscribers = self.community_manager.get_channel_subscribers("telegram", level)


            


            sent_count = 0


            for subscriber in subscribers:


                telegram_id = subscriber.get("telegram_id")


                


                if telegram_id:


                    success = await self.send_message(telegram_id, text, parse_mode)


                    


                    if success:


                        sent_count += 1


                        


            logger.info(f"Broadcast message sent to {sent_count} users")


            return sent_count


            


        except Exception as e:


            logger.error(f"Failed to broadcast message: {str(e)}")


            return 0


            


    # Command handlers


    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /start command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                logger.warning(f"Unauthorized access attempt from user {user_id}")


                return


                


            welcome_text = (


                "üöÄ *Welcome to WarMachine Trading Platform* üöÄ\n\n"


                "I am your AI-powered trading assistant. I can help you with:\n\n"


                "‚Ä¢ Market analysis and charts\n"


                "‚Ä¢ Portfolio tracking\n"


                "‚Ä¢ Trading signals\n"


                "‚Ä¢ News and alerts\n\n"


                "Use /help to see available commands."


            )


            


            # Add subscription buttons


            keyboard = [


                [


                    InlineKeyboardButton("üìä Market Overview", callback_data="market_overview"),


                    InlineKeyboardButton("üìà Top Movers", callback_data="top_movers")


                ],


                [


                    InlineKeyboardButton("üíº My Portfolio", callback_data="portfolio"),


                    InlineKeyboardButton("‚öôÔ∏è Settings", callback_data="settings")


                ]


            ]


            


            reply_markup = InlineKeyboardMarkup(keyboard)


            


            await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)


            logger.info(f"Start command from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in start command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /help command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            help_text = (


                "üìö *WarMachine Commands* üìö\n\n"


                "üîπ */status* - System status\n"


                "üîπ */positions* - Current positions\n"


                "üîπ */portfolio* - Portfolio overview\n"


                "üîπ */chart SYMBOL* - Get price chart\n"


                "üîπ */analyze SYMBOL* - AI analysis\n"


                "üîπ */buy SYMBOL AMOUNT* - Create buy order\n"


                "üîπ */sell SYMBOL AMOUNT* - Create sell order\n"


                "üîπ */alert SYMBOL PRICE* - Set price alert\n"


                "üîπ */news SYMBOL* - Latest news\n"


                "üîπ */predict SYMBOL* - AI price prediction\n\n"


                "Example: /chart AAPL"


            )


            


            await update.message.reply_text(help_text, parse_mode="Markdown")


            logger.info(f"Help command from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in help command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /status command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Get system status (placeholder)


            status_text = (


                "‚öôÔ∏è *WarMachine Status* ‚öôÔ∏è\n\n"


                "‚úÖ AI Commander: Running\n"


                "‚úÖ Market Watcher: Running\n"


                "‚úÖ AI Reporter: Running\n"


                "‚úÖ Voice Manager: Running\n\n"


                "üî∑ Active Strategies: 7\n"


                "üî∑ Portfolio Performance: +5.24%\n"


                "üî∑ Alerts Today: 12\n"


                "üî∑ Reports Generated: 5\n\n"


                "Last Updated: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")


            )


            


            await update.message.reply_text(status_text, parse_mode="Markdown")


            logger.info(f"Status command from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in status command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /positions command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Get positions (placeholder)


            positions_text = (


                "üìä *Current Positions* üìä\n\n"


                "1. *AAPL*: 25 shares @ $185.64 (+2.9%)\n"


                "2. *MSFT*: 15 shares @ $365.25 (+4.2%)\n"


                "3. *NVDA*: 10 shares @ $423.85 (+5.7%)\n\n"


                "Total Value: $16,524.50\n"


                "Total P/L: +$738.25 (+4.5%)"


            )


            


            await update.message.reply_text(positions_text, parse_mode="Markdown")


            logger.info(f"Positions command from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in positions command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /portfolio command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Get portfolio (placeholder)


            portfolio_text = (


                "üíº *Portfolio Overview* üíº\n\n"


                "Total Balance: $105,243.78\n"


                "Daily Change: +$789.32 (+0.75%)\n"


                "Monthly Change: +$3,380.12 (+3.21%)\n\n"


                "*Asset Allocation:*\n"


                "üîπ Stocks: 65%\n"


                "üîπ ETFs: 20%\n"


                "üîπ Crypto: 10%\n"


                "üîπ Cash: 5%"


            )


            


            await update.message.reply_text(portfolio_text, parse_mode="Markdown")


            logger.info(f"Portfolio command from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in portfolio command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_chart(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /chart command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Check arguments


            if not context.args or len(context.args) < 1:


                await update.message.reply_text("Please specify a symbol. Example: /chart AAPL")


                return


                


            symbol = context.args[0].upper()


            


            # Generate chart (placeholder)


            await update.message.reply_text(f"Generating chart for {symbol}...")


            


            # This would generate an actual chart in a real implementation


            # For now, we'll just send a message


            chart_text = (


                f"üìà *{symbol} Chart* üìà\n\n"


                f"Current Price: $185.64\n"


                f"Day Range: $182.45 - $186.20\n"


                f"52-Week Range: $142.37 - $190.54\n\n"


                f"Volume: 54.3M\n"


                f"Avg Volume: 62.1M\n\n"


                f"Chart generation feature coming soon!"


            )


            


            await update.message.reply_text(chart_text, parse_mode="Markdown")


            logger.info(f"Chart command for {symbol} from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in chart command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /analyze command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Check arguments


            if not context.args or len(context.args) < 1:


                await update.message.reply_text("Please specify a symbol. Example: /analyze AAPL")


                return


                


            symbol = context.args[0].upper()


            


            # Check if AI model router is available


            if not self.ai_model_router:


                await update.message.reply_text("AI analysis not available. Please try again later.")


                return


                


            await update.message.reply_text(f"Analyzing {symbol}... This might take a moment.")


            


            # Generate AI analysis


            prompt = f"Provide a brief analysis (maximum 300 words) of {symbol} stock including current price trends, key technical indicators, and a short-term outlook. Format with markdown bullet points."


            


            analysis = self.ai_model_router.ask(prompt, temperature=0.7)


            


            # Limit response length


            max_length = 2000


            if len(analysis) > max_length:


                analysis = analysis[:max_length] + "...\n\n*Note: Analysis truncated due to length*"


                


            # Send analysis


            analysis_text = f"üîç *AI Analysis: {symbol}* üîç\n\n{analysis}"


            


            await update.message.reply_text(analysis_text, parse_mode="Markdown")


            logger.info(f"Analyze command for {symbol} from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in analyze command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred during analysis.")


            


    async def cmd_buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /buy command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Check arguments


            if not context.args or len(context.args) < 2:


                await update.message.reply_text("Please specify symbol and amount. Example: /buy AAPL 5")


                return


                


            symbol = context.args[0].upper()


            amount = context.args[1]


            


            # Process buy order (placeholder)


            await update.message.reply_text(f"‚ö†Ô∏è This is a simulation. No real orders are being placed.")


            


            buy_text = (


                f"üü¢ *Buy Order Simulated* üü¢\n\n"


                f"Symbol: {symbol}\n"


                f"Amount: {amount} shares\n"


                f"Estimated Price: $185.64\n"


                f"Estimated Total: ${float(amount) * 185.64:.2f}\n\n"


                f"Status: Simulated\n"


                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


            )


            


            await update.message.reply_text(buy_text, parse_mode="Markdown")


            logger.info(f"Buy command for {symbol} ({amount}) from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in buy command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_sell(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /sell command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Check arguments


            if not context.args or len(context.args) < 2:


                await update.message.reply_text("Please specify symbol and amount. Example: /sell AAPL 5")


                return


                


            symbol = context.args[0].upper()


            amount = context.args[1]


            


            # Process sell order (placeholder)


            await update.message.reply_text(f"‚ö†Ô∏è This is a simulation. No real orders are being placed.")


            


            sell_text = (


                f"üî¥ *Sell Order Simulated* üî¥\n\n"


                f"Symbol: {symbol}\n"


                f"Amount: {amount} shares\n"


                f"Estimated Price: $185.64\n"


                f"Estimated Total: ${float(amount) * 185.64:.2f}\n\n"


                f"Status: Simulated\n"


                f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


            )


            


            await update.message.reply_text(sell_text, parse_mode="Markdown")


            logger.info(f"Sell command for {symbol} ({amount}) from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in sell command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_alert(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /alert command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Check arguments


            if not context.args or len(context.args) < 2:


                await update.message.reply_text("Please specify symbol and price. Example: /alert AAPL 190")


                return


                


            symbol = context.args[0].upper()


            price = context.args[1]


            


            # Set alert (placeholder)


            alert_text = (


                f"üîî *Price Alert Set* üîî\n\n"


                f"Symbol: {symbol}\n"


                f"Alert Price: ${price}\n"


                f"Current Price: $185.64\n\n"


                f"You will be notified when {symbol} reaches ${price}."


            )


            


            await update.message.reply_text(alert_text, parse_mode="Markdown")


            logger.info(f"Alert command for {symbol} (${price}) from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in alert command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /news command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Check arguments


            symbol = "MARKET"


            if context.args and len(context.args) > 0:


                symbol = context.args[0].upper()


                


            # Get news (placeholder)


            news_text = (


                f"üì∞ *Latest {symbol} News* üì∞\n\n"


                f"1. **Company Announces Record Earnings**\n"


                f"Strong quarterly results exceed analyst expectations\n\n"


                f"2. **New Product Launch Planned**\n"


                f"Innovative features expected to drive growth\n\n"


                f"3. **Industry Analysis Shows Positive Trends**\n"


                f"Market share increasing in key segments"


            )


            


            await update.message.reply_text(news_text, parse_mode="Markdown")


            logger.info(f"News command for {symbol} from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in news command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred.")


            


    async def cmd_predict(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle /predict command"""


        try:


            user_id = str(update.effective_user.id)


            


            # Check if user is allowed


            if self.allowed_users and user_id not in self.allowed_users:


                await update.message.reply_text("Sorry, you are not authorized to use this bot.")


                return


                


            # Check arguments


            if not context.args or len(context.args) < 1:


                await update.message.reply_text("Please specify a symbol. Example: /predict AAPL")


                return


                


            symbol = context.args[0].upper()


            


            # Check if AI model router is available


            if not self.ai_model_router:


                await update.message.reply_text("AI prediction not available. Please try again later.")


                return


                


            await update.message.reply_text(f"Generating prediction for {symbol}... This might take a moment.")


            


            # Generate AI prediction


            prompt = f"Provide a brief price prediction (maximum 200 words) for {symbol} stock for the next week. Include current price, support/resistance levels, and a clear price target with confidence level."


            


            prediction = self.ai_model_router.ask(prompt, temperature=0.7)


            


            # Limit response length


            max_length = 1500


            if len(prediction) > max_length:


                prediction = prediction[:max_length] + "...\n\n*Note: Prediction truncated due to length*"


                


            # Send prediction


            prediction_text = f"üîÆ *AI Prediction: {symbol}* üîÆ\n\n{prediction}\n\n‚ö†Ô∏è *Disclaimer:* This is for informational purposes only and not financial advice."


            


            await update.message.reply_text(prediction_text, parse_mode="Markdown")


            logger.info(f"Predict command for {symbol} from user {user_id}")


            


        except Exception as e:


            logger.error(f"Error in predict command: {str(e)}")


            await update.message.reply_text("Sorry, an error occurred during prediction.")


            


    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle unknown commands"""


        await update.message.reply_text("Sorry, I don't understand that command. Use /help to see available commands.")


        


    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):


        """Handle callback queries from inline keyboards"""


        query = update.callback_query


        await query.answer()


        


        callback_data = query.data


        


        try:


            if callback_data == "market_overview":


                text = (


                    "üìä *Market Overview* üìä\n\n"


                    "S&P 500: 4,783.45 (+0.6%)\n"


                    "Nasdaq: 16,748.32 (+0.9%)\n"


                    "Dow Jones: 38,654.78 (+0.4%)\n\n"


                    "VIX: 14.32 (-2.1%)\n"


                    "10Y Yield: 3.87%\n\n"


                    "BTC-USD: $42,156.78 (-1.2%)\n"


                    "ETH-USD: $2,345.67 (-0.8%)"


                )


                


                await query.edit_message_text(text=text, parse_mode="Markdown")


                


            elif callback_data == "top_movers":


                text = (


                    "üìà *Top Gainers* üìà\n\n"


                    "1. NVDA: $423.85 (+5.7%)\n"


                    "2. TSLA: $215.43 (+4.5%)\n"


                    "3. AMD: $182.34 (+3.8%)\n\n"


                    "üìâ *Top Losers* üìâ\n\n"


                    "1. META: $475.21 (-2.3%)\n"


                    "2. NFLX: $628.75 (-1.8%)\n"


                    "3. AMZN: $182.34 (-1.5%)"


                )


                


                await query.edit_message_text(text=text, parse_mode="Markdown")


                


            elif callback_data == "portfolio":


                text = (


                    "üíº *Portfolio Overview* üíº\n\n"


                    "Total Balance: $105,243.78\n"


                    "Daily Change: +$789.32 (+0.75%)\n"


                    "Monthly Change: +$3,380.12 (+3.21%)\n\n"


                    "*Asset Allocation:*\n"


                    "üîπ Stocks: 65%\n"


                    "üîπ ETFs: 20%\n"


                    "üîπ Crypto: 10%\n"


                    "üîπ Cash: 5%"


                )


                


                await query.edit_message_text(text=text, parse_mode="Markdown")


                


            elif callback_data == "settings":


                text = (


                    "‚öôÔ∏è *Settings* ‚öôÔ∏è\n\n"


                    "Manage your settings using the following commands:\n\n"


                    "*/alerts* - Manage price alerts\n"


                    "*/subscription* - Manage subscription\n"


                    "*/preferences* - Set notifications preferences\n\n"


                    "Current Plan: Free\n"


                    "Notification Status: Enabled"


                )


                


                await query.edit_message_text(text=text, parse_mode="Markdown")


                


        except Exception as e:


            logger.error(f"Error handling callback: {str(e)}")


            await query.edit_message_text(text="Sorry, an error occurred.")





def main():


    """Main function to start the Telegram bot"""


    import sys


    try:


        # Create logs directory if it doesn't exist


        os.makedirs("logs", exist_ok=True)


        


        # Create and start the bot


        config_path = "config/warmachine_config.json"


        if not os.path.exists(config_path):


            print(f"配置文件 {config_path} 不存在！")


            return


        with open(config_path, "r", encoding="utf-8") as f:


            config = json.load(f)


        bot = TelegramBot(config)


        bot.start()


        


    except Exception as e:


        logger.error(f"Failed to start Telegram bot: {str(e)}")


        sys.exit(1)





if __name__ == "__main__":


    main() 