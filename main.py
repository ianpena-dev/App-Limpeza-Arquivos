"""
ClearFiles - Automated Disk Space Recovery Tool
Main UI and Application Logic
"""

import os
import json
import threading
import sys
import logging
import ctypes
from tkinter import filedialog, messagebox
from PIL import Image
import pystray
from pystray import MenuItem as item

import customtkinter as ctk
import cleaner
from cleaner import clean_folder, format_size, log_history, empty_recycle_bin
import scheduler

# Função para localizar recursos (ícones, imagens) dentro do executável
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Define onde os dados (config/histórico) serão salvos: em %APPDATA% para ficarem "escondidos"
DATA_DIR = os.path.join(os.getenv('APPDATA'), "ClearFiles")
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

# Atualiza os caminhos no módulo cleaner também
cleaner.HISTORY_FILE = HISTORY_FILE
cleaner.LOG_FILE = os.path.join(DATA_DIR, "cleaner.log")

# Setup appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    """
    Main application class for ClearFiles.
    """
    def __init__(self):
        super().__init__()

        self.title("ClearFiles")
        self.geometry("900x650")
        self.resizable(False, False)
        
        # Tenta aplicar o tema escuro na barra de título do Windows
        try:
            from ctypes import windll, byref, sizeof, c_int
            HWND = windll.user32.GetParent(self.winfo_id())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            dark_mode = c_int(1)
            windll.dwmapi.DwmSetWindowAttribute(HWND, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(dark_mode), sizeof(dark_mode))
        except:
            pass

        # Load icon
        icon_path = resource_path("icon.ico")
        if os.path.exists(icon_path):
            try:
                self.after(200, lambda: self.iconbitmap(icon_path))
            except Exception as e:
                logging.error(f"Could not load icon: {e}")

        # Data initialization
        config_data = self.load_config()
        self.folders = config_data.get("folders", [])
        self.schedule_type = config_data.get("schedule_type", "Manual")
        self.schedule_interval = config_data.get("schedule_interval", 60)
        
        # Força Modo Dark permanente
        ctk.set_appearance_mode("Dark")

        self._setup_layout()
        self._setup_sidebar()
        self._setup_main_content()
        
        self.selected_folder_var = ctk.StringVar(value="")
        self.refresh_folder_list()
        
        # Tray Icon setup
        self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.create_tray_icon()

    def hide_window(self):
        """Hides the window instead of closing it"""
        self.withdraw()

    def show_window(self, icon=None, item=None):
        """Shows the window again (thread-safe)"""
        self.after(0, self._show_window_main)

    def _show_window_main(self):
        self.deiconify()
        self.focus_force()
        self.refresh_history()

    def quit_app(self, icon=None, item=None):
        """Completely closes the application"""
        if icon:
            icon.stop()
        self.after(0, self._actual_quit)

    def _actual_quit(self):
        """Internal method to perform the actual destruction of the app"""
        try:
            self.destroy()
        except:
            pass
        sys.exit(0)

    def create_tray_icon(self):
        """Creates the system tray icon"""
        icon_path = resource_path("icon.ico")
        if not os.path.exists(icon_path):
            logging.warning(f"Tray icon skipped: {icon_path} not found.")
            return

        try:
            image = Image.open(icon_path)
            menu = (
                item('Abrir ClearFiles', self.show_window, default=True),
                item('Limpar Agora', lambda i, it: self.start_cleaning_thread()),
                item('Sair', self.quit_app)
            )
            self.tray_icon = pystray.Icon("clearfiles", image, "ClearFiles Professional", menu)
            
            # Start tray icon in a separate thread
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            logging.error(f"Error creating tray icon: {e}")

    def _setup_layout(self):
        """Configure main grid layout"""
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def _setup_sidebar(self):
        """Create and configure the sidebar components with a modern premium look"""
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#111111")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        # Logo Section
        logo_path = resource_path("logo.png")
        if os.path.exists(logo_path):
            try:
                logo_image = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(100, 100)
                )
                self.logo_label = ctk.CTkLabel(self.sidebar_frame, image=logo_image, text="")
                self.logo_label.grid(row=0, column=0, padx=20, pady=(40, 5))
            except Exception as e:
                logging.error(f"Could not load logo: {e}")
        
        self.logo_text = ctk.CTkLabel(
            self.sidebar_frame, text="CLEARFILES", 
            font=ctk.CTkFont(size=24, weight="bold", family="Segoe UI"), text_color="#FFFFFF"
        )
        self.logo_text.grid(row=1, column=0, padx=20, pady=(0, 40))

        # Status Badge (Modern Card)
        self.status_card = ctk.CTkFrame(self.sidebar_frame, corner_radius=12, fg_color="#1E1E1E", border_width=1, border_color="#333333")
        self.status_card.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.status_title = ctk.CTkLabel(
            self.status_card, text="STATUS DO SISTEMA", 
            font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888"
        )
        self.status_title.pack(padx=15, pady=(12, 0), anchor="w")
        
        self.status_label = ctk.CTkLabel(
            self.status_card, text="Pronto para Otimizar", 
            font=ctk.CTkFont(size=14, weight="bold"), text_color="#00D2FF"
        )
        self.status_label.pack(padx=15, pady=(0, 12), anchor="w")

        # Main Action Button (Restaurado)
        self.clean_button = ctk.CTkButton(
            self.sidebar_frame, text="LIMPAR AGORA", 
            height=50, corner_radius=10,
            fg_color="#0078D7", hover_color="#005A9E", 
            text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold", size=15),
            command=self.start_cleaning_thread
        )
        self.clean_button.grid(row=3, column=0, padx=20, pady=30)

        # Version Info
        self.version_label = ctk.CTkLabel(
            self.sidebar_frame, text="v2.2 Pro Edition\n© 2026 ClearFiles Team", 
            font=ctk.CTkFont(size=10), text_color="#555555"
        )
        self.version_label.grid(row=5, column=0, padx=20, pady=20)

    def _setup_main_content(self):
        """Create and configure the main content area with a clean layout"""
        self.content_frame = ctk.CTkFrame(self, fg_color=("#F0F0F0", "#0A0A0A"), corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_columnconfigure(0, weight=1)
        self.content_frame.grid_rowconfigure(1, weight=1)
        
        self.main_header = ctk.CTkLabel(
            self.content_frame, text="Painel de Controle", 
            font=ctk.CTkFont(size=28, weight="bold"), text_color=("#111111", "#FFFFFF")
        )
        self.main_header.grid(row=0, column=0, padx=40, pady=(40, 15), sticky="w")

        # Tabview Styling
        self.tabview = ctk.CTkTabview(
            self.content_frame, 
            fg_color="transparent",
            segmented_button_fg_color=("#E0E0E0", "#1E1E1E"),
            segmented_button_selected_color="#0078D7",
            segmented_button_selected_hover_color="#005A9E",
            segmented_button_unselected_color=("#E0E0E0", "#1E1E1E"),
            segmented_button_unselected_hover_color=("#D0D0D0", "#333333")
        )
        self.tabview.grid(row=1, column=0, padx=30, pady=(0, 30), sticky="nsew")
        
        self.tab_control = self.tabview.add("Limpeza")
        self.tab_history = self.tabview.add("Histórico")
        
        # Scrollable container
        self.scroll_control = ctk.CTkScrollableFrame(self.tab_control, fg_color="transparent")
        self.scroll_control.pack(fill="both", expand=True)
        
        self._setup_folder_management(self.scroll_control)
        self._setup_automation(self.scroll_control)
        self._setup_history_tab(self.tab_history)

    def _setup_folder_management(self, parent):
        """Setup the folder management section with a modern clean look"""
        self.folder_card = ctk.CTkFrame(parent, fg_color=("#FFFFFF", "#151515"), corner_radius=15, border_width=1, border_color=("#CCCCCC", "#252525"))
        self.folder_card.pack(fill="x", padx=10, pady=10)
        
        header = ctk.CTkFrame(self.folder_card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 15))
        
        ctk.CTkLabel(header, text="📁", font=ctk.CTkFont(size=22), text_color=("#000000", "#FFFFFF")).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(header, text="Diretórios para Limpeza", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#111111", "#FFFFFF")).pack(side="left")

        self.folder_frame = ctk.CTkScrollableFrame(self.folder_card, height=180, fg_color=("#F9F9F9", "#0D0D0D"), corner_radius=10, border_width=1, border_color=("#E0E0E0", "#202020"))
        self.folder_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        actions = ctk.CTkFrame(self.folder_card, fg_color="transparent")
        actions.pack(fill="x", padx=20, pady=(15, 20))
        
        self.add_button = ctk.CTkButton(
            actions, text="Adicionar Pasta", width=150, height=35, corner_radius=8,
            fg_color="#0078D7", hover_color="#005A9E", text_color="#FFFFFF", 
            font=ctk.CTkFont(weight="bold"), command=self.add_folder
        )
        self.add_button.pack(side="left", padx=(0, 12))
        
        self.remove_button = ctk.CTkButton(
            actions, text="Remover Selecionada", width=180, height=35, corner_radius=8,
            fg_color="transparent", border_width=1, border_color=("#777777", "#444444"), 
            text_color=("#333333", "#BBBBBB"), hover_color=("#E0E0E0", "#2D2D2D"), 
            font=ctk.CTkFont(weight="bold"), command=self.remove_selected
        )
        self.remove_button.pack(side="left")

    def _setup_automation(self, parent):
        """Setup the automation section with modern switches and layout"""
        self.schedule_card = ctk.CTkFrame(parent, fg_color=("#FFFFFF", "#151515"), corner_radius=15, border_width=1, border_color=("#CCCCCC", "#252525"))
        self.schedule_card.pack(fill="x", padx=10, pady=10)
        
        header = ctk.CTkFrame(self.schedule_card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 15))
        
        ctk.CTkLabel(header, text="⚙️", font=ctk.CTkFont(size=22), text_color=("#000000", "#FFFFFF")).pack(side="left", padx=(0, 12))
        ctk.CTkLabel(header, text="Automação de Limpeza", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#111111", "#FFFFFF")).pack(side="left")

        self.sched_var = ctk.StringVar(value=self.schedule_type)
        options = ctk.CTkFrame(self.schedule_card, fg_color="transparent")
        options.pack(fill="x", padx=25, pady=5)

        # Usando cores mais vibrantes para os radio buttons
        radio_params = {"variable": self.sched_var, "text_color": ("#333333", "#CCCCCC"), "hover_color": ("#E0E0E0", "#333333"), "fg_color": "#0078D7"}
        
        ctk.CTkRadioButton(options, text="Somente Manual", value="Manual", **radio_params).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        ctk.CTkRadioButton(options, text="Ao Iniciar (Logon)", value="Logon", **radio_params).grid(row=0, column=1, padx=10, pady=10, sticky="w")
        ctk.CTkRadioButton(options, text="Ao Desligar", value="Shutdown", **radio_params).grid(row=1, column=0, padx=10, pady=10, sticky="w")

        interval_box = ctk.CTkFrame(options, fg_color="transparent")
        interval_box.grid(row=1, column=1, padx=10, pady=10, sticky="w")
        
        ctk.CTkRadioButton(interval_box, text="Intervalo (min):", value="Interval", **radio_params).pack(side="left")
        
        self.interval_entry = ctk.CTkEntry(
            interval_box, width=60, height=28, corner_radius=6,
            fg_color=("#FFFFFF", "#0D0D0D"), border_color=("#CCCCCC", "#333333"), text_color=("#000000", "#FFFFFF")
        )
        self.interval_entry.insert(0, str(self.schedule_interval))
        self.interval_entry.pack(side="left", padx=10)

        self.apply_button = ctk.CTkButton(
            self.schedule_card, text="SALVAR E APLICAR CONFIGURAÇÕES", 
            width=300, height=45, corner_radius=10,
            fg_color="#0078D7", hover_color="#005A9E", text_color="#FFFFFF",
            font=ctk.CTkFont(weight="bold", size=14),
            command=self.update_schedule
        )
        self.apply_button.pack(pady=(25, 30))

    def _setup_history_tab(self, parent):
        """Setup the history display tab"""
        header = ctk.CTkFrame(parent, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=(10, 0))
        
        ctk.CTkLabel(header, text="Histórico de Atividades", font=ctk.CTkFont(size=18, weight="bold"), text_color=("#111111", "#FFFFFF")).pack(side="left", padx=20, pady=15)
        
        self.clear_history_btn = ctk.CTkButton(
            header, text="Limpar Histórico", width=130, height=32, corner_radius=8,
            fg_color=("#BBBBBB", "#333333"), hover_color=("#999999", "#444444"), text_color=("#FFFFFF", "#FFFFFF"),
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self.clear_history
        )
        self.clear_history_btn.pack(side="right", padx=20)

        self.history_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.refresh_history()

    def clear_history(self):
        """Removes all history entries after user confirmation"""
        if not os.path.exists(HISTORY_FILE):
            return
            
        if messagebox.askyesno("Confirmar", "Deseja realmente apagar todo o histórico de limpezas?"):
            try:
                os.remove(HISTORY_FILE)
                self.refresh_history()
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível apagar o histórico: {e}")

    def refresh_history(self):
        """Reload and display history entries with a premium card design"""
        for widget in self.history_frame.winfo_children():
            widget.destroy()
            
        if not os.path.exists(HISTORY_FILE):
            ctk.CTkLabel(self.history_frame, text="Nenhum histórico disponível.", text_color=("#777777", "#555555"), font=ctk.CTkFont(size=14)).pack(pady=60)
            return
            
        try:
            with open(HISTORY_FILE, "r") as f:
                history = json.load(f)
                
            if not history:
                ctk.CTkLabel(self.history_frame, text="O histórico está vazio.", text_color=("#777777", "#555555"), font=ctk.CTkFont(size=14)).pack(pady=60)
                return
                
            for entry in history:
                card = ctk.CTkFrame(self.history_frame, fg_color=("#FFFFFF", "#151515"), corner_radius=12, border_width=1, border_color=("#CCCCCC", "#252525"))
                card.pack(fill="x", padx=10, pady=6)
                
                content = ctk.CTkFrame(card, fg_color="transparent")
                content.pack(fill="x", padx=20, pady=12)
                
                date_label = ctk.CTkLabel(content, text=f"📅 {entry['date']}", font=ctk.CTkFont(size=13, weight="bold"), text_color=("#555555", "#888888"))
                date_label.pack(side="left")
                
                # Highlight size in blue
                size_label = ctk.CTkLabel(content, text=entry['size'], font=ctk.CTkFont(size=14, weight="bold"), text_color="#00D2FF")
                size_label.pack(side="right")
                
                items_label = ctk.CTkLabel(content, text=f"{entry['items']} itens removidos  | ", font=ctk.CTkFont(size=13), text_color=("#333333", "#BBBBBB"))
                items_label.pack(side="right", padx=5)
                
        except Exception as e:
            logging.error(f"Error refreshing history: {e}")

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
            ctk.CTkLabel(self.folder_frame, text="Nenhum diretório adicionado para limpeza.", text_color=("#5a5a5a", "#aaaaaa")).pack(pady=40)
            return

        for folder in self.folders:
            rb = ctk.CTkRadioButton(
                self.folder_frame, text=folder, 
                value=folder, variable=self.selected_folder_var,
                font=ctk.CTkFont(size=12), text_color=("#000000", "#ffffff")
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
                self.status_label.configure(text="Modo Manual", text_color=("#666666", "#aaaaaa"))
                msg = "Agendamentos automáticos desativados."
            elif mode == "Logon":
                scheduler.set_logon_mode(exe_path)
                self.status_label.configure(text="Agendado: Logon", text_color="#0078d7")
                msg = "O ClearFiles será executado sempre que você iniciar o Windows."
            elif mode == "Shutdown":
                scheduler.set_shutdown_mode(exe_path)
                self.status_label.configure(text="Agendado: Shutdown", text_color="#0078d7")
                msg = "O ClearFiles será executado ao desligar o computador."
            elif mode == "Interval":
                val = self.interval_entry.get()
                interval = int(val) if val.isdigit() else 60
                scheduler.set_interval_mode(exe_path, interval)
                self.status_label.configure(text=f"Agendado: {interval}m", text_color="#0078d7")
                msg = f"O ClearFiles será executado a cada {interval} minutos."
            
            messagebox.showinfo("Configuração Aplicada", f"{msg}\n\nO aplicativo continuará funcionando em segundo plano na bandeja do sistema.")
        except Exception as e:
            messagebox.showerror("Erro de Agendamento", f"Falha ao configurar tarefa: {e}")

    def start_cleaning_thread(self):
        """Triggers the cleaning process in a background thread"""
        if not self.folders:
            messagebox.showwarning("Aviso", "Por favor, adicione ao menos uma pasta.")
            return
        
        self.clean_button.configure(state="disabled", text="LIMPANDO...")
        self.status_label.configure(text="Limpando...", text_color=("#666666", "#aaaaaa"))
        
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
            
        # Clean recycle bin automatically
        if empty_recycle_bin():
            total_success += 1 # Conta como 1 operação de limpeza na lixeira
        
        # Log to history
        if total_success > 0:
            log_history(total_success, total_freed)
        
        # Update UI on main thread
        self.after(0, lambda: self._update_ui_after_cleaning(total_success, total_freed))

    def _update_ui_after_cleaning(self, total_success, total_freed):
        self.refresh_history()
        self.refresh_folder_list()
        self.status_label.configure(text=f"Liberado: {format_size(total_freed)}", text_color=("#000000", "#ffffff"))
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
                total_freed = 0
                total_success = 0
                for folder in folders:
                    s, f, size, errors = clean_folder(folder)
                    total_success += s
                    total_freed += size
                    
                if empty_recycle_bin():
                    total_success += 1
                
                if total_success > 0:
                    log_history(total_success, total_freed)
        except Exception as e:
            logging.error(f"Silent clean error: {e}")

def check_single_instance():
    mutex_name = "Global\\ClearFilesProfessionalMutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    last_error = ctypes.windll.kernel32.GetLastError()
    if last_error == 183: # ERROR_ALREADY_EXISTS
        return False
    # Keep the mutex reference alive
    return mutex

if __name__ == "__main__":
    if "--silent" in sys.argv:
        silent_clean()
    else:
        app_mutex = check_single_instance()
        if not app_mutex:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            messagebox.showwarning("Aviso", "O ClearFiles já está em execução.")
            sys.exit(0)
            
        app = App()
        app.mainloop()
