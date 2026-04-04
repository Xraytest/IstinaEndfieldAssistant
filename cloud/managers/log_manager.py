from datetime import datetime
import tkinter as tk

class LogManager:

    def __init__(self, log_text_widget, status_bar):
        self.log_text_widget = log_text_widget
        self.status_bar = status_bar

    def log_message(self, message, category='general', level='INFO'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_entry = f'[{timestamp}] [{category.upper()}] {level}: {message}'
        if self.log_text_widget:
            self.log_text_widget.insert(tk.END, log_entry + '\n')
            self.log_text_widget.see(tk.END)
        if self.status_bar:
            self.status_bar.config(text=message)
        print(log_entry)

    def clear_log(self):
        if self.log_text_widget:
            self.log_text_widget.delete(1.0, tk.END)