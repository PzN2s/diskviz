#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

P1='\033[38;5;218m'
P2='\033[38;5;212m'
P3='\033[38;5;207m'
P4='\033[38;5;171m'
P5='\033[38;5;135m'
P6='\033[38;5;99m'

echo -e "${P1}██████╗ ███████╗██╗  ██╗ █████╗ ███╗   ███╗${NC}"
echo -e "${P2}██╔══██╗██╔════╝██║  ██║██╔══██╗████╗ ████║${NC}"
echo -e "${P3}██████╔╝█████╗  ███████║███████║██╔████╔██║${NC}"
echo -e "${P4}██╔══██╗██╔══╝  ██╔══██║██╔══██║██║╚██╔╝██║${NC}"
echo -e "${P5}██║  ██║███████╗██║  ██║██║  ██║██║ ╚═╝ ██║${NC}"
echo -e "${P6}╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝${NC}"
echo -e "${P4}                DiskViz Installer${NC}"
echo ""

info()  { echo -e "${GREEN}[+]${NC} $1"; }
warn()  { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[-]${NC} $1"; }

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "$ID"
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        echo "$DISTRIB_ID" | tr '[:upper:]' '[:lower:]'
    elif [ -f /etc/redhat-release ]; then
        if grep -qi "centos" /etc/redhat-release 2>/dev/null; then
            echo "centos"
        elif grep -qi "rocky" /etc/redhat-release 2>/dev/null; then
            echo "rocky"
        elif grep -qi "alma" /etc/redhat-release 2>/dev/null; then
            echo "alma"
        else
            echo "rhel"
        fi
    else
        echo "unknown"
    fi
}

install_package() {
    local pkg="$1"
    local distro
    distro=$(detect_distro)
    case "$distro" in
        ubuntu|debian|linuxmint|pop|elementary|kali|raspbian|zorin)
            sudo apt update -qq && sudo apt install -y -qq "$pkg"
            ;;
        fedora|rhel|rocky|alma)
            sudo dnf install -y -q "$pkg"
            ;;
        centos)
            sudo yum install -y -q "$pkg"
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            sudo pacman -S --noconfirm --needed "$pkg"
            ;;
        alpine)
            sudo apk add --quiet "$pkg"
            ;;
        opensuse-leap|opensuse-tumbleweed)
            sudo zypper install -y -f "$pkg"
            ;;
        void)
            sudo xbps-install -Sy "$pkg"
            ;;
        gentoo)
            sudo emerge --ask=n --oneshot "$pkg"
            ;;
        clear-linux-os)
            sudo swupd bundle-add "$pkg"
            ;;
        nixos)
            warn "NixOS detected. Using nix-shell (recommended for NixOS)."
            return 0
            ;;
        *)
            warn "Unknown distro ($distro). Trying package manager..."
            if command -v apt &>/dev/null; then
                sudo apt update -qq && sudo apt install -y -qq "$pkg"
            elif command -v dnf &>/dev/null; then
                sudo dnf install -y -q "$pkg"
            elif command -v yum &>/dev/null; then
                sudo yum install -y -q "$pkg"
            elif command -v pacman &>/dev/null; then
                sudo pacman -S --noconfirm --needed "$pkg"
            elif command -v apk &>/dev/null; then
                sudo apk add --quiet "$pkg"
            elif command -v zypper &>/dev/null; then
                sudo zypper install -y -f "$pkg"
            elif command -v xbps-install &>/dev/null; then
                sudo xbps-install -Sy "$pkg"
            elif command -v emerge &>/dev/null; then
                sudo emerge --ask=n --oneshot "$pkg"
            elif command -v swupd &>/dev/null; then
                sudo swupd bundle-add "$pkg"
            else
                error "Could not find a package manager. Install '$pkg' manually."
                return 1
            fi
            ;;
    esac
}

install_python3() {
    local distro
    distro=$(detect_distro)
    case "$distro" in
        nixos)
            install_package "python3" || true
            ;;
        *)
            install_package "python3" || install_package "python" || true
            ;;
    esac
}

install_pip() {
    local distro
    distro=$(detect_distro)
    case "$distro" in
        ubuntu|debian|linuxmint|pop|elementary|kali|raspbian|zorin)
            install_package "python3-pip" || true
            ;;
        fedora|rhel|rocky|alma|centos)
            install_package "python3-pip" || true
            ;;
        arch|manjaro|endeavouros|garuda|artix)
            install_package "python-pip" || true
            ;;
        alpine)
            install_package "py3-pip" || true
            ;;
        opensuse-leap|opensuse-tumbleweed)
            install_package "python3-pip" || true
            ;;
        void)
            install_package "python3-pip" || true
            ;;
        gentoo)
            install_package "dev-python/pip" || true
            ;;
        clear-linux-os)
            install_package "python3-basic" || true
            ;;
        nixos)
            warn "NixOS: Use nix-shell to run DiskViz:"
            echo "  nix-shell -p python3 python3Packages.textual xclip --run 'python3 diskviz.py'"
            return 0
            ;;
        *)
            if command -v ensurepip &>/dev/null; then
                python3 -m ensurepip --upgrade 2>/dev/null || true
            fi
            ;;
    esac
}

# --- Check sudo ---
if ! command -v sudo &>/dev/null; then
    warn "sudo not found. Some operations may require root access."
    warn "Install sudo or run as root."
fi

# --- NixOS early exit (before any installation attempts) ---
if [ "$(detect_distro)" = "nixos" ]; then
    echo ""
    warn "NixOS detected. DiskViz runs best via nix-shell:"
    echo ""
    echo "  nix-shell -p python3 python3Packages.textual xclip --run 'python3 diskviz.py'"
    echo ""
    info "Exiting. No changes were made to your system."
    exit 0
fi

# --- Check python3 ---
if ! command -v python3 &>/dev/null; then
    warn "python3 not found. Installing..."
    install_python3 || true
    if ! command -v python3 &>/dev/null; then
        error "python3 still not found. Please install Python 3.8+ manually."
        exit 1
    fi
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || ([ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]); then
    error "Python 3.8+ required, found $PY_VER"
    exit 1
fi
info "Python $PY_VER found"

# --- Check pip ---
if ! python3 -m pip --version &>/dev/null; then
    warn "pip not found. Installing..."
    install_pip
    if ! python3 -m pip --version &>/dev/null; then
        error "pip still not found. Please install pip manually."
        exit 1
    fi
fi
info "pip found"

# --- Install textual ---
if python3 -c "import textual" 2>/dev/null; then
    info "textual already installed"
else
    info "Installing textual..."
    if python3 -m pip install --user textual 2>&1; then
        info "textual installed (--user)"
    elif python3 -m pip install textual 2>&1; then
        info "textual installed"
    else
        error "Failed to install textual. Check permissions or network."
        error "Manual: python3 -m pip install textual"
        exit 1
    fi
fi

# --- Install xclip ---
if command -v xclip &>/dev/null; then
    info "xclip already installed"
else
    info "Installing xclip..."
    install_package "xclip" || warn "Could not install xclip. Clipboard copy (c) will not work."
fi

chmod +x diskviz.py 2>/dev/null || true

echo ""
info "Installation complete!"
echo "  Run:  python3 diskviz.py"
echo "  Or:   ./diskviz.py"
