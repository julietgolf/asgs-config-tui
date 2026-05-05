import curses
import json
import os
import sys
import argparse
from asgs_config.validator import ActiveStormValidator
from asgs_config.config_generator import StormConfigGenerator

# Constants
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
DEFAULT_SETTINGS = {
    "template_path": "config_template.sh",
    "nhc_url": "https://www.nhc.noaa.gov/CurrentStorms.json",
    "default_dir": ".",
    "NCPU": "15",
    "NCPUCAPACITY": "9999",
    #"COLDSTARTDATE": "",
    "HOTORCOLD": "coldstart",
    "STARTING_WATER_LEVEL": "0",
    "GRIDNAME": "LKOKE"
}

def set_secure_permissions(path):
    """Sets file permissions to 710 (Owner: RWX, Group: X, Others: None) or Windows equivalent."""
    if sys.platform == "win32":
        try:
            os.system(f'icacls "{path}" /inheritance:r /quiet')
            username = os.getlogin()
            os.system(f'icacls "{path}" /grant:r "{username}":(F) /quiet')
            os.system(f'icacls "{path}" /grant:r *S-1-5-32-545:(RX) /quiet')
        except Exception:
            pass
    else:
        try:
            os.chmod(path, 0o710)
        except Exception:
            pass

def load_settings():
    """Loads settings from JSON, creating default if missing."""
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        set_secure_permissions(SETTINGS_FILE)
        return DEFAULT_SETTINGS
    
    with open(SETTINGS_FILE, 'r') as f:
        settings = json.load(f)
    
    updated = False
    for k, v in DEFAULT_SETTINGS.items():
        if k not in settings:
            settings[k] = v
            updated = True
    if updated:
        save_settings(settings)
            
    return settings

def save_settings(settings):
    """Saves settings to JSON and ensures secure permissions."""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f, indent=4)
    set_secure_permissions(SETTINGS_FILE)

def get_input(stdscr, y, x, prompt, initial_text="", max_len=50):
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
    def __init__(self, stdscr, nhc_url=None, historical_path=None):
        self.stdscr = stdscr
        self.settings = load_settings()
        self.historical_path = historical_path
        url = nhc_url if nhc_url else self.settings.get("nhc_url")
        self.validator = ActiveStormValidator(url=url)
        self.generator = None
        self.state = "SELECT"
        self.selected_storm_id = None
        self.form_fields = []
        self.scenarios = [{"name": "nhcConsensus", "percent": 0}]
        self.current_field_idx = 0
        self.status_message = ""
        self.status_color = 1
        self.dynamic_instance_name = True

        curses.start_color()
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_YELLOW, curses.COLOR_BLACK)

        curses.curs_set(0)
        self.stdscr.keypad(True)

    def run(self):
        while self.state != "EXIT":
            self.stdscr.clear()
            if self.state == "SELECT":
                self.screen_select()
            elif self.state == "EDIT":
                self.screen_edit()
            elif self.state == "SCENARIOS":
                self.screen_scenarios()
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
                self.stdscr.addstr(6 + i, 2, f"{storm.get('name', 'Unknown'):<15} {storm.get('id', 'N/A'):<15}", style)
        self.stdscr.addstr(h - 3, 2, "UP/DOWN: Navigate | ENTER: Select | C: Custom ID | Q: Quit", curses.color_pair(5))

    def screen_edit(self):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(1, 2, f"Variable Form Editor - Storm: {self.selected_storm_id}", curses.color_pair(5) | curses.A_BOLD)
        for i, field in enumerate(self.form_fields):
            style = curses.color_pair(2) if i == self.current_field_idx else curses.color_pair(1)
            self.stdscr.addstr(4 + i*2, 2, f"{field['label']}:", curses.A_BOLD)
            self.stdscr.addstr(4 + i*2, 25, f" {field['value']} ", style)
        self.stdscr.addstr(h - 3, 2, "UP/DOWN: Navigate | ENTER: Edit Field | S: Proceed to Scenarios | B/ESC: Back", curses.color_pair(5))

    def screen_scenarios(self):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(1, 2, "Scenario Editor", curses.color_pair(5) | curses.A_BOLD)
        for i, sc in enumerate(self.scenarios):
            style = curses.color_pair(2) if i == self.current_field_idx else curses.color_pair(1)
            self.stdscr.addstr(4 + i, 2, f"{i}) {sc['name']}", style)
        
        plus_style = curses.color_pair(2) if self.current_field_idx == len(self.scenarios) else curses.color_pair(1)
        self.stdscr.addstr(5 + len(self.scenarios), 2, "[+]", plus_style)
        
        self.stdscr.addstr(h - 3, 2, "UP/DOWN: Navigate | ENTER: Add/Select | D: Delete | S: Confirm & Save | B: Back", curses.color_pair(5))

    def screen_confirm(self):
        h, w = self.stdscr.getmaxyx()
        self.stdscr.addstr(1, 2, "Confirmation", curses.color_pair(5) | curses.A_BOLD)
        self.stdscr.addstr(4, 2, self.status_message, curses.color_pair(self.status_color))
        self.stdscr.addstr(h - 3, 2, "N: Create New Config | Q: Exit", curses.color_pair(5))

    def handle_input(self, ch):
        if ch == curses.KEY_RESIZE: return
        if self.state == "SELECT":
            storms = self.validator.active_storms
            if ch in (ord('q'), ord('Q')): self.state = "EXIT"
            elif ch == curses.KEY_UP: self.current_field_idx = max(0, self.current_field_idx - 1)
            elif ch == curses.KEY_DOWN and storms: self.current_field_idx = min(len(storms) - 1, self.current_field_idx + 1)
            elif ch in (10, 13, curses.KEY_ENTER) and storms: self.init_generator(storms[self.current_field_idx]['id'])
            elif ch in (ord('c'), ord('C')): self.prompt_custom_id()
        elif self.state == "EDIT":
            if ch in (27, ord('b'), ord('B')): self.state = "SELECT"; self.current_field_idx = 0
            elif ch == curses.KEY_UP: self.current_field_idx = max(0, self.current_field_idx - 1)
            elif ch == curses.KEY_DOWN: self.current_field_idx = min(len(self.form_fields) - 1, self.current_field_idx + 1)
            elif ch in (10, 13, curses.KEY_ENTER): self.edit_field()
            elif ch in (ord('s'), ord('S')): self.state = "SCENARIOS"; self.current_field_idx = 0
        elif self.state == "SCENARIOS":
            if ch in (ord('b'), ord('B')): self.state = "EDIT"; self.current_field_idx = 0
            elif ch == curses.KEY_UP: self.current_field_idx = max(0, self.current_field_idx)
            elif ch == curses.KEY_UP: self.current_field_idx = max(0, self.current_field_idx - 1)
            elif ch == curses.KEY_DOWN: self.current_field_idx = min(len(self.scenarios), self.current_field_idx + 1)
            elif ch in (10, 13, curses.KEY_ENTER):
                if self.current_field_idx == len(self.scenarios): self.prompt_add_scenario()
                else: pass # No specific action for selecting existing scenario except confirmation
            elif ch in (ord('d'), ord('D'), curses.KEY_DC):
                if 0 < self.current_field_idx < len(self.scenarios):
                    self.scenarios.pop(self.current_field_idx)
                    self.current_field_idx = min(self.current_field_idx, len(self.scenarios))
            elif ch in (ord('s'), ord('S')): self.save_config()
        elif self.state == "CONFIRM":
            if ch in (ord('n'), ord('N')): self.state = "SELECT"; self.current_field_idx = 0; self.validator = ActiveStormValidator(url=self.validator.url)
            elif ch in (ord('q'), ord('Q')): self.state = "EXIT"

    def prompt_custom_id(self):
        h, w = self.stdscr.getmaxyx()
        cid = get_input(self.stdscr, h - 2, 2, "Enter 8-char Storm ID: ", max_len=8)
        if len(cid) == 8: self.init_generator(cid)

    def init_generator(self, storm_id):
        try:
            self.selected_storm_id = storm_id
            self.generator = StormConfigGenerator(storm_id, self.settings['template_path'], self.settings.get("default_dir"))
            
            # Set CLI-driven historical attributes
            self.generator.historical = "1" if self.historical_path else "0"
            self.generator.fdir = self.historical_path if self.historical_path else ""

            system_keys = {"template_path", "nhc_url", "default_dir"}
            self.form_fields = [
                {"label": "INSTANCE NAME", "attr": "instance_name", "value": self.generator.instance_name},
                {"label": "OUTPUT DIRECTORY", "attr": "output_dir", "value": self.generator.output_dir}
            ]
            for key in DEFAULT_SETTINGS:
                if key not in system_keys:
                    if not hasattr(self.generator, key): setattr(self.generator, key, self.settings.get(key, ""))
                    val = getattr(self.generator, key)
                    self.form_fields.append({"label": key, "attr": key, "value": str(val)})
                    if key == "GRIDNAME":
                        ni = self.generator._base_instance_name.replace("%GRIDNAME%", str(val))
                        self.form_fields[0]['value'] = ni; self.generator.instance_name = ni
            self.state = "EDIT"; self.current_field_idx = 0
        except Exception as e:
            self.stdscr.addstr(10, 2, f"Error: {e}", curses.color_pair(3)); self.stdscr.getch()

    def edit_field(self):
        field = self.form_fields[self.current_field_idx]
        h, w = self.stdscr.getmaxyx()
        nv = get_input(self.stdscr, h - 2, 2, f"New {field['label']}: ", initial_text=field['value'])
        field['value'] = nv
        if self.dynamic_instance_name:
            if field["label"] == "INSTANCE NAME" and nv != self.generator.instance_name: self.dynamic_instance_name = False
            elif field['label'] == "GRIDNAME":
                ni = self.generator._base_instance_name.replace("%GRIDNAME%", nv)
                self.form_fields[0]['value'] = ni; self.generator.instance_name = ni
        setattr(self.generator, field['attr'], nv)

    def prompt_add_scenario(self):
        options = ["nhcConsensus", "veer", "maxWindSpeed", "overlandSpeed"]
        idx = 0
        h, w = self.stdscr.getmaxyx()
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(1, 2, "Add Scenario - Select Base:", curses.color_pair(5) | curses.A_BOLD)
            for i, opt in enumerate(options):
                style = curses.color_pair(2) if i == idx else curses.color_pair(1)
                self.stdscr.addstr(3 + i, 4, opt, style)
            self.stdscr.refresh()
            
            ch = self.stdscr.getch()
            if ch == curses.KEY_UP: idx = max(0, idx - 1)
            elif ch == curses.KEY_DOWN: idx = min(len(options) - 1, idx + 1)
            elif ch in (10, 13, curses.KEY_ENTER):
                base = options[idx]
                if base == "nhcConsensus":
                    self.add_scenario_to_list("nhcConsensus", 0)
                    return
                else:
                    # Inline prompt
                    prompt = f" Percent:      (-100 ≤ p < 0 < p ≤ 100)"
                    y, x = 3 + idx, 4 + len(base)
                    val_str = get_input(self.stdscr, y, x, prompt)
                    try:
                        p = int(val_str)
                        if p == 0 or p < -100 or p > 100: raise ValueError()
                        mapping = {
                            "veer": ("Left", "Right"),
                            "maxWindSpeed": ("Slower", "Faster"),
                            "overlandSpeed": ("Slower", "Faster")
                        }
                        desc = mapping[base][1 if p > 0 else 0]
                        name = f"{base}{desc}{abs(p)}"
                        self.add_scenario_to_list(name, p)
                        return
                    except ValueError:
                        self.stdscr.addstr(h-2, 2, "Invalid input. Must be integer (-100 to 100, not 0).", curses.color_pair(3))
                        self.stdscr.getch()
            elif ch == 27: return

    def add_scenario_to_list(self, name, percent):
        if any(s['name'] == name for s in self.scenarios):
            self.stdscr.addstr(7, 2, f"Warning: Scenario '{name}' already exists.", curses.color_pair(3))
            self.stdscr.getch()
        else:
            self.scenarios.append({"name": name, "percent": percent})

    def format_scenarios_block(self):
        block = ""
        for i, sc in enumerate(self.scenarios):
            block += f"    {i})\n"
            if sc['name'] == "nhcConsensus":
                block += "        ENSTORM=nhcTrack\n"
            else:
                block += f"        ENSTORM={sc['name']}\n"
                block += f"        PERCENT={sc['percent']}\n"
            block += "        ;;\n"
        return block

    def save_config(self):
        try:
            self.generator.storm_scenerios = self.format_scenarios_block()
            setattr(self.generator, "NUM_FORECAST_SCENARIOS", str(len(self.scenarios) + 1))
            path = self.generator.write_config()
            self.status_message = f"Configuration saved successfully to {path}"
            self.status_color = 4
        except Exception as e:
            self.status_message = f"Failed to save config: {e}"
            self.status_color = 3
        self.state = "CONFIRM"

def main(stdscr, nhc_url, historical_path=None):
    StormTUI(stdscr, nhc_url, historical_path).run()

def run():
    p = argparse.ArgumentParser()
    p.add_argument("--url",help="Set an alternate url for an NHC style advisory json.")
    p.add_argument("--set-url",help="Change the value for url in the settings file.")
    p.add_argument("--set-template",help="Change the value for template in the settings file.")
    p.add_argument("--set-dir",help="Change the value for dir in the settings file.")
    p.add_argument("--set", nargs=2,help="Set the default value for a generic setting.")
    p.add_argument("--list-settings", action="store_true",help="List of keys to be used by --set.")
    p.add_argument("-H", "--historical", help="Set historical mode with provided path.")
    args = p.parse_args()
    if args.list_settings: print(json.dumps(load_settings(), indent=4)); return
    if args.set_url or args.set_template or args.set_dir or args.set:
        s = load_settings()
        if args.set_url: s["nhc_url"] = args.set_url
        if args.set_template: s["template_path"] = args.set_template
        if args.set_dir: s["default_dir"] = args.set_dir
        if args.set: s[args.set[0]] = args.set[1]
        save_settings(s)
    curses.wrapper(main, args.url, args.historical)
