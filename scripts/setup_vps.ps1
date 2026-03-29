# setup_vps.ps1 — TRADER AI VPS Setup (Windows Server / Windows 11)
# Run as Administrator in PowerShell on the VPS
# Installs: Docker Desktop, Python 3.11, Nginx, rclone, win-acme
# Then clones the repo and configures it for production

param(
    [string]$RepoUrl  = "https://github.com/Ximena5745/Trading_IA.git",
    [string]$AppDir   = "C:\trader_ai",
    [string]$Domain   = "",   # e.g. "traderai.example.com" — leave empty to skip HTTPS
    [string]$Branch   = "main"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$msg) {
    Write-Host "`n==> $msg" -ForegroundColor Cyan
}

# ── 1. Check Administrator ────────────────────────────────────────────────────
Write-Step "Checking administrator privileges"
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Error "Run this script as Administrator"
    exit 1
}

# ── 2. Install winget packages ────────────────────────────────────────────────
Write-Step "Installing dependencies via winget"
$packages = @(
    @{ id = "Git.Git";           name = "Git" },
    @{ id = "Python.Python.3.11"; name = "Python 3.11" }
)
foreach ($pkg in $packages) {
    Write-Host "  Installing $($pkg.name)..."
    winget install --id $pkg.id --silent --accept-source-agreements --accept-package-agreements 2>$null
}

# ── 3. Docker Desktop ─────────────────────────────────────────────────────────
Write-Step "Checking Docker Desktop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "  Docker not found — download manually from https://www.docker.com/products/docker-desktop"
    Write-Host "  Then re-run this script."
    exit 1
} else {
    Write-Host "  Docker found ✅"
}

# ── 4. Clone / update repository ──────────────────────────────────────────────
Write-Step "Setting up repository at $AppDir"
if (Test-Path $AppDir) {
    Write-Host "  Directory exists — pulling latest changes"
    Push-Location $AppDir
    git pull origin $Branch
    Pop-Location
} else {
    git clone --branch $Branch $RepoUrl $AppDir
}

# ── 5. Python virtual environment + dependencies ──────────────────────────────
Write-Step "Creating Python virtual environment"
Push-Location $AppDir
python -m venv .venv
& "$AppDir\.venv\Scripts\Activate.ps1"
python -m pip install --upgrade pip
pip install -r requirements.txt
Pop-Location

# ── 6. .env file ──────────────────────────────────────────────────────────────
Write-Step "Checking .env"
$envFile = Join-Path $AppDir ".env"
if (-not (Test-Path $envFile)) {
    Copy-Item "$AppDir\.env.example" $envFile
    Write-Host "  .env created from template — EDIT IT before starting the app!" -ForegroundColor Yellow
    Write-Host "  notepad $envFile"
} else {
    Write-Host "  .env already exists ✅"
}

# ── 7. Docker Compose — DB + Redis ────────────────────────────────────────────
Write-Step "Starting Docker services (db, redis)"
Push-Location "$AppDir\docker"
docker compose up db redis -d
Write-Host "  Waiting 10s for DB to initialize..."
Start-Sleep -Seconds 10
Write-Host "  Applying database schema..."
$schemaPath = "$AppDir\scripts\migrations\001_initial_schema.sql"
$schema2Path = "$AppDir\scripts\migrations\002_instruments.sql"
docker exec -i trader_db psql -U trader -d trader_ai -f /dev/stdin < $schemaPath
docker exec -i trader_db psql -U trader -d trader_ai -f /dev/stdin < $schema2Path
Pop-Location

# ── 8. Nginx ──────────────────────────────────────────────────────────────────
Write-Step "Setting up Nginx"
$nginxDir = "C:\nginx"
if (-not (Test-Path $nginxDir)) {
    Write-Host "  Download Nginx for Windows from https://nginx.org/en/download.html"
    Write-Host "  Extract to C:\nginx and re-run this script."
} else {
    Copy-Item "$AppDir\docker\nginx.conf" "$nginxDir\conf\nginx.conf" -Force
    if ($Domain) {
        (Get-Content "$nginxDir\conf\nginx.conf") -replace "YOUR_DOMAIN_OR_IP", $Domain |
            Set-Content "$nginxDir\conf\nginx.conf"
        Write-Host "  Domain set to $Domain in nginx.conf ✅"
    }
    Write-Host "  Nginx config updated ✅"
}

# ── 9. Windows Task Scheduler — backup ────────────────────────────────────────
Write-Step "Creating daily backup Task Scheduler job"
$pythonPath = "$AppDir\.venv\Scripts\python.exe"
$scriptPath = "$AppDir\scripts\backup_db.py"
$action  = New-ScheduledTaskAction -Execute $pythonPath -Argument "`"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At "03:00AM"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1)
Register-ScheduledTask -TaskName "TraderAI_Backup" -Action $action -Trigger $trigger `
    -Settings $settings -RunLevel Highest -Force | Out-Null
Write-Host "  Backup task registered ✅ (runs daily at 03:00 AM)"

# ── 10. Summary ───────────────────────────────────────────────────────────────
Write-Host "`n" + ("=" * 60) -ForegroundColor Green
Write-Host "TRADER AI VPS Setup Complete!" -ForegroundColor Green
Write-Host ("=" * 60)
Write-Host @"

Next steps:
  1. Edit the .env file:         notepad $AppDir\.env
  2. Create admin user:          cd $AppDir && .venv\Scripts\python.exe scripts\seed_admin.py
  3. Start the API:              cd $AppDir && .venv\Scripts\uvicorn.exe api.main:app --host 0.0.0.0 --port 8000
  4. Start Streamlit:            cd $AppDir && .venv\Scripts\streamlit.exe run app/dashboard.py --server.port 8501
  5. Start Nginx:                C:\nginx\nginx.exe
  6. Configure HTTPS (win-acme): https://www.win-acme.com/
  7. Test health:                curl http://localhost:8000/health

Windows Firewall — allow only:
  netsh advfirewall firewall add rule name="HTTP"  dir=in action=allow protocol=TCP localport=80
  netsh advfirewall firewall add rule name="HTTPS" dir=in action=allow protocol=TCP localport=443
"@
