import requests
import time
import os
import sys
from functools import cache
from typing import Callable, Optional
from pathlib import Path
from datetime import datetime, timedelta

from GithubUpdater import GithubUpdater
from ConfigHandler import ConfigHandler, ConfigSections as CS

CWD = Path(__file__).parent

class WebhookUpdater:
    """Class responsible for managing a Discord webhook, including sending and updating messages, and checking for updates from a GitHub repository using a GithubUpdater instance."""
    def __init__(self, config: ConfigHandler, filename: str = "config.ini", timeout: int = 20):
        """Initializes the WebhookUpdater by loading configuration from the specified file, setting up the webhook URL, and ensuring a message ID is available for updates."""
        self.config = config
        self.timeout = timeout
        self.github_updater: Optional[GithubUpdater] = None
        self.last_msg: str = ""
        
        # Get webhook details from config file
        self.config = config

        self.id = config.get_value(CS.WEBHOOK, "id")
        if self.id == "":
            raise ValueError("Webhook ID is not set in the configuration file.")
            
        self.token = config.get_value(CS.WEBHOOK, "token")
        if self.token == "":
            raise ValueError("Webhook Token is not set in the configuration file.")
        
        # Construct webhook URL
        self.hook_url = f"https://discord.com/api/webhooks/{self.id}/{self.token}"

        self.msg_id = config.get_value(CS.WEBHOOK, "msg_id")
        if self.msg_id == "":
            print("No existing message ID found, sending new message...")
            self.get_new_msg_id()
        
        try:
            self.update_msg("Setup...")

        except:
            print("Failed to update message, resetting MSG_ID and sending new message...")
            self.config.change_value(CS.WEBHOOK, "msg_id", "")
            self.get_new_msg_id()

    def get_new_msg_id(self):
        """Sends a new message to the Discord channel and updates the configuration with the new message ID."""
        response = self.send_msg("Setup...")
            
        self.msg_id = response["id"]
        self.config.change_value(CS.WEBHOOK, "msg_id", str(self.msg_id))

    @cache
    def text_to_emoji(self, text: str) -> str:
        """Converts a given text string to a corresponding string of Discord letter emojis."""
        indicator = ":regional_indicator_?:"
        emoji_text = ""
        
        for l in text.lower():
            emoji_text += indicator.replace("?", l)
        
        return emoji_text

    def send_msg(self, content: str) -> dict:
        """Sends a message to the Discord channel via the webhook and returns the response as a dictionary."""
        resp = requests.post(
            self.hook_url + "?wait=true",
            json={"content": content}
        )

        if resp.status_code != 200 and not resp.json().get("webhook_id", None):
            raise Exception(f"Failed to send message: {resp.status_code} - {resp.text}")

        return resp.json()

    def update_msg(self, content: str) -> dict:
        """Updates the existing Discord message with new content."""
        resp = requests.patch(
            self.hook_url + f"/messages/{self.msg_id}" + "?wait=true",
            json={"content": content}
        )

        if resp.status_code != 200 and not resp.json().get("webhook_id", None):
            raise Exception(f"Failed to update message: {resp.status_code} - {resp.text}")
        
        return resp.json()

    def update_loop(self, content_func: Callable[..., str]):
        """
        Main loop that updates the Discord message with content from the provided function and checks for GitHub updates at specified intervals.  
        @param content_func: A function that generates the content to be sent to Discord. It should accept a boolean parameter indicating whether an update check is being performed.
        """
        try:
            last_check = self.config.get_value(CS.UPDATER, "next_update_check")
            next_update_check = datetime.fromtimestamp(float(last_check))
        
        except ValueError:
            next_update_check = datetime.now()
            self.config.change_value(CS.UPDATER, "next_update_check", str(next_update_check.timestamp()))
        
        last_sha = self.config.get_value(CS.UPDATER, "last_sha")

        while True:
            content = content_func(False)

            if content != self.last_msg:
                self.update_msg(content)
                self.last_msg = content

            if (now := datetime.now()) >= next_update_check:
                next_update_check = now + timedelta(days=1)

                print(f"[{now}]Checking for updates...")

                if self.github_updater is not None:
                    last_sha, do_update = self.github_updater.check_repo(last_sha) 
                
                    if do_update:
                        self.config.change_value(CS.UPDATER, "last_sha", last_sha)
                        self.config.change_value(CS.UPDATER, "next_update_check", str(next_update_check.timestamp()))
                        content_func(True)
                        self.restart()
                
                else:
                    print("No Github updater set")
                    exit(1)

            time.sleep(self.timeout)

    def set_updater(self, updater: GithubUpdater):
        """Sets the GithubUpdater instance to be used for checking updates."""
        self.github_updater = updater

    def restart(self):
        """Restarts the application by re-executing the current Python script with the same arguments."""
        print("Restarting application...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)