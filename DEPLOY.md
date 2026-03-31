# StreetSense -- Railway Deployment Guide

## Prerequisites
- GitHub account with the streetsense repo pushed
- Railway account (https://railway.app -- sign up with GitHub)

---

## Step 1: Push code to GitHub

```bash
cd D:\streetsense
git add -A
git commit -m "Deployment ready: all phases complete"
git push origin main
```

## Step 2: Build frontend for production

```bash
cd D:\streetsense\frontend
npm install
npm run build
```

This creates `backend/static/` with the compiled React app.

```bash
cd D:\streetsense
git add backend/static/
git commit -m "Add frontend production build"
git push origin main
```

## Step 3: Upload AI weights to the repo (or use Git LFS)

The best.pt file is ~22MB. You have two options:

### Option A: Git LFS (recommended for files >10MB)
```bash
git lfs install
git lfs track "*.pt"
git add .gitattributes
git add backend/ai/weights/best.pt
git commit -m "Add YOLO weights via LFS"
git push origin main
```

### Option B: Skip weights (AI will be disabled, app still works)
The app runs without AI -- upload/detection won't work but
dashboard, map, auth, and complaint management all work.
You can add weights later via Railway volume.

## Step 4: Create Railway project

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your `streetsense` repository
4. Railway auto-detects the Dockerfile

## Step 5: Add PostgreSQL database

1. In your Railway project, click "+ New"
2. Select "Database" -> "PostgreSQL"
3. Railway creates a PostgreSQL instance automatically
4. It sets `DATABASE_URL` environment variable automatically

## Step 6: Configure environment variables

In Railway dashboard -> your service -> Variables tab, add:

```
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=${{Postgres.DATABASE_URL}}
DATABASE_SYNC_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=generate-a-random-64-char-string-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=["*"]
MIDAS_MODEL_TYPE=MiDaS_small
CONFIDENCE_THRESHOLD=0.5
UPLOAD_DIR=uploads
MAX_UPLOAD_SIZE_MB=20
```

IMPORTANT: For DATABASE_URL, Railway's PostgreSQL gives you a URL like:
  postgresql://user:pass@host:port/dbname

But our app needs TWO versions:
  - DATABASE_URL: add "+asyncpg" after postgresql
    postgresql+asyncpg://user:pass@host:port/dbname
  - DATABASE_SYNC_URL: use as-is
    postgresql://user:pass@host:port/dbname

You can do this in Railway Variables by referencing the Postgres variable
and manually editing, or set them directly.

## Step 7: Fix DATABASE_URL for asyncpg

Railway's Postgres plugin sets DATABASE_URL as:
  postgresql://...

Our async SQLAlchemy needs:
  postgresql+asyncpg://...

In Railway Variables, set:
  DATABASE_URL = (copy from Postgres, add +asyncpg after postgresql)
  DATABASE_SYNC_URL = (copy from Postgres, use as-is)

## Step 8: Deploy

Railway auto-deploys when you push to GitHub.
Check the deployment logs in Railway dashboard.

You should see:
  - Docker build completing
  - "StreetSense is ready" in logs
  - Green checkmark on deployment

## Step 9: Get your URL

Railway gives you a URL like:
  https://streetsense-production-xxxx.up.railway.app

Open it -- you should see the login page!

## Step 10: Create admin user

1. Sign up through the UI
2. Open Railway's PostgreSQL plugin
3. Click "Query" tab
4. Run: UPDATE users SET role='ADMIN' WHERE email='your@email.com';

---

## Troubleshooting

### "Application failed to respond"
- Check logs in Railway dashboard
- Likely DATABASE_URL format issue (needs +asyncpg)

### AI detection returns 503
- Weights file not found
- Upload best.pt via Git LFS or Railway volume
- Or set MIDAS_MODEL_TYPE=MiDaS_small for smaller memory footprint

### Memory issues
- Railway free tier has 512MB RAM
- YOLOv8s + MiDaS_small needs ~1.5GB
- Upgrade to Developer plan ($5/mo) for 8GB RAM

### Database connection refused
- Make sure PostgreSQL service is running in Railway
- Check DATABASE_URL variable is set correctly

---

## Architecture on Railway

```
Railway Project
  |
  +-- Web Service (Dockerfile)
  |     - FastAPI backend
  |     - React frontend (static files)
  |     - AI models (YOLO + MiDaS)
  |     - Port: $PORT (auto-assigned)
  |
  +-- PostgreSQL Database
        - Auto-provisioned
        - DATABASE_URL injected
```
