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
        self.repo_path = os.getenv("REPO_PATH", "./stats-repo")
        self.statistics_folder = os.path.join(self.repo_path, "statistics")
        self.git_repo_url = os.getenv("GIT_REPO_URL")
        self.git_username = os.getenv("GIT_USERNAME")
        self.git_email = os.getenv("GIT_EMAIL")
        self.github_token = os.getenv("GITHUB_TOKEN")

        # Initialize message tracking
        self.messages_per_hour = 0
        self.last_hour = datetime.now().hour

        # Track if repo is properly set up
        self.repo_initialized = False

    async def on_ready(self):
        print(f"Logged in as {self.user.name} ({self.user.id})")
        print("------")

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
        repo_exists = os.path.exists(os.path.join(self.repo_path, ".git"))

        if not repo_exists:
            print("Repository not found. Setting up...")

            # Ensure the base directory exists but is empty for cloning
            if os.path.exists(self.repo_path):
                # Check if directory is empty
                if os.listdir(self.repo_path):
                    print(
                        "Repo path exists but is not empty. Creating new directory..."
                    )
                    # Create a new directory with a timestamp to avoid conflicts
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    self.repo_path = f"{self.repo_path}_{timestamp}"
                    self.statistics_folder = os.path.join(self.repo_path, "statistics")
                    os.makedirs(self.repo_path, exist_ok=True)
                else:
                    # Directory exists but is empty, we can use it
                    pass
            else:
                # Create the directory
                os.makedirs(self.repo_path, exist_ok=True)

            # Try to clone if we have a URL
            if self.git_repo_url and self.github_token:
                try:
                    print("Attempting to clone repository...")

                    # Modify URL to include token for authentication
                    repo_url = self.git_repo_url.replace(
                        "https://", f"https://{self.github_token}@"
                    )

                    # Use async subprocess
                    result = await asyncio.create_subprocess_exec(
                        "git",
                        "clone",
                        repo_url,
                        self.repo_path,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await result.communicate()

                    if result.returncode == 0:
                        print("Repository cloned successfully")
                        self.repo_initialized = True
                    else:
                        print(f"Clone failed: {stderr.decode()}")
                        # Initialize a new git repo if clone fails
                        await self.run_async_git_operation(self.initialize_git_repo)
                except Exception as e:
                    print(f"Error during clone: {e}")
                    # Initialize a new git repo if clone fails
                    await self.run_async_git_operation(self.initialize_git_repo)
            else:
                # Initialize a new git repo if no URL provided
                await self.run_async_git_operation(self.initialize_git_repo)
        else:
            print("Repository already exists")
            self.repo_initialized = True

        # Configure git user if we have credentials
        if self.git_username and self.git_email:
            await self.run_git_command(["config", "user.name", self.git_username])
            await self.run_git_command(["config", "user.email", self.git_email])

        # Configure git to not prompt for passwords
        await self.run_git_command(["config", "core.askPass", ""])

        # Store credentials in file to avoid prompts
        if self.github_token and self.git_repo_url:
            credentials_content = f"https://{self.github_token}@github.com\n"
            credentials_file = os.path.join(self.repo_path, ".git-credentials")
            with open(credentials_file, "w") as f:
                f.write(credentials_content)

        # Create statistics folder if it doesn't exist
        os.makedirs(self.statistics_folder, exist_ok=True)

    async def run_async_git_operation(self, sync_func):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, sync_func)

    async def run_git_command(self, args, check=True, timeout=30):
        global process
        try:
            process = await asyncio.create_subprocess_exec(
                "git",
                *args,
                cwd=self.repo_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            if check and process.returncode != 0:
                raise subprocess.CalledProcessError(
                    process.returncode, args, stdout.decode(), stderr.decode()
                )

            return stdout.decode(), stderr.decode()
        except asyncio.TimeoutError:
            print(f"Git command timed out: git {' '.join(args)}")
            if process:
                process.kill()
            raise
        except Exception as e:
            print(f"Error running git command {' '.join(args)}: {e}")
            raise

    def initialize_git_repo(self):
        try:
            print("Initializing new git repository...")

            # Set the default branch to main
            subprocess.run(
                ["git", "init", "-b", "main"], cwd=self.repo_path, check=True
            )

            # Configure git user BEFORE committing
            if self.git_username and self.git_email:
                subprocess.run(
                    ["git", "config", "user.name", self.git_username],
                    cwd=self.repo_path,
                    check=True,
                )

                subprocess.run(
                    ["git", "config", "user.email", self.git_email],
                    cwd=self.repo_path,
                    check=True,
                )
            else:
                # Set fallback credentials to avoid commit errors
                subprocess.run(
                    ["git", "config", "user.name", "StatsBot"],
                    cwd=self.repo_path,
                    check=True,
                )
                subprocess.run(
                    ["git", "config", "user.email", "statsbot@localhost"],
                    cwd=self.repo_path,
                    check=True,
                )

            # Configure to avoid password prompts
            subprocess.run(
                ["git", "config", "core.askPass", ""], cwd=self.repo_path, check=True
            )

            # If we have a remote URL, set it up
            if self.git_repo_url:
                # Modify URL to include token for authentication
                repo_url = (
                    self.git_repo_url.replace(
                        "https://", f"https://{self.github_token}@"
                    )
                    if self.github_token
                    else self.git_repo_url
                )

                subprocess.run(
                    ["git", "remote", "add", "origin", repo_url],
                    cwd=self.repo_path,
                    check=True,
                )

                # Store credentials to avoid prompts
                if self.github_token:
                    credentials_content = f"https://{self.github_token}@github.com\n"
                    credentials_file = os.path.join(self.repo_path, ".git-credentials")
                    with open(credentials_file, "w") as f:
                        f.write(credentials_content)

            # Create README or initial file to commit
            readme_path = os.path.join(self.repo_path, "README.md")
            if not os.path.exists(readme_path):
                with open(readme_path, "w") as f:
                    f.write(
                        "# Server Statistics\n\nThis repository contains automated server statistics.\n"
                    )

            # Create statistics folder
            os.makedirs(self.statistics_folder, exist_ok=True)

            # Create initial stats file
            stats_file = os.path.join(self.statistics_folder, "server_stats.json")
            if not os.path.exists(stats_file):
                with open(stats_file, "w") as f:
                    json.dump({"stats": []}, f, indent=2)

            # Add and commit initial files
            subprocess.run(["git", "add", "."], cwd=self.repo_path, check=True)
            subprocess.run(
                ["git", "commit", "-m", "Initial commit - stats tracking"],
                cwd=self.repo_path,
                check=True,
            )

            self.repo_initialized = True
            print("Git repository initialized successfully with 'main' branch")

        except subprocess.CalledProcessError as e:
            print(f"Error initializing git repository: {e}")
            if hasattr(e, "stderr") and e.stderr:
                print(f"Error details: {e.stderr}")
            self.repo_initialized = False

    def get_server_stats(self, guild):
        total_members = guild.member_count
        online_members = sum(
            1
            for member in guild.members
            if member.status != discord.Status.offline and not member.bot
        )

        return {
            "total_members": total_members,
            "online_members": online_members,
            "messages_per_hour": self.messages_per_hour,
            "timestamp": datetime.now().isoformat(),
        }

    def save_stats_to_file(self, stats):
        stats_file = os.path.join(self.statistics_folder, "server_stats.json")

        # Initialize data structure
        data = {"stats": []}

        # Load existing data if file exists and is valid JSON
        if os.path.exists(stats_file):
            try:
                with open(stats_file, "r") as f:
                    file_data = json.load(f)
                    # Ensure the data has the expected structure
                    if (
                        isinstance(file_data, dict)
                        and "stats" in file_data
                        and isinstance(file_data["stats"], list)
                    ):
                        data = file_data
                        print(
                            f"Loaded existing stats file with {len(data['stats'])} entries"
                        )
                    else:
                        print("Warning: Invalid JSON structure, resetting data")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error reading stats file: {e}. Creating new file.")

        # Append new stats
        data["stats"].append(stats)

        # Keep only last 2016 entries (7 days of 5-minute intervals)
        if len(data["stats"]) > 2016:
            data["stats"] = data["stats"][-2016:]

        # Save to file with error handling
        try:
            with open(stats_file, "w") as f:
                json.dump(data, f, indent=2)
            print(
                f"Successfully saved stats to file (total entries: {len(data['stats'])})"
            )
            return True
        except Exception as e:
            print(f"Error saving stats file: {e}")
            return False

    async def sync_with_remote(self):
        try:
            print("Syncing with remote repository...")

            # Fetch the latest changes
            await self.run_git_command(["fetch", "origin"], check=False)

            # Try to pull with rebase first
            stdout, stderr = await self.run_git_command(
                ["pull", "--rebase", "origin", "main"], check=False
            )

            if "CONFLICT" in stdout or "CONFLICT" in stderr:
                print("Merge conflict detected. Resetting and forcing our changes...")
                # If there's a conflict, reset and force push
                await self.run_git_command(["reset", "--hard", "HEAD"], check=False)
                return False
            elif "fatal:" in stderr or "error:" in stderr:
                print(f"Pull failed: {stderr}")
                return False
            else:
                print("Successfully synced with remote")
                return True

        except Exception as e:
            print(f"Error syncing with remote: {e}")
            return False

    async def commit_and_push(self):
        if not self.repo_initialized:
            print("Repository not initialized, skipping git operations")
            return False

        try:
            # First, sync with remote to avoid conflicts
            if not await self.sync_with_remote():
                print("Sync failed, attempting to force push...")
                # If sync fails, we'll try to force push our changes

            # Add all files in statistics folder to git
            await self.run_git_command(["add", "statistics/"])

            # Check if there are changes to commit
            stdout, stderr = await self.run_git_command(
                ["status", "--porcelain"], check=False
            )

            if not stdout.strip():
                print("No changes to commit")
                return True

            # Commit changes
            commit_message = f"Update server stats - {datetime.now().isoformat()}"
            await self.run_git_command(["commit", "-m", commit_message])

            print("Committed changes successfully")

            # Push changes to main branch with timeout
            try:
                # Try normal push first
                push_task = self.run_git_command(
                    ["push", "origin", "main"], check=False
                )
                stdout, stderr = await asyncio.wait_for(push_task, timeout=30.0)

                if "rejected" in stderr:
                    print("Push rejected, trying force push...")
                    # If push is rejected, try force push
                    push_task = self.run_git_command(
                        ["push", "--force", "origin", "main"], check=False
                    )
                    stdout, stderr = await asyncio.wait_for(push_task, timeout=30.0)

                    if "fatal:" in stderr or "error:" in stderr:
                        print(f"Force push failed: {stderr}")
                        return False
                    else:
                        print("Force push successful")
                        return True
                elif "fatal:" in stderr or "error:" in stderr:
                    print(f"Push failed: {stderr}")
                    return False
                else:
                    print(f"Stats pushed successfully at {datetime.now().isoformat()}")
                    return True

            except asyncio.TimeoutError:
                print("Git push timed out after 30 seconds")
                return False

        except subprocess.CalledProcessError as e:
            print(f"Git error: {e}")
            if hasattr(e, "stderr") and e.stderr:
                print(f"Git stderr: {e.stderr}")
            return False
        except Exception as e:
            print(f"Unexpected error in git operations: {e}")
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
            if self.save_stats_to_file(stats):
                # Commit and push asynchronously
                await self.commit_and_push()
            else:
                print("Failed to save stats, skipping git operations")

        except Exception as e:
            print(f"Error in stats loop: {e}")

    @stats_loop.before_loop
    async def before_stats_loop(self):
        await self.wait_until_ready()


# Create and run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")

    if not token:
        print("Error: DISCORD_TOKEN not found in environment variables")
        print("Please check your .env file")
        exit(1)

    bot = StatsBot()
    bot.run(token)
