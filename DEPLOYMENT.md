# Betfair File Parser v3.0 - Deployment Guide

**Complete step-by-step instructions for deploying to production**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Testing](#local-testing)
3. [Backend Deployment (Google Cloud Run)](#backend-deployment-google-cloud-run)
4. [Frontend Deployment (Cloudflare Pages)](#frontend-deployment-cloudflare-pages)
5. [Google Cloud Storage Setup](#google-cloud-storage-setup)
6. [Environment Configuration](#environment-configuration)
7. [CI/CD Pipeline](#cicd-pipeline)
8. [Post-Deployment Verification](#post-deployment-verification)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts & Tools

1. **Google Cloud Project**
   - Active Google Cloud account
   - Project with Cloud Run API enabled
   - Service account with appropriate permissions

2. **Cloudflare Account**
   - Active Cloudflare account
   - Domain registered and configured
   - Pages enabled in your Cloudflare account

3. **Local Tools**
   ```bash
   # Google Cloud SDK
   curl https://sdk.cloud.google.com | bash
   exec -l $SHELL
   gcloud init
   
   # Docker
   # Install from https://www.docker.com/products/docker-desktop
   
   # GitHub CLI (for CI/CD)
   brew install gh  # macOS
   # or download from https://cli.github.com
   ```

### Verify Installations

```bash
gcloud --version
docker --version
npm --version
node --version
```

---

## Local Testing

### Test Backend Locally

1. **Build Backend Image**
   ```bash
   docker build -f Dockerfile.backend -t betfair-parser-backend:latest .
   ```

2. **Run Backend Container**
   ```bash
   docker run -d \
     --name betfair-parser-backend \
     -p 8000:8000 \
     -v $(pwd)/storage:/app/storage \
     betfair-parser-backend:latest
   ```

3. **Test Endpoints**
   ```bash
   # Health check
   curl http://localhost:8000/health
   
   # System status
   curl http://localhost:8000/api/system-status
   
   # API docs
   open http://localhost:8000/docs
   ```

4. **Stop Container**
   ```bash
   docker stop betfair-parser-backend
   docker rm betfair-parser-backend
   ```

### Test Full Stack Locally

1. **Run Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Access Services**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000
   - Backend Docs: http://localhost:8000/docs

3. **Test Workflow**
   - Upload test file
   - Parse file
   - Export data
   - Verify results

4. **Stop Stack**
   ```bash
   docker-compose down -v
   ```

---

## Backend Deployment (Google Cloud Run)

### Step 1: Prepare Google Cloud Project

1. **Set Project Variables**
   ```bash
   export PROJECT_ID="your-gcp-project-id"
   export REGION="us-central1"
   export SERVICE_NAME="betfair-parser-backend"
   
   gcloud config set project $PROJECT_ID
   ```

2. **Enable Required APIs**
   ```bash
   gcloud services enable \
     run.googleapis.com \
     cloudbuild.googleapis.com \
     containerregistry.googleapis.com \
     storage-api.googleapis.com
   ```

3. **Create Cloud Storage Bucket** (for persistent storage)
   ```bash
   gsutil mb -l $REGION gs://${PROJECT_ID}-betfair-parser/
   ```

### Step 2: Configure Service Account

1. **Create Service Account**
   ```bash
   gcloud iam service-accounts create betfair-parser \
     --display-name="Betfair Parser Service Account"
   ```

2. **Grant Permissions**
   ```bash
   # Cloud Run permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member=serviceAccount:betfair-parser@${PROJECT_ID}.iam.gserviceaccount.com \
     --role=roles/run.invoker
   
   # Cloud Storage permissions
   gcloud projects add-iam-policy-binding $PROJECT_ID \
     --member=serviceAccount:betfair-parser@${PROJECT_ID}.iam.gserviceaccount.com \
     --role=roles/storage.objectAdmin
   ```

### Step 3: Build and Push Backend Image

1. **Configure Docker Authentication**
   ```bash
   gcloud auth configure-docker gcr.io
   ```

2. **Build Image**
   ```bash
   docker build \
     -f Dockerfile.backend \
     -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest \
     -t gcr.io/${PROJECT_ID}/${SERVICE_NAME}:v1.0.0 \
     .
   ```

3. **Push to Container Registry**
   ```bash
   docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest
   docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME}:v1.0.0
   ```

4. **Verify Push**
   ```bash
   gcloud container images list --repository=gcr.io/${PROJECT_ID}
   gcloud container images describe gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest
   ```

### Step 4: Deploy to Cloud Run

1. **Create Cloud Run Service**
   ```bash
   gcloud run deploy $SERVICE_NAME \
     --image=gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest \
     --platform=managed \
     --region=$REGION \
     --memory=2Gi \
     --cpu=2 \
     --timeout=300 \
     --max-instances=100 \
     --allow-unauthenticated \
     --service-account=betfair-parser@${PROJECT_ID}.iam.gserviceaccount.com \
     --set-env-vars="ENV=production,GCP_PROJECT=${PROJECT_ID}"
   ```

2. **Get Service URL**
   ```bash
   BACKEND_URL=$(gcloud run services describe $SERVICE_NAME \
     --platform managed \
     --region $REGION \
     --format 'value(status.url)')
   
   echo "Backend URL: $BACKEND_URL"
   ```

3. **Test Deployed Backend**
   ```bash
   curl $BACKEND_URL/health
   curl $BACKEND_URL/api/system-status
   ```

### Step 5: Configure Persistent Storage

1. **Mount Cloud Storage Bucket**
   
   Update `backend/main.py` to use Google Cloud Storage:
   ```python
   from google.cloud import storage
   
   # Initialize storage client
   storage_client = storage.Client()
   bucket = storage_client.bucket(f"{os.getenv('GCP_PROJECT')}-betfair-parser")
   ```

2. **Update Environment Variables**
   ```bash
   gcloud run services update $SERVICE_NAME \
     --update-env-vars="GCS_BUCKET=${PROJECT_ID}-betfair-parser"
   ```

---

## Frontend Deployment (Cloudflare Pages)

### Option 1: GitHub Integration (Recommended)

1. **Push Code to GitHub**
   ```bash
   git remote add origin https://github.com/charles-ascot/intakehub-v3
   git branch -M main
   git push -u origin main
   ```

2. **Connect to Cloudflare Pages**
   - Log in to Cloudflare dashboard
   - Navigate to "Pages"
   - Click "Connect to Git"
   - Authorize GitHub
   - Select `charles-ascot/intakehub-v3` repository
   - Click "Begin setup"

3. **Configure Build Settings**
   - **Framework preset**: React
   - **Build command**: `npm install && npm run build`
   - **Build output directory**: `build`
   - **Root directory**: `frontend`

4. **Set Environment Variables**
   - Click "Environment variables"
   - Add production variables:
     ```
     REACT_APP_API_URL = https://your-backend.run.app/api
     NODE_ENV = production
     ```

5. **Deploy**
   - Click "Save and deploy"
   - Cloudflare automatically deploys on every push to main

### Option 2: Manual Deployment

1. **Build Frontend**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

2. **Install Wrangler CLI**
   ```bash
   npm install -g wrangler
   wrangler login
   ```

3. **Create `wrangler.toml`**
   ```toml
   name = "betfair-parser-frontend"
   type = "javascript"
   account_id = "your-account-id"
   workers_dev = true
   route = ""
   zone_id = ""
   
   [env.production]
   name = "betfair-parser-frontend"
   route = "https://youromain.com/*"
   zone_id = "your-zone-id"
   ```

4. **Deploy**
   ```bash
   wrangler pages publish frontend/build
   ```

5. **Update Custom Domain**
   - In Cloudflare dashboard: Pages → Custom domains
   - Add your domain
   - Configure DNS records

### Step 2: Configure CORS for API Requests

In Cloudflare dashboard:

1. **Add WAF Rule** (if needed)
   - Navigate to Security → WAF
   - Add custom rule to allow your frontend domain

2. **Configure Page Rules**
   - Pages → Settings → Build & deployment
   - Environment variables already set above

### Step 3: Set Production API URL

Update `frontend/.env.production`:
```
REACT_APP_API_URL=https://betfair-parser-backend-xxxx.run.app/api
```

Or set in Cloudflare Pages dashboard:
- Settings → Environment variables
- Production: `REACT_APP_API_URL=https://your-backend.run.app/api`

---

## Google Cloud Storage Setup

### Create Storage Integration (Optional but Recommended)

1. **Create Buckets**
   ```bash
   # Raw data bucket
   gsutil mb -l $REGION gs://${PROJECT_ID}-betfair-raw/
   
   # Processed data bucket
   gsutil mb -l $REGION gs://${PROJECT_ID}-betfair-processed/
   
   # Export bucket
   gsutil mb -l $REGION gs://${PROJECT_ID}-betfair-exports/
   ```

2. **Set Bucket Permissions**
   ```bash
   # Grant service account access
   gsutil iam ch serviceAccount:betfair-parser@${PROJECT_ID}.iam.gserviceaccount.com:objectViewer gs://${PROJECT_ID}-betfair-raw
   gsutil iam ch serviceAccount:betfair-parser@${PROJECT_ID}.iam.gserviceaccount.com:objectCreator gs://${PROJECT_ID}-betfair-processed
   ```

3. **Enable Lifecycle Policies** (Optional)
   ```bash
   # Auto-delete old uploads after 30 days
   gsutil lifecycle set - gs://${PROJECT_ID}-betfair-raw <<'EOF'
   {
     "lifecycle": {
       "rule": [
         {
           "action": {"type": "Delete"},
           "condition": {"age": 30}
         }
       ]
     }
   }
   EOF
   ```

### Update Backend to Use Cloud Storage

Modify `backend/main.py`:

```python
import os
from google.cloud import storage

class CloudStorageManager:
    def __init__(self):
        self.client = storage.Client()
        self.bucket = self.client.bucket(
            os.getenv('GCS_BUCKET', f"{os.getenv('GCP_PROJECT')}-betfair-parser")
        )
    
    async def upload_file(self, filename: str, content: bytes):
        blob = self.bucket.blob(f"uploads/{filename}")
        blob.upload_from_string(content)
    
    async def download_file(self, filename: str) -> bytes:
        blob = self.bucket.blob(f"exports/{filename}")
        return blob.download_as_bytes()
```

---

## Environment Configuration

### Backend Environment Variables

**Development** (`.env`):
```bash
ENV=development
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
LOG_LEVEL=INFO
```

**Production** (Cloud Run):
```bash
gcloud run services update betfair-parser-backend \
  --update-env-vars="ENV=production,LOG_LEVEL=WARNING,GCP_PROJECT=${PROJECT_ID}"
```

### Frontend Environment Variables

**Development** (`frontend/.env`):
```bash
REACT_APP_API_URL=http://localhost:8000/api
REACT_APP_ENV=development
```

**Production** (Cloudflare Pages):
```bash
REACT_APP_API_URL=https://betfair-parser-backend-xxxx.run.app/api
REACT_APP_ENV=production
```

---

## CI/CD Pipeline

### GitHub Actions Setup

1. **Create `.github/workflows/deploy.yml`**
   ```yaml
   name: Deploy Betfair Parser

   on:
     push:
       branches: [ main ]

   env:
     PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
     REGION: us-central1

   jobs:
     deploy-backend:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         - name: Set up Cloud SDK
           uses: google-github-actions/setup-gcloud@v1
           with:
             project_id: ${{ env.PROJECT_ID }}
             service_account_key: ${{ secrets.GCP_SA_KEY }}
             export_default_credentials: true
         
         - name: Configure Docker
           run: gcloud auth configure-docker gcr.io
         
         - name: Build Backend
           run: |
             docker build -f Dockerfile.backend \
               -t gcr.io/$PROJECT_ID/betfair-parser-backend:latest \
               -t gcr.io/$PROJECT_ID/betfair-parser-backend:$GITHUB_SHA \
               .
         
         - name: Push Backend
           run: |
             docker push gcr.io/$PROJECT_ID/betfair-parser-backend:latest
             docker push gcr.io/$PROJECT_ID/betfair-parser-backend:$GITHUB_SHA
         
         - name: Deploy to Cloud Run
           run: |
             gcloud run deploy betfair-parser-backend \
               --image=gcr.io/$PROJECT_ID/betfair-parser-backend:latest \
               --platform=managed \
               --region=$REGION \
               --allow-unauthenticated

     deploy-frontend:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v3
         
         - name: Build Frontend
           run: |
             cd frontend
             npm install
             npm run build
         
         - name: Deploy to Cloudflare Pages
           uses: cloudflare/pages-action@v1
           with:
             apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
             accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
             projectName: betfair-parser
             directory: frontend/build
   ```

2. **Add Secrets to GitHub**
   ```bash
   gh secret set GCP_PROJECT_ID --body "your-project-id"
   gh secret set GCP_SA_KEY --body "$(cat /path/to/service-account-key.json)"
   gh secret set CLOUDFLARE_API_TOKEN --body "your-api-token"
   gh secret set CLOUDFLARE_ACCOUNT_ID --body "your-account-id"
   ```

---

## Post-Deployment Verification

### Test Backend

```bash
# Replace with your actual URL
BACKEND_URL="https://betfair-parser-backend-xxxx.run.app"

# Health check
curl $BACKEND_URL/health

# System status
curl $BACKEND_URL/api/system-status

# Upload test file
curl -X POST $BACKEND_URL/api/upload \
  -F "files=@test-data.bz2"

# API documentation
open $BACKEND_URL/docs
```

### Test Frontend

```bash
# Navigate to your Cloudflare Pages URL
open https://betfair-parser.pages.dev

# Test workflow:
# 1. Upload test file
# 2. Parse file
# 3. Export data
# 4. Check console for errors
```

### Monitor Deployment

**Google Cloud Run**:
```bash
# View logs
gcloud run services describe betfair-parser-backend \
  --region us-central1

# Stream logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=betfair-parser-backend" \
  --limit 50 \
  --format json
```

**Cloudflare Pages**:
- Dashboard → Pages → betfair-parser → Deployments
- View real-time logs and performance metrics

---

## Troubleshooting

### Cloud Run Issues

**Issue**: Container won't start
```bash
# Check logs
gcloud run services describe betfair-parser-backend --region us-central1

# Rebuild with verbose output
docker build -f Dockerfile.backend --progress=plain .
```

**Issue**: Out of memory
```bash
# Increase memory
gcloud run services update betfair-parser-backend \
  --memory=4Gi \
  --region us-central1
```

**Issue**: Timeout during parsing
```bash
# Increase timeout
gcloud run services update betfair-parser-backend \
  --timeout=600 \
  --region us-central1
```

### Cloudflare Pages Issues

**Issue**: Build fails
- Check build output in Cloudflare dashboard
- Verify `package.json` has correct build script
- Ensure environment variables are set correctly

**Issue**: API calls return CORS errors
- Update `REACT_APP_API_URL` in Cloudflare Pages environment variables
- Ensure backend allows cross-origin requests

**Issue**: Blank page after deploy
- Check browser console (DevTools) for JavaScript errors
- Verify React build was successful: `npm run build`
- Check network requests to ensure API connectivity

### General Debugging

**Enable detailed logging**:
```bash
# Backend
gcloud run services update betfair-parser-backend \
  --update-env-vars="LOG_LEVEL=DEBUG"

# View logs in real-time
gcloud logging tail "resource.type=cloud_run_revision" --limit=50
```

**Test connectivity**:
```bash
# Test backend from frontend
curl -v https://your-backend.run.app/api/system-status

# Test CORS
curl -v -H "Origin: https://your-frontend.pages.dev" \
  https://your-backend.run.app/api/system-status
```

---

## Rollback Procedures

### Rollback Backend

```bash
# View deployment history
gcloud run services describe betfair-parser-backend --region us-central1

# Deploy previous version
gcloud run deploy betfair-parser-backend \
  --image=gcr.io/$PROJECT_ID/betfair-parser-backend:v1.0.0 \
  --region us-central1
```

### Rollback Frontend

In Cloudflare Pages dashboard:
- Pages → betfair-parser → Deployments
- Click previous deployment
- Select "Rollback to this deployment"

---

## Performance Optimization

### Scale Backend

```bash
# Increase max instances
gcloud run services update betfair-parser-backend \
  --max-instances=200 \
  --region us-central1

# Increase concurrent requests
gcloud run services update betfair-parser-backend \
  --concurrency=80 \
  --region us-central1
```

### Cache Frontend

Cloudflare Pages automatically caches:
- All `.js` and `.css` files (with cache busting)
- Images and media
- HTML (with short TTL for updates)

Additional caching configuration in `_headers` file (frontend/public/):
```
/*
  Cache-Control: public, max-age=3600
```

---

## Cost Optimization

### Google Cloud Run

- Pay only for invocations
- Typical cost: $0.40 per million requests + compute time
- Estimated monthly: $10-50 depending on usage

### Cloudflare Pages

- Free tier includes 500 builds/month
- Unlimited bandwidth
- No egress charges

### Google Cloud Storage

- Storage: $0.023 per GB/month
- Estimated: $2-10/month for typical usage

---

## Monitoring & Alerts

### Set Up Cloud Monitoring

```bash
# Create uptime check
gcloud monitoring uptime-checks create \
  --display-name="Betfair Parser Health" \
  --http-check-path="/health" \
  --monitored-resource-uri="https://your-backend.run.app/health"

# Create alert policy
gcloud alpha monitoring policies create \
  --notification-channels="YOUR_CHANNEL_ID" \
  --display-name="Backend Error Rate" \
  --condition-display-name="5xx errors"
```

### Cloudflare Analytics

- Pages → betfair-parser → Analytics Engine
- View requests, errors, performance metrics

---

## Success Checklist

- [ ] Backend successfully deployed to Cloud Run
- [ ] Frontend deployed to Cloudflare Pages
- [ ] API endpoints responding with correct data
- [ ] File upload/parse/export workflow working
- [ ] Performance acceptable (<1s response times)
- [ ] No console errors in browser
- [ ] CORS configured correctly
- [ ] Environment variables set in both services
- [ ] Monitoring and alerts configured
- [ ] Backups and storage configured

---

## Next Steps

1. **Connect to database** (optional)
   - Set up Firestore for persistent state
   - Store processing history

2. **Add authentication** (optional)
   - Implement Google Cloud IAM
   - Add user management

3. **Expand API** 
   - Add more export formats
   - Implement real-time streaming

4. **Scale infrastructure**
   - Set up load balancing
   - Configure auto-scaling policies

---

**Last Updated**: January 5, 2026  
**Questions?** Check the main README.md or review detailed logs in Google Cloud Console
