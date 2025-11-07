# Env setup (portable, no-bake)

You can paste secrets interactively or scan a folder for `keys.info` / `.env` files and merge into `.env`.

## Files
- `example.env` — copy to `.env` as a starting point
- `setup_env.sh` — Linux/macOS interactive/import
- `setup_env.ps1` — Windows PowerShell interactive/import

## Linux/macOS
```bash
chmod +x setup_env.sh
# interactive (paste values)
./setup_env.sh

# OR scan a folder for keys.info / *.env / *.txt and merge
./setup_env.sh --scan .

# OR import a specific file
./setup_env.sh --from-file /path/to/keys.info
```

## Windows (PowerShell)
```powershell
# interactive
.\setup_env.ps1

# scan current dir
.\setup_env.ps1 -Scan -ScanDir .

# import a specific file
.\setup_env.ps1 -FromFile C:\path\to\keys.info
```

Backups are created as `.env.YYYYmmdd-HHMMSS.bak` if a `.env` already exists.
Only whitelisted keys are imported.
