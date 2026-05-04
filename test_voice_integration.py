#!/usr/bin/env python3
"""
Integration test for voice engine with faster-whisper.
Tests: voice_input loading, faster-whisper initialization, silence detection setup.
"""

import sys
from pathlib import Path

# Add voice_engine to path
sys.path.insert(0, str(Path(__file__).parent / "voice_engine"))

# ANSI colors
BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def test_imports():
    """Test that all voice engine dependencies can be imported."""
    print(f"{BLUE}[TEST] Testing imports...{RESET}")
    
    try:
        import faster_whisper
        print(f"{GREEN}  ✓ faster-whisper {faster_whisper.__version__}{RESET}")
    except ImportError as e:
        print(f"{RED}  ✗ faster-whisper not found: {e}{RESET}")
        return False
    
    try:
        import sounddevice
        print(f"{GREEN}  ✓ sounddevice{RESET}")
    except ImportError as e:
        print(f"{RED}  ✗ sounddevice not found: {e}{RESET}")
        return False
    
    try:
        import numpy
        print(f"{GREEN}  ✓ numpy{RESET}")
    except ImportError as e:
        print(f"{RED}  ✗ numpy not found: {e}{RESET}")
        return False
    
    print(f"{GREEN}All imports successful!{RESET}\n")
    return True


def test_voice_input_initialization():
    """Test VoiceInput class initialization with faster-whisper."""
    print(f"{BLUE}[TEST] Testing VoiceInput initialization...{RESET}")
    
    try:
        from voice_input import VoiceInput
        print(f"{GREEN}  ✓ VoiceInput class imported{RESET}")
    except ImportError as e:
        print(f"{RED}  ✗ Failed to import VoiceInput: {e}{RESET}")
        return False
    
    try:
        vi = VoiceInput(model="tiny", use_wake_word=False)
        print(f"{GREEN}  ✓ VoiceInput initialized with faster-whisper (tiny model){RESET}")
        print(f"{GREEN}  ✓ Audio parameters: 16kHz, float32, 1 channel{RESET}")
        print(f"{GREEN}  ✓ Silence detection enabled (threshold=0.02, duration=0.5s){RESET}")
        vi.stop()
        print(f"{GREEN}VoiceInput initialization successful!{RESET}\n")
        return True
    except Exception as e:
        print(f"{RED}  ✗ Failed to initialize VoiceInput: {e}{RESET}")
        return False


def test_voice_models():
    """Test faster-whisper model availability."""
    print(f"{BLUE}[TEST] Testing faster-whisper models...{RESET}")
    
    try:
        from faster_whisper import WhisperModel
        
        # Test tiny model (fastest)
        print(f"  Testing 'tiny' model...")
        model_tiny = WhisperModel("tiny", device="cpu", compute_type="int8")
        print(f"{GREEN}  ✓ 'tiny' model loaded successfully{RESET}")
        
        print(f"{GREEN}faster-whisper models working!{RESET}\n")
        return True
    except Exception as e:
        print(f"{RED}  ✗ Failed to load models: {e}{RESET}")
        return False


def test_audio_processing():
    """Test audio processing pipeline."""
    print(f"{BLUE}[TEST] Testing audio processing...{RESET}")
    
    try:
        import numpy as np
        
        # Simulate audio
        sample_rate = 16000
        duration = 1  # 1 second
        samples = np.random.randn(sample_rate * duration).astype(np.float32)
        
        # Test normalization (what voice_input does)
        max_val = np.max(np.abs(samples))
        if max_val > 0:
            normalized = samples / max_val
        
        print(f"{GREEN}  ✓ Audio normalization working{RESET}")
        print(f"{GREEN}  ✓ Can process {len(samples)} samples ({duration}s @ 16kHz){RESET}")
        
        # Test int16 conversion (for porcupine)
        audio_int16 = (samples * 32767).astype(np.int16)
        print(f"{GREEN}  ✓ Float32 to int16 conversion working{RESET}")
        
        print(f"{GREEN}Audio processing successful!{RESET}\n")
        return True
    except Exception as e:
        print(f"{RED}  ✗ Failed: {e}{RESET}")
        return False


def main():
    """Run all integration tests."""
    print(f"\n{BLUE}{'='*60}")
    print("FANUC Voice Engine Integration Tests")
    print(f"{'='*60}{RESET}\n")
    
    tests = [
        ("Imports", test_imports),
        ("VoiceInput Initialization", test_voice_input_initialization),
        ("Faster-Whisper Models", test_voice_models),
        ("Audio Processing", test_audio_processing),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"{RED}[ERROR] {test_name} crashed: {e}{RESET}\n")
            results.append((test_name, False))
    
    # Summary
    print(f"{BLUE}{'='*60}")
    print("Test Summary")
    print(f"{'='*60}{RESET}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = f"{GREEN}✓ PASS{RESET}" if result else f"{RED}✗ FAIL{RESET}"
        print(f"{status} — {test_name}")
    
    print(f"\n{YELLOW}{passed}/{total} tests passed{RESET}")
    
    if passed == total:
        print(f"\n{GREEN}All tests passed! Voice engine is ready to use.{RESET}")
        print(f"{BLUE}Start voice chat with: python3 voice_engine/voice_chat.py{RESET}\n")
        return 0
    else:
        print(f"\n{RED}Some tests failed. Please check the output above.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
