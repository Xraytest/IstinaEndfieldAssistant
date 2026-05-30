"""
PyQt6 application entry - simplified for agent mode
"""
import sys
import os
import logging
import json
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QThread

try:
    from .main_window import MainWindow
    from .theme.theme_manager import ThemeManager
except ImportError:
    import sys
    import os
    current_file = os.path.abspath(__file__)
    pyqt6_dir = os.path.dirname(current_file)
    gui_dir = os.path.dirname(pyqt6_dir)
    src_dir = os.path.dirname(gui_dir)
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    from gui.pyqt6.main_window import MainWindow
    from gui.pyqt6.theme.theme_manager import ThemeManager


class QtLogHandler(logging.Handler, QObject):
    log_signal = pyqtSignal(str, str)

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_signal.emit(msg, record.levelname)
        except Exception:
            pass


class WorkerThread(QThread):
    finished = pyqtSignal(object)

    def __init__(self, target, args=None):
        super().__init__()
        self.target = target
        self.args = args or ()

    def run(self):
        result = self.target(*self.args)
        self.finished.emit(result)


class PyQt6Application(QApplication):
    def __init__(self, argv=None, auth_manager=None, device_manager=None,
                 agent_executor=None, communicator=None, screen_capture=None,
                 config=None):
        super().__init__(argv or sys.argv)
        self.main_window = None
        self.auth_manager = auth_manager
        self.device_manager = device_manager
        self.agent_executor = agent_executor
        self.communicator = communicator
        self.screen_capture = screen_capture
        self.config = config

    def run(self):
        self.main_window = MainWindow(
            auth_manager=self.auth_manager,
            device_manager=self.device_manager,
            agent_executor=self.agent_executor,
            communicator=self.communicator,
            screen_capture=self.screen_capture,
            config=self.config
        )
        self.main_window.show()
        return self.exec()


def run_application(auth_manager=None, device_manager=None,
                    agent_executor=None, communicator=None, 
                    screen_capture=None, touch_executor=None,
                    config=None):
    """
    Run the PyQt6 application with business logic components
    
    Args:
        auth_manager: AuthManager instance for authentication
        device_manager: DeviceManager instance for device management  
        agent_executor: AgentExecutor instance for agent execution
        communicator: ClientCommunicator instance for server communication
        screen_capture: ScreenCapture instance for screenshots
        touch_executor: TouchManager instance for touch operations
        config: Configuration dictionary
    """
    print("[APP_MAIN] Creating QApplication...")
    app = QApplication(sys.argv)
    
    # Apply theme
    print("[APP_MAIN] Applying theme...")
    theme = ThemeManager.get_instance()
    app.setStyleSheet(theme.get_stylesheet())
    
    # Create main window with all business logic components
    print("[APP_MAIN] Creating MainWindow...")
    main_window = MainWindow(
        auth_manager=auth_manager,
        device_manager=device_manager,
        agent_executor=agent_executor,
        communicator=communicator,
        screen_capture=screen_capture,
        touch_executor=touch_executor,
        config=config
    )
    
    print("[APP_MAIN] Showing window...")
    main_window.show()
    main_window.raise_()  # Bring to front
    main_window.activateWindow()  # Activate window
    
    print("[APP_MAIN] Starting event loop...")
    return app.exec()
