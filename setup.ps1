<#
.SYNOPSIS
    Windows setup script for mini_transcriber (equivalent to setup.sh for Linux)
.DESCRIPTION
    Installs Python dependencies for mini_transcriber on Windows.
    Requires Python 3.12+ and optionally 'uv' for faster installs.
.NOTES
    Run from PowerShell: .\setup.ps1
    Prerequisites: Python 3.12+, FFmpeg (optional, for audio conversion)
#>

$ErrorActionPreference = "Stop"

Write-Host "=== mini_transcriber Windows Setup ===" -ForegroundColor Cyan

# Check Python version
$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    try {
        $version = & $cmd --version 2>$null
        if ($version -match "Python 3\.(\d+)") {
            $minor = [int]$Matches[1]
            if ($minor -ge 12) {
                $pythonCmd = $cmd
                Write-Host "Found $version using '$cmd'" -ForegroundColor Green
                break
            }
        }
    } catch {
        # Command not found, try next
    }
}

if (-not $pythonCmd) {
    Write-Host "ERROR: Python 3.12+ is required but not found." -ForegroundColor Red
    Write-Host "Please install Python 3.12 or later from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Check for FFmpeg (optional)
$ffmpegFound = $null -ne (Get-Command "ffmpeg" -ErrorAction SilentlyContinue)
if ($ffmpegFound) {
    Write-Host "FFmpeg found" -ForegroundColor Green
} else {
    Write-Host "FFmpeg not found (optional - needed for audio conversion)" -ForegroundColor Yellow
    Write-Host "Install FFmpeg from https://ffmpeg.org/download.html or via winget/choco" -ForegroundColor Yellow
}

# Determine install mode
$INSTALL_FULL = $env:INSTALL_FULL -eq "1"

# Check for uv
$uvFound = $null -ne (Get-Command "uv" -ErrorAction SilentlyContinue)

if ($uvFound) {
    Write-Host "Detected 'uv' - using uv for dependency management" -ForegroundColor Green
    
    # Prefer a frozen CPU-only install
    if (Test-Path "uv.lock") {
        Write-Host "uv.lock detected - performing a frozen CPU-only install" -ForegroundColor Cyan
        try {
            & uv add --frozen --requirements requirements-cpu.txt
            Write-Host "Installed from uv.lock (frozen)" -ForegroundColor Green
        } catch {
            Write-Host "uv add --frozen failed. If you intentionally updated requirements, run:" -ForegroundColor Yellow
            Write-Host "  uv add -r requirements-cpu.txt --index-strategy unsafe-best-match && uv add --frozen --requirements requirements-cpu.txt" -ForegroundColor Yellow
        }
    } else {
        Write-Host "No uv.lock present - creating a CPU-only lock from requirements-cpu.txt" -ForegroundColor Cyan
        try {
            & uv add -r requirements-cpu.txt --index-strategy unsafe-best-match
            & uv add --frozen --requirements requirements-cpu.txt
        } catch {
            Write-Host "uv add failed. Try running: uv add -r requirements-cpu.txt --index-strategy unsafe-best-match" -ForegroundColor Yellow
        }
    }
    
    if ($INSTALL_FULL) {
        Write-Host "Installing full requirements from requirements-full.txt (user opted-in)" -ForegroundColor Cyan
        try {
            & uv add -r requirements-full.txt
            Write-Host "Full dependencies installed" -ForegroundColor Green
        } catch {
            Write-Host "ERROR: 'uv add -r requirements-full.txt' failed" -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Defaulting to CPU-only install" -ForegroundColor Cyan
        try {
            & uv add -r requirements-cpu.txt
            Write-Host "CPU-only dependencies installed" -ForegroundColor Green
        } catch {
            Write-Host "Warning: 'uv add -r requirements-cpu.txt' failed. Trying essential packages..." -ForegroundColor Yellow
            try {
                & uv add pytest flask numpy whisper
                
                # Ensure pip is available
                & uv run python -m ensurepip --upgrade 2>$null
                
                # Install CPU-only torch/torchaudio
                Write-Host "Installing CPU-only torch/torchaudio..." -ForegroundColor Cyan
                & uv add --index https://download.pytorch.org/whl/cpu `
                    -f https://download.pytorch.org/whl/cpu/torch_stable.html `
                    torch==2.2.2+cpu torchaudio==2.2.2+cpu 2>$null
                
                # Install numba/llvmlite (whisper dependencies - use pip as uv add may not handle these well)
                Write-Host "Installing numba and llvmlite..." -ForegroundColor Cyan
                & uv pip install llvmlite numba 2>$null
                
                # Install remaining runtime deps
                & uv add --index-strategy unsafe-best-match flask numpy soundfile sounddevice tqdm regex tiktoken requests 2>$null
                
                # Install openai-whisper (use pip with --no-deps to avoid pulling heavy optional deps)
                Write-Host "Installing openai-whisper..." -ForegroundColor Cyan
                & uv pip install --no-deps git+https://github.com/openai/whisper.git@main 2>$null
                
                # Verification
                Write-Host "Verifying torch and whisper imports..." -ForegroundColor Cyan
                & uv run python -c "import importlib,sys; print('python',sys.executable); importlib.import_module('torch'); print('torch OK'); importlib.import_module('whisper'); print('whisper OK')" 2>$null
            } catch {
                Write-Host "ERROR: Failed to install essential packages" -ForegroundColor Red
                exit 1
            }
        }
    }
    Write-Host "Run scripts with: uv run python <script>" -ForegroundColor Green
} else {
    Write-Host "'uv' not found - using pip with venv" -ForegroundColor Yellow
    
    # Create virtual environment
    $venvPath = "venv"
    if (-not (Test-Path $venvPath)) {
        Write-Host "Creating virtual environment..." -ForegroundColor Cyan
        & $pythonCmd -m venv $venvPath
    }
    
    # Activate venv and install deps
    $activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
    if (Test-Path $activateScript) {
        Write-Host "Activating virtual environment..." -ForegroundColor Cyan
        . $activateScript
        
        # Upgrade pip
        & python -m pip install --upgrade pip
        
        if ($INSTALL_FULL) {
            Write-Host "Installing full requirements..." -ForegroundColor Cyan
            & python -m pip install -r requirements-full.txt
        } else {
            Write-Host "Installing CPU-only PyTorch and torchaudio..." -ForegroundColor Cyan
            & python -m pip install --index-url https://download.pytorch.org/whl/cpu `
                torch==2.2.2+cpu torchaudio==2.2.2+cpu `
                -f https://download.pytorch.org/whl/cpu/torch_stable.html 2>$null
            
            Write-Host "Installing numba/llvmlite..." -ForegroundColor Cyan
            & python -m pip install llvmlite numba 2>$null
            
            Write-Host "Installing openai-whisper and CPU runtime requirements..." -ForegroundColor Cyan
            # Use --no-deps for whisper to avoid pulling heavy optional deps
            & python -m pip install --no-deps git+https://github.com/openai/whisper.git@main 2>$null
            $cpuInstallResult = & python -m pip install -r requirements-cpu.txt 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Warning: requirements-cpu.txt install had issues, installing essential packages..." -ForegroundColor Yellow
                & python -m pip install pytest flask numpy
            }
            
            # Verification
            Write-Host "Verifying torch and whisper imports..." -ForegroundColor Cyan
            & python -c "import importlib,sys; print('python',sys.executable); importlib.import_module('torch'); print('torch OK'); importlib.import_module('whisper'); print('whisper OK')" 2>$null
        }
        
        Write-Host "Setup complete. Activate with: .\venv\Scripts\Activate.ps1" -ForegroundColor Green
    } else {
        Write-Host "ERROR: Failed to create virtual environment" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n=== Setup Complete ===" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. Run CLI: uv run python cli.py path/to/audio.wav" -ForegroundColor White
Write-Host "     (The tiny model will auto-download on first use)" -ForegroundColor Gray
Write-Host "  2. Run server: uv run python app.py" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Optional: Pre-download models to avoid download time during first use:" -ForegroundColor Gray
Write-Host "  uv run python download_model.py --model tiny" -ForegroundColor Gray
