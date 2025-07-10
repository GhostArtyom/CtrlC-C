import os
import sys
import pyperclip
import keyboard
import threading
from threading import Timer
from pystray import MenuItem as item
import pystray
from PIL import Image, ImageDraw
from ctypes import windll
import winreg as reg
import win32event
import win32api
from winerror import ERROR_ALREADY_EXISTS
import logging
import subprocess


def get_log_file_path():
    """Get the path for the log file, differentiating between script and executable."""
    if getattr(sys, 'frozen', False):
        home_dir = os.path.expanduser('~')
        log_dir = os.path.join(home_dir, 'ctrlcc')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        return os.path.join(log_dir, 'CtrlC_C_log.txt')
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'CtrlC_C_log.txt')


def view_logs(icon, item):
    """Open the log file with the default text editor."""
    try:
        if os.name == 'nt':  # Windows
            os.startfile(log_filepath)
        elif os.name == 'posix':  # Unix-like
            subprocess.run(['open', log_filepath], check=True)
        else:
            logging.error("Unsupported OS for viewing logs")
    except Exception as e:
        logging.error(f"Error opening log file: {e}")


def add_to_startup():
    """Add the application to the Windows startup registry."""
    if getattr(sys, 'frozen', False):
        app_path = sys.executable
    else:
        app_path = os.path.abspath(__file__)

    try:
        key = reg.HKEY_CURRENT_USER
        key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        open = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
        reg.SetValueEx(open, "CtrlC+C", 0, reg.REG_SZ, app_path)
        reg.CloseKey(open)
        return True
    except WindowsError:
        return False


def remove_from_startup():
    """Remove the application from the Windows startup registry."""
    try:
        key = reg.HKEY_CURRENT_USER
        key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        open = reg.OpenKey(key, key_value, 0, reg.KEY_ALL_ACCESS)
        reg.DeleteValue(open, "CtrlC+C")
        reg.CloseKey(open)
        return True
    except WindowsError:
        return False


def toggle_startup():
    """Toggle whether the application is in the Windows startup registry."""
    if is_in_startup():
        return remove_from_startup()
    else:
        return add_to_startup()


def is_in_startup():
    """Check whether the application is in the Windows startup registry."""
    try:
        key = reg.HKEY_CURRENT_USER
        key_value = "Software\\Microsoft\\Windows\\CurrentVersion\\Run"
        open = reg.OpenKey(key, key_value, 0, reg.KEY_READ)
        reg.QueryValueEx(open, "CtrlC+C")
        reg.CloseKey(open)
        return True
    except WindowsError:
        return False


def show_message_box(title, message, ask_hide_tray=False):
    """Show a message box with the given title and message."""
    MB_YESNO = 0x04  # Show "Yes" and "No" buttons
    IDYES = 6  # Return value when user clicks "Yes"

    if ask_hide_tray:
        # Append tray hide question to message
        message += "\n\n是否隐藏托盘图标？"
        result = windll.user32.MessageBoxW(0, message, title, MB_YESNO)
        if result == IDYES:
            return True  # User chose to hide the tray
    else:
        # Show standard message box
        windll.user32.MessageBoxW(0, message, title, 0)
    return False  # User chose not to hide the tray


def toggle_strip_blankspace():
    """Toggle whether to remove blank space from copied text."""
    global is_strip_blankspace
    is_strip_blankspace = not is_strip_blankspace
    return is_strip_blankspace


def strip_newlines(text):
    """Remove all types of newline characters from a string."""
    try:
        text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')
        logging.info(f"removed newlines: {text}")  # Log the stripped text
        return text
    except Exception as e:
        logging.error(f"Error while accessing clipboard: {e}")
        return ""


def strip_blankspace(text):
    """Remove all types of blank space characters from a string."""
    try:
        text = text.replace(' ', '')
        logging.info(f"removed blank space: {text}")  # Log the stripped text
        return text
    except Exception as e:
        logging.error(f"Error while accessing clipboard: {e}")
        return ""


def get_clipboard_text():
    """Get the current text on the clipboard and then clear it."""
    try:
        text = pyperclip.paste()
        pyperclip.copy("")  # Clear the clipboard
        return text
    except Exception as e:
        logging.error(f"Error while accessing clipboard: {e}")
        return ""


def set_clipboard_text(text):
    """Set the given text on the clipboard."""
    pyperclip.copy(text)


def on_c_press(event):
    global strip_attempted
    """Start a timer after first 'C' press, if 'Ctrl' is held down."""
    if keyboard.is_pressed('ctrl'):
        if hasattr(on_c_press, 'first_press_timer') and on_c_press.first_press_timer is not None:
            # If timer exists, we are within 1.0 seconds of first press, so we execute the action
            on_c_press.first_press_timer.cancel()
            strip_attempted = True
            perform_clipboard_action()
            Timer(0.5, check_conflict).start()
        else:
            # Start a timer that waits for another 'C' press within 1.0 seconds
            on_c_press.first_press_timer = Timer(1.0, reset_first_press_timer)
            on_c_press.first_press_timer.start()
    else:
        reset_first_press_timer()


def check_conflict():
    """Check if strip_newlines was attempted but not executed, indicating a hotkey conflict."""
    global strip_attempted, strip_executed
    if strip_attempted and not strip_executed:
        # If strip_newlines was attempted but not executed, then we might have a conflict
        show_message_box("快捷键冲突", "Ctrl+C+C 快捷键可能被其他程序占用。")
    # Reset flags for the next attempt
    strip_attempted = False
    strip_executed = False


def perform_clipboard_action():
    """Perform the action of copying the clipboard text and removing newlines."""
    global strip_executed
    reset_first_press_timer()
    try:
        current_data = get_clipboard_text()
        stripped_text = strip_newlines(current_data)
        if is_strip_blankspace:
            stripped_text = strip_blankspace(stripped_text)
        set_clipboard_text(stripped_text)
        logging.info(f"Stripped text: {stripped_text}")
        strip_executed = True
    except Exception as e:
        logging.error(f"Error in perform_clipboard_action: {e}")


def reset_first_press_timer():
    """Reset the timer for double 'C' press."""
    on_c_press.first_press_timer = None


def create_icon(image_name):
    """The application is frozen."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    # The application is not frozen
    else:
        base_path = os.path.abspath(".")

    # Correct the path to the icon file
    icon_path = os.path.join(base_path, image_name)
    return Image.open(icon_path)


def setup_tray_icon(hide_tray_icon):
    """Load your own image as icon and setup tray icon with menu."""
    icon_image = create_icon("ctrlcc.ico")

    # The menu that will appear when the user right-clicks the icon
    menu = (
        item('Toggle Start on Boot', toggle_startup, checked=lambda item: is_in_startup()),
        item('Toggle Strip Blank Space', toggle_strip_blankspace, checked=lambda item: is_strip_blankspace),
        item('View Logs', view_logs),
        item('Hide Tray', hide_tray),
        item('Exit', exit_program),
    )

    if not hide_tray_icon:
        icon = pystray.Icon("ctrlcc", icon_image, "CtrlC+C", menu)
        icon.run()
    else:
        threading.Event().wait()


def hide_tray(icon):
    """Hide the system tray icon."""
    icon.visible = False  # This will hide the system tray icon


def exit_program(icon):
    """Exit the program and stop the system tray icon."""
    icon.stop()  # This will stop the system tray icon and the associated message loop
    keyboard.unhook_all()


if __name__ == "__main__":

    log_filepath = get_log_file_path()
    logging.basicConfig(filename=log_filepath, level=logging.INFO, format='%(asctime)s, %(levelname)s, %(message)s')

    strip_attempted = False
    strip_executed = False

    is_strip_blankspace = False

    mutex_name = "CtrlC_C_Application_Mutex"

    mutex = win32event.CreateMutex(None, False, mutex_name)
    last_error = win32api.GetLastError()

    if last_error == ERROR_ALREADY_EXISTS:
        show_message_box("应用程序已运行", "CtrlC+C 应用程序已经在运行了。")
        sys.exit(0)

    # Show instruction message box
    instruction_message = ("欢迎使用 CtrlC+C ！\n\n【按住 Ctrl 键并按 C 键两次】以复制文本并删除换行。\n\n如有问题，请联系：\nchenluda01@gmail.com 或 ghostartyomns@gmail.com")
    hide_tray_icon = show_message_box("© 2025 Glenn & GhostArtyom.", instruction_message, ask_hide_tray=True)

    on_c_press.first_press_timer = None
    keyboard.on_release_key('c', on_c_press)
    setup_tray_icon(hide_tray_icon)  # Start the system tray icon
