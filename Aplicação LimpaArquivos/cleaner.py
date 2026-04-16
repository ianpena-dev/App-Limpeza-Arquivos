import os
import shutil
import logging

def clean_folder(folder_path):
    """
    Tries to delete all files and subdirectories within the given folder path.
    Returns (success_count, fail_count, total_size_freed_bytes, errors)
    """
    success_count = 0
    fail_count = 0
    total_size_freed = 0
    errors = []

    if not os.path.exists(folder_path):
        return 0, 0, 0, [f"Pasta não existe: {folder_path}"]

    for item in os.listdir(folder_path):
        item_path = os.path.join(folder_path, item)
        try:
            # Calculate size before deletion
            if os.path.isfile(item_path) or os.path.islink(item_path):
                file_size = os.path.getsize(item_path)
                os.unlink(item_path)
                total_size_freed += file_size
                success_count += 1
            elif os.path.isdir(item_path):
                # Calculate size of directory recursively
                dir_size = 0
                for dirpath, dirnames, filenames in os.walk(item_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        if not os.path.islink(fp):
                            dir_size += os.path.getsize(fp)
                
                shutil.rmtree(item_path)
                total_size_freed += dir_size
                success_count += 1
        except Exception as e:
            fail_count += 1
            errors.append(f"Erro ao remover {item}: {str(e)}")
    
    return success_count, fail_count, total_size_freed, errors

def format_size(size_bytes):
    """Helper to format bytes into human readable format"""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])
