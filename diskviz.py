#!/usr/bin/env python3
import os
import subprocess
import sys


def detect_distro():
    distro = ""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("ID="):
                    distro = line.strip().split("=", 1)[1].strip('"').lower()
                    break
    except FileNotFoundError:
        pass
    return distro


DISTRO_INSTALL = {
    "ubuntu": "sudo apt install python3-pip",
    "debian": "sudo apt install python3-pip",
    "linuxmint": "sudo apt install python3-pip",
    "pop": "sudo apt install python3-pip",
    "elementary": "sudo apt install python3-pip",
    "fedora": "sudo dnf install python3-pip",
    "rhel": "sudo dnf install python3-pip",
    "centos": "sudo yum install python3-pip",
    "rocky": "sudo dnf install python3-pip",
    "alma": "sudo dnf install python3-pip",
    "arch": "sudo pacman -S python-pip",
    "manjaro": "sudo pacman -S python-pip",
    "endeavouros": "sudo pacman -S python-pip",
    "alpine": "sudo apk add py3-pip",
    "opensuse-leap": "sudo zypper install python3-pip",
    "opensuse-tumbleweed": "sudo zypper install python3-pip",
    "void": "sudo xbps-install -S python3-pip",
    "gentoo": "sudo emerge pip",
    "nixos": "use nix-shell -p python3Packages.textual",
    "clear-linux-os": "sudo swupd bundle-add python3-basic",
}


def ensure_deps():
    if sys.version_info < (3, 8):
        print(f"Error: Python 3.8+ required, found {sys.version}")
        sys.exit(1)

    try:
        import textual
        return
    except ImportError:
        pass

    distro = detect_distro()
    pip_install = DISTRO_INSTALL.get(distro, "sudo apt install python3-pip")

    try:
        subprocess.check_call(["uv", "--version"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Installing textual via uv...")
        subprocess.check_call(["uv", "pip", "install", "--system", "textual"])
        return
    except Exception:
        pass

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Installing textual via pip...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "textual"])
        return
    except Exception:
        pass

    print("Error: uv and pip not found.")
    print(f"Install pip for your distro ({distro or 'unknown'}):")
    print(f"  {pip_install}")
    print("  or install uv: curl -LsSf https://astral.sh/uv/install.sh | sh")
    sys.exit(1)


def get_size(path):
    total = 0
    try:
        if os.path.isfile(path) or os.path.islink(path):
            return os.path.getsize(path)
        for dirpath, dirnames, filenames in os.walk(path, onerror=lambda e: None):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    if not os.path.islink(fp):
                        total += os.path.getsize(fp)
                except (OSError, PermissionError):
                    continue
    except (PermissionError, OSError):
        return 0
    return total


def human_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024
    return f"{num_bytes:.1f} PB"


def size_color(pct):
    if pct >= 66:
        return "bar-red"
    elif pct >= 33:
        return "bar-yellow"
    else:
        return "bar-green"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("DiskViz - Terminal disk space visualizer")
        print(f"Usage: {sys.argv[0]} [directory]")
        print("  directory   Path to scan (default: current directory)")
        print("  q           Quit")
        print("  t           Change theme")
        print("  Up/Down     Move cursor")
        print("  Right       Enter directory")
        print("  Left        Go back")
        sys.exit(0)

    ensure_deps()

    import asyncio
    from textual.app import App, ComposeResult, Theme
    from textual.widgets import Header, Footer, Static, ProgressBar, Label
    from textual.containers import Vertical, ScrollableContainer

    class SilentScrollableContainer(ScrollableContainer):
        can_focus = False

        def _on_key(self, event):
            pass

    class DiskVizApp(App):
        CSS = """
        Screen {
            align: center middle;
        }
        #body {
            width: 80;
            height: auto;
            align: center middle;
        }
        #path_label {
            text-style: bold;
            color: $primary;
            width: 100%;
            text-align: center;
            padding: 1 2;
            background: $surface;
            border: tall $primary;
            margin: 0 0 1 0;
        }
        #total_label {
            color: $success;
            text-style: bold;
            padding: 0 0 1 0;
            width: auto;
        }
        #items {
            width: 80;
            height: 22;
            border: round $primary;
            background: $surface;
            padding: 1 2;
        }
        .item_row {
            height: 3;
            margin: 0 0 1 0;
            padding: 0 1;
        }
        .item_label {
            color: $foreground;
        }
        .item_selected {
            background: $surface;
            border-left: heavy $primary;
            padding-left: 1;
        }
        .item_selected .item_label {
            color: $primary;
            text-style: bold;
        }
        #selected_label {
            color: $accent;
            text-style: italic;
            width: auto;
            padding: 0 1;
            margin: 1 0 0 0;
        }
        ProgressBar Bar {
            width: 100%;
        }
        .bar-red > Bar > .bar--bar { color: $error; }
        .bar-yellow > Bar > .bar--bar { color: $warning; }
        .bar-green > Bar > .bar--bar { color: $success; }
        ProgressBar > .bar--indeterminate { color: $accent; }
        """
        TITLE = "✦ DiskViz"
        SUB_TITLE = "DEV:Reham"

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("t", "change_theme", "Theme"),
            ("up", "move_up", "Up"),
            ("down", "move_down", "Down"),
            ("right", "enter_dir", "Enter"),
            ("left", "go_up", "Back"),
        ]

        def __init__(self, target_path):
            super().__init__()
            self.target_path = os.path.abspath(target_path)
            self.results = []
            self.cursor = 0
            self.theme = "tokyo-night"

            self.register_theme(Theme(
                name="kanagawa",
                primary="#C8C090",
                secondary="#7FB4CA",
                warning="#FF9E3B",
                error="#C34043",
                success="#76946A",
                accent="#957FB8",
                foreground="#DCD7BA",
                background="#1F1F28",
                surface="#2A2A37",
                panel="#363646",
                dark=True,
            ))
            self.register_theme(Theme(
                name="everforest",
                primary="#A7C080",
                secondary="#7FBBB3",
                warning="#EBCB8B",
                error="#E67E80",
                success="#A7C080",
                accent="#D39BB6",
                foreground="#D3C6AA",
                background="#2D353B",
                surface="#343F44",
                panel="#425047",
                dark=True,
            ))
            self.register_theme(Theme(
                name="one-dark",
                primary="#61AFEF",
                secondary="#C678DD",
                warning="#E5C07B",
                error="#E06C75",
                success="#98C379",
                accent="#56B6C2",
                foreground="#ABB2BF",
                background="#282C34",
                surface="#2C313A",
                panel="#3E4451",
                dark=True,
            ))
            self.register_theme(Theme(
                name="tokyo-night-storm",
                primary="#7AA2F7",
                secondary="#BB9AF7",
                warning="#E0AF68",
                error="#F7768E",
                success="#9ECE6A",
                accent="#FF9E64",
                foreground="#C0CAF5",
                background="#1A1B26",
                surface="#24283B",
                panel="#414868",
                dark=True,
            ))
            self.register_theme(Theme(
                name="cyberpunk",
                primary="#F5E0DC",
                secondary="#F2CDCD",
                warning="#F9E2AF",
                error="#F38BA8",
                success="#A6E3A1",
                accent="#CBA6F7",
                foreground="#F5E0DC",
                background="#11111B",
                surface="#1E1E2E",
                panel="#313244",
                dark=True,
            ))
            self.register_theme(Theme(
                name="oxocarbon",
                primary="#82CFFF",
                secondary="#33B1FF",
                warning="#FFA166",
                error="#FF6768",
                success="#42BE65",
                accent="#BE95FF",
                foreground="#E0E0E0",
                background="#161616",
                surface="#1E1E1E",
                panel="#262626",
                dark=True,
            ))
            self.register_theme(Theme(
                name="modus-vivendi",
                primary="#81A1C1",
                secondary="#B48EAD",
                warning="#EBCB8B",
                error="#BF616A",
                success="#A3BE8C",
                accent="#5E81AC",
                foreground="#BBC2CF",
                background="#1D2021",
                surface="#242829",
                panel="#3B4252",
                dark=True,
            ))
            self.register_theme(Theme(
                name="apprentice",
                primary="#FFAF5F",
                secondary="#BD93F9",
                warning="#FFAF5F",
                error="#FF5F5F",
                success="#5FD7AF",
                accent="#808080",
                foreground="#ACB4BC",
                background="#1C1C1C",
                surface="#262626",
                panel="#333333",
                dark=True,
            ))
            self.register_theme(Theme(
                name="tokyo-xterm",
                primary="#74A5E6",
                secondary="#A885ED",
                warning="#E8C76E",
                error="#EF687C",
                success="#72C886",
                accent="#F19852",
                foreground="#BCBCBC",
                background="#000000",
                surface="#111111",
                panel="#222222",
                dark=True,
            ))
            self.register_theme(Theme(
                name="nightfox",
                primary="#73DACA",
                secondary="#BB9AF7",
                warning="#E0AF68",
                error="#F7768E",
                success="#73DACA",
                accent="#FF9E64",
                foreground="#CDDBF4",
                background="#192330",
                surface="#232E3F",
                panel="#2B3B51",
                dark=True,
            ))

        def compose(self) -> ComposeResult:
            yield Header()
            with Vertical(id="body"):
                yield Label(f"Current: {self.target_path}", id="path_label")
                yield Label("", id="total_label")
                with SilentScrollableContainer(id="items"):
                    yield Static("Calculating sizes... please wait")
                yield Label("", id="selected_label")
            yield Footer()

        async def on_mount(self):
            self.run_worker(self.scan_and_display, exclusive=True)

        def action_move_up(self):
            self._move_cursor(-1)

        def action_move_down(self):
            self._move_cursor(1)

        def action_enter_dir(self):
            self._enter_dir()

        def action_go_up(self):
            self._go_up()

        def _move_cursor(self, direction):
            if not self.results:
                return
            self.cursor = max(0, min(len(self.results) - 1, self.cursor + direction))
            self._refresh_cursor()
            self._update_selected_label()

        def _enter_dir(self):
            if not self.results:
                return
            name, size, is_dir = self.results[self.cursor]
            if not is_dir:
                return
            self.target_path = os.path.join(self.target_path, name)
            self.cursor = 0
            self.query_one("#path_label").update(f"Current: {self.target_path}")
            self.run_worker(self.scan_and_display, exclusive=True)

        def _go_up(self):
            parent = os.path.dirname(self.target_path)
            if parent == self.target_path:
                return
            self.target_path = parent
            self.cursor = 0
            self.query_one("#path_label").update(f"Current: {self.target_path}")
            self.run_worker(self.scan_and_display, exclusive=True)

        def _update_selected_label(self):
            label = self.query_one("#selected_label", Label)
            if not self.results:
                label.update("")
                return
            name, size, is_dir = self.results[self.cursor]
            kind = "Folder" if is_dir else "File"
            full_path = os.path.join(self.target_path, name)
            icon = "[dir]" if is_dir else "[file]"
            label.update(f"{icon} {name}  •  {kind}  •  {human_size(size)}  •  {full_path}")

        def _refresh_cursor(self):
            container = self.query_one("#items", SilentScrollableContainer)
            rows = container.query(".item_row")
            for i, row in enumerate(rows):
                if i == self.cursor:
                    row.add_class("item_selected")
                    row.scroll_visible()
                else:
                    row.remove_class("item_selected")

        async def scan_and_display(self):
            loop = asyncio.get_running_loop()

            def do_scan():
                try:
                    entries = os.listdir(self.target_path)
                except (PermissionError, FileNotFoundError, NotADirectoryError):
                    return None
                results = []
                for entry in entries:
                    full_path = os.path.join(self.target_path, entry)
                    size = get_size(full_path)
                    is_dir = os.path.isdir(full_path)
                    results.append((entry, size, is_dir))
                results.sort(key=lambda x: x[1], reverse=True)
                total = sum(r[1] for r in results)
                return results, total

            result = await loop.run_in_executor(None, do_scan)

            if result is None:
                container = self.query_one("#items", SilentScrollableContainer)
                container.remove_children()
                container.mount(Static("Permission denied or path not found."))
                return

            self.results, total = result
            self.cursor = 0

            self.query_one("#total_label", Label).update(
                f"Total: {human_size(total)}   •   {len(self.results)} items"
            )

            container = self.query_one("#items", SilentScrollableContainer)
            container.remove_children()

            if not self.results:
                container.mount(Static("(empty directory)"))
                self.query_one("#selected_label", Label).update("")
                return

            max_size = max((r[1] for r in self.results), default=1) or 1

            for i, (name, size, is_dir) in enumerate(self.results):
                icon = "[dir]" if is_dir else "[file]"
                pct = (size / max_size) * 100 if max_size else 0
                bar_class = size_color(pct)
                selected = i == self.cursor
                indicator = "▸ " if selected else "  "

                row = Vertical(classes="item_row")
                container.mount(row)
                label_cls = "item_label item_selected" if selected else "item_label"
                row.mount(Static(
                    f"{indicator}{icon} {name}   [b]{human_size(size)}[/b]",
                    classes=label_cls,
                ))
                bar = ProgressBar(
                    total=100, show_eta=False, show_percentage=False, classes=bar_class
                )
                row.mount(bar)
                bar.update(progress=pct)

            self._update_selected_label()

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(target):
        print(f"Error: '{target}' is not a valid directory.")
        sys.exit(1)
    DiskVizApp(target).run()
