import ollama
import readline
import sys
import os

MODEL = 'llama3'  # Change this to your preferred model name
PRECONTEXT_FILE = os.path.join(os.path.dirname(__file__), 'precontext.txt')

def load_precontext():
    if os.path.exists(PRECONTEXT_FILE):
        with open(PRECONTEXT_FILE, 'r') as f:
            return f.read().strip()
    return ''

def main():
    print(f"Ollama Terminal Chat - Model: {MODEL}\nType 'exit' or Ctrl+C to quit.\n")
    client = ollama.Client()
    history = []
    precontext = load_precontext()
    if precontext:
        history.append({"role": "system", "content": precontext})
        print(f"[System precontext loaded]\n")
    while True:
        try:
            user_input = input("You: ").strip()
            if user_input.lower() in {"exit", "quit"}:
                print("Goodbye!")
                break
            if not user_input:
                continue
            history.append({"role": "user", "content": user_input})
            response = client.chat(model=MODEL, messages=history)
            answer = response['message']['content']
            print(f"{MODEL}: {answer}\n")
            history.append({"role": "assistant", "content": answer})
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"[Error] {e}")
            break

if __name__ == "__main__":
    main()
