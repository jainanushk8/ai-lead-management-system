# scripts/start_ollama.ps1
# Starts Ollama server with OLLAMA_MODELS pointing to D:\Ollama\models

$env:OLLAMA_MODELS = "D:\Ollama\models"
$ollamaBin = "C:\Users\HP\AppData\Local\Programs\Ollama\ollama.exe"

if (-not (Test-Path $ollamaBin)) {
    Write-Error "Ollama executable not found at $ollamaBin"
    exit 1
}

Write-Host "Starting Ollama server with models directory: $env:OLLAMA_MODELS"
& $ollamaBin serve
