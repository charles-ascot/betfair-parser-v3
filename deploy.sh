#!/bin/bash

# Betfair File Parser v3.0 - Deployment Script
# Deploys backend to Cloud Run and frontend to Cloudflare Pages

set -e

PROJECT_ID="betfair-file-parser"
REGION="australia-southeast1"
SERVICE_NAME="betfair-parser-api"
GCS_BUCKET="${PROJECT_ID}.appspot.com"

echo "========================================"
echo "Betfair File Parser v3.0 - Deployment"
echo "========================================"

# Check if gcloud is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null 2>&1; then
    echo "Please authenticate with gcloud first:"
    echo "  gcloud auth login"
    exit 1
fi

# Set project
echo ""
echo "Setting GCP project to: $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo ""
echo "Enabling required APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    firestore.googleapis.com \
    storage.googleapis.com \
    --quiet

# Initialize Firebase (if not already done)
echo ""
echo "Setting up Firebase..."
if ! firebase projects:list | grep -q "$PROJECT_ID"; then
    echo "Adding Firebase to project..."
    firebase projects:addfirebase $PROJECT_ID || true
fi

# Deploy Firebase Storage rules
echo ""
echo "Deploying Firebase Storage rules..."
firebase deploy --only storage --project $PROJECT_ID || echo "Storage rules may need manual setup"

# Deploy Firestore rules
echo ""
echo "Deploying Firestore rules..."
firebase deploy --only firestore --project $PROJECT_ID || echo "Firestore rules may need manual setup"

# Create storage bucket if not exists
echo ""
echo "Setting up Cloud Storage bucket..."
gsutil mb -p $PROJECT_ID -l $REGION gs://$GCS_BUCKET 2>/dev/null || echo "Bucket already exists"
gsutil cors set cors.json gs://$GCS_BUCKET 2>/dev/null || true

# Build and deploy backend to Cloud Run
echo ""
echo "Building and deploying backend to Cloud Run..."
cd backend

gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --set-env-vars="USE_FIREBASE=true,GCS_BUCKET=$GCS_BUCKET,GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --memory 1Gi \
    --timeout 300 \
    --concurrency 80

# Get the Cloud Run URL
BACKEND_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)")
echo ""
echo "Backend deployed to: $BACKEND_URL"

cd ..

# Update frontend with backend URL
echo ""
echo "Updating frontend configuration..."
cat > frontend/.env.production << EOF
REACT_APP_API_URL=${BACKEND_URL}/api
EOF

# Build frontend for Cloudflare
echo ""
echo "Building frontend..."
cd frontend
npm ci --legacy-peer-deps
npm run build
cd ..

echo ""
echo "========================================"
echo "Deployment Complete!"
echo "========================================"
echo ""
echo "Backend API: $BACKEND_URL"
echo "API Docs: $BACKEND_URL/docs"
echo ""
echo "Next steps for Cloudflare Pages:"
echo "1. Go to https://dash.cloudflare.com"
echo "2. Create a new Pages project"
echo "3. Connect your repository OR upload frontend/build folder"
echo "4. Set build command: npm run build"
echo "5. Set output directory: build"
echo "6. Add environment variable: REACT_APP_API_URL=$BACKEND_URL/api"
echo ""
echo "Or deploy via Wrangler CLI:"
echo "  cd frontend && npx wrangler pages deploy build --project-name=betfair-parser"
echo ""
