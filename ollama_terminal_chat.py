import ollama
import readline
import sys

MODEL = 'llama3'  # Change this to your preferred model name


def main():
    print(f"Ollama Terminal Chat - Model: {MODEL}\nType 'exit' or Ctrl+C to quit.\n")
    client = ollama.Client()
    history = []
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
