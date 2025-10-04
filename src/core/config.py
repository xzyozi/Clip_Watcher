# Window sizes
SETTINGS_WINDOW_GEOMETRY = "450x550"
MAIN_WINDOW_GEOMETRY = "600x530"

# Padding
FRAME_PADDING = "10"
BUTTON_PADDING_X = 5
BUTTON_PADDING_Y = 5

# History settings
HISTORY_LIMIT_MIN = 10
HISTORY_LIMIT_MAX = 1000
HISTORY_LIMIT_INCREMENT = 10

# Define themes
THEMES = {
    "light": {
        # General colors
        "bg": "#FFFFFF",              # Main window background
        "fg": "#212121",              # Default foreground/text color

        # Selection colors
        "select_bg": "#E3F2FD",        # Background color for selected items in lists/text
        "select_fg": "#212121",        # Foreground color for selected items

        # Frame & Label colors
        "frame_bg": "#F5F5F5",         # Background for frames and group boxes
        "label_fg": "#757575",         # Labels and secondary text

        # Entry widgets (Text, Entry, Spinbox)
        "entry_bg": "#FFFFFF",         # Background for text entry widgets
        "entry_fg": "#212121",         # Text color for entry widgets

        # Button colors
        "button_bg": "#E0E0E0",        # Background for buttons
        "button_fg": "#212121",        # Text color for buttons

        # Listbox/Treeview colors
        "listbox_bg": "#FFFFFF",       # Background for lists and trees
        "listbox_fg": "#212121",       # Text color for lists and trees

        # Special colors
        "pinned_bg": "#FFF9C4",        # Background for pinned items in the history

        # Menu colors
        "menu_bg": "#FFFFFF",         # Background for menus
        "menu_fg": "#212121",         # Text color for menus
        "active_menu_bg": "#E3F2FD",   # Background for active/hovered menu items
        "active_menu_fg": "#212121",   # Text color for active/hovered menu items
    },
    "dark": {
        # General colors
        "bg": "#282A36",              # Main window background (Dracula theme)
        "fg": "#F8F8F2",              # Default foreground/text color (off-white)

        # Selection colors
        "select_bg": "#44475A",        # Background color for selected items
        "select_fg": "#F8F8F2",        # Foreground color for selected items

        # Frame & Label colors
        "frame_bg": "#21222C",         # Background for frames and group boxes
        "label_fg": "#BD93F9",         # Labels and secondary text (light purple)

        # Entry widgets (Text, Entry, Spinbox)
        "entry_bg": "#343746",         # Background for text entry widgets
        "entry_fg": "#F8F8F2",         # Text color for entry widgets

        # Button colors
        "button_bg": "#44475A",        # Background for buttons
        "button_fg": "#F8F8F2",        # Text color for buttons

        # Listbox/Treeview colors
        "listbox_bg": "#282A36",       # Background for lists and trees
        "listbox_fg": "#F8F8F2",       # Text color for lists and trees

        # Special colors
        "pinned_bg": "#6272A4",        # Background for pinned items (a muted blue)

        # Menu colors
        "menu_bg": "#21222C",         # Background for menus
        "menu_fg": "#F8F8F2",         # Text color for menus
        "active_menu_bg": "#44475A",   # Background for active/hovered menu items
        "active_menu_fg": "#BD93F9",   # Text color for active/hovered menu items (light purple)
    }
}