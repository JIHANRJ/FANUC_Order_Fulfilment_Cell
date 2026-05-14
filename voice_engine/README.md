# Voice Engine

Speech-to-text transcription using **faster-whisper** on the local machine. The voice stack listens on the microphone, transcribes speech locally, and forwards the resulting text to the chat pipeline.

## Files

- **voice_input.py** — Core voice input handler with faster-whisper integration
- **voice_chat.py** — Voice-enabled chat interface
- **voice_tuner.py** — Interactive microphone tuning tool for noise/confidence filtering
- **__init__.py** — Package initialization

## Usage

### Voice Chat Only

```bash
cd voice_engine
python3 voice_chat.py
```

Choose mode `1` for voice input. The system will listen for speech, transcribe it with faster-whisper, and send it to the LLM.

### Tune Voice Filtering

```bash
cd voice_engine
python3 voice_tuner.py
```

The tuner records two samples locally:
- ambient noise
- a normal spoken command

It prints measured RMS/peak values, local transcription confidence, visualizes audio waveforms and settings, and optionally saves the tuned parameters to a JSON file.

**Recommended workflow:**
1. Run `python3 voice_tuner.py` to test your microphone
2. Adjust microphone gain in system settings if needed
3. Use command-line flags to experiment: `python3 voice_tuner.py --silence-threshold 0.003 --amplitude-accept-threshold 0.003`
4. When you find settings that work well, save them: `python3 voice_tuner.py --save-settings`
5. Settings are now persisted to `voice_settings.json` and will auto-load on future runs

**Tuner command-line options:**
- `--silence-threshold FLOAT` — amplitude threshold for silence detection
- `--amplitude-accept-threshold FLOAT` — minimum RMS amplitude before transcription
- `--silence-duration FLOAT` — seconds of silence before sending audio
- `--min-duration FLOAT` — minimum audio duration to transcribe
- `--confidence-logprob-threshold FLOAT` — minimum model confidence score
- `--save-settings` — save discovered settings to `voice_settings.json`
- `--show-previous` — display previously saved settings
- `--no-graph` — skip matplotlib visualization

## Features

- **Fast transcription** — Uses faster-whisper with the ctranslate2 backend
- **CPU-friendly defaults** — Uses the `int8` compute path by default
- **Real-time listening** — Listens continuously on the microphone
- **Auto-detection** — Detects speech automatically via amplitude threshold
- **Silence-based trigger** — Sends audio for transcription after silence is detected
- **Low latency** — The `tiny` model is the fastest option
- **Better accuracy** — Larger models improve accuracy at the cost of speed

## How It Works

1. Microphone listens continuously in a background thread
2. Audio chunks are buffered as they arrive (float32 format)
3. When silence is detected after speech, audio is sent to faster-whisper
4. Faster-whisper transcribes using the local ctranslate2 backend
5. Transcribed text is returned to chat
6. Chat sends the order to the handler and the robot registers are updated

## Confidence Filtering

The engine applies several checks before sending text to the LLM to avoid random-noise transcripts:

- **Minimum text length:** short fragments are rejected (default 3 chars)
- **Amplitude check:** raw audio RMS must exceed a minimum threshold
- **Model confidence:** if the model exposes `avg_logprob`/`no_speech_prob`, the engine uses those scores to reject low-confidence transcriptions
- **Fallbacks:** when model scores are unavailable, amplitude + length checks are used

You can adjust thresholds from the command line via `master_terminal_chat.py --voice ...` or tune them interactively with `voice_tuner.py`.

## Performance

| Model | Speed (M1/M2) | Accuracy | Size |
|-------|---------------|----------|------|
| tiny  | ~1 sec        | Good     | 39M  |
| base  | ~2 sec        | Better   | 140M |

Faster-whisper with int8 quantization is **5-10x faster** than openai-whisper on ARM64!

## Settings Persistence

Once you tune the voice parameters using `voice_tuner.py`, your optimal settings are automatically saved to `voice_settings.json` (when using `--save-settings`). These settings persist across system restarts:

- **Auto-load on startup:** When you run `master_terminal_chat.py --voice`, it automatically loads saved settings as defaults
- **Override with command-line flags:** CLI flags still take precedence if provided, e.g., `python3 master_terminal_chat.py --voice --silence-threshold 0.010`
- **View previously saved settings:** Use `voice_tuner.py --show-previous` to see what parameters were last saved

**Typical workflow:**
```bash
# 1. Discover optimal settings
python3 voice_tuner.py --silence-threshold 0.003 --amplitude-accept-threshold 0.003

# 2. Save them
python3 voice_tuner.py --save-settings

# 3. On next system start, settings auto-apply:
python3 ../master_terminal_chat.py --voice --frontend
# Loads: silence_threshold=0.003, amplitude_accept_threshold=0.003, etc.

# 4. Or override a single setting:
python3 ../master_terminal_chat.py --voice --silence-threshold 0.010
# Loads saved model and other settings, but uses CLI silence-threshold
```

## Customization

Edit **voice_input.py**:

```python
# Change Whisper model (bigger = more accurate, slower)
voice_input = VoiceInput(model="base", use_wake_word=False)

# Adjust silence detection
DEFAULT_SILENCE_THRESHOLD = 0.08  # amplitude threshold (higher = more sensitive)
DEFAULT_SILENCE_DURATION = 0.5    # seconds of silence before transcribe
DEFAULT_MIN_DURATION = 0.3        # minimum audio duration to transcribe
```

## Dependencies

- `faster-whisper` - Fast Whisper inference
- `sounddevice` - Microphone input
- `numpy` - Audio processing

## Wake Word Detection

Wake-word support depends on the current voice backend configuration. The default project setup runs without wake word, and the browser UI uses the Python voice engine rather than a browser microphone API.

If wake-word mode is enabled in code, it should be treated as an optional advanced setup, not part of the basic first-run path.

## Recommended First Test

Run the smoke test after installing dependencies:

```bash
python3 ../test_voice_integration.py
```

If that passes, start voice chat with:

```bash
python3 ../master_terminal_chat.py --voice --voice-model tiny
```
