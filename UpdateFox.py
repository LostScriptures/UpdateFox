import psutil
import time
from functools import partial
import bambulabs_api as bl

from webhook import WebhookUpdater

def get_system_stats(printer: bl.Printer) -> str:
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
    updater = WebhookUpdater(timeout=10)
    ip = updater.get_config_value("PRINTER", "ip")
    serial = updater.get_config_value("PRINTER", "serial")
    access_code = updater.get_config_value("PRINTER", "access_code")
    
    printer = bl.Printer(ip, access_code, serial)
    
    printer.connect()
    with_session = partial(get_system_stats, printer)
    updater.update_loop(with_session)
    
    printer.disconnect()