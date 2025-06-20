
import tkinter as tk
from tkinter import ttk, scrolledtext, font as tkfont
import webbrowser
import os

class AutomationInterfaceView:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Automation Control Panel")
        self.root.geometry("700x550")
        self.root.minsize(500, 400)

        self.is_process_running = False
        self.is_process_paused = False

        self._apply_styles()
        self._initialize_main_frames()
        self._populate_ui_elements()
        self._synchronize_button_states()

    def _apply_styles(self):
        style = ttk.Style()
        available_themes = style.theme_names()
        
        preferred_themes = ['clam', 'vista', 'xpnative', 'default'] 
        for theme_name in preferred_themes:
            if theme_name in available_themes:
                try:
                    style.theme_use(theme_name)
                    break
                except tk.TclError:
                    continue
        
        default_font_name = tkfont.nametofont("TkDefaultFont").actual()["family"]
        
        style.configure("TButton", padding=6, font=(default_font_name, 10))
        style.configure("StatKey.TLabel", font=(default_font_name, 10))
        style.configure("StatValue.TLabel", font=(default_font_name, 10, 'bold'))
        self.log_area_font = tkfont.Font(family=default_font_name, size=9)

    def _initialize_main_frames(self):
        self.base_frame = ttk.Frame(self.root, padding="10 10 10 10")
        self.base_frame.pack(expand=True, fill=tk.BOTH)

        self.action_controls_frame = ttk.Frame(self.base_frame, padding="5")
        self.action_controls_frame.pack(fill=tk.X, pady=(0,10))

        self.logging_output_frame = ttk.Frame(self.base_frame, padding="5")
        self.logging_output_frame.pack(expand=True, fill=tk.BOTH, pady=(0,10))

        self.statistics_display_frame = ttk.Frame(self.base_frame, padding="5")
        self.statistics_display_frame.pack(fill=tk.X, pady=(0,10))
        self.statistics_display_frame.columnconfigure(1, weight=1)

        self.file_access_frame = ttk.Frame(self.base_frame, padding="5")
        self.file_access_frame.pack(fill=tk.X)

    def _populate_ui_elements(self):
        self._build_action_control_buttons()
        self._build_logging_output_area()
        self._build_statistics_display_labels()
        self._build_file_access_buttons()

    def _build_action_control_buttons(self):
        self.run_stop_button = ttk.Button(self.action_controls_frame, text="Run", command=self._trigger_run_stop_sequence)
        self.run_stop_button.pack(side=tk.LEFT, padx=(0, 5))

        self.pause_resume_button = ttk.Button(self.action_controls_frame, text="Pause", command=self._trigger_pause_resume_sequence)
        self.pause_resume_button.pack(side=tk.LEFT, padx=(5, 0))

    def _build_logging_output_area(self):
        self.log_display_text_widget = scrolledtext.ScrolledText(
            self.logging_output_frame, 
            wrap=tk.WORD, 
            height=10, 
            state=tk.DISABLED, 
            font=self.log_area_font
        )
        self.log_display_text_widget.pack(expand=True, fill=tk.BOTH)
        self.post_message_to_log("Interface initialized. Awaiting user action.")

    def _build_statistics_display_labels(self):
        stat_definitions = [
            ("Total Successful Accounts:", "0"),
            ("Total Cycles:", "0"),
            ("Total Failed Accounts:", "0"),
            ("Last Successful Account:", "N/A")
        ]
        
        self.statistic_string_vars = {}

        for index, (description, initial_val) in enumerate(stat_definitions):
            key_label = ttk.Label(self.statistics_display_frame, text=description, style="StatKey.TLabel")
            key_label.grid(row=index, column=0, sticky=tk.W, padx=5, pady=2)
            
            value_string_var = tk.StringVar(value=initial_val)
            value_display_label = ttk.Label(self.statistics_display_frame, textvariable=value_string_var, style="StatValue.TLabel")
            value_display_label.grid(row=index, column=1, sticky=tk.W, padx=5, pady=2)
            
            storage_key = description.lower().replace(" ", "_").rstrip(":")
            self.statistic_string_vars[storage_key] = value_string_var

    def _build_file_access_buttons(self):
        self.open_application_logs_button = ttk.Button(self.file_access_frame, text="Open Logs", command=self._execute_open_logs_file)
        self.open_application_logs_button.pack(side=tk.LEFT, padx=(0, 5))

        self.open_error_logs_button = ttk.Button(self.file_access_frame, text="Open Errors", command=self._execute_open_errors_file)
        self.open_error_logs_button.pack(side=tk.LEFT, padx=(5, 0))

    def _trigger_run_stop_sequence(self):
        if self.is_process_running:
            self.is_process_running = False
            self.is_process_paused = False 
            self.post_message_to_log("Process execution stopped by user.")
        else: 
            self.is_process_running = True
            self.is_process_paused = False 
            self.post_message_to_log("Process execution initiated by user.")
        self._synchronize_button_states()

    def _trigger_pause_resume_sequence(self):
        if not self.is_process_running:
            return

        if self.is_process_paused:
            self.is_process_paused = False
            self.post_message_to_log("Process execution resumed.")
        else: 
            self.is_process_paused = True
            self.post_message_to_log("Process execution paused.")
        self._synchronize_button_states()

    def _synchronize_button_states(self):
        if self.is_process_running:
            self.run_stop_button.config(text="Stop")
            if self.is_process_paused:
                self.run_stop_button.config(state=tk.DISABLED)
                self.pause_resume_button.config(text="Resume", state=tk.NORMAL)
            else: 
                self.run_stop_button.config(state=tk.NORMAL)
                self.pause_resume_button.config(text="Pause", state=tk.NORMAL)
        else: 
            self.run_stop_button.config(text="Run", state=tk.NORMAL)
            self.pause_resume_button.config(text="Pause", state=tk.DISABLED)
            
    def _execute_open_logs_file(self):
        self._open_file_with_default_application("logs.txt")

    def _execute_open_errors_file(self):
        self._open_file_with_default_application("errors.txt")

    def _open_file_with_default_application(self, relative_file_path):
        try:
            absolute_file_path = os.path.abspath(relative_file_path)
            webbrowser.open(f"file:///{absolute_file_path}")
            self.post_message_to_log(f"Attempting to open: {absolute_file_path}")
        except Exception as e:
            self.post_message_to_log(f"Error opening {relative_file_path}: {str(e)}")

    def post_message_to_log(self, entry_text):
        self.log_display_text_widget.config(state=tk.NORMAL)
        self.log_display_text_widget.insert(tk.END, entry_text + "\n")
        self.log_display_text_widget.see(tk.END)
        self.log_display_text_widget.config(state=tk.DISABLED)
        
    def set_statistic_value(self, statistic_key_name, new_display_value):
        normalized_key = statistic_key_name.lower().replace(" ", "_").rstrip(":")
        if normalized_key in self.statistic_string_vars:
            self.statistic_string_vars[normalized_key].set(str(new_display_value))
        else:
            self.post_message_to_log(f"Developer notice: Statistic key '{statistic_key_name}' is not recognized.")


def execute_graphical_user_interface():
    application_root_window = tk.Tk()
    AutomationInterfaceView(application_root_window)
    application_root_window.mainloop()

if __name__ == "__main__":
    execute_graphical_user_interface()