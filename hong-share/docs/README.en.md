# hong-share

Temporarily share files between Mac and Windows using the local Git repository at `C:/Users/86150/Desktop/hong/share`.

## Usage

Talk to pi naturally:

```text
Upload C:/Users/86150/Downloads/report.pdf to share
```

```text
Clean up share
```

```text
Fetch report.pdf from share
```

## How it works

- **Upload**: Copies the file into `C:/Users/86150/Desktop/hong/share`, then runs `git add / commit / push`.
- **Clean**: Resets `master` to the empty `empty` branch and force-pushes to remote.
- **Fetch**: Runs `git pull` and searches for the requested file.

## Scripts

On Windows, use the PowerShell scripts in `scripts/`:

```powershell
scripts/share-upload.ps1 <file-path>
scripts/share-fetch.ps1 [file-name]
scripts/share-clean.ps1
```

If PowerShell reports an execution policy error, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

[中文版本](README.md)
