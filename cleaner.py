import os
import shutil
import logging
import math
import json
import ctypes
import sys
import stat
import uuid
from datetime import datetime, timedelta

# Default values, will be updated by main.py
HISTORY_FILE = "history.json"
LOG_FILE = "cleaner.log"
QUARANTINE_DIR = ""
QUARANTINE_FILE = ""

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

def remove_readonly(func, path, excinfo):
    """
    Error handler for shutil.rmtree.
    If the error is due to an access issue (read-only), it changes the permission and retries.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)

def empty_recycle_bin():
    """Empties the Windows Recycle Bin silently"""
    setup_logging()
    try:
        # 7 = SHERB_NOCONFIRMATION (1) | SHERB_NOPROGRESSUI (2) | SHERB_NOSOUND (4)
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 7)
        if result == 0:
            logging.info("Lixeira esvaziada com sucesso.")
            return True
    except Exception as e:
        logging.error(f"Erro ao esvaziar a lixeira: {e}")
    return False

def log_history(items, size_freed):
    """
    Saves the cleaning operation results to a history JSON file.
    """
    setup_logging() 
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
    if not os.path.exists(folder_path):
        return 0
    try:
        for entry in os.scandir(folder_path):
            if entry.is_file(follow_symlinks=False):
                total_size += entry.stat().st_size
            elif entry.is_dir(follow_symlinks=False):
                total_size += get_folder_size(entry.path)
    except (PermissionError, OSError) as e:
        logging.warning(f"Could not calculate size for {folder_path}: {e}")
    return total_size

def move_to_quarantine(item_path):
    """
    Moves an item to the quarantine directory and records its metadata.
    """
    if not QUARANTINE_DIR or not QUARANTINE_FILE:
        return False, 0
    
    if not os.path.exists(QUARANTINE_DIR):
        os.makedirs(QUARANTINE_DIR)
        
    item_name = os.path.basename(item_path)
    unique_id = str(uuid.uuid4())
    quarantine_path = os.path.join(QUARANTINE_DIR, unique_id)
    
    is_dir = os.path.isdir(item_path)
    try:
        size = get_folder_size(item_path) if is_dir else os.path.getsize(item_path)
        
        # Tenta mover, se falhar (ex: unidades diferentes), copia e apaga
        try:
            shutil.move(item_path, quarantine_path)
        except:
            if is_dir:
                shutil.copytree(item_path, quarantine_path)
                shutil.rmtree(item_path, onerror=remove_readonly)
            else:
                shutil.copy2(item_path, quarantine_path)
                try:
                    os.chmod(item_path, stat.S_IWRITE)
                    os.unlink(item_path)
                except Exception as e:
                    logging.error(f"Failed to delete original file after copy: {e}")
                    # Se não conseguiu apagar o original, removemos o da quarentena para não duplicar
                    if os.path.exists(quarantine_path):
                        os.unlink(quarantine_path)
                    raise e
        
        metadata = {
            "id": unique_id,
            "original_name": item_name,
            "original_path": item_path,
            "quarantine_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "size": size,
            "is_dir": is_dir
        }
        
        quarantine_data = []
        if os.path.exists(QUARANTINE_FILE):
            try:
                with open(QUARANTINE_FILE, "r") as f:
                    quarantine_data = json.load(f)
            except:
                quarantine_data = []
                
        quarantine_data.append(metadata)
        
        with open(QUARANTINE_FILE, "w") as f:
            json.dump(quarantine_data, f, indent=4)
            
        logging.info(f"Item movido para quarentena: {item_name} -> {unique_id}")
        return True, size
    except Exception as e:
        logging.error(f"Error moving {item_name} to quarantine: {e}")
        return False, 0

def clean_folder(folder_path, exclude_paths=None):
    """
    Moves files and subdirectories within the given folder path to quarantine.
    Returns (success_count, fail_count, total_size_freed_bytes, errors)
    """
    setup_logging()
    success_count = 0
    fail_count = 0
    total_size_freed = 0
    errors = []

    if exclude_paths is None:
        exclude_paths = []
        if hasattr(sys, '_MEIPASS'):
            exclude_paths.append(os.path.abspath(sys._MEIPASS).lower())

    if not os.path.exists(folder_path):
        error_msg = f"Pasta não existe: {folder_path}"
        logging.error(error_msg)
        return 0, 0, 0, [error_msg]

    try:
        for entry in os.scandir(folder_path):
            item_path = entry.path
            if os.path.abspath(item_path).lower() in exclude_paths:
                continue

            success, size = move_to_quarantine(item_path)
            if success:
                total_size_freed += size
                success_count += 1
            else:
                fail_count += 1
                errors.append(f"Falha ao mover para quarentena: {entry.name}")
                
    except Exception as e:
        error_msg = f"Erro ao acessar diretório {folder_path}: {str(e)}"
        errors.append(error_msg)
        logging.error(error_msg)
    
    return success_count, fail_count, total_size_freed, errors

def process_quarantine_auto_delete():
    """
    Permanently deletes items from quarantine that are older than 30 days.
    """
    setup_logging()
    if not os.path.exists(QUARANTINE_FILE):
        return
        
    try:
        with open(QUARANTINE_FILE, "r") as f:
            quarantine_data = json.load(f)
            
        now = datetime.now()
        thirty_days_ago = now - timedelta(days=30)
        
        remaining_data = []
        for item in quarantine_data:
            q_date = datetime.strptime(item["quarantine_date"], "%Y-%m-%d %H:%M:%S")
            if q_date < thirty_days_ago:
                # Delete permanently
                q_path = os.path.join(QUARANTINE_DIR, item["id"])
                if os.path.exists(q_path):
                    try:
                        if item["is_dir"]:
                            shutil.rmtree(q_path, onerror=remove_readonly)
                        else:
                            os.unlink(q_path)
                        logging.info(f"Item {item['original_name']} removido permanentemente da quarentena por decurso de prazo (30 dias).")
                    except Exception as e:
                        logging.error(f"Erro ao deletar item expirado {item['original_name']}: {e}")
                        remaining_data.append(item)
                else:
                    logging.warning(f"Item {item['original_name']} não encontrado fisicamente para deleção automática.")
            else:
                remaining_data.append(item)
                
        with open(QUARANTINE_FILE, "w") as f:
            json.dump(remaining_data, f, indent=4)
            
    except Exception as e:
        logging.error(f"Error during auto-delete from quarantine: {e}")

def restore_from_quarantine(item_id):
    """Restores an item from quarantine to its original location"""
    setup_logging()
    try:
        with open(QUARANTINE_FILE, "r") as f:
            quarantine_data = json.load(f)
            
        item_index = -1
        for i, item in enumerate(quarantine_data):
            if item["id"] == item_id:
                item_index = i
                break
        
        if item_index == -1:
            logging.error(f"Tentativa de restaurar item inexistente ID: {item_id}")
            return False, "Item não encontrado no registro da quarentena."
            
        item = quarantine_data[item_index]
        q_path = os.path.join(QUARANTINE_DIR, item["id"])
        dest_path = item["original_path"]
        
        logging.info(f"Iniciando restauração: {item['original_name']} para {dest_path}")
        
        if os.path.exists(q_path):
            # Ensure destination directory exists
            dest_dir = os.path.dirname(dest_path)
            if not os.path.exists(dest_dir):
                os.makedirs(dest_dir)
                logging.info(f"Diretório de destino criado: {dest_dir}")
                
            # Se o arquivo já existir no destino, removemos para evitar erro no move/copy
            if os.path.exists(dest_path):
                logging.warning(f"Arquivo já existe no destino. Sobrescrevendo: {dest_path}")
                try:
                    if os.path.isdir(dest_path):
                        shutil.rmtree(dest_path, onerror=remove_readonly)
                    else:
                        os.unlink(dest_path)
                except Exception as e:
                    logging.error(f"Não foi possível remover arquivo existente no destino: {e}")
                    return False, f"O arquivo já existe no destino e não pôde ser sobrescrito: {e}"

            # Tenta restaurar
            try:
                shutil.move(q_path, dest_path)
            except Exception as e:
                logging.warning(f"shutil.move falhou, tentando copy+delete: {e}")
                try:
                    if item["is_dir"]:
                        shutil.copytree(q_path, dest_path)
                        shutil.rmtree(q_path, onerror=remove_readonly)
                    else:
                        shutil.copy2(q_path, dest_path)
                        os.unlink(q_path)
                except Exception as e2:
                    logging.error(f"Falha total na restauração: {e2}")
                    return False, f"Erro ao mover arquivo de volta: {e2}"
            
            # Remove from metadata
            quarantine_data.pop(item_index)
            with open(QUARANTINE_FILE, "w") as f:
                json.dump(quarantine_data, f, indent=4)
            
            logging.info(f"Item restaurado com sucesso: {item['original_name']}")
            return True, "Item restaurado com sucesso."
        else:
            logging.error(f"Arquivo físico não encontrado na quarentena: {q_path}")
            return False, "Arquivo físico não encontrado na quarentena."
            
    except Exception as e:
        logging.error(f"Erro inesperado na restauração: {e}")
        return False, str(e)

def delete_permanently(item_id):
    """Permanently deletes an item from quarantine"""
    setup_logging()
    try:
        with open(QUARANTINE_FILE, "r") as f:
            quarantine_data = json.load(f)
            
        item_index = -1
        for i, item in enumerate(quarantine_data):
            if item["id"] == item_id:
                item_index = i
                break
        
        if item_index == -1:
            return False, "Item não encontrado."
            
        item = quarantine_data[item_index]
        q_path = os.path.join(QUARANTINE_DIR, item["id"])
        
        logging.info(f"Deletando permanentemente: {item['original_name']} (ID: {item['id']})")
        
        # Tenta deletar o arquivo físico
        file_deleted = True
        if os.path.exists(q_path):
            try:
                if item["is_dir"]:
                    shutil.rmtree(q_path, onerror=remove_readonly)
                else:
                    # Força permissão de escrita antes de apagar
                    os.chmod(q_path, stat.S_IWRITE)
                    os.unlink(q_path)
            except Exception as e:
                logging.error(f"Erro ao deletar arquivo físico na quarentena: {e}")
                file_deleted = False
                # Mesmo se falhar a deleção física (ex: arquivo preso por outro processo), 
                # vamos remover do JSON para o usuário não ficar vendo o erro repetidamente.
                # O autodelete de 30 dias tentará limpar os restos depois.
                
        # Remove from metadata (sempre, para evitar loop de erro na UI)
        quarantine_data.pop(item_index)
        with open(QUARANTINE_FILE, "w") as f:
            json.dump(quarantine_data, f, indent=4)
            
        if not file_deleted:
            return True, "Item removido da lista (o arquivo físico estava ocupado e será removido automaticamente mais tarde)."
            
        return True, "Item removido permanentemente."
            
    except Exception as e:
        logging.error(f"Erro ao deletar item da quarentena: {e}")
        return False, str(e)

def format_size(size_bytes):
    """Helper to format bytes into human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"
