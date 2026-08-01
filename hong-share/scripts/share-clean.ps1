$ErrorActionPreference = "Stop"

$SHARE_DIR = "C:/Users/86150/Desktop/hong/share"

Set-Location $SHARE_DIR

if (-not (Test-Path ".git")) {
    Write-Error "$SHARE_DIR is not a git repository."
    exit 1
}

# 获取空分支的最新 commit
$emptyCommit = git rev-parse origin/empty 2>$null
if (-not $emptyCommit) {
    Write-Error "Cannot find origin/empty branch."
    exit 1
}

# 重置 master 到空分支并强制推送
git checkout master
git reset $emptyCommit
git clean -fd
git push origin master -f

Write-Host "Share cleaned."
