$root = 'd:\SecuraAI2'
Write-Output '=== BACKEND LOCAL SETUP CHECK ==='
Set-Location $root
Write-Output ('Python (global): ' + (python --version 2>$null))
$vpy = Join-Path $root '.venv\Scripts\python.exe'
Write-Output ('Python (venv): ' + (if (Test-Path $vpy) { (& $vpy --version 2>$null) } else { 'NOT FOUND' }))
& $vpy -c "import fastapi, torch, transformers, cv2, psycopg2, sqlalchemy, alembic; print('fastapi:', fastapi.__version__, '| torch:', torch.__version__, '| transformers:', transformers.__version__, '| cv2:', cv2.__version__, '| psycopg2:', psycopg2.__version__, '| alembic:', alembic.__version__)"
Write-Output '--- Model weights (local, 2GB project) ---'
Get-ChildItem -Recurse -File (Join-Path $root 'backend\models\weights') -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum | ForEach-Object { Write-Output ('Total weights: ' + [math]::Round($_.Sum/1GB,2) + ' GB') }
Write-Output '--- Weights subdirs ---'
Get-ChildItem -Recurse -Directory (Join-Path $root 'backend\models\weights') -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name
if (Test-Path (Join-Path $root '.env')) { Write-Output '.env: EXISTS' } else { Write-Output '.env: MISSING (copy from .env.example)' }