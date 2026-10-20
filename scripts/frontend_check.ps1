Set-Location d:\SecuraAI2\frontend
Write-Output ('Node: ' + (node --version 2>$null))
Write-Output ('npm: ' + (npm --version 2>$null))
if (Test-Path node_modules) { Write-Output ('node_modules dirs: ' + (Get-ChildItem node_modules -Directory -ErrorAction SilentlyContinue | Measure-Object).Count) } else { Write-Output 'node_modules MISSING (run npm install)' }
if (Test-Path dist) { Write-Output ('dist files: ' + (Get-ChildItem dist -Recurse -File -ErrorAction SilentlyContinue | Measure-Object).Count) } else { Write-Output 'dist MISSING' }
Write-Output '--- VITE_API_BASE_URL in src/services/api.ts ---'
Get-Content src\services\api.ts -First 12