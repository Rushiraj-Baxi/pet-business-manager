# Deployment Guide — ANI Enterprises (PET Business Manager)

## Prerequisites

- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) installed and logged in (`az login`)
- [Node.js](https://nodejs.org/) with npm
- [SWA CLI](https://github.com/Azure/static-web-apps-cli) installed globally: `npm install -g @azure/static-web-apps-cli`
- Python 3.12+

## Azure Resources

| Resource | Name | Type |
|----------|------|------|
| Resource Group | `pet-business-rg` | — |
| Backend | `pet-business-api` | App Service (B1 Linux, Python 3.12) |
| Frontend | `pet-business-web` | Static Web App (Free) |

**URLs:**
- Frontend: `https://ambitious-grass-05285fe00.2.azurestaticapps.net`
- Backend API: `https://pet-business-api.azurewebsites.net/api`

---

## Deploying Frontend Changes

Run these commands from the project root (`soft/`):

```powershell
# 1. Build with production API URL
cd frontend
$env:VITE_API_URL = "https://pet-business-api.azurewebsites.net/api"
npm run build

# 2. Copy SWA config into dist
Copy-Item staticwebapp.config.json dist\

# 3. Deploy to Azure Static Web Apps
$token = (az staticwebapp secrets list --name pet-business-web --resource-group pet-business-rg --query "properties.apiKey" -o tsv)
swa deploy dist --deployment-token $token --env production

cd ..
```

---

## Deploying Backend Changes

**Important:** Do NOT use PowerShell's `Compress-Archive` — it creates backslash paths that break on Linux. Use .NET's `ZipFile` instead.

Run these commands from the project root (`soft/`):

```powershell
# 1. Create zip with forward-slash paths (required for Linux)
Add-Type -AssemblyName System.IO.Compression.FileSystem

$src = (Resolve-Path "backend").Path
$zip = (Resolve-Path ".").Path + "\backend_deploy.zip"
if (Test-Path $zip) { Remove-Item $zip }

[System.IO.Compression.ZipFile]::CreateFromDirectory($src, $zip)

# Remove __pycache__ entries from the zip
$archive = [System.IO.Compression.ZipFile]::Open($zip, 'Update')
$toDelete = $archive.Entries | Where-Object { $_.FullName -match '__pycache__' }
$toDelete | ForEach-Object { $_.Delete() }
$archive.Dispose()

Write-Host "Created: $((Get-Item $zip).Length) bytes"

# 2. Deploy to Azure App Service
az webapp deploy --name pet-business-api --resource-group pet-business-rg --src-path $zip --type zip

# 3. Restart the app
az webapp restart --name pet-business-api --resource-group pet-business-rg
```

After deploying, wait ~60 seconds for the container to restart, then verify:

```powershell
# Check health
python -c "import urllib.request; r=urllib.request.urlopen('https://pet-business-api.azurewebsites.net/api/health'); print(r.status, r.read().decode())"
```

If this is the **first deploy** or you deleted the venv, the first container start takes ~5-7 minutes (pip install). It will time out once but the venv persists — the second start succeeds immediately.

---

## Deploying Both (Full Deploy)

```powershell
# 1. Deploy backend first (steps above)
# 2. Deploy frontend (steps above)
# 3. Commit and push
git add -A
git commit -m "Your commit message"
git push origin master
```

---

## Key App Settings (already configured)

These are set on the App Service and generally don't need changes:

| Setting | Value |
|---------|-------|
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `false` |
| `ENABLE_ORYX_BUILD` | `false` |
| `WEBSITES_PORT` | `8000` |
| `WEBSITES_CONTAINER_START_TIME_LIMIT` | `400` |
| `CORS_ORIGINS` | `https://ambitious-grass-05285fe00.2.azurestaticapps.net,...` |
| Startup command | `bash /home/site/wwwroot/startup.sh` |

To update a setting:
```powershell
az webapp config appsettings set --name pet-business-api --resource-group pet-business-rg --settings KEY=VALUE
```

---

## Troubleshooting

**View container logs:**
```powershell
az webapp log download --name pet-business-api --resource-group pet-business-rg --log-file logs.zip
Expand-Archive logs.zip -DestinationPath logs -Force
Get-Content logs\LogFiles\*docker* -Tail 50
```

**503 errors after deploy:** Wait 60-90 seconds — the container is starting up. If it persists after 5 minutes, check logs.

**Backend returns errors:** SSH into the container or check logs. The SQLite database lives at `/home/data/business.db` on Azure (persists across restarts).
