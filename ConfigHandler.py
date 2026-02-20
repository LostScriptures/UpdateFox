from configparser import ConfigParser
from enum import StrEnum
from pathlib import Path

CWD = Path(__file__).parent

class ConfigSections(StrEnum):
    WEBHOOK = "WEBHOOK"
    UPDATER = "UPDATER"
    PRINTER = "PRINTER"

class ConfigHandler:
    """Holds the values of the config file in memory and provides methods to access and modify them."""
    def __init__(self, filename: str):
        self.filename = filename
        self.parser = ConfigParser()

        try:
            with open(CWD / filename, "r") as f:
                self.parser.read_file(f)

        except FileNotFoundError:
            print(f"Could not find configuration file: {filename}")
            exit(1)

        except PermissionError:
            print(f"Permission denied when trying to read configuration file: {filename}")
            exit(1)

    def get_value(self, section: str, key: str) -> str:
        """Retrieves a configuration value from the config parser, ensuring that it exists and is not empty."""
        if self.parser is None:
            raise RuntimeError("Configuration parser is not initialized.")
        
        value = self.parser.get(section, key)
        if value == "":
            print(f"Configuration value for [{section}] {key} is empty.")
        return value
    
    def __write_config(self):
        """Writes the current configuration back to the specified file."""
        if self.parser is None:
            raise ValueError("Configuration parser is not initialized.")

        try:
            with open(CWD / self.filename, "w") as f:
                self.parser.write(f)
        
        except FileNotFoundError:
            print("Could not find configuration file")
            exit(1)

        except PermissionError:
            print("Permission denied when trying to write to configuration file")
            exit(1)

    def change_value(self, section: str, key: str, value: str):
        """Changes a configuration value and writes the updated configuration back to the file."""
        if self.parser is None:
            raise ValueError("Configuration parser is not initialized.")
        
        try:
            self.parser.set(section, key, value)
            self.__write_config()

        except Exception as e:
            print(f"Error changing configuration value for [{section}] {key}: {e}")
            exit(1)
