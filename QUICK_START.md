# Betfair File Parser v3.0 - Quick Start Guide

**Get started in 5 minutes**

---

## Option A: Docker (Recommended)

```bash
# 1. Clone and navigate to project
git clone https://github.com/charles-ascot/intakehub-v3
cd betfair-parser-v3

# 2. Start all services
docker-compose up --build

# 3. Access application
# Frontend: http://localhost:3000
# Backend: http://localhost:8000
# API Docs: http://localhost:8000/docs

# 4. Stop services (Ctrl+C), then:
docker-compose down
```

---

## Option B: Local Development

### Backend Setup

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run server
python main.py
# Or with auto-reload: uvicorn main:app --reload

# Server runs on http://localhost:8000
```

### Frontend Setup (New Terminal)

```bash
# 1. Navigate to frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Run development server
npm start

# Frontend opens at http://localhost:3000
```

---

## Test the Application

### Upload & Parse Test File

1. **Create test data file** (or use existing Betfair data):
   ```bash
   # Create simple NDJSON test file
   cat > test_data.ndjson << 'EOF'
   {"marketId":"1.123456","marketName":"Test Market","runners":[{"selectionId":123,"name":"Horse 1"}]}
   {"marketId":"1.123456","type":"mc","marketDefinition":{"runners":[{"status":"ACTIVE","id":123}]}}
   EOF
   
   # Compress it
   bzip2 test_data.ndjson  # Creates test_data.ndjson.bz2
   ```

2. **Upload via UI**:
   - Go to http://localhost:3000
   - Click "Select Files"
   - Choose `test_data.ndjson.bz2`
   - Click "Upload Files"

3. **Parse the file**:
   - Click "Parse Files"
   - Monitor progress (takes <1s for test file)

4. **Export data**:
   - Select "JSON" format
   - Click "Export Selected"
   - Download or view results

---

## Project Structure

```
betfair-parser-v3/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt      # Python dependencies
│   └── storage/             # File cache (created on startup)
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # Main component
│   │   ├── App.css          # Styles
│   │   ├── components/      # React components
│   │   └── index.jsx        # Entry point
│   ├── public/
│   │   └── index.html       # HTML template
│   ├── package.json         # NPM config
│   └── .env                 # Environment variables
│
├── docker-compose.yml       # Local dev setup
├── Dockerfile.backend       # Backend container
├── Dockerfile.frontend      # Frontend container
├── README.md               # Full documentation
├── DEPLOYMENT.md           # Production deployment
└── QUICK_START.md         # This file
```

---

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/api/system-status` | GET | System metrics |
| `/api/upload` | POST | Upload files |
| `/api/uploaded-files` | GET | List uploaded files |
| `/api/parse` | POST | Parse files |
| `/api/parsed-files` | GET | List parsed files |
| `/api/export` | POST | Export data |
| `/api/cache/clear-*` | POST | Clear caches |

Full API docs: http://localhost:8000/docs

---

## Common Tasks

### View Backend Logs
```bash
# With docker-compose
docker-compose logs -f backend

# Local development
# Logs print to terminal where you ran `python main.py`
```

### View Frontend Console
- Open browser DevTools (F12)
- Click "Console" tab
- Look for errors or API issues

### Clear Cache
```bash
# Via API
curl -X POST http://localhost:8000/api/cache/clear-uploaded
curl -X POST http://localhost:8000/api/cache/clear-parsed
curl -X POST http://localhost:8000/api/cache/clear-exported

# Or via UI
# Click "Clear Cache" buttons in Overview panel
```

### Reset Everything
```bash
# With Docker
docker-compose down -v
docker-compose up --build

# Locally
rm -rf storage/  # Delete file cache
```

---

## Troubleshooting

**"Cannot connect to API"**
- Ensure backend is running: `docker ps` or `python main.py`
- Check if port 8000 is available
- Verify `REACT_APP_API_URL` is correct

**"Parse failed"**
- Check file format (BZ2, GZ, TAR, ZIP, JSON supported)
- Verify file contains valid Betfair NDJSON data
- Check backend logs for specific error

**"Upload fails"**
- Check file size (should be <2GB for typical usage)
- Verify disk space in storage directory
- Check backend memory availability

**"Port already in use"**
```bash
# Find process using port 3000 or 8000
lsof -i :3000
lsof -i :8000

# Kill process (replace 12345 with PID)
kill -9 12345

# Or change ports
docker-compose up -e "BACKEND_PORT=8001" "FRONTEND_PORT=3001"
```

---

## Performance Tips

- **Large files**: Increase backend memory and timeout
- **Multiple files**: Use batch processing (parse 10+ files at once)
- **Frequent uploads**: Monitor storage directory size
- **Export speed**: CSV/Parquet faster than JSON for large datasets

---

## Next Steps

1. **Review full documentation**: `README.md`
2. **Deploy to production**: `DEPLOYMENT.md`
3. **Understand architecture**: `ARCHITECTURE.md`
4. **Explore API**: http://localhost:8000/docs

---

## Support

- **API Issues**: Check http://localhost:8000/docs
- **UI Issues**: Check browser DevTools console
- **Docker Issues**: Run `docker-compose logs`
- **Git Issues**: Review `.gitignore` and branch strategy

---

**Ready to start?** Run `docker-compose up` and navigate to http://localhost:3000

Good luck! 🚀
