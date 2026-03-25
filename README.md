# StreetSense — AI-Powered Road Monitoring & Smart Complaint Management System

## Overview

StreetSense is a cloud-based intelligent road infrastructure monitoring system that uses
computer vision (YOLOv8 + MiDaS depth estimation) to detect road hazards — potholes, cracks,
garbage, and open manholes — estimate their severity using depth-aware analysis, and route
complaints to the appropriate municipal authorities.

## Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────────┐
│   Frontend   │───▶│   FastAPI    │───▶│   PostgreSQL     │
│  React+Vite  │    │   Backend    │    │   Database       │
└──────────────┘    └──────┬───────┘    └──────────────────┘
                           │
                    ┌──────┴───────┐
                    │  AI Pipeline │
                    │  YOLOv8 +    │
                    │  MiDaS       │
                    └──────────────┘
```

## Tech Stack

| Layer     | Technology                         |
|-----------|------------------------------------|
| AI        | YOLOv8, MiDaS (PyTorch), OpenCV   |
| Backend   | FastAPI, SQLAlchemy, Alembic       |
| Database  | PostgreSQL                         |
| Frontend  | React 18, Vite, Leaflet, Tailwind  |
| DevOps    | Docker, Docker Compose             |

## Quick Start

```bash
# Clone
git clone <repo-url> && cd streetsense

# Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install && npm run dev
```

## Project Phases

- [x] Phase 1: Project Setup
- [ ] Phase 2: AI Model Setup (YOLOv8)
- [ ] Phase 3: Depth Estimation (MiDaS)
- [ ] Phase 4: Inference Pipeline
- [ ] Phase 5: Severity Estimation
- [ ] Phase 6: Backend Development
- [ ] Phase 7: Geo-Tagging & Routing
- [ ] Phase 8: Complaint Lifecycle
- [ ] Phase 9: Feed Simulation
- [ ] Phase 10: Frontend (React)
- [ ] Phase 11: Notifications

## License

MIT
