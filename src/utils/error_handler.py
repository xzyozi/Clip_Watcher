import tkinter as tk
from tkinter import messagebox
import logging

logger = logging.getLogger(__name__)

def log_and_show_error(title: str, message: str, exc_info: bool = False):
    """
    Logs an error and displays an error message box to the user.

    Args:
        title (str): The title for the error message box.
        message (str): The message to display in the error box and to log.
        exc_info (bool): If True, exception information is added to the log message.
    """
    logger.error(message, exc_info=exc_info)
    messagebox.showerror(title, message)