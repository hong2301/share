param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("upload", "fetch", "clean")]
    [string]$Action,
    [string[]]$Files
)

$ErrorActionPreference = "Stop"

# 读取配置
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $scriptDir "..\config.json"
$config = Get-Content $configPath -Raw | ConvertFrom-Json
$SHARE_DIR = $config.share_dir
$REMOTE = $config.remote
if (-not $REMOTE) { $REMOTE = "origin" }
$BRANCH = $config.branch
if (-not $BRANCH) { $BRANCH = "master" }
$username = $config.username
if (-not $username) { $username = "unknown" }

# 确保目录存在
if (-not (Test-Path $SHARE_DIR)) {
    New-Item -ItemType Directory -Path $SHARE_DIR -Force | Out-Null
}

Set-Location $SHARE_DIR

# 检查 git 仓库
if (-not (Test-Path ".git")) {
    Write-Error "$SHARE_DIR is not a git repository."
    exit 1
}

switch ($Action) {
    "upload" {
        $ErrorActionPreference = "Continue"
        
        # 复制文件到 share
        foreach ($src in $Files) {
            if (Test-Path $src) {
                $item = Get-Item $src
                $dest = Join-Path $SHARE_DIR $item.Name
                if ($item.PSIsContainer) {
                    Copy-Item -Path $src -Destination $dest -Recurse -Force
                } else {
                    Copy-Item -Path $src -Destination $dest -Force
                }
                Write-Host "Copied: $src"
            } else {
                Write-Host "Warning: not found: $src"
            }
        }

        # 切到分支并拉取（冲突时以本地上传的为准）
        git checkout $BRANCH
        git pull -X ours $REMOTE $BRANCH

        # 检查是否有变更
        $status = git status --porcelain
        if ([string]::IsNullOrWhiteSpace($status)) {
            Write-Host "Nothing to upload."
            exit 0
        }

        # 提交并推送
        $timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
        git add .
        git commit -m "upload [$username] $timestamp"
        git push $REMOTE $BRANCH
        Write-Host "Upload complete."
    }
    "fetch" {
        git fetch $REMOTE
        git checkout $BRANCH
        git pull $REMOTE $BRANCH
        Write-Host "Fetch complete."
    }
    "clean" {
        # 清空文件
        git rm -rf . 2>$null
        git clean -fd 2>$null

        # 创建清空提交
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        git commit -m "clear [$username] $timestamp" --allow-empty

        # 强制推送
        git push $REMOTE $BRANCH -f
        Write-Host "Share cleaned. History preserved."
    }
}
