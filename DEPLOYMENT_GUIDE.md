# 🚀 Samanvay SIH 2026 - Deployment Guide

This guide will help you deploy your Samanvay project to get a live URL for your PPT presentation.

## ✅ Prerequisites
1. GitHub account
2. Render.com account (free tier)
3. Your code pushed to GitHub

## 📋 Step-by-Step Deployment

### Step 1: Push Code to GitHub
```bash
# If not already done:
git init
git add .
git commit -m "Initial commit: Samanvay SIH 2026 project"
git branch -M main
git remote add origin https://github.com/yourusername/sih2.git
git push -u origin main
```

### Step 2: Deploy to Render.com

#### Option A: Using render.yaml (Recommended)
1. Go to [Render.com](https://render.com) and sign in with GitHub
2. Click "New" → "Blueprint from repo"
3. Select your `sih2` repository
4. Render will auto-detect `render.yaml` and create:
   - Backend service (FastAPI)
   - Frontend service (React/Vite)
   - PostgreSQL database (free tier)
5. Click "Apply Blueprint" → Wait 3-5 minutes for deployment

#### Option B: Manual Service Creation
1. **PostgreSQL Database:**
   - New → PostgreSQL
   - Name: `samanvay-db`
   - Plan: Free
   - Create

2. **Backend Service:**
   - New → Web Service
   - Connect your GitHub repo
   - Name: `samanvay-backend`
   - Environment: Docker
   - Build Command: (leave empty)
   - Start Command: (leave empty)
   - Dockerfile: `backend/Dockerfile`
   - Environment:
     ```
     SAMANVAY_DATABASE_URL: [from your postgres db connection string]
     SAMANVAY_CORS_ORIGINS: https://samanvay-frontend.onrender.com
     ```

3. **Frontend Service:**
   - New → Web Service
   - Connect your GitHub repo
   - Name: `samanvay-frontend`
   - Environment: Docker
   - Build Command: (leave empty)
   - Start Command: (leave empty)
   - Dockerfile: `frontend/Dockerfile`
   - Environment:
     ```
     VITE_API_BASE: https://samanvay-backend.onrender.com/api
     ```
   - Under "Advanced": Add dependency on `samanvay-backend`

### Step 3: Get Your Live URL
After deployment (3-5 minutes):
- **Frontend URL:** `https://samanvay-frontend.onrender.com` ← **USE THIS IN YOUR PPT**
- **Backend API:** `https://samanvay-backend.onrender.com`
- **API Docs:** `https://samanvay-backend.onrender.com/docs`

### Step 4: Test Your Deployment
1. Visit your frontend URL
2. Verify the dashboard loads showing: 
   - "1,274 → 435" material code reduction
   - Precision: 90.2%, Recall: 80.5%, F1: 85.1%
3. Try the "Ingest & Run" button to re-run pipeline
4. Check "Review Queue" and "Families" pages

## 🔧 Troubleshooting

### If you see "Connection refused" or 502 errors:
1. Check Render dashboard for service logs
2. Ensure backend is healthy before frontend starts
3. Verify environment variables are set correctly
4. Wait 1-2 minutes after backend deploy before frontend

### If data doesn't persist:
- Free Render PostgreSQL persists data between restarts
- The `seed_db.py` script runs on backend startup (check logs)
- Data should remain until you manually delete the database

## 📝 For Your PPT Slide
```
Live Demo: https://samanvay-frontend.onrender.com

Samanvay - AI-Driven Material Code Standardization
• 1,274 → 435 codes (65.9% reduction)
• Precision: 90.2% | Recall: 80.5% | F1: 85.1%
• Deployed on Render.com (Free Tier)
• Tech: React/Vite + FastAPI + PostgreSQL + pgvector
```

## ⏱️ Time Estimate
- Pushing to GitHub: 2 minutes
- Render setup: 5 minutes  
- Deployment build: 3-5 minutes
- **Total: ~10-12 minutes** to have a live URL

## 💡 Pro Tips
1. **First load may be slow** (free services spin down after 15 min inactivity)
2. **Have backup screenshots** ready just in case
3. **Test the link** 10 minutes before your presentation
4. **Note in PPT:** "Demo may take 10-15 seconds to load on first visit"

---

**Ready to deploy?** Follow these steps and you'll have a live URL for your judges in under 15 minutes!