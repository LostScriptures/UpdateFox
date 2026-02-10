import psutil
import time
from functools import partial
import bambulabs_api as bl

from webhook import WebhookUpdater
from GithubUpdater import GithubUpdater

def get_system_stats(printer: bl.Printer, restart: bool) -> str:
    """Gathers system statistics such as CPU usage, RAM usage, battery status, and printer status, and returns a formatted string with this information. If the restart flag is set, it disconnects the printer and returns a restart message."""
    if restart:
        printer.disconnect()
        return "Restarting..."
    
    msg = "System Stats:\n-- CPU --\n"

    # CPU usage (percentage)
    cpu_usage = psutil.cpu_percent(interval=1)

    # RAM usage
    memory = psutil.virtual_memory()
    ram_used = memory.used / (1024 ** 3)      # GB
    ram_total = memory.total / (1024 ** 3)    # GB
    ram_percent = memory.percent

    # Battery / power info (if available)
    battery = psutil.sensors_battery()

    msg += f"CPU Usage: {cpu_usage}%\n"

    # CPU frequency
    freq = psutil.cpu_freq()
    msg += f"CPU Frequency: {freq.current:.2f} MHz\n"
    msg += "Core Usages: "
    for i, usage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
        msg += f"|{i}: {usage}% "
    msg += "|\n"

    # RAM usage
    msg += "-- RAM --\n"
    msg += f"RAM Usage: {ram_used:.2f} GB / {ram_total:.2f} GB ({ram_percent}%)\n"

    msg += "-- Battery --\n"
    if battery:
        msg += f"Battery: {battery.percent}%\n"
        msg += f"Plugged in: {battery.power_plugged}\n"
    else:
        msg += "Battery info not available\n"

    # Get a status string from the printer
    msg += f"-- Printer --\n"
    status = printer.get_current_state()
    msg += f"Printer status: {status}\n"
    if status.name != "IDLE":
        msg += f"Current Job: {printer.get_file_name()}\n"
        msg += f"Progress: {printer.current_layer_num()}/{printer.total_layer_num()} ({printer.get_percentage()}%)\n"

    return msg

if __name__ == "__main__":
    webhook = WebhookUpdater(timeout=10)
    ip = webhook.get_config_value("PRINTER", "ip")
    serial = webhook.get_config_value("PRINTER", "serial")
    access_code = webhook.get_config_value("PRINTER", "access_code")

    # Set up the GithubUpdater with details from the configuration file and assign it to the WebhookUpdater instance
    github_updater = GithubUpdater(
        repo_owner=webhook.get_config_value("UPDATER", "repo_owner"),
        repo_name=webhook.get_config_value("UPDATER", "repo_name"),
        branch=webhook.get_config_value("UPDATER", "branch"),
        trigger=webhook.get_config_value("UPDATER", "trigger"),
        local_repo_path=webhook.get_config_value("UPDATER", "local_repo_path")
    )

    webhook.set_updater(github_updater)

    printer = bl.Printer(ip, access_code, serial)
    
    printer.connect()
    with_session = partial(get_system_stats, printer)
    webhook.update_loop(with_session)
    
    printer.disconnect()