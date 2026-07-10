param(
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = 'C:\Users\rseex\OneDrive\Desktop\ros2_fanuc_interface\New Development\FANUC_LLM_Control2_ordfil\FANUC_LLM_Control2'
$VenvPython = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
$MasterScript = Join-Path $ProjectRoot 'master_terminal_chat.py'
$OllamaExe = (Get-Command ollama).Source
$EdgeExe = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
$ChromeExe = 'C:\Program Files\Google\Chrome\Application\chrome.exe'

function Test-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Url,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            Invoke-RestMethod -Uri $Url -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    return $false
}

function Get-FrontendPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$StdOutLog,
        [Parameter(Mandatory = $true)]
        [string]$StdErrLog
    )

    $combined = ''
    if (Test-Path $StdOutLog) {
        $combined += Get-Content -Path $StdOutLog -Raw -ErrorAction SilentlyContinue
    }
    if (Test-Path $StdErrLog) {
        $combined += "`n" + (Get-Content -Path $StdErrLog -Raw -ErrorAction SilentlyContinue)
    }

    if ($combined -match 'Frontend ready: http://[^:]+:(\d+)') {
        return [int]$Matches[1]
    }

    return $null
}

if (-not (Test-Path $VenvPython)) {
    throw "Missing virtual environment python: $VenvPython"
}

Write-Host "[launcher] Project root: $ProjectRoot"

$ollamaRunning = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $ollamaRunning) {
    Write-Host "[launcher] Starting Ollama..."
    Start-Process -FilePath $OllamaExe -ArgumentList 'serve' -WindowStyle Minimized | Out-Null
    if (-not (Test-HttpReady -Url 'http://127.0.0.1:11434/api/tags' -TimeoutSeconds 120)) {
        throw 'Ollama did not become ready on http://127.0.0.1:11434.'
    }
} else {
    Write-Host "[launcher] Ollama already running."
}

$timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$stdoutLog = Join-Path $env:TEMP "fanuc-master-$timestamp.out.log"
$stderrLog = Join-Path $env:TEMP "fanuc-master-$timestamp.err.log"

Write-Host "[launcher] Starting FANUC master process..."
$masterProc = Start-Process -FilePath $VenvPython -ArgumentList @(
    '-u',
    'master_terminal_chat.py',
    '--frontend',
    '--frontend-host',
    '127.0.0.1'
) -WorkingDirectory $ProjectRoot -RedirectStandardOutput $stdoutLog -RedirectStandardError $stderrLog -PassThru

$frontendPort = $null
for ($attempt = 0; $attempt -lt 240; $attempt++) {
    if ($masterProc.HasExited) {
        break
    }

    $frontendPort = Get-FrontendPort -StdOutLog $stdoutLog -StdErrLog $stderrLog
    if ($frontendPort) {
        break
    }

    Start-Sleep -Milliseconds 500
}

if (-not $frontendPort) {
    $tail = ''
    if (Test-Path $stdoutLog) {
        $tail += (Get-Content -Path $stdoutLog -Tail 20 -ErrorAction SilentlyContinue | Out-String)
    }
    if (Test-Path $stderrLog) {
        $tail += (Get-Content -Path $stderrLog -Tail 20 -ErrorAction SilentlyContinue | Out-String)
    }

    if ($masterProc.HasExited) {
        throw "Master process exited before the frontend became ready. Last output:`n$tail"
    }

    throw "Timed out waiting for the frontend to announce its port. Last output:`n$tail"
}

Write-Host "[launcher] Frontend ready on port $frontendPort"

if (-not $NoBrowser) {
    $frontendUrl = "http://127.0.0.1:$frontendPort"
    Write-Host "[launcher] Opening browser: $frontendUrl"

    if (Test-Path $ChromeExe) {
        Start-Process -FilePath $ChromeExe -ArgumentList @(
            '--kiosk',
            $frontendUrl,
            '--no-first-run'
        ) | Out-Null
    } elseif (Test-Path $EdgeExe) {
        Start-Process -FilePath $EdgeExe -ArgumentList @(
            '--kiosk',
            $frontendUrl,
            '--no-first-run'
        ) | Out-Null
    } else {
        Start-Process -FilePath $frontendUrl | Out-Null
    }
}

Write-Host '[launcher] Done.'
