#!/usr/bin/env python3
"""
Master Terminal Chat - Unified interface for FANUC robot order fulfillment
Manages both the robot handler (register writes) and LLM chat simultaneously.
"""

import subprocess
import sys
import os
import time
import signal
import atexit
from pathlib import Path

# ANSI colors
WHITE = "\033[97m"
CRX_GREEN = "\033[38;2;0;255;102m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

# Paths
PROJECT_ROOT = Path(__file__).parent
ROBOT_HANDLER_DIR = PROJECT_ROOT / "Robot_handler"
LLM_ENGINE_DIR = PROJECT_ROOT / "LLM_engine"
HANDLER_SCRIPT = ROBOT_HANDLER_DIR / "robot_handler.py"
CHAT_SCRIPT = LLM_ENGINE_DIR / "chat.py"
PIPE_PATH = ROBOT_HANDLER_DIR / "robot_handler.pipe"
CURRENT_CART = ROBOT_HANDLER_DIR / "current_cart.json"

# Robot connection
ROBOT_IP = "172.168.10.2"
ROBOT_PORT = 4880

# Global process handles
handler_proc = None
chat_proc = None


def cleanup():
    """Cleanup: terminate both processes and remove pipe."""
    global handler_proc, chat_proc
    
    print(f"\n{RED}[MASTER] Shutting down...{RESET}")
    
    if handler_proc and handler_proc.poll() is None:
        print(f"{RED}[MASTER] Terminating handler...{RESET}")
        handler_proc.terminate()
        try:
            handler_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            handler_proc.kill()
    
    if chat_proc and chat_proc.poll() is None:
        print(f"{RED}[MASTER] Terminating chat...{RESET}")
        chat_proc.terminate()
        try:
            chat_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            chat_proc.kill()
    
    if PIPE_PATH.exists():
        try:
            os.remove(PIPE_PATH)
            print(f"{RED}[MASTER] Removed pipe{RESET}")
        except Exception as e:
            print(f"{RED}[MASTER] Error removing pipe: {e}{RESET}")
    
    print(f"{RED}[MASTER] Shutdown complete{RESET}")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    cleanup()
    sys.exit(0)


def check_files():
    """Verify all required files exist."""
    required = [HANDLER_SCRIPT, CHAT_SCRIPT, CURRENT_CART]
    for path in required:
        if not path.exists():
            print(f"{RED}[ERROR] Missing file: {path}{RESET}")
            sys.exit(1)
    print(f"{YELLOW}[MASTER] All files verified{RESET}")


def start_handler():
    """Start the robot handler in watch mode."""
    global handler_proc
    
    print(f"{YELLOW}[MASTER] Starting robot handler (IP: {ROBOT_IP}:{ROBOT_PORT})...{RESET}")
    
    try:
        handler_proc = subprocess.Popen(
            [
                sys.executable,
                str(HANDLER_SCRIPT),
                "--watch",
                "--robot-ip",
                ROBOT_IP,
                "--robot-port",
                str(ROBOT_PORT),
            ],
            cwd=str(ROBOT_HANDLER_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        print(f"{YELLOW}[MASTER] Handler started (PID: {handler_proc.pid}){RESET}")
        
        # Give handler time to initialize
        time.sleep(1)
        
        # Check if handler is still running
        if handler_proc.poll() is not None:
            stdout, _ = handler_proc.communicate()
            print(f"{RED}[ERROR] Handler failed to start:{RESET}")
            print(stdout)
            sys.exit(1)
        
        print(f"{CRX_GREEN}[MASTER] Handler ready{RESET}")
        return True
    except Exception as e:
        print(f"{RED}[ERROR] Failed to start handler: {e}{RESET}")
        return False


def start_chat():
    """Start the chat interface."""
    global chat_proc
    
    print(f"{YELLOW}[MASTER] Starting chat interface...{RESET}")
    
    try:
        chat_proc = subprocess.Popen(
            [sys.executable, str(CHAT_SCRIPT)],
            cwd=str(LLM_ENGINE_DIR),
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        print(f"{YELLOW}[MASTER] Chat started (PID: {chat_proc.pid}){RESET}")
        return True
    except Exception as e:
        print(f"{RED}[ERROR] Failed to start chat: {e}{RESET}")
        return False


def monitor_handler():
    """Monitor handler in background and print its output."""
    if not handler_proc:
        return
    
    try:
        while True:
            line = handler_proc.stdout.readline()
            if not line:
                break
            # Print handler output with proper formatting
            if line.strip():
                print(line.rstrip(), file=sys.stderr, flush=True)
    except Exception:
        pass


def main():
    """Main orchestration."""
    print(f"\n{CRX_GREEN}{'='*60}")
    print(f"FANUC CRX Order Fulfillment - Master Terminal Chat")
    print(f"Robot: {ROBOT_IP}:{ROBOT_PORT}")
    print(f"{'='*60}{RESET}\n")
    
    # Setup signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    atexit.register(cleanup)
    
    # Verify files
    check_files()
    
    # Reset cart to zero
    try:
        initial_cart = {
            "Nuttiess Chocolate": 0,
            "NIVEA": 0,
            "Shampoo": 0,
            "Appy Fizz": 0,
            "Cough Syrup": 0,
            "Coca Cola": 0,
            "Tea Botx": 0,
            "Pringles": 0,
            "Noodles": 0,
            "Bar": 0,
            "Ponds": 0,
            "Dove": 0,
        }
        import json
        with open(CURRENT_CART, "w") as f:
            json.dump(initial_cart, f, indent=2)
        print(f"{YELLOW}[MASTER] Cart reset to zero{RESET}\n")
    except Exception as e:
        print(f"{RED}[ERROR] Failed to reset cart: {e}{RESET}")
        sys.exit(1)
    
    # Start handler first
    if not start_handler():
        sys.exit(1)
    
    # Start chat interface
    if not start_chat():
        cleanup()
        sys.exit(1)
    
    print(f"\n{CRX_GREEN}[MASTER] System ready. Type your order!{RESET}\n")
    
    # Wait for chat to finish
    try:
        chat_proc.wait()
    except KeyboardInterrupt:
        pass
    
    cleanup()


if __name__ == "__main__":
    main()
