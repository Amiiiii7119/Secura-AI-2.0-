# Deployment and Rollback Procedures

## 1. Backup Checkpoints Saved
Before changes were made, full recoverable backups of the modified application files were preserved at:
`D:\SecuraAI2\.backup_mission24\`
- `evidence.py`
- `video_orchestrator.py`
- `video_fusion.py`
- `metadata_inspector.py`
- `routes.py`
- `App.tsx`
- `VideoForensicsWorkspace.tsx`
- `api.ts`

To roll back, restore files from `D:\SecuraAI2\.backup_mission24\` to their respective locations in `backend/app` and `frontend/src`.

---

## 2. Server Startup Commands

### Backend (FastAPI / Uvicorn)
```powershell
cd D:\SecuraAI2
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

### Frontend (Vite + React)
```powershell
cd D:\SecuraAI2\frontend
npm run dev -- --host
```
Application UI: [http://localhost:5173/](http://localhost:5173/)\n