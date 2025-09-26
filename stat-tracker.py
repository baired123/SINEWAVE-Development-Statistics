import os
import json
import asyncio
import discord
from discord.ext import tasks
from datetime import datetime, timedelta
import subprocess
import shutil
from dotenv import load_dotenv
import aiohttp

# Load environment variables
load_dotenv()


class StatsBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        intents.presences = True
        intents.message_content = True
        super().__init__(intents=intents)

        self.message_count = 0
        self.repo_path = os.getenv('REPO_PATH', './stats-repo')
        self.statistics_folder = os.path.join(self.repo_path, 'statistics')
        self.git_repo_url = os.getenv('GIT_REPO_URL')
        self.git_username = os.getenv('GIT_USERNAME')
        self.git_email = os.getenv('GIT_EMAIL')
        self.github_token = os.getenv('GITHUB_TOKEN')

        # Initialize message tracking
        self.messages_per_hour = 0
        self.last_hour = datetime.now().hour

    async def on_ready(self):
        print(f'Logged in as {self.user.name} ({self.user.id})')
        print('------')

        # Clone repository if it doesn't exist
        await self.setup_repository()

        # Start the stats collection loop
        self.stats_loop.start()

    async def on_message(self, message):
        # Ignore bot messages
        if message.author.bot:
            return

        current_hour = datetime.now().hour

        # Reset counter if hour changed
        if current_hour != self.last_hour:
            self.messages_per_hour = 0
            self.last_hour = current_hour

        self.messages_per_hour += 1

    async def setup_repository(self):
        if not os.path.exists(self.repo_path):
            print("Cloning repository...")

            # Modify URL to include token for authentication
            repo_url = self.git_repo_url.replace(
                'https://',
                f'https://{self.github_token}@'
            )

            try:
                subprocess.run([
                    'git', 'clone', repo_url, self.repo_path
                ], check=True, capture_output=True)
                print("Repository cloned successfully")
            except subprocess.CalledProcessError as e:
                print(f"Error cloning repository: {e}")
                # Create directory if clone fails
                os.makedirs(self.repo_path, exist_ok=True)

        # Create statistics folder if it doesn't exist
        os.makedirs(self.statistics_folder, exist_ok=True)

        # Configure git user
        subprocess.run([
            'git', 'config', 'user.name', self.git_username
        ], cwd=self.repo_path, check=False)

        subprocess.run([
            'git', 'config', 'user.email', self.git_email
        ], cwd=self.repo_path, check=False)

    def get_server_stats(self, guild):
        """Get server statistics"""
        total_members = guild.member_count
        online_members = sum(1 for member in guild.members
                             if member.status != discord.Status.offline and
                             not member.bot)

        return {
            "total_members": total_members,
            "online_members": online_members,
            "messages_per_hour": self.messages_per_hour,
            "timestamp": datetime.now().isoformat()
        }

    def save_stats_to_file(self, stats):
        stats_file = os.path.join(self.statistics_folder, 'server_stats.json')

        # Load existing data or create new
        if os.path.exists(stats_file):
            with open(stats_file, 'r') as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {"stats": []}
        else:
            data = {"stats": []}

        # Append new stats
        data["stats"].append(stats)

        # Keep only last 2016 entries (7 days of 5-minute intervals)
        if len(data["stats"]) > 2016:
            data["stats"] = data["stats"][-2016:]

        # Save to file
        with open(stats_file, 'w') as f:
            json.dump(data, f, indent=2)

        return stats_file

    def commit_and_push(self):
        try:
            # Add all files in statistics folder to git
            subprocess.run([
                'git', 'add', 'statistics/'
            ], cwd=self.repo_path, check=True)

            # Check if there are changes to commit
            result = subprocess.run([
                'git', 'status', '--porcelain'
            ], cwd=self.repo_path, capture_output=True, text=True, check=True)

            if not result.stdout.strip():
                print("No changes to commit")
                return True

            # Commit changes
            commit_message = f"Update server stats - {datetime.now().isoformat()}"
            subprocess.run([
                'git', 'commit', '-m', commit_message
            ], cwd=self.repo_path, check=True)

            # Push changes
            subprocess.run([
                'git', 'push'
            ], cwd=self.repo_path, check=True)

            print(f"Stats updated and pushed at {datetime.now().isoformat()}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"Git error: {e}")
            return False

    @tasks.loop(minutes=5)
    async def stats_loop(self):
        try:
            # Get the first guild the bot is in
            if not self.guilds:
                print("Bot is not in any guilds")
                return

            guild = self.guilds[0]  # Use the first guild

            # Get stats
            stats = self.get_server_stats(guild)
            print(f"Collected stats: {stats}")

            # Save to file
            self.save_stats_to_file(stats)

            # Commit and push
            self.commit_and_push()

        except Exception as e:
            print(f"Error in stats loop: {e}")

    @stats_loop.before_loop
    async def before_stats_loop(self):
        await self.wait_until_ready()


# Create and run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')

    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables")
        print("Please check your .env file")
        exit(1)

    bot = StatsBot()
    bot.run(token)