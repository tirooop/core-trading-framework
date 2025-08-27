# Fixed file
Ã¾#!/usr/bin/env python
"""
WarMachine - Discord Bot

This module implements a Discord bot for interacting with the WarMachine platform.
"""

import os
import sys
import logging
import json
import asyncio
import time
from datetime import datetime
import discord
from discord.ext import commands

# Set up logging
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
        
        # Register commands
        self._register_commands()
        
        logger.info("Discord bot initialized")
    
    def _register_commands(self):
        """Register Discord bot commands"""
        
        @self.bot.event
        async def on_ready():
            """Event fired when bot is ready"""
            logger.info(f"Discord bot is ready: {self.bot.user.name}")
            
        @self.bot.command(name="status", help="Get system status")
        async def status(ctx):
            """Get system status"""
            await ctx.send("WarMachine status: All systems operational")
    
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
        logger.info("Discord bot shutdown requested")
