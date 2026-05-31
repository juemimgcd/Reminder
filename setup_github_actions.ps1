param(
    [string]$Repository = "juemimgcd/Reminder",
    [string]$DeployHost = "124.223.14.145",
    [int]$DeployPort = 22,
    [string]$DeployUser = "root",
    [string]$DeployAppDir = "/opt/reminder",
    [string]$DeployBranch = "master",
    [ValidateSet("0", "1")]
    [string]$DeployEnableNginxSync = "1",
    [string]$SshKeyPath = "",
    [switch]$KeepPasswordSecret
)

$ErrorActionPreference = "Stop"

function Get-GhCommand {
    $cmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $fallbacks = @(
        "$env:ProgramFiles\GitHub CLI\gh.exe",
        "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe"
    )

    foreach ($path in $fallbacks) {
        if (Test-Path $path) {
            return $path
        }
    }

    return $null
}

function Ensure-GhInstalled {
    $gh = Get-GhCommand
    if ($gh) {
        return $gh
    }

    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "GitHub CLI is not installed, and winget is not available. Please install GitHub CLI manually first."
    }

    Write-Host "[1/5] Installing GitHub CLI via winget..."
    & $winget.Source install --id GitHub.cli -e --source winget --accept-source-agreements --accept-package-agreements

    $gh = Get-GhCommand
    if (-not $gh) {
        throw "GitHub CLI installation completed, but gh was not found in PATH. Please reopen PowerShell and rerun this script."
    }

    return $gh
}

function Ensure-GhAuth {
    param(
        [string]$GhPath
    )

    & $GhPath auth status 1>$null 2>$null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    Write-Host "[2/5] GitHub CLI is not authenticated. Starting web login..."
    & $GhPath auth login --hostname github.com --web --git-protocol ssh
}

function Require-File {
    param(
        [string]$PathValue,
        [string]$Description
    )

    if (-not (Test-Path $PathValue)) {
        throw "$Description not found: $PathValue"
    }
}

if (-not $SshKeyPath) {
    $preferredKeys = @(
        "$HOME\.ssh\reminder_actions_v2",
        "$HOME\.ssh\reminder_actions",
        "$HOME\.ssh\id_ed25519"
    )

    foreach ($candidate in $preferredKeys) {
        if (Test-Path $candidate) {
            $SshKeyPath = $candidate
            break
        }
    }
}

if (-not $SshKeyPath) {
    throw "No SSH private key path was provided, and no default key was found. Pass -SshKeyPath explicitly."
}

Require-File -PathValue $SshKeyPath -Description "SSH private key"

$sshKey = Get-Content -Raw -Path $SshKeyPath
if (-not $sshKey.Trim()) {
    throw "SSH private key file is empty: $SshKeyPath"
}

$gh = Ensure-GhInstalled
Ensure-GhAuth -GhPath $gh

Write-Host "[3/5] Configuring repository variables for $Repository..."
$variables = [ordered]@{
    DEPLOY_HOST              = $DeployHost
    DEPLOY_PORT              = [string]$DeployPort
    DEPLOY_USER              = $DeployUser
    DEPLOY_APP_DIR           = $DeployAppDir
    DEPLOY_BRANCH            = $DeployBranch
    DEPLOY_ENABLE_NGINX_SYNC = $DeployEnableNginxSync
}

foreach ($entry in $variables.GetEnumerator()) {
    Write-Host "  - variable $($entry.Key)"
    & $gh variable set $entry.Key --repo $Repository --body $entry.Value
}

Write-Host "[4/5] Configuring repository secrets for $Repository..."
& $gh secret set DEPLOY_SSH_KEY --repo $Repository --body $sshKey

if (-not $KeepPasswordSecret) {
    $existingSecretNames = @(
        & $gh secret list --repo $Repository |
        ForEach-Object {
            if ($_ -match '^\s*([A-Z0-9_]+)\s') {
                $matches[1]
            }
        }
    ) | Where-Object { $_ }

    if ($existingSecretNames -contains "DEPLOY_PASSWORD") {
        & $gh secret delete DEPLOY_PASSWORD --repo $Repository
    }
}

Write-Host "[5/5] Done."
Write-Host ""
Write-Host "Repository variables configured:"
foreach ($entry in $variables.GetEnumerator()) {
    Write-Host "  $($entry.Key)=$($entry.Value)"
}
Write-Host ""
Write-Host "Repository secret configured:"
Write-Host "  DEPLOY_SSH_KEY (from $SshKeyPath)"
if (-not $KeepPasswordSecret) {
    Write-Host "  DEPLOY_PASSWORD removed if it previously existed"
}
Write-Host ""
Write-Host "You can now rerun the GitHub Actions workflow."
