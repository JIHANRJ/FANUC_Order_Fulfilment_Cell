param()

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvDir = Join-Path $RootDir ".venv"
$Requirements = Join-Path $RootDir "requirements.txt"

if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
    $PythonArgs = @()
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCmd = "py"
    $PythonArgs = @("-3")
} else {
    throw "Python 3 is required but was not found on PATH."
}

Write-Host "[setup] Repository root: $RootDir"

if (-not (Test-Path $VenvDir)) {
    Write-Host "[setup] Creating virtual environment in .venv"
    & $PythonCmd @PythonArgs -m venv $VenvDir
}

Write-Host "[setup] Activating virtual environment"
. (Join-Path $VenvDir "Scripts\Activate.ps1")

Write-Host "[setup] Upgrading pip"
python -m pip install --upgrade pip

Write-Host "[setup] Installing Python dependencies"
python -m pip install -r $Requirements

Write-Host "[setup] Verifying core imports"
@'
import sys

checks = [
    ("numpy", "numpy"),
    ("sounddevice", "sounddevice"),
    ("faster-whisper", "faster_whisper"),
]

failed = []
for label, module_name in checks:
    try:
        __import__(module_name)
        print(f"[setup] OK: {label}")
    except Exception as exc:
        failed.append((label, exc))
        print(f"[setup] FAIL: {label}: {exc}")

if failed:
    print("[setup] One or more imports failed. If sounddevice is missing system libraries, install them and rerun setup.")
    sys.exit(1)
'@ | python -

Write-Host ""
Write-Host "[setup] Setup complete. Next steps:"
Write-Host "[setup] 1. Start Ollama with: ollama serve"
Write-Host "[setup] 2. Pull a model with: ollama pull llama3:latest"
Write-Host "[setup] 3. Start the app with: python master_terminal_chat.py --frontend"