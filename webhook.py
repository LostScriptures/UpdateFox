import requests
import time
from functools import cache
from configparser import ConfigParser
from typing import Callable
from pathlib import Path

CWD = Path(__file__).parent

class WebhookUpdater:
    def __init__(self, filename: str = "config.ini", timeout: int = 20):
        self.timeout = timeout
        self.last_msg: str = ""
        
        # Get webhook details from config file
        parser = ConfigParser()
        self.config = parser

        try:
            with open(CWD / filename, "r") as f:
                parser.read_file(f)

        except FileNotFoundError:
            print(f"Could not find configuration file: {filename}")
            exit(1)

        except PermissionError:
            print(f"Permission denied when trying to read configuration file: {filename}")
            exit(1)

        self.id = self.get_config_value("WEBHOOK", "ID")
        if self.id == "":
            raise ValueError("Webhook ID is not set in the configuration file.")
            
        self.token = self.get_config_value("WEBHOOK", "TOKEN")
        if self.token == "":
            raise ValueError("Webhook Token is not set in the configuration file.")
        
        # Construct webhook URL
        self.hook_url = f"https://discord.com/api/webhooks/{self.id}/{self.token}"


        self.msg_id = self.get_config_value("WEBHOOK", "MSG_ID")
        if self.msg_id == "":
            response = self.send_msg("Setup...")
            
            self.msg_id = response["id"]
            parser.set("WEBHOOK", "MSG_ID", str(self.msg_id))

            self.write_config(filename)

    def write_config(self, filename: str):
        if self.config is None:
            raise ValueError("Configuration parser is not initialized.")

        try:
            with open(CWD / filename, "w") as f:
                self.config.write(f)
        
        except FileNotFoundError:
            print("Could not find configuration file")
            exit(1)

        except PermissionError:
            print("Permission denied when trying to write to configuration file")
            exit(1)

    @cache
    def text_to_emoji(self, text: str) -> str:
        indicator = ":regional_indicator_?:"
        emoji_text = ""
        
        for l in text.lower():
            emoji_text += indicator.replace("?", l)
        
        return emoji_text

    def send_msg(self, content: str) -> dict:
        resp = requests.post(
            self.hook_url + "?wait=true",
            json={"content": content}
        )

        if resp.status_code != 200 and not resp.json().get("webhook_id", None):
            raise Exception(f"Failed to send message: {resp.status_code} - {resp.text}")

        return resp.json()

    def update_msg(self, content: str) -> dict:
        resp = requests.patch(
            self.hook_url + f"/messages/{self.msg_id}" + "?wait=true",
            json={"content": content}
        )

        if resp.status_code != 200 and not resp.json().get("webhook_id", None):
            raise Exception(f"Failed to update message: {resp.status_code} - {resp.text}")
        
        return resp.json()

    def get_config_value(self, section: str, key: str) -> str:
        if self.config is None:
            raise ValueError("Configuration parser is not initialized.")
        
        try:
            value = self.config.get(section, key)
            if value == "":
                raise ValueError(f"Configuration value for [{section}] {key} is empty.")
            return value

        except Exception as e:
            print(f"Error retrieving configuration value for [{section}] {key}: {e}")
            exit(1)

    def change_config_value(self, section: str, key: str, value: str):
        if self.config is None:
            raise ValueError("Configuration parser is not initialized.")
        
        try:
            self.config.set(section, key, value)
            self.write_config("config.ini")

        except Exception as e:
            print(f"Error changing configuration value for [{section}] {key}: {e}")
            exit(1)

    def update_loop(self, content_func: Callable[..., str]):

        while True:
            content = content_func()

            if content != self.last_msg:
                self.update_msg(content)
                self.last_msg = content
            
            time.sleep(self.timeout)