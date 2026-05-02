import curses
import json
import os
import sys
import argparse
from asgs_config.validator import ActiveStormValidator
from asgs_config.config_generator import StormConfigGenerator

# Constants
SETTINGS_FILE = open(os.path.join(os.path.dirname(__file__), "settings.json"))
DEFAULT_SETTINGS = {
    "template_path": "template.sh",
    "nhc_url": ActiveStormValidator.DEFAULT_URL
}

def load_settings():
    """Loads settings from JSON, creating default if missing."""
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        return DEFAULT_SETTINGS
    
    with open(SETTINGS_FILE, 'r') as f:
        settings = json.load(f)
    
    # Ensure all default keys exist
    updated = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = v
            updated = True
    if updated:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
            
    return settings

def get_input(stdscr, y, x, prompt, initial_text="", max_len=50, secret=False):
    """Safely gets text input from the user in curses."""
    curses.echo()
    stdscr.addstr(y, x, prompt)
    stdscr.addstr(y, x + len(prompt), initial_text)
    stdscr.refresh()
    
    buf = list(initial_text)
    pos = len(buf)
    
    while True:
        stdscr.move(y, x + len(prompt) + pos)
        ch = stdscr.getch()
        
        if ch in (10, 13, curses.KEY_ENTER):
            break
        elif ch in (curses.KEY_BACKSPACE, 127, 8):
            if pos > 0:
                pos -= 1
                buf.pop(pos)
                stdscr.addstr(y, x + len(prompt) + pos, " " * (len(buf) - pos + 1))
        elif 32 <= ch <= 126 and len(buf) < max_len:
            buf.insert(pos, chr(ch))
            pos += 1
        
        stdscr.addstr(y, x + len(prompt), "".join(buf))
        stdscr.refresh()

    curses.noecho()
    return "".join(buf)

class StormTUI:
    def __init__(self, stdscr, nhc_url=None):
        self.stdscr = stdscr
        self.settings = load_settings()
        
        # Override settings URL if provided via CLI flag
        url = nhc_url if nhc_url else self.settings.get("nhc_url")
        self.validator = ActiveStormValidator(url=url)
        
        self.generator = None
        self.state = "SELECT"
        self.selected_storm_id = None
        self.form_fields = []
        self.current_field_idx = 0
        self.status_message = ""
        self.status_color = 1 # Normal

        # Initialize colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Normal
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)    # Selected
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)     # Warning/Error
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Success
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Header

        curses.curs_set(0) # Hide cursor
        self.stdscr.keypad(True)

    def run(self):
        while self.state != "EXIT":
            self.stdscr.clear()
            if self.state == "SELECT":
                self.screen_select()
            elif self.state == "EDIT":
                self.screen_edit()
            elif self.state == "CONFIRM":
                self.screen_confirm()
            self.stdscr.refresh()
            
            ch = self.stdscr.getch()
            self.handle_input(ch)

    def screen_select(self):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(1, 2, "Storm Selection Menu", curses.color_pair(5) | curses.A_BOLD)
        
        if self.validator.unvalidated_mode:
            self.stdscr.addstr(2, 2, "WARNING: Could not connect to NHC. Running in unvalidated mode.", curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(3, 2, f"Source: {self.validator.url}", curses.color_pair(1))
        else:
            self.stdscr.addstr(2, 2, f"Connected to: {self.validator.url}", curses.color_pair(4))
        
        storms = self.validator.active_storms
        if not storms:
            self.stdscr.addstr(5, 2, "No active storms currently.")
        else:
            self.stdscr.addstr(5, 2, f"{'Name':<15} {'ID':<15}", curses.A_UNDERLINE)
            for i, storm in enumerate(storms):
                style = curses.color_pair(2) if i == self.current_field_idx else curses.color_pair(1)
                name = storm.get("name", "Unknown")
                sid = storm.get("id", "N/A")
                self.stdscr.addstr(6 + i, 2, f"{name:<15} {sid:<15}", style)

        self.stdscr.addstr(h - 3, 2, "UP/DOWN: Navigate | ENTER: Select | C: Custom ID | Q: Quit", curses.color_pair(5))

    def screen_edit(self):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(1, 2, f"Configuration Editor - Storm: {self.selected_storm_id}", curses.color_pair(5) | curses.A_BOLD)
        
        for i, field in enumerate(self.form_fields):
            style = curses.color_pair(2) if i == self.current_field_idx else curses.color_pair(1)
            label = field['label']
            value = field['value']
            self.stdscr.addstr(4 + i*2, 2, f"{label}:", curses.A_BOLD)
            self.stdscr.addstr(4 + i*2, 20, f" {value} ", style)

        self.stdscr.addstr(h - 3, 2, "UP/DOWN: Navigate | ENTER: Edit Field | S: Save | B/ESC: Back", curses.color_pair(5))

    def screen_confirm(self):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(1, 2, "Confirmation", curses.color_pair(5) | curses.A_BOLD)
        self.stdscr.addstr(4, 2, self.status_message, curses.color_pair(self.status_color))
        
        self.stdscr.addstr(h - 3, 2, "N: Create New Config | Q: Exit", curses.color_pair(5))

    def handle_input(self, ch):
        if ch == curses.KEY_RESIZE:
            return

        if self.state == "SELECT":
            storms = self.validator.active_storms
            if ch == ord('q') or ch == ord('Q'):
                self.state = "EXIT"
            elif ch == curses.KEY_UP:
                self.current_field_idx = max(0, self.current_field_idx - 1)
            elif ch == curses.KEY_DOWN:
                if storms:
                    self.current_field_idx = min(len(storms) - 1, self.current_field_idx + 1)
            elif ch in (10, 13, curses.KEY_ENTER):
                if storms:
                    self.init_generator(storms[self.current_field_idx]['id'])
            elif ch in (ord('c'), ord('C')):
                self.prompt_custom_id()

        elif self.state == "EDIT":
            if ch in (27, ord('b'), ord('B')): # ESC or B
                self.state = "SELECT"
                self.current_field_idx = 0
            elif ch == curses.KEY_UP:
                self.current_field_idx = max(0, self.current_field_idx - 1)
            elif ch == curses.KEY_DOWN:
                self.current_field_idx = min(len(self.form_fields) - 1, self.current_field_idx + 1)
            elif ch in (10, 13, curses.KEY_ENTER):
                self.edit_field()
            elif ch in (ord('s'), ord('S')):
                self.save_config()

        elif self.state == "CONFIRM":
            if ch in (ord('n'), ord('N')):
                self.state = "SELECT"
                self.current_field_idx = 0
                # Refresh data from the same URL
                self.validator = ActiveStormValidator(url=self.validator.url)
            elif ch in (ord('q'), ord('Q')):
                self.state = "EXIT"

    def prompt_custom_id(self):
        h, w = self.stdscr.getmaxyx()
        custom_id = get_input(self.stdscr, h - 2, 2, "Enter 8-char Storm ID: ", max_len=8)
        if len(custom_id) == 8:
            self.init_generator(custom_id)
        else:
            self.status_message = "Invalid ID length. Must be 8 characters."

    def init_generator(self, storm_id):
        try:
            self.selected_storm_id = storm_id
            self.generator = StormConfigGenerator(storm_id, self.settings['template_path'], self.settings.get("default_dir"))
            self.form_fields = [
                {"label": "Instance Name", "attr": "instance_name", "value": self.generator.instance_name},
                {"label": "Output Directory", "attr": "output_dir", "value": self.generator.output_dir}
            ]
            self.state = "EDIT"
            self.current_field_idx = 0
        except Exception as e:
            self.stdscr.addstr(10, 2, f"Error: {e}", curses.color_pair(3))
            self.stdscr.getch()

    def edit_field(self):
        field = self.form_fields[self.current_field_idx]
        h, w = self.stdscr.getmaxyx()
        new_val = get_input(self.stdscr, h - 2, 2, f"New {field['label']}: ", initial_text=field['value'])
        field['value'] = new_val
        setattr(self.generator, field['attr'], new_val)

    def save_config(self):
        try:
            path = self.generator.write_config()
            self.status_message = f"Configuration saved successfully to {path}"
            self.status_color = 4 # Success
        except Exception as e:
            self.status_message = f"Failed to save config: {e}"
            self.status_color = 3 # Error
        self.state = "CONFIRM"

def main(stdscr, nhc_url):
    tui = StormTUI(stdscr, nhc_url=nhc_url)
    tui.run()

def run():
    parser = argparse.ArgumentParser(description="Storm Configuration Generator TUI")
    parser.add_argument("--url", help="Custom NHC JSON URL")
    args = parser.parse_args()
    
    curses.wrapper(main, args.url)
