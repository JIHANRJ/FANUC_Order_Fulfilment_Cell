import json
import os
import subprocess
import sys

# ANSI color codes
WHITE = "\033[97m"
CRX_GREEN = "\033[38;2;0;255;102m"  # FANUC CRX green
RESET = "\033[0m"
RED = "\033[91m"

ENGINE_DIR = os.path.dirname(__file__)
HANDLER_PIPE = os.path.join(os.path.dirname(ENGINE_DIR), "Robot_handler", "robot_handler.pipe")
HANDLER_SCRIPT = os.path.join(os.path.dirname(ENGINE_DIR), "Robot_handler", "robot_handler.py")


def parse_llm_payload(raw_content: str) -> dict:
    return json.loads(raw_content)


def send_to_handler(payload: dict) -> None:
    if not os.path.exists(HANDLER_PIPE):
        print(f"{RED}[Handler] Live terminal not running yet. Start: python3 Robot_handler/robot_handler.py --watch{RESET}")
        return

    try:
        fd = os.open(HANDLER_PIPE, os.O_WRONLY | os.O_NONBLOCK)
    except OSError:
        print(f"{RED}[Handler] Live terminal not connected. Start: python3 Robot_handler/robot_handler.py --watch{RESET}")
        return

    try:
        with os.fdopen(fd, "w") as pipe:
            pipe.write(json.dumps(payload) + "\n")
            pipe.flush()
    except BrokenPipeError:
        print(f"{RED}[Handler] The live handler disconnected. Restart it in another terminal.{RESET}")


def main():
    print("\nType 'exit' or Ctrl+C to quit.\n")
    engine_proc = subprocess.Popen(
        [sys.executable, "LLM_engine.py"],
        cwd=ENGINE_DIR,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        while True:
            user_input = input(f"{WHITE}You: {RESET}")
            if user_input.lower() in {"exit", "quit"}:
                engine_proc.stdin.write("exit\n")
                engine_proc.stdin.flush()
                print("Goodbye!")
                break

            engine_proc.stdin.write(user_input + "\n")
            engine_proc.stdin.flush()

            output = engine_proc.stdout.readline().strip()
            if not output:
                stderr_output = engine_proc.stderr.readline().strip()
                if stderr_output:
                    print(f"{RED}[Engine] {stderr_output}{RESET}")
                continue

            try:
                data = json.loads(output)
            except json.JSONDecodeError:
                print(f"{RED}[Malformed output] {output}{RESET}")
                continue

            if "error" in data:
                print(f"{RED}[Engine Error] {data['error']}{RESET}")
                continue

            content = data.get("content", "")
            try:
                payload = parse_llm_payload(content)
            except json.JSONDecodeError:
                print(f"{CRX_GREEN}CRX: {content}{RESET}\n")
                continue

            response = payload.get("response", "")
            cart = payload.get("cart", {})
            print(f"{CRX_GREEN}CRX: {response}{RESET}")
            print(f"{CRX_GREEN}Cart: {json.dumps(cart, indent=2)}{RESET}\n")
            send_to_handler(payload)

    except KeyboardInterrupt:
        print("\nGoodbye!")
    finally:
        try:
            engine_proc.terminate()
        except Exception:
            pass


if __name__ == "__main__":
    main()
