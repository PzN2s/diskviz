#!/usr/bin/env python3
__version__ = "1.0.0"
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
    "nixos": "nix-shell -p python3Packages.textual xclip --run 'python3 diskviz.py'",
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

    if distro == "nixos":
        print("NixOS detected. Use nix-shell to run:")
        print("  nix-shell -p python3 python3Packages.textual xclip --run 'python3 diskviz.py .'")
        sys.exit(1)

    print("DiskViz requires 'textual' which is not installed.")
    print()

    if "--no-confirm" not in sys.argv:
        try:
            answer = input("Install textual now? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(1)
        if answer not in ("y", "yes"):
            print()
            print("Install manually:")
            print(f"  {pip_install}")
            print("  or: pip3 install textual")
            sys.exit(1)
        print()

    print("Verifying package integrity (hash pinning)...")
    print()

    verified = verify_and_download_textual()

    if not verified:
        print()
        print("SECURITY: Could not verify textual package.")
        print("This could be a network issue or a MITM attack.")
        print()
        print("Install manually from a trusted source:")
        print(f"  {pip_install}")
        print("  or: pip3 install textual")
        print("  Verify hash at: https://pypi.org/project/textual/")
        sys.exit(1)

    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", verified])
    except Exception as e:
        print(f"pip install failed: {e}")
        print("Try manually: pip3 install textual")
        sys.exit(1)
    finally:
        try:
            os.remove(verified)
            os.rmdir(os.path.dirname(verified))
        except OSError:
            pass


def get_size(path):
    total = 0
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        if os.path.islink(path):
            target = os.path.realpath(path)
            if os.path.isfile(target):
                return os.path.getsize(target)
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


TEXTUAL_VERSION = "8.2.8"
TEXTUAL_WHEEL = "textual-8.2.8-py3-none-any.whl"
TEXTUAL_SHA256 = "267375fd402dc8d981457212efa71f0e3365fd17bba144ba9bb3ed7563cb374a"
PYPI_WHEEL_URL = f"https://files.pythonhosted.org/packages/py3/t/textual/{TEXTUAL_WHEEL}"


def verify_and_download_textual():
    import hashlib
    import tempfile
    try:
        from urllib.request import urlopen, Request
        from urllib.error import URLError
    except ImportError:
        return False

    print(f"Downloading textual {TEXTUAL_VERSION} from PyPI...")
    try:
        req = Request(PYPI_WHEEL_URL, headers={"User-Agent": "diskviz/1.0"})
        with urlopen(req, timeout=30) as resp:
            content = resp.read()
    except (URLError, OSError) as e:
        print(f"WARNING: Download failed: {e}")
        return False

    actual_hash = hashlib.sha256(content).hexdigest()

    if actual_hash != TEXTUAL_SHA256:
        print(f"SECURITY ALERT: Hash mismatch!")
        print(f"  Expected: {TEXTUAL_SHA256}")
        print(f"  Got:      {actual_hash}")
        print(f"Possible MITM attack or corrupted download.")
        return False

    print(f"VERIFIED: Hash matches for {TEXTUAL_WHEEL}")

    tmpdir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmpdir, TEXTUAL_WHEEL)
    with open(tmp_path, "wb") as f:
        f.write(content)
    return tmp_path


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print("DiskViz - Terminal disk space visualizer")
        print(f"Usage: {sys.argv[0]} [directory]")
        print("  directory    Path to scan (default: current directory)")
        print("  --no-confirm    Skip install confirmation prompt")
        print("")
        print("Keyboard shortcuts:")
        print("  Up/Down      Move cursor")
        print("  Right        Enter directory")
        print("  Left         Go back")
        print("  r            Refresh current directory")
        print("  c            Copy path to clipboard")
        print("  /            Search files")
        print("  Escape       Clear search / unfocus")
        print("  s            Cycle sort (size / name / date)")
        print("  t            Change theme")
        print("  q            Quit")
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "--version":
        print(f"DiskViz {__version__}")
        sys.exit(0)

    ensure_deps()

    import asyncio
    from textual.app import App, ComposeResult, Theme
    from textual.widgets import Header, Footer, Static, Label, Input
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
            width: 76;
            height: auto;
        }
        #search_row {
            width: 100%;
            height: 3;
            layout: horizontal;
            margin: 0 0 1 0;
        }
        #search_input {
            width: 1fr;
            height: 3;
            margin: 0 1 0 0;
        }
        #sort_label {
            width: 14;
            height: 3;
            content-align: right middle;
            color: $accent;
            text-style: bold;
        }
        #path_label {
            width: 100%;
            height: 3;
            content-align: center middle;
            text-align: center;
            text-style: bold;
            color: $primary;
            background: $surface;
            border: double $primary;
            margin: 0 0 1 0;
        }
        #total_label {
            width: 100%;
            height: 1;
            content-align: center middle;
            text-align: center;
            color: $success;
            text-style: bold;
            margin: 0 0 1 0;
        }
        #items {
            width: 100%;
            height: 20;
            border: heavy $primary;
            background: $surface;
            padding: 0;
        }
        .item_row {
            height: 1;
            margin: 0;
            padding: 0;
            layout: horizontal;
        }
        .item_label {
            color: $foreground;
            padding: 0 1;
        }
        .item_name {
            width: 1fr;
        }
        .item_size {
            width: auto;
            text-align: right;
            min-width: 10;
        }
        .item_selected .item_label {
            color: $primary;
            text-style: bold;
            background: $panel;
        }
        #selected_label {
            width: 100%;
            height: 1;
            content-align: center middle;
            color: $accent;
            text-style: italic;
            margin: 1 0 0 0;
            text-align: center;
        }
        #warning_label {
            width: 100%;
            height: auto;
            color: $error;
            text-style: bold;
            padding: 0 1;
            margin: 0 0 1 0;
            background: $surface;
            border: heavy $error;
            display: none;
        }
        #warning_label.visible {
            display: block;
        }
        """
        TITLE = "✦ DiskViz"
        SUB_TITLE = "DEV:Reham"

        BINDINGS = [
            ("q", "quit", "Quit"),
            ("r", "refresh", "Refresh"),
            ("c", "copy_path", "Copy"),
            ("t", "change_theme", "Theme"),
            ("up", "move_up", "Up"),
            ("down", "move_down", "Down"),
            ("right", "enter_dir", "Enter"),
            ("left", "go_up", "Back"),
            ("s", "toggle_sort", "Sort"),
            ("slash", "activate_search", "Search"),
            ("escape", "clear_search", "Clear"),
        ]

        def __init__(self, target_path):
            super().__init__()
            self.target_path = os.path.abspath(target_path)
            self.all_results = []
            self.results = []
            self.cursor = 0
            self.sort_mode = "size"
            self.search_query = ""
            self._resetting = False

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
                yield Label("", id="warning_label")
                with Vertical(id="search_row"):
                    yield Input(placeholder="Search files... ( / )", id="search_input")
                    yield Label("Sort: Size", id="sort_label")
                yield Label(self.target_path, id="path_label")
                yield Label("", id="total_label")
                with SilentScrollableContainer(id="items"):
                    yield Static("Calculating sizes... please wait")
                yield Label("", id="selected_label")
            yield Footer()

        async def on_mount(self):
            self.query_one("#search_input").can_focus = False
            self.run_worker(self.scan_and_display, exclusive=True)

        def action_move_up(self):
            self._move_cursor(-1)

        def action_move_down(self):
            self._move_cursor(1)

        def action_enter_dir(self):
            self._enter_dir()

        def action_go_up(self):
            self._go_up()

        def action_refresh(self):
            self.cursor = 0
            self._reset_search()
            self.run_worker(self.scan_and_display, exclusive=True)

        def action_copy_path(self):
            if not self.results:
                return
            name, size, is_dir, mtime = self.results[self.cursor]
            full_path = os.path.join(self.target_path, name)
            try:
                p = subprocess.Popen(["xclip", "-selection", "clipboard"],
                                     stdin=subprocess.PIPE)
                p.communicate(full_path.encode())
            except FileNotFoundError:
                try:
                    p = subprocess.Popen(["xsel", "--clipboard", "--input"],
                                         stdin=subprocess.PIPE)
                    p.communicate(full_path.encode())
                except FileNotFoundError:
                    self.query_one("#selected_label", Label).update(
                        "[dim]No clipboard tool found (install xclip or xsel)[/dim]"
                    )
                    return
            self.query_one("#selected_label", Label).update(
                f"Copied: {full_path}"
            )

        def action_toggle_sort(self):
            modes = ["size", "name", "mtime"]
            idx = modes.index(self.sort_mode)
            self.sort_mode = modes[(idx + 1) % len(modes)]
            sort_labels = {"size": "Sort: Size", "name": "Sort: Name", "mtime": "Sort: Date"}
            self.query_one("#sort_label", Label).update(sort_labels[self.sort_mode])
            self._apply_sort_and_filter()

        def action_activate_search(self):
            inp = self.query_one("#search_input", Input)
            inp.can_focus = True
            inp.focus()

        def action_clear_search(self):
            inp = self.query_one("#search_input", Input)
            if self.search_query:
                inp.value = ""
                self.search_query = ""
                self._apply_sort_and_filter()
            inp.can_focus = False
            inp.blur()

        def on_input_changed(self, event: Input.Changed):
            if self._resetting:
                return
            self.search_query = event.value.lower()
            self._apply_sort_and_filter()

        def _apply_sort_and_filter(self):
            filtered = list(self.all_results)
            if self.search_query:
                filtered = [r for r in filtered if self.search_query in r[0].lower()]
            if self.sort_mode == "size":
                filtered.sort(key=lambda x: x[1], reverse=True)
            elif self.sort_mode == "name":
                filtered.sort(key=lambda x: x[0].lower())
            elif self.sort_mode == "mtime":
                filtered.sort(key=lambda x: x[3], reverse=True)
            self.results = filtered
            self.cursor = 0
            self._display_results()

        def _move_cursor(self, direction):
            if not self.results:
                return
            self.cursor = max(0, min(len(self.results) - 1, self.cursor + direction))
            self._refresh_cursor()
            self._update_selected_label()

        def _enter_dir(self):
            if not self.results:
                return
            name, size, is_dir, mtime = self.results[self.cursor]
            if not is_dir:
                return
            self.target_path = os.path.abspath(os.path.join(self.target_path, name))
            self.cursor = 0
            self._reset_search()
            self.query_one("#path_label").update(self.target_path)
            self.run_worker(self.scan_and_display, exclusive=True)

        def _go_up(self):
            parent = os.path.dirname(self.target_path)
            if parent == self.target_path:
                return
            self.target_path = parent
            self.cursor = 0
            self._reset_search()
            self.query_one("#path_label").update(self.target_path)
            self.run_worker(self.scan_and_display, exclusive=True)

        def _reset_search(self):
            self._resetting = True
            self.search_query = ""
            self.query_one("#search_input", Input).value = ""
            self._resetting = False

        def _update_selected_label(self):
            label = self.query_one("#selected_label", Label)
            if not self.results:
                label.update("")
                return
            name, size, is_dir, mtime = self.results[self.cursor]
            icon = "[bold cyan]DIR[/bold cyan]" if is_dir else "[dim]file[/dim]"
            label.update(f"{icon} {name}  \u00b7  {human_size(size)}")

        def _refresh_cursor(self):
            container = self.query_one("#items", SilentScrollableContainer)
            rows = container.query(".item_row")
            for i, row in enumerate(rows):
                if i == self.cursor:
                    row.add_class("item_selected")
                    row.scroll_visible()
                else:
                    row.remove_class("item_selected")

        def _display_results(self):
            container = self.query_one("#items", SilentScrollableContainer)
            container.remove_children()

            total_all = sum(r[1] for r in self.all_results)
            count_all = len(self.all_results)
            shown = len(self.results)
            if self.search_query and shown != count_all:
                self.query_one("#total_label", Label).update(
                    f"Total: {human_size(total_all)}   \u00b7   {shown}/{count_all} items"
                )
            else:
                self.query_one("#total_label", Label).update(
                    f"Total: {human_size(total_all)}   \u00b7   {count_all} items"
                )

            warning = self.query_one("#warning_label", Label)
            large_items = [r for r in self.all_results if total_all > 0 and r[1] > total_all * 0.8]
            if large_items:
                items_text = "   ".join(
                    f"[bold]{r[0]}[/bold] ({human_size(r[1])})" for r in large_items
                )
                warning.update(f"  WARNING: {items_text}")
                warning.add_class("visible")
            else:
                warning.update("")
                warning.remove_class("visible")

            if not self.results:
                msg = "(empty directory)" if not self.all_results else "No matches"
                container.mount(Static(f"[dim]{msg}[/dim]"))
                self.query_one("#selected_label", Label).update("")
                return

            for i, (name, size, is_dir, mtime) in enumerate(self.results):
                icon = "[bold cyan]DIR[/bold cyan] " if is_dir else "[dim]file[/dim] "
                selected = i == self.cursor
                indicator = "[bold cyan]\u25cf[/bold cyan] " if selected else "  "
                trunc_name = name[:40] + "..." if len(name) > 40 else name
                size_str = human_size(size)

                row_cls = "item_row item_selected" if selected else "item_row"
                row = Vertical(classes=row_cls)
                container.mount(row)
                row.mount(Static(
                    f"{indicator}{icon}{trunc_name}",
                    classes="item_label item_name",
                ))
                row.mount(Static(
                    f"[b]{size_str}[/b]",
                    classes="item_label item_size",
                ))

            self._update_selected_label()

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
                    try:
                        mtime = os.path.getmtime(full_path)
                    except (OSError, PermissionError):
                        mtime = 0
                    results.append((entry, size, is_dir, mtime))
                total = sum(r[1] for r in results)
                return results, total

            result = await loop.run_in_executor(None, do_scan)

            if result is None:
                container = self.query_one("#items", SilentScrollableContainer)
                container.remove_children()
                container.mount(Static("[dim]Permission denied or path not found.[/dim]"))
                self.all_results = []
                self.results = []
                self.query_one("#total_label", Label).update("")
                self.query_one("#selected_label", Label).update("")
                return

            self.all_results, total = result
            self._apply_sort_and_filter()

    target = sys.argv[1] if len(sys.argv) > 1 else "."
    if not os.path.isdir(target):
        print(f"Error: '{target}' is not a valid directory.")
        sys.exit(1)
    DiskVizApp(target).run()
