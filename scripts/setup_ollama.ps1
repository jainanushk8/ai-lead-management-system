# scripts/setup_ollama.ps1
# Helper script to configure Ollama to store its models and binaries on a custom drive (e.g. F: drive)
# This prevents filling up the C: drive.

param (
    [string]$ModelsDirectory = "D:\Ollama\models"
)

Write-Host "Configuring Ollama Model Directory to: $ModelsDirectory"

if (-not (Test-Path $ModelsDirectory)) {
    New-Item -ItemType Directory -Path $ModelsDirectory -Force | Out-Null
    Write-Host "Created directory: $ModelsDirectory"
}

# Set User Environment Variable OLLAMA_MODELS so Ollama stores all downloaded models on this custom drive
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ModelsDirectory, "User")
$env:OLLAMA_MODELS = $ModelsDirectory

Write-Host "OLLAMA_MODELS environment variable successfully set to: $ModelsDirectory"
Write-Host "Any model pulled with 'ollama run' or 'ollama pull' will now be saved in $ModelsDirectory."
