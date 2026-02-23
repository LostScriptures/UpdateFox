import psutil
from functools import partial
from dataclasses import dataclass, field
import bambulabs_api as bl
from pathlib import Path

from webhook import WebhookUpdater
from GithubUpdater import GithubUpdater
from ConfigHandler import ConfigHandler, ConfigSections as CS

# TODO: Make the entire system into a server and multi client system
#       - Client gathers pc data and reports back to server
#       - Server collects data and printer info and sends updates to discord 

@dataclass
class PCStats:
    cpu_usage: float = field(default=0.0)
    cpu_freq: float = field(default=0.0)
    cpu_core_usages: list[float] = field(default_factory=list)

    ram_used: float = field(default=0.0)
    ram_total: float = field(default=0.0)
    ram_percent: float = field(default=0.0)
    battery: bool = field(default=False)
    battery_percent: float = field(default=0.0)
    battery_plugged: bool = field(default=False)

def gather_system_stats() -> PCStats:
    """Gathers system statistics such as CPU usage, RAM usage, and battery status, and returns a PCStats dataclass instance with this information."""
    stats = PCStats()

    # CPU usage (percentage)
    stats.cpu_usage = psutil.cpu_percent(interval=1)

    # CPU frequency
    freq = psutil.cpu_freq()
    stats.cpu_freq = freq.current if freq else 0.0

    # CPU core usages
    stats.cpu_core_usages = psutil.cpu_percent(percpu=True, interval=1)

    # RAM usage
    memory = psutil.virtual_memory()
    stats.ram_used = memory.used / (1024 ** 3)      # GB
    stats.ram_total = memory.total / (1024 ** 3)    # GB
    stats.ram_percent = memory.percent

    # Battery / power info (if available)
    battery = psutil.sensors_battery()
    if battery:
        stats.battery = True
        stats.battery_percent = battery.percent
        stats.battery_plugged = battery.power_plugged
    
    else:
        stats.battery = False

    return stats

def construct_msg(printer: bl.Printer, restart: bool) -> str:
    """Gathers system statistics such as CPU usage, RAM usage, battery status, and printer status, and returns a formatted string with this information. If the restart flag is set, it disconnects the printer and returns a restart message."""
    if restart:
        printer.disconnect()
        return "Restarting..."
    
    system_stats = gather_system_stats()

    msg = "System Stats:\n-- CPU --\n"

    # CPU
    msg += f"CPU Usage: {system_stats.cpu_usage}%\n"

    msg += f"CPU Frequency: {system_stats.cpu_freq:.2f} MHz\n"
    msg += "Core Usages: "
    for i, usage in enumerate(system_stats.cpu_core_usages):
        msg += f"|{i}: {usage}% "
    msg += "|\n"

    # RAM
    msg += "-- RAM --\n"
    msg += f"RAM Usage: {system_stats.ram_used:.2f} GB / {system_stats.ram_total:.2f} GB ({system_stats.ram_percent}%)\n"

    # Battery
    msg += "-- Battery --\n"
    if system_stats.battery:
        msg += f"Battery: {system_stats.battery_percent}%\n"
        msg += f"Plugged in: {system_stats.battery_plugged}\n"
    else:
        msg += "Battery info not available\n"

    # Printer
    msg += f"-- Printer --\n"
    status = printer.get_current_state()
    msg += f"Printer status: {status}\n"

    if status.name != "IDLE":
        msg += f"Current Job: {printer.get_file_name()}\n"
        msg += f"Progress: {printer.current_layer_num()}/{printer.total_layer_num()} ({printer.get_percentage()}%)\n"

    return msg

if __name__ == "__main__":
    config = ConfigHandler("config.ini")
    webhook = WebhookUpdater(config, timeout=10)

    if config.get_value(CS.UPDATER, "local_repo_path") == "":
        print("Setting local_repo_path to the current directory...")
        config.change_value(CS.UPDATER, "local_repo_path", str(Path(__file__).parent))
        print(Path(__file__).parent)

    # Set up the GithubUpdater with details from the configuration file and assign it to the WebhookUpdater instance
    github_updater = GithubUpdater(
        config.get_value(CS.UPDATER, "repo_owner"),
        config.get_value(CS.UPDATER, "repo_name"),
        config.get_value(CS.UPDATER, "branch"),
        config.get_value(CS.UPDATER, "local_repo_path")
    )

    webhook.set_updater(github_updater)

    printer = bl.Printer(
        config.get_value(CS.PRINTER, "ip"),
        config.get_value(CS.PRINTER, "access_code"),
        config.get_value(CS.PRINTER, "serial")
    )
    
    printer.connect()
    with_session = partial(construct_msg, printer)
    try:
        print("Starting update loop...")
        webhook.update_loop(with_session)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        printer.disconnect()