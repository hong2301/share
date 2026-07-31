# hong-share

在 Mac 与 Windows 之间用本地 Git 仓库 `C:/Users/86150/Desktop/hong/share` 临时共享文件。

## 使用方式

直接对 pi 说：

```text
把 C:/Users/86150/Downloads/report.pdf 上传到 share
```

```text
清空一下 share
```

```text
获取一下 share 的 report.pdf
```

## 触发词

| 意图 | 示例 |
|------|------|
| 上传文件 | "把 xxx 上传到 share"、"传 xxx 到 share" |
| 清空仓库 | "清空一下 share"、"把 share 清空" |
| 获取文件 | "获取一下 share 的 xxx"、"从 share 拿 xxx" |

## 工作原理

- 上传：把文件复制到 `C:/Users/86150/Desktop/hong/share`，然后 `git add / commit / push`。
- 清空：把 `master` 重置到空分支 `empty` 的状态，并强制推送到远程。
- 获取：执行 `git pull`，然后在仓库里查找指定文件。

## 脚本

Windows 使用 PowerShell 脚本（位于 `scripts/` 目录）：

```powershell
scripts/share-upload.ps1 <file-path>
scripts/share-fetch.ps1 [file-name]
scripts/share-clean.ps1
```

如果 PowerShell 提示执行策略被禁用，先运行：

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

[English Version](docs/README.en.md)
