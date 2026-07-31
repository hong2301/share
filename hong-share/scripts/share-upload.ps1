$ErrorActionPreference = "Stop"

$SHARE_DIR = "C:/Users/86150/Desktop/hong/share"

# 确保 SHARE_DIR 存在
if (-not (Test-Path $SHARE_DIR)) {
    New-Item -ItemType Directory -Path $SHARE_DIR -Force | Out-Null
}

# 如果传入了文件/目录参数，先复制到 SHARE_DIR
foreach ($src in $args) {
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

Set-Location $SHARE_DIR

if (-not (Test-Path ".git")) {
    Write-Error "$SHARE_DIR is not a git repository."
    exit 1
}

# 切到 master 并拉取最新状态
git checkout master
git pull origin master

# 检查是否有需要提交的内容
$status = git status --porcelain
if ([string]::IsNullOrWhiteSpace($status)) {
    Write-Host "Nothing to upload."
    exit 0
}

# 提交并推送
$timestamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
git add .
git commit -m "upload $timestamp"
git push origin master

Write-Host "Upload complete."
