import os
import shutil
import logging
import math
import json
from datetime import datetime

HISTORY_FILE = "history.json"
LOG_FILE = "cleaner.log"

def setup_logging():
    """Configures logging with the current LOG_FILE path"""
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s: %(message)s',
        filename=LOG_FILE,
        filemode='a'
    )

def log_history(items, size_freed):
    """
    Saves the cleaning operation results to a history JSON file.
    """
    setup_logging() # Ensure logging is ready
    new_entry = {
        "date": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "items": items,
        "size": format_size(size_freed)
    }
    
    history = []
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
        except Exception as e:
            logging.error(f"Error reading history file: {e}")
            history = []
    
    history.insert(0, new_entry)
    # Keep only the last 50 entries
    history = history[:50]
    
    try:
        with open(HISTORY_FILE, "w") as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        logging.error(f"Error writing to history file: {e}")

def get_folder_size(folder_path):
    """
    Calculates the total size of a folder recursively.
    """
    total_size = 0
    try:
        for entry in os.scandir(folder_path):
            if entry.is_file(follow_symlinks=False):
                total_size += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total_size += get_folder_size(entry.path)
    except (PermissionError, OSError) as e:
        logging.warning(f"Could not calculate size for {folder_path}: {e}")
    return total_size

def clean_folder(folder_path):
    """
    Tries to delete all files and subdirectories within the given folder path.
    Returns (success_count, fail_count, total_size_freed_bytes, errors)
    """
    setup_logging() # Ensure logging is ready
    success_count = 0
    fail_count = 0
    total_size_freed = 0
    errors = []

    if not os.path.exists(folder_path):
        error_msg = f"Pasta não existe: {folder_path}"
        logging.error(error_msg)
        return 0, 0, 0, [error_msg]

    try:
        for entry in os.scandir(folder_path):
            item_path = entry.path
            try:
                # Calculate size before deletion
                if entry.is_file(follow_symlinks=False) or entry.is_symlink():
                    file_size = entry.stat().st_size
                    os.unlink(item_path)
                    total_size_freed += file_size
                    success_count += 1
                elif entry.is_dir(follow_symlinks=False):
                    dir_size = get_folder_size(item_path)
                    shutil.rmtree(item_path)
                    total_size_freed += dir_size
                    success_count += 1
            except Exception as e:
                fail_count += 1
                error_msg = f"Erro ao remover {entry.name}: {str(e)}"
                errors.append(error_msg)
                logging.error(error_msg)
    except Exception as e:
        error_msg = f"Erro ao acessar diretório {folder_path}: {str(e)}"
        errors.append(error_msg)
        logging.error(error_msg)
    
    return success_count, fail_count, total_size_freed, errors

def format_size(size_bytes):
    """Helper to format bytes into human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
