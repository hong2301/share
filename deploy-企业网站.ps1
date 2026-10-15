# -*- coding: utf-8 -*-
<#
  企业网站 — 一键部署脚本（在目标机器上运行）
  用途：备份旧版 → 清空旧文件 → 解压新版 → 校验 md5

  用法（PowerShell）：
    .\deploy-企业网站.ps1
  或指定包路径：
    .\deploy-企业网站.ps1 -Zip "D:\somewhere\网站复刻.zip"
#>
param(
    [string]$Zip  = "",
    [string]$Dest = "E:\网站\企业网站",
    [string]$BackupRoot = "E:\网站\_备份",
    [string]$ShareUnc = "\\DESKTOP-8QDEIM7\homeShare\网站复刻.zip"
)

$ErrorActionPreference = "Stop"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"

Write-Host "=== 企业网站部署 ===" -ForegroundColor Cyan
Write-Host "目标目录: $Dest"

# ---------- 1. 定位 zip ----------
if (-not $Zip) {
    $candidates = @(
        $ShareUnc,
        (Join-Path $PSScriptRoot "网站复刻.zip"),
        "E:\网站\网站复刻.zip"
    )
    foreach ($c in $candidates) {
        if (Test-Path $c) { $Zip = $c; break }
    }
}
if (-not $Zip -or -not (Test-Path $Zip)) {
    Write-Host "❌ 找不到 网站复刻.zip，请用 -Zip 指定路径" -ForegroundColor Red
    exit 1
}
$zipSize = (Get-Item $Zip).Length
$sha = (Get-FileHash $Zip -Algorithm SHA256).Hash
Write-Host "包: $Zip"
Write-Host "大小: $zipSize 字节"
Write-Host "SHA256: $sha"

# ---------- 2. 备份旧版 ----------
if (Test-Path $Dest) {
    $bak = Join-Path $BackupRoot ("企业网站_" + $ts)
    New-Item -ItemType Directory -Path $bak -Force | Out-Null
    Write-Host "备份旧版 -> $bak"
    Copy-Item -Path (Join-Path $Dest "*") -Destination $bak -Recurse -Force -ErrorAction SilentlyContinue
    $oldCount = (Get-ChildItem $bak -Recurse -File | Measure-Object).Count
    Write-Host "已备份 $oldCount 个文件"

    Write-Host "清空目标目录（删除旧版本）..."
    Get-ChildItem -Path $Dest -Force | Remove-Item -Recurse -Force
} else {
    New-Item -ItemType Directory -Path $Dest -Force | Out-Null
    Write-Host "目标目录不存在，已创建"
}

# ---------- 3. 解压新版 ----------
$tmp = Join-Path $env:TEMP ("shijiao_" + $ts)
if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
New-Item -ItemType Directory -Path $tmp -Force | Out-Null
Write-Host "解压到临时目录..."
Expand-Archive -Path $Zip -DestinationPath $tmp -Force

# zip 内顶层目录名（如「网站复刻」）需要剥掉
$entries = Get-ChildItem $tmp
$root = if ($entries.Count -eq 1 -and $entries[0].PSIsContainer) { $entries[0].FullName } else { $tmp }
Write-Host "内容根: $root"
Copy-Item -Path (Join-Path $root "*") -Destination $Dest -Recurse -Force

# ---------- 4. 校验 ----------
Write-Host "`n校验清单 vs 落地文件..."
$inZip = @{}
Get-ChildItem -Path (Join-Path $root "*") -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($root.Length).TrimStart('\')
    $inZip[$rel] = (Get-FileHash $_.FullName -Algorithm MD5).Hash
}
$bad = @()
foreach ($k in $inZip.Keys) {
    $f = Join-Path $Dest $k
    if (-not (Test-Path $f)) { $bad += "缺失: $k"; continue }
    if ((Get-FileHash $f -Algorithm MD5).Hash -ne $inZip[$k]) { $bad += "不一致: $k" }
}
$total = $inZip.Count
$htmlCount = (Get-ChildItem -Path $Dest -Recurse -Filter "*.html" -File | Measure-Object).Count

Write-Host "`n=== 结果 ===" -ForegroundColor Cyan
Write-Host "包内文件: $total"
Write-Host "HTML 页面: $htmlCount"
if ($bad.Count -eq 0) {
    Write-Host "✅ $total/$total 校验通过，无缺失无不一致" -ForegroundColor Green
} else {
    Write-Host "❌ 有 $($bad.Count) 个文件问题：" -ForegroundColor Red
    $bad | Select-Object -First 20 | ForEach-Object { Write-Host "   $_" }
}

Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue

# ---------- 5. 冒烟测试 ----------
$idx = Join-Path $Dest "index.html"
if (Test-Path $idx) {
    $head = Get-Content $idx -Raw -TotalCount 1
    Write-Host "`n首页存在: $idx"
    if ($head -match "中税银企") { Write-Host "✅ 首页标题含「中税银企」" -ForegroundColor Green }
} else {
    Write-Host "❌ 首页 index.html 不存在" -ForegroundColor Red
}

Write-Host "`n完成。双击 $idx 即可预览（无需服务器）。" -ForegroundColor Green
