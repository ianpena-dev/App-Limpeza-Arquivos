"""
ClearFiles - Automated Disk Space Recovery Tool
Main UI and Application Logic
"""

import os
import json
import threading
import sys
import logging
from tkinter import filedialog, messagebox
from PIL import Image

import customtkinter as ctk
from cleaner import clean_folder, format_size
import scheduler

# Configuration
CONFIG_FILE = "config.json"

# Setup appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    """
    Main application class for ClearFiles.
    """
    def __init__(self):
        super().__init__()

        self.title("ClearFiles Professional")
        self.geometry("900x650")
        self.resizable(False, False)
        
        # Load icon
        if os.path.exists("icon.ico"):
            try:
                self.after(200, lambda: self.iconbitmap("icon.ico"))
            except Exception as e:
                logging.error(f"Could not load icon: {e}")

        # Data initialization
        config_data = self.load_config()
        self.folders = config_data.get("folders", [])
        self.schedule_type = config_data.get("schedule_type", "Manual")
        self.schedule_interval = config_data.get("schedule_interval", 60)

        self._setup_layout()
        self._setup_sidebar()
        self._setup_main_content()
        
        self.selected_folder_var = ctk.StringVar(value="")
        self.refresh_folder_list()

    def _setup_layout(self):
        """Configure main grid layout"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _setup_sidebar(self):
        """Create and configure the sidebar components"""
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#1a1a1a")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Logo
        if os.path.exists("logo.png"):
            try:
                logo_image = ctk.CTkImage(
                    light_image=Image.open("logo.png"),
                    dark_image=Image.open("logo.png"),
                    size=(120, 120)
                )
                self.logo_label = ctk.CTkLabel(self.sidebar_frame, image=logo_image, text="")
                self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10))
            except Exception as e:
                logging.error(f"Could not load logo: {e}")
        
        self.logo_text = ctk.CTkLabel(
            self.sidebar_frame, text="CLEARFILES", 
            font=ctk.CTkFont(size=22, weight="bold", family="Segoe UI")
        )
        self.logo_text.grid(row=1, column=0, padx=20, pady=(0, 30))

        # Status Badge
        self.status_card = ctk.CTkFrame(self.sidebar_frame, corner_radius=10, fg_color="#2d2d2d")
        self.status_card.grid(row=2, column=0, padx=15, pady=10, sticky="ew")
        
        self.status_title = ctk.CTkLabel(
            self.status_card, text="STATUS DO SISTEMA", 
            font=ctk.CTkFont(size=10, weight="bold"), text_color="#5a5a5a"
        )
        self.status_title.pack(padx=10, pady=(10, 0), anchor="w")
        
        self.status_label = ctk.CTkLabel(
            self.status_card, text="Pronto", 
            font=ctk.CTkFont(size=13, weight="bold"), text_color="#0078d7"
        )
        self.status_label.pack(padx=10, pady=(0, 10), anchor="w")

        # Main Action Button
        self.clean_button = ctk.CTkButton(
            self.sidebar_frame, text="LIMPAR AGORA", 
            height=45, fg_color="#0078d7", hover_color="#005a9e",
            font=ctk.CTkFont(weight="bold", size=14),
            command=self.start_cleaning_thread
        )
        self.clean_button.grid(row=3, column=0, padx=20, pady=30)

        # Version Info
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame, text="v2.1 Professional Edition\n© 2026 ClearFiles Team", 
            font=ctk.CTkFont(size=10), text_color="#444444"
        )
        self.version_label.grid(row=5, column=0, padx=20, pady=20)

    def _setup_main_content(self):
        """Create and configure the main content area"""
        self.content_frame = ctk.CTkFrame(self, fg_color="#121212", corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        
        self.main_header = ctk.CTkLabel(
            self.content_frame, text="Painel de Controle", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.main_header.grid(row=0, column=0, padx=30, pady=(30, 20), sticky="w")

        self._setup_folder_management()
        self._setup_automation()

    def _setup_folder_management(self):
        """Setup the folder management section"""
        self.folder_card = ctk.CTkFrame(self.content_frame, fg_color="#1e1e1e", corner_radius=15)
        self.folder_card.grid(row=1, column=0, padx=30, pady=10, sticky="nsew")
        
        header = ctk.CTkFrame(self.folder_card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(header, text="📁", font=ctk.CTkFont(size=20)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header, text="Diretórios para Limpeza", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.folder_frame = ctk.CTkScrollableFrame(self.folder_card, height=180, fg_color="transparent")
        self.folder_frame.pack(fill="both", expand=True, padx=15, pady=5)
        
        actions = ctk.CTkFrame(self.folder_card, fg_color="transparent")
        actions.pack(fill="x", padx=15, pady=(10, 15))
        
        self.add_button = ctk.CTkButton(actions, text="Adicionar Pasta", width=140, height=32, command=self.add_folder)
        self.add_button.pack(side="left", padx=(0, 10))
        
        self.remove_button = ctk.CTkButton(
            actions, text="Remover Selecionada", width=160, height=32, 
            fg_color="transparent", border_width=1, command=self.remove_selected
        )
        self.remove_button.pack(side="left")

    def _setup_automation(self):
        """Setup the automation and scheduling section"""
        self.schedule_card = ctk.CTkFrame(self.content_frame, fg_color="#1e1e1e", corner_radius=15)
        self.schedule_card.grid(row=2, column=0, padx=30, pady=20, sticky="ew")
        
        header = ctk.CTkFrame(self.schedule_card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=(15, 10))
        
        ctk.CTkLabel(header, text="⚙️", font=ctk.CTkFont(size=20)).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(header, text="Automação de Limpeza", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.sched_var = ctk.StringVar(value=self.schedule_type)
        options = ctk.CTkFrame(self.schedule_card, fg_color="transparent")
        options.pack(fill="x", padx=20, pady=5)

        ctk.CTkRadioButton(options, text="Somente Manual", value="Manual", variable=self.sched_var, command=self.update_schedule).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkRadioButton(options, text="Ao Iniciar o Windows", value="Logon", variable=self.sched_var, command=self.update_schedule).grid(row=0, column=1, padx=10, pady=10, sticky="w")
        ctk.CTkRadioButton(options, text="Ao Desligar o Computador", value="Shutdown", variable=self.sched_var, command=self.update_schedule).grid(row=1, column=0, padx=10, pady=10, sticky="w")

        interval_box = ctk.CTkFrame(options, fg_color="transparent")
        interval_box.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        ctk.CTkRadioButton(interval_box, text="A cada (min):", value="Interval", variable=self.sched_var, command=self.update_schedule).pack(side="left")
        
        self.interval_entry = ctk.CTkEntry(interval_box, width=50, height=24, border_width=1)
        self.interval_entry.insert(0, str(self.schedule_interval))
        self.interval_entry.pack(side="left", padx=5)
        self.interval_entry.bind("<FocusOut>", lambda e: self.update_schedule())

    def load_config(self):
        """Loads configuration from JSON file"""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return {"folders": data, "schedule_type": "Manual", "schedule_interval": 60}
                    return data
            except Exception as e:
                logging.error(f"Error loading config: {e}")
                return {}
        return {}

    def save_config(self):
        """Saves current configuration to JSON file"""
        try:
            config = {
                "folders": self.folders,
                "schedule_type": self.sched_var.get(),
                "schedule_interval": int(self.interval_entry.get() if self.interval_entry.get().isdigit() else 60)
            }
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving config: {e}")

    def refresh_folder_list(self):
        """Updates the visual folder list in the UI"""
        for widget in self.folder_frame.winfo_children():
            widget.destroy()
        
        if not self.folders:
            ctk.CTkLabel(self.folder_frame, text="Nenhum diretório adicionado para limpeza.", text_color="#5a5a5a").pack(pady=40)
            return

        for folder in self.folders:
            rb = ctk.CTkRadioButton(
                self.folder_frame, text=folder, 
                value=folder, variable=self.selected_folder_var,
                font=ctk.CTkFont(size=12)
            )
            rb.pack(padx=10, pady=8, anchor="w")

    def add_folder(self):
        """Handles directory selection and addition"""
        folder = filedialog.askdirectory()
        if folder and folder not in self.folders:
            self.folders.append(folder)
            self.save_config()
            self.refresh_folder_list()
            self.status_label.configure(text="Pasta Adicionada")

    def remove_selected(self):
        """Handles removal of the selected directory"""
        folder = self.selected_folder_var.get()
        if folder in self.folders:
            self.folders.remove(folder)
            self.save_config()
            self.refresh_folder_list()
            self.selected_folder_var.set("")
            self.status_label.configure(text="Pasta Removida")
        else:
            messagebox.showinfo("ClearFiles", "Selecione uma pasta na lista acima.")

    def update_schedule(self):
        """Synchronizes UI schedule settings with Windows Task Scheduler"""
        self.save_config()
        mode = self.sched_var.get()
        exe_path = os.path.abspath(sys.executable)
        
        try:
            if mode == "Manual":
                scheduler.set_manual_mode()
                self.status_label.configure(text="Modo Manual", text_color="#aaaaaa")
            elif mode == "Logon":
                scheduler.set_logon_mode(exe_path)
                self.status_label.configure(text="Agendado: Logon", text_color="#0078d7")
            elif mode == "Shutdown":
                scheduler.set_shutdown_mode(exe_path)
                self.status_label.configure(text="Agendado: Shutdown", text_color="#0078d7")
            elif mode == "Interval":
                val = self.interval_entry.get()
                interval = int(val) if val.isdigit() else 60
                scheduler.set_interval_mode(exe_path, interval)
                self.status_label.configure(text=f"Agendado: {interval}m", text_color="#0078d7")
        except Exception as e:
            messagebox.showerror("Erro de Agendamento", f"Falha ao configurar tarefa: {e}")

    def start_cleaning_thread(self):
        """Triggers the cleaning process in a background thread"""
        if not self.folders:
            messagebox.showwarning("Aviso", "Por favor, adicione ao menos uma pasta.")
            return
        
        self.clean_button.configure(state="disabled", text="LIMPANDO...")
        self.status_label.configure(text="Limpando...", text_color="#d35b5b")
        
        thread = threading.Thread(target=self.run_cleaning)
        thread.daemon = True
        thread.start()

    def run_cleaning(self):
        """Background worker for the cleaning logic"""
        total_freed = 0
        total_success = 0
        
        for folder in self.folders:
            s, f, size, errors = clean_folder(folder)
            total_success += s
            total_freed += size
        
        self.status_label.configure(text=f"Liberado: {format_size(total_freed)}", text_color="#00d778")
        self.clean_button.configure(state="normal", text="LIMPAR AGORA")
        messagebox.showinfo(
            "ClearFiles Professional", 
            f"Operação finalizada!\n\nItens removidos: {total_success}\nEspaço recuperado: {format_size(total_freed)}"
        )

def silent_clean():
    """Execution mode for scheduled tasks (no UI)"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                folders = config.get("folders", [])
                for folder in folders:
                    clean_folder(folder)
        except Exception as e:
            logging.error(f"Silent clean error: {e}")

if __name__ == "__main__":
    if "--silent" in sys.argv:
        silent_clean()
    else:
        app = App()
        app.mainloop()
