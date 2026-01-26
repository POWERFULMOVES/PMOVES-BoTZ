# Setup PMOVES-BoTZ
Write-Host "Setting up PMOVES-BoTZ..."

# Check for .env
if (-not (Test-Path .env)) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item .env.example .env
}

# Install dependencies (if any)
# pip install -r requirements.txt

Write-Host "Setup complete."
