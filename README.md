# FANUC CRX Order Fulfillment System

An LLM-powered order tending interface for FANUC CRX robots. Natural language chat control with real-time register writes via OPC UA.

## Quick Start

### Prerequisites
- Python 3.8+
- Ollama (install from https://ollama.com)
- FANUC robot with OPC UA support (optional; simulator mode available)

### Setup

1. **Clone and navigate:**
   ```bash
   git clone https://github.com/JIHANRJ/FANUC_LLM_Control2.git
   cd FANUC_Control2
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install ollama opcua
   ```

4. **Pull the LLM model:**
   ```bash
   ollama pull llama3
   ```

5. **Start Ollama server (in another terminal):**
   ```bash
   ollama serve
   ```

## Running

### Master Terminal Chat (unified interface)

```bash
python3 master_terminal_chat.py
```

This starts both the robot handler and chat interface together.

**Options:**
- Robot is pre-configured to `172.168.10.2:4880`
- Edit `master_terminal_chat.py` to change robot IP/port
- Runs in simulator mode if robot is unreachable

### Advanced: Separate Terminals

**Terminal 1 - Robot Handler (watches for register writes):**
```bash
python3 Robot_handler/robot_handler.py --watch --robot-ip 172.168.10.2
```

**Terminal 2 - Chat Interface:**
```bash
cd LLM_engine
python3 chat.py
```

## Usage

1. Type orders in natural language:
   ```
   You: I want 2 chocolates and 5 pringles
   CRX: Order confirmed! [JSON response with register writes]
   ```

2. All register writes appear in red debug output in the handler terminal
3. Type `exit` to quit

## Architecture

- **LLM Engine** (`LLM_engine/`) - Llama3 chat with strict JSON output
- **Robot Handler** (`Robot_handler/`) - Computes deltas, writes FANUC registers via OPC UA
- **Master Terminal** (`master_terminal_chat.py`) - Orchestrates both components

## Configuration

Edit `LLM_engine/precontext.txt` to customize:
- Robot personality
- Item descriptions
- System behavior

## Files

- `master_terminal_chat.py` — Main entry point
- `LLM_engine/LLM_engine.py` — LLM backend with strict JSON schema
- `LLM_engine/chat.py` — Terminal interface
- `Robot_handler/robot_handler.py` — Register handler and OPC UA client
- `Robot_handler/fanuc_register_opcua.py` — FANUC OPC UA library
- `Robot_handler/current_cart.json` — Current order state
