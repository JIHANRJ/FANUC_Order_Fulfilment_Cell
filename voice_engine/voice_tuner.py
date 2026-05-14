#!/usr/bin/env python3
"""
Voice tuning tool for faster-whisper-based input.

This utility records a short ambient-noise sample and a short speech sample,
then prints audio metrics, transcription confidence, and suggested threshold
values so you can tune voice filtering before anything reaches the LLM.

Enhanced with matplotlib graphs and settings persistence.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

from voice_input import (
    SAMPLE_RATE,
    DEFAULT_SILENCE_THRESHOLD,
    DEFAULT_SILENCE_DURATION,
    DEFAULT_MIN_DURATION,
    DEFAULT_MIN_TRANSCRIPT_CHARS,
    DEFAULT_AMPLITUDE_ACCEPT_THRESHOLD,
    DEFAULT_CONFIDENCE_LOGPROB_THRESHOLD,
)

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"


@dataclass
class AudioStats:
    mean_abs: float
    rms: float
    peak: float
    duration: float


@dataclass
class TranscriptStats:
    text: str
    avg_logprob: Optional[float]
    no_speech_prob: Optional[float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tune microphone thresholds for the FANUC voice engine")
    parser.add_argument("--model", default="tiny", help="faster-whisper model size to test")
    parser.add_argument("--sample-rate", type=int, default=SAMPLE_RATE, help="Recording sample rate")
    parser.add_argument("--noise-seconds", type=float, default=3.0, help="Ambient-noise capture length")
    parser.add_argument("--speech-seconds", type=float, default=4.0, help="Speech capture length")
    parser.add_argument("--device", default=None, help="Optional microphone device index/name")
    parser.add_argument("--compute-type", default="int8", help="faster-whisper compute type")
    parser.add_argument("--language", default="en", help="Transcription language")
    parser.add_argument("--save-wav", action="store_true", help="Save captured samples as .npy files for offline review")
    parser.add_argument("--save-settings", action="store_true", help="Save recommended settings to voice_settings.json")
    parser.add_argument("--show-previous", action="store_true", help="Display previously saved settings")
    parser.add_argument("--no-graph", action="store_true", help="Skip matplotlib graph generation")
    return parser.parse_args()


def record_audio(seconds: float, sample_rate: int, device: Optional[str] = None) -> np.ndarray:
    print(f"{YELLOW}[TUNER] Recording {seconds:.1f}s... keep quiet / speak when prompted{RESET}")
    frames = int(seconds * sample_rate)
    audio = sd.rec(frames, samplerate=sample_rate, channels=1, dtype=np.float32, device=device)
    sd.wait()
    return audio.flatten()


def compute_stats(audio: np.ndarray, sample_rate: int) -> AudioStats:
    if audio.size == 0:
        return AudioStats(mean_abs=0.0, rms=0.0, peak=0.0, duration=0.0)
    return AudioStats(
        mean_abs=float(np.mean(np.abs(audio))),
        rms=float(np.sqrt(np.mean(np.square(audio)))),
        peak=float(np.max(np.abs(audio))),
        duration=float(audio.size / sample_rate),
    )


def transcribe(model: WhisperModel, audio: np.ndarray, language: str) -> TranscriptStats:
    normalized = audio.astype(np.float32)
    max_val = float(np.max(np.abs(normalized))) if normalized.size else 0.0
    if max_val > 0:
        normalized = normalized / max_val

    segments, info = model.transcribe(normalized, language=language, beam_size=1)
    text = " ".join(segment.text for segment in segments).strip()

    logprobs = []
    for segment in segments:
        if hasattr(segment, "avg_logprob"):
            try:
                logprobs.append(float(getattr(segment, "avg_logprob")))
            except Exception:
                pass

    avg_logprob = sum(logprobs) / len(logprobs) if logprobs else None
    no_speech_prob = None
    try:
        if hasattr(info, "no_speech_prob"):
            no_speech_prob = float(getattr(info, "no_speech_prob"))
    except Exception:
        no_speech_prob = None

    return TranscriptStats(text=text, avg_logprob=avg_logprob, no_speech_prob=no_speech_prob)


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def recommend_thresholds(noise: AudioStats, speech: AudioStats, speech_tx: TranscriptStats) -> dict:
    silence_threshold = clamp(noise.mean_abs * 1.6, 0.01, 0.15)
    amplitude_accept = clamp(max(noise.rms * 2.5, noise.mean_abs * 3.0), 0.01, 0.2)

    if speech_tx.avg_logprob is not None:
        confidence_threshold = clamp(speech_tx.avg_logprob - 0.35, -2.5, -0.1)
    else:
        confidence_threshold = DEFAULT_CONFIDENCE_LOGPROB_THRESHOLD

    min_chars = DEFAULT_MIN_TRANSCRIPT_CHARS
    if len(speech_tx.text.split()) <= 1 and len(speech_tx.text) > 0:
        min_chars = max(DEFAULT_MIN_TRANSCRIPT_CHARS, 4)

    min_duration = clamp(max(DEFAULT_MIN_DURATION, speech.duration * 0.15), 0.2, 1.0)

    return {
        "silence_threshold": silence_threshold,
        "amplitude_accept_threshold": amplitude_accept,
        "confidence_logprob_threshold": confidence_threshold,
        "min_transcript_chars": min_chars,
        "min_duration": min_duration,
    }


def print_stats(label: str, stats: AudioStats) -> None:
    print(f"{BLUE}[TUNER] {label} stats{RESET}")
    print(f"  mean_abs: {stats.mean_abs:.6f}")
    print(f"  rms:      {stats.rms:.6f}")
    print(f"  peak:     {stats.peak:.6f}")
    print(f"  duration: {stats.duration:.2f}s")


def print_transcript_stats(label: str, stats: TranscriptStats) -> None:
    print(f"{BLUE}[TUNER] {label} transcription{RESET}")
    print(f"  text: {stats.text or '[empty]'}")
    print(f"  avg_logprob: {stats.avg_logprob if stats.avg_logprob is not None else '[n/a]'}")
    print(f"  no_speech_prob: {stats.no_speech_prob if stats.no_speech_prob is not None else '[n/a]'}")


def save_sample(name: str, audio: np.ndarray) -> None:
    out_path = Path(__file__).with_name(f"{name}.npy")
    np.save(out_path, audio)
    print(f"{YELLOW}[TUNER] Saved sample to {out_path}{RESET}")


def get_settings_path() -> Path:
    """Get the path to the voice settings JSON file."""
    return Path(__file__).parent / "voice_settings.json"


def load_settings() -> Optional[dict]:
    """Load saved voice settings from JSON."""
    settings_path = get_settings_path()
    if settings_path.exists():
        try:
            with open(settings_path) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def save_settings(recommendations: dict) -> None:
    """Save voice settings to JSON."""
    settings_path = get_settings_path()
    try:
        with open(settings_path, "w") as f:
            json.dump(recommendations, f, indent=2)
        print(f"{GREEN}[TUNER] Settings saved to {settings_path}{RESET}")
    except Exception as e:
        print(f"{RED}[TUNER] Failed to save settings: {e}{RESET}")


def plot_audio_comparison(noise: np.ndarray, speech: np.ndarray, noise_stats: AudioStats, speech_stats: AudioStats, recommendations: dict) -> None:
    """Generate matplotlib visualization of audio and thresholds."""
    if not MATPLOTLIB_AVAILABLE:
        print(f"{YELLOW}[TUNER] matplotlib not available; skipping graphs (install: pip install matplotlib){RESET}")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Voice Tuning Analysis", fontsize=16, fontweight="bold")

    # Plot 1: Waveforms
    time_noise = np.arange(len(noise)) / SAMPLE_RATE
    time_speech = np.arange(len(speech)) / SAMPLE_RATE
    axes[0, 0].plot(time_noise, noise, alpha=0.7, label="Ambient Noise", color="orange")
    axes[0, 0].plot(time_speech, speech, alpha=0.7, label="Speech", color="blue")
    axes[0, 0].axhline(recommendations["amplitude_accept_threshold"], color="red", linestyle="--", label=f"Amplitude threshold ({recommendations['amplitude_accept_threshold']:.4f})")
    axes[0, 0].axhline(-recommendations["amplitude_accept_threshold"], color="red", linestyle="--")
    axes[0, 0].set_xlabel("Time (s)")
    axes[0, 0].set_ylabel("Amplitude")
    axes[0, 0].set_title("Waveforms with Amplitude Gate")
    axes[0, 0].legend()
    axes[0, 0].grid(True, alpha=0.3)

    # Plot 2: RMS over time (sliding window)
    window_size = SAMPLE_RATE // 10  # 100ms windows
    noise_rms = [np.sqrt(np.mean(noise[i:i+window_size]**2)) for i in range(0, len(noise) - window_size, window_size)]
    speech_rms = [np.sqrt(np.mean(speech[i:i+window_size]**2)) for i in range(0, len(speech) - window_size, window_size)]
    
    axes[0, 1].plot(noise_rms, marker="o", label="Ambient Noise RMS", color="orange", alpha=0.7)
    axes[0, 1].plot(speech_rms, marker="s", label="Speech RMS", color="blue", alpha=0.7)
    axes[0, 1].axhline(recommendations["amplitude_accept_threshold"], color="red", linestyle="--", label=f"Accept threshold ({recommendations['amplitude_accept_threshold']:.4f})")
    axes[0, 1].set_xlabel("Time Window (100ms each)")
    axes[0, 1].set_ylabel("RMS Amplitude")
    axes[0, 1].set_title("RMS Over Time")
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    # Plot 3: Statistics comparison
    stats_labels = ["Mean Abs", "RMS", "Peak"]
    noise_vals = [noise_stats.mean_abs, noise_stats.rms, noise_stats.peak]
    speech_vals = [speech_stats.mean_abs, speech_stats.rms, speech_stats.peak]
    x_pos = np.arange(len(stats_labels))
    width = 0.35
    axes[1, 0].bar(x_pos - width/2, noise_vals, width, label="Ambient Noise", color="orange", alpha=0.7)
    axes[1, 0].bar(x_pos + width/2, speech_vals, width, label="Speech", color="blue", alpha=0.7)
    axes[1, 0].set_ylabel("Amplitude")
    axes[1, 0].set_title("Audio Statistics")
    axes[1, 0].set_xticks(x_pos)
    axes[1, 0].set_xticklabels(stats_labels)
    axes[1, 0].legend()
    axes[1, 0].grid(True, alpha=0.3, axis="y")

    # Plot 4: Recommended settings
    settings_text = f"""Current Recommended Settings:

silence_threshold: {recommendations['silence_threshold']:.4f}
amplitude_accept_threshold: {recommendations['amplitude_accept_threshold']:.4f}
confidence_logprob_threshold: {recommendations['confidence_logprob_threshold']:.4f}
min_transcript_chars: {recommendations['min_transcript_chars']}
min_duration: {recommendations['min_duration']:.2f}s

---
Noise RMS: {noise_stats.rms:.6f}
Speech RMS: {speech_stats.rms:.6f}
Ratio: {speech_stats.rms / max(noise_stats.rms, 1e-9):.2f}x
"""
    axes[1, 1].text(0.05, 0.95, settings_text, transform=axes[1, 1].transAxes, 
                    fontfamily="monospace", fontsize=10, verticalalignment="top",
                    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5))
    axes[1, 1].axis("off")

    plt.tight_layout()
    graph_path = Path(__file__).parent / "voice_tuning_graph.png"
    plt.savefig(graph_path, dpi=100, bbox_inches="tight")
    print(f"{GREEN}[TUNER] Graph saved to {graph_path}{RESET}")
    plt.show(block=False)



def main() -> int:
    args = parse_args()

    print(f"\n{GREEN}{'='*60}")
    print("FANUC Voice Tuning Tool (Enhanced with Graphs)")
    print(f"{'='*60}{RESET}")
    print(f"Model: {args.model} | Sample rate: {args.sample_rate} Hz | Compute: {args.compute_type}")
    print("This tool only records locally and never sends audio to the LLM.\n")

    # Show previous settings if requested
    if args.show_previous:
        prev_settings = load_settings()
        if prev_settings:
            print(f"{GREEN}[TUNER] Previously saved settings:{RESET}")
            for key, value in prev_settings.items():
                print(f"  {key}: {value}")
            print()
        else:
            print(f"{YELLOW}[TUNER] No previous settings found{RESET}\n")

    try:
        model = WhisperModel(args.model, device="cpu", compute_type=args.compute_type)
    except Exception as e:
        print(f"{RED}[TUNER] Failed to load Whisper model: {e}{RESET}")
        return 1

    input(f"{YELLOW}[TUNER] Press Enter to record ambient noise...{RESET}")
    noise_audio = record_audio(args.noise_seconds, args.sample_rate, args.device)
    noise_stats = compute_stats(noise_audio, args.sample_rate)

    input(f"{YELLOW}[TUNER] Press Enter and speak a normal command...{RESET}")
    speech_audio = record_audio(args.speech_seconds, args.sample_rate, args.device)
    speech_stats = compute_stats(speech_audio, args.sample_rate)
    speech_tx = transcribe(model, speech_audio, args.language)

    if args.save_wav:
        save_sample("voice_tuner_noise", noise_audio)
        save_sample("voice_tuner_speech", speech_audio)

    print()
    print_stats("Ambient noise", noise_stats)
    print_stats("Speech", speech_stats)
    print_transcript_stats("Speech", speech_tx)

    recommendations = recommend_thresholds(noise_stats, speech_stats, speech_tx)

    print(f"\n{GREEN}[TUNER] Suggested settings{RESET}")
    print(f"  silence_threshold: {recommendations['silence_threshold']:.3f}")
    print(f"  amplitude_accept_threshold: {recommendations['amplitude_accept_threshold']:.3f}")
    print(f"  confidence_logprob_threshold: {recommendations['confidence_logprob_threshold']:.3f}")
    print(f"  min_transcript_chars: {recommendations['min_transcript_chars']}")
    print(f"  min_duration: {recommendations['min_duration']:.2f}")

    if noise_stats.rms > 0 and speech_stats.rms / max(noise_stats.rms, 1e-9) < 2.5:
        print(f"\n{RED}[TUNER] Warning: speech is not much louder than noise. Consider a better mic or a quieter room.{RESET}")

    # Generate graphs unless disabled
    if not args.no_graph:
        print()
        plot_audio_comparison(noise_audio, speech_audio, noise_stats, speech_stats, recommendations)

    # Save settings if requested
    if args.save_settings:
        save_settings(recommendations)

    print(f"\n{BLUE}[TUNER] Try the suggested values in master_terminal_chat.py:{RESET}")
    print(
        f"python3 master_terminal_chat.py --voice --silence-threshold {recommendations['silence_threshold']:.3f} "
        f"--amplitude-accept-threshold {recommendations['amplitude_accept_threshold']:.3f} "
        f"--confidence-logprob-threshold {recommendations['confidence_logprob_threshold']:.3f} "
        f"--min-transcript-chars {recommendations['min_transcript_chars']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())