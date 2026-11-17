# scripts/start_n8n.ps1
# Runs n8n locally via npx with data directory anchored inside the project folder

$n8nUserFolder = "$PSScriptRoot\..\n8n\.n8n"

if (-not (Test-Path $n8nUserFolder)) {
    New-Item -ItemType Directory -Path $n8nUserFolder -Force | Out-Null
}

$env:N8N_USER_FOLDER = (Resolve-Path $n8nUserFolder).Path
$env:N8N_PORT = "5678"
$env:N8N_HOST = "localhost"
$env:N8N_DIAGNOSTICS_ENABLED = "false"
$env:N8N_VERSION_NOTIFICATIONS_ENABLED = "false"

Write-Host "Starting n8n with user data at: $env:N8N_USER_FOLDER"
Write-Host "n8n UI will be available at: http://localhost:5678"

npx n8n
