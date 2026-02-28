import logging
import psutil
import time

# Create a custom logger
step_logger = logging.getLogger("step_logger")
step_logger.setLevel(logging.INFO)

# Create console handler
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# Create formatter
formatter = logging.Formatter('%(asctime)s | %(levelname)-7s | %(message)s', datefmt='%H:%M:%S')
ch.setFormatter(formatter)

# Add handler to logger
if not step_logger.handlers:
    step_logger.addHandler(ch)

def log_memory_status(step_name, start_time=None):
    mem = psutil.virtual_memory().percent
    cpu = psutil.cpu_percent()
    msg = f"[{step_name}] | CPU: {cpu}% | RAM: {mem}%"
    if start_time:
        duration = time.time() - start_time
        msg += f" | Duration: {duration:.2f}s"
    step_logger.info(msg)