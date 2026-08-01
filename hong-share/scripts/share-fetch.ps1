$ErrorActionPreference = "Stop"

$SHARE_DIR = "C:/Users/86150/Desktop/hong/share"

Set-Location $SHARE_DIR

if (-not (Test-Path ".git")) {
    Write-Error "$SHARE_DIR is not a git repository."
    exit 1
}

# 拉取最新内容
git checkout master
git pull origin master

# 如果传入了文件名参数，则查找
if ($args[0]) {
    $pattern = $args[0]
    $file = Get-ChildItem -Path $SHARE_DIR -File -Name $pattern | Select-Object -First 1
    if ($file) {
        $fullPath = Join-Path $SHARE_DIR $file
        Write-Host "Found: $fullPath"
    } else {
        Write-Host "Not found: $pattern"
        Write-Host "Current files in share:"
        Get-ChildItem -Path $SHARE_DIR -File | Select-Object -ExpandProperty Name
    }
} else {
    Write-Host "Current files in share:"
    Get-ChildItem -Path $SHARE_DIR -File | Select-Object -ExpandProperty Name
}
