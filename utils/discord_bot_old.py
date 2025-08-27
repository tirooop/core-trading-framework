# Fixed file
þ#!/usr/bin/env python
"""
WarMachine - Discord Bot

This module implements a Discord bot for interacting with the WarMachine platform.
It provides commands for checking status, getting reports, managing strategies,
and receiving alerts through Discord channels.

Bot Name: ModleWAI
Application ID: 1368888271991472149
"""

import os
import sys
import logging
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path
import discord
from discord.ext import commands, tasks

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/discord_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class DiscordBot:
    """Discord Bot for WarMachine Platform"""
    
    def __init__(self, config):
        """
        Initialize the Discord bot
        
        Args:
            config: Platform configuration dictionary
        """
        self.config = config
        self.discord_config = config.get("discord", {})
        self.token = self.discord_config.get("token", "")
        
        if not self.token or self.token == "YOUR_DISCORD_BOT_TOKEN_HERE":
            logger.warning("Discord token not set in configuration")
            
        # Initialize the Discord client
        intents = discord.Intents.default()
        
        self.bot = commands.Bot(command_prefix=self.discord_config.get("command_prefix", "/"), intents=intents)
        
        # Register event handlers
        self._register_events()
        
        # Register commands
        self._register_commands()
        
        logger.info("Discord bot initialized")
        
    def _register_events(self):
        """Register Discord event handlers"""
        
        @self.bot.event
        async def on_ready():
            """Event fired when bot is ready"""
            logger.info(f"Discord bot is ready: {self.bot.user.name}")
            logger.info(f"Bot ID: {self.bot.user.id}")
            logger.info(f"Command prefix: {self.bot.command_prefix}")
            
        @self.bot.event
        async def on_command_error(ctx, error):
            """Event fired when a command raises an error"""
            if isinstance(error, commands.CommandNotFound):
                await ctx.send(f"B’?Command not found. Use `/help` to see available commands.")
            elif isinstance(error, commands.MissingRequiredArgument):
                await ctx.send(f"B’?Missing required argument: {error.param.name}")
            elif isinstance(error, commands.BadArgument):
                await ctx.send(f"B’?Bad argument: {error}")
            else:
                logger.error(f"Command error: {error}")
                await ctx.send(f"B’?An error occurred: {error}")
                
    def _register_commands(self):
        """Register Discord bot commands"""
        
        @self.bot.command(name="start", help="Welcome message")
        async def start(ctx):
            """Display welcome message"""
            user = ctx.author
            
            # Create embed message
            embed = discord.Embed(
                title="ƒ™;æ Welcome to WarMachine!",
                description="AI-powered trading system",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Features", value=(
                "%’?Market analysis and charts\n"
                "%’?Portfolio tracking\n"
                "%’?Trading signals\n"
                "%’?News and alerts"
            ), inline=False)
            
            embed.add_field(name="Getting Started", value="Use `/help` to see all available commands.", inline=False)
            
            embed.set_footer(text=f"WarMachine v13.9 | SaaS Quantitative AI Platform")
            
            await ctx.send(embed=embed)
            
        @self.bot.command(name="help", help="Show help information")
        async def help(ctx):
            """Show help information"""
            user = ctx.author
            
            # Create embed message
            embed = discord.Embed(
                title="ƒ™Nd WarMachine Commands",
                description="Here are the available commands:",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="General", value=(
                "`/start` - Welcome message\n"
                "`/help` - Show this help message\n"
                "`/status` - System status"
            ), inline=False)
            
            embed.add_field(name="Market", value=(
                "`/market <symbol>` - Market data for a symbol"
            ), inline=False)
            
            embed.set_footer(text=f"WarMachine v13.9 | Type `/help` for commands")
            
            await ctx.send(embed=embed)
            
        @self.bot.command(name="status", help="Get system status")
        async def status(ctx):
            """Get system status"""
            # Create embed message
            embed = discord.Embed(
                title="?’k{ System Status",
                description="All systems operational",
                color=discord.Color.green()
            )
            
            embed.add_field(name="Version", value="v13.9", inline=True)
            embed.add_field(name="Uptime", value="1h 23m", inline=True)
            embed.add_field(name="API Status", value="Online", inline=True)
            
            await ctx.send(embed=embed)
            
        @self.bot.command(name="market", help="Get market data for a symbol")
        async def market(ctx, symbol):
            """Get market data for a symbol"""
            if not symbol:
                await ctx.send("B’?Please specify symbol: `/market <symbol>`")
                return
                
            symbol = symbol.upper()
            
            # Create embed message
            embed = discord.Embed(
                title=f"ƒ™3d {symbol} Market Data",
                description=f"Current market data for {symbol}",
                color=discord.Color.blue()
            )
            
            # In a real implementation, this would fetch actual market data
            # For now, return simulated data
            embed.add_field(name="Price", value="$157.34", inline=True)
            embed.add_field(name="Change", value="+1.2%", inline=True)
            embed.add_field(name="Volume", value="1.2M", inline=True)
            
            embed.set_footer(text=f"Data as of {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            await ctx.send(embed=embed)
    
    def run(self):
        """Run the Discord bot"""
        if not self.token:
            logger.error("Cannot start Discord bot: Token not set in configuration")
            return
            
        try:
            self.bot.run(self.token)
        except Exception as e:
            logger.error(f"Failed to run Discord bot: {str(e)}")
            
    def shutdown(self):
        """Shutdown the Discord bot"""
        # Nothing to do here - the bot runs in its own thread
        logger.info("Discord bot shutdown requested")

# For testing as standalone script
if __name__ == "__main__":
    # Load configuration
    try:
        with open("config/warmachine_config.json", "r") as f:
            config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load configuration: {str(e)}")
        config = {}
        
    # Create bot
    bot = DiscordBot(config)
    
    # Run bot
    bot.run() 
