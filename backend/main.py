"""
Betfair File Parser v3.0 - FastAPI Backend
Professional financial data parsing utility for Betfair historical racing data
Part of Chimera Intake Hub 3.0 - Ascot Wealth Management
"""

import os
import json
import bz2
import gzip
import tarfile
import zipfile
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import aiofiles
import pandas as pd
import orjson

# Firebase imports
from google.cloud import storage as gcs
from google.cloud import firestore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment
USE_FIREBASE = os.getenv("USE_FIREBASE", "false").lower() == "true"
GCS_BUCKET = os.getenv("GCS_BUCKET", "betfair-parser-files")
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT", "betfair-file-parser")


# ============================================================================
# DATA MODELS
# ============================================================================

class CacheStatus(BaseModel):
    """Cache status information"""
    uploaded_files_count: int
    uploaded_files_size_mb: float
    parsed_files_count: int
    parsed_files_size_mb: float
    exported_files_count: int
    exported_files_size_mb: float


class SystemStatus(BaseModel):
    """System status information"""
    api_status: str = "online"
    app_health: str = "normal"
    storage_backend: str = "local"
    cache_status: CacheStatus


class ParseRequest(BaseModel):
    """Parse request parameters"""
    files: Optional[List[str]] = None


class ExportRequest(BaseModel):
    """Export request parameters"""
    files: List[str]
    format: str = "json"
    include_metadata: bool = True


# ============================================================================
# STORAGE MANAGER - Supports Local and Firebase Storage
# ============================================================================

class StorageManager:
    """Manages file storage - supports local and Firebase Storage"""

    def __init__(self, use_firebase: bool = False):
        self.use_firebase = use_firebase

        if use_firebase:
            self.gcs_client = gcs.Client()
            self.bucket = self.gcs_client.bucket(GCS_BUCKET)
            self.db = firestore.Client()
            logger.info(f"Using Firebase Storage: {GCS_BUCKET}")
        else:
            self.storage_path = Path("./storage")
            self.uploaded_path = self.storage_path / "uploaded"
            self.parsed_path = self.storage_path / "parsed"
            self.exported_path = self.storage_path / "exported"

            for path in [self.uploaded_path, self.parsed_path, self.exported_path]:
                path.mkdir(parents=True, exist_ok=True)
            logger.info("Using local file storage")

    def _get_prefix(self, category: str) -> str:
        return f"{category}/"

    async def save_file(self, category: str, filename: str, content: bytes) -> bool:
        """Save file to storage"""
        try:
            if self.use_firebase:
                blob = self.bucket.blob(f"{category}/{filename}")
                blob.upload_from_string(content)
                # Store metadata in Firestore
                self.db.collection("files").document(f"{category}_{filename}").set({
                    "filename": filename,
                    "category": category,
                    "size_bytes": len(content),
                    "uploaded_at": datetime.utcnow().isoformat()
                })
            else:
                path = getattr(self, f"{category}_path") / filename
                async with aiofiles.open(path, 'wb') as f:
                    await f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error saving file {filename}: {e}")
            return False

    async def save_file_text(self, category: str, filename: str, content: str) -> bool:
        """Save text file to storage"""
        return await self.save_file(category, filename, content.encode('utf-8'))

    async def read_file(self, category: str, filename: str) -> Optional[bytes]:
        """Read file from storage"""
        try:
            if self.use_firebase:
                blob = self.bucket.blob(f"{category}/{filename}")
                return blob.download_as_bytes()
            else:
                path = getattr(self, f"{category}_path") / filename
                async with aiofiles.open(path, 'rb') as f:
                    return await f.read()
        except Exception as e:
            logger.error(f"Error reading file {filename}: {e}")
            return None

    async def read_file_text(self, category: str, filename: str) -> Optional[str]:
        """Read text file from storage"""
        content = await self.read_file(category, filename)
        return content.decode('utf-8') if content else None

    async def file_exists(self, category: str, filename: str) -> bool:
        """Check if file exists"""
        if self.use_firebase:
            blob = self.bucket.blob(f"{category}/{filename}")
            return blob.exists()
        else:
            path = getattr(self, f"{category}_path") / filename
            return path.exists()

    async def list_files(self, category: str) -> List[Dict[str, Any]]:
        """List files in category"""
        files = []
        try:
            if self.use_firebase:
                blobs = self.bucket.list_blobs(prefix=f"{category}/")
                for blob in blobs:
                    if blob.name != f"{category}/":
                        files.append({
                            "filename": blob.name.split("/")[-1],
                            "size_bytes": blob.size or 0,
                            "size_mb": round((blob.size or 0) / (1024 * 1024), 2),
                            "uploaded_at": blob.updated.isoformat() if blob.updated else ""
                        })
            else:
                path = getattr(self, f"{category}_path")
                for file_path in path.glob("*"):
                    if file_path.is_file():
                        stat = file_path.stat()
                        files.append({
                            "filename": file_path.name,
                            "size_bytes": stat.st_size,
                            "size_mb": round(stat.st_size / (1024 * 1024), 2),
                            "uploaded_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
                        })
        except Exception as e:
            logger.error(f"Error listing files in {category}: {e}")
        return sorted(files, key=lambda x: x.get("uploaded_at", ""), reverse=True)

    async def get_stats(self, category: str) -> Dict[str, Any]:
        """Get storage stats for category"""
        files = await self.list_files(category)
        total_size = sum(f.get("size_bytes", 0) for f in files)
        return {
            "count": len(files),
            "size_mb": round(total_size / (1024 * 1024), 2)
        }

    async def clear_category(self, category: str) -> bool:
        """Clear all files in category"""
        try:
            if self.use_firebase:
                blobs = self.bucket.list_blobs(prefix=f"{category}/")
                for blob in blobs:
                    blob.delete()
                # Clear Firestore metadata
                docs = self.db.collection("files").where("category", "==", category).stream()
                for doc in docs:
                    doc.reference.delete()
            else:
                path = getattr(self, f"{category}_path")
                for file in path.glob("*"):
                    if file.is_file():
                        file.unlink()
            return True
        except Exception as e:
            logger.error(f"Error clearing {category}: {e}")
            return False

    async def get_file_path(self, category: str, filename: str) -> Optional[Path]:
        """Get local file path (for local storage only)"""
        if self.use_firebase:
            return None
        path = getattr(self, f"{category}_path") / filename
        return path if path.exists() else None


# ============================================================================
# BETFAIR DATA PARSER
# ============================================================================

class BetfairDataParser:
    """Handles Betfair data file parsing"""

    @staticmethod
    def decompress_file(file_bytes: bytes, filename: str) -> bytes:
        """Decompress file based on extension"""
        filename_lower = filename.lower()

        if filename_lower.endswith('.bz2'):
            return bz2.decompress(file_bytes)

        if filename_lower.endswith('.gz'):
            return gzip.decompress(file_bytes)

        if filename_lower.endswith('.tar') or filename_lower.endswith('.tar.bz2'):
            try:
                tar = tarfile.open(fileobj=io.BytesIO(file_bytes))
                members = tar.getmembers()
                if members:
                    return tar.extractfile(members[0]).read()
            except Exception as e:
                logger.error(f"Error extracting TAR: {e}")

        if filename_lower.endswith('.zip'):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    if zf.namelist():
                        return zf.read(zf.namelist()[0])
            except Exception as e:
                logger.error(f"Error extracting ZIP: {e}")

        return file_bytes

    @staticmethod
    def parse_ndjson(data: bytes) -> List[Dict[str, Any]]:
        """Parse NDJSON format"""
        records = []
        try:
            lines = data.decode('utf-8').strip().split('\n')
            for line in lines:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        logger.warning(f"Skipping invalid JSON line: {e}")
        except UnicodeDecodeError:
            logger.error("Could not decode file as UTF-8")
        return records

    @staticmethod
    def extract_market_data(records: List[Dict]) -> Dict[str, Any]:
        """Extract and structure market data"""
        markets = {}

        for record in records:
            market_id = record.get('marketId') or record.get('id')
            if not market_id:
                continue

            if market_id not in markets:
                markets[market_id] = {
                    'market_id': market_id,
                    'updates': [],
                    'definition': None
                }

            if 'mc' in record:
                markets[market_id]['updates'].append(record)

            if 'marketDefinition' in record:
                markets[market_id]['definition'] = record['marketDefinition']

        return {
            'market_count': len(markets),
            'record_count': len(records),
            'markets': markets
        }


# ============================================================================
# FASTAPI APPLICATION
# ============================================================================

storage = StorageManager(use_firebase=USE_FIREBASE)
parser = BetfairDataParser()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info(f"Betfair File Parser v3.0 started (Firebase: {USE_FIREBASE})")
    yield
    logger.info("Betfair File Parser v3.0 shutting down")


app = FastAPI(
    title="Betfair File Parser v3.0",
    description="Professional financial data parsing utility for Betfair historical racing data",
    version="3.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# HEALTH & STATUS ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/api/system-status")
async def get_system_status() -> SystemStatus:
    """Get current system status"""
    uploaded_stats = await storage.get_stats("uploaded")
    parsed_stats = await storage.get_stats("parsed")
    exported_stats = await storage.get_stats("exported")

    cache_status = CacheStatus(
        uploaded_files_count=uploaded_stats["count"],
        uploaded_files_size_mb=uploaded_stats["size_mb"],
        parsed_files_count=parsed_stats["count"],
        parsed_files_size_mb=parsed_stats["size_mb"],
        exported_files_count=exported_stats["count"],
        exported_files_size_mb=exported_stats["size_mb"]
    )

    return SystemStatus(
        storage_backend="Firebase" if USE_FIREBASE else "Local",
        cache_status=cache_status
    )


# ============================================================================
# FILE UPLOAD ENDPOINTS
# ============================================================================

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """Upload Betfair data files"""
    upload_results = []

    for file in files:
        try:
            content = await file.read()
            success = await storage.save_file("uploaded", file.filename, content)

            if success:
                upload_results.append({
                    "filename": file.filename,
                    "size_bytes": len(content),
                    "status": "uploaded",
                    "timestamp": datetime.utcnow().isoformat()
                })
                logger.info(f"Uploaded: {file.filename} ({len(content)} bytes)")
            else:
                upload_results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": "Failed to save file"
                })
        except Exception as e:
            logger.error(f"Upload error for {file.filename}: {e}")
            upload_results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })

    return {
        "total": len(files),
        "successful": len([r for r in upload_results if r["status"] == "uploaded"]),
        "results": upload_results
    }


@app.get("/api/uploaded-files")
async def list_uploaded_files() -> List[Dict[str, Any]]:
    """List all uploaded files"""
    return await storage.list_files("uploaded")


# ============================================================================
# PARSING ENDPOINTS
# ============================================================================

@app.post("/api/parse")
async def parse_files(request: ParseRequest = None) -> Dict[str, Any]:
    """Parse uploaded Betfair data files"""
    parse_results = []

    files = request.files if request and request.files else None
    if not files:
        uploaded = await storage.list_files("uploaded")
        files = [f["filename"] for f in uploaded]

    for filename in files:
        try:
            content = await storage.read_file("uploaded", filename)

            if not content:
                parse_results.append({
                    "filename": filename,
                    "status": "error",
                    "error": "File not found"
                })
                continue

            # Decompress and parse
            decompressed = parser.decompress_file(content, filename)
            records = parser.parse_ndjson(decompressed)
            market_data = parser.extract_market_data(records)

            # Save parsed data
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            output_filename = f"{base_name}_parsed.json"
            output_content = orjson.dumps(market_data).decode('utf-8')

            await storage.save_file_text("parsed", output_filename, output_content)

            parse_results.append({
                "filename": filename,
                "status": "success",
                "records_parsed": market_data["record_count"],
                "markets_parsed": market_data["market_count"],
                "output_file": output_filename,
                "parse_timestamp": datetime.utcnow().isoformat()
            })

            logger.info(f"Parsed {filename}: {market_data['record_count']} records")

        except Exception as e:
            logger.error(f"Parse error for {filename}: {e}")
            parse_results.append({
                "filename": filename,
                "status": "error",
                "error": str(e)
            })

    return {
        "total": len(files),
        "successful": len([r for r in parse_results if r["status"] == "success"]),
        "results": parse_results
    }


@app.get("/api/parsed-files")
async def list_parsed_files() -> List[Dict[str, Any]]:
    """List all parsed files"""
    return await storage.list_files("parsed")


# ============================================================================
# EXPORT ENDPOINTS
# ============================================================================

@app.post("/api/export")
async def export_files(request: ExportRequest) -> Dict[str, Any]:
    """Export parsed files in requested format"""
    export_results = []

    for filename in request.files:
        try:
            # Ensure we're looking for parsed file
            if not filename.endswith("_parsed.json"):
                base = filename.rsplit('.', 1)[0] if '.' in filename else filename
                filename = f"{base}_parsed.json"

            content = await storage.read_file_text("parsed", filename)

            if not content:
                export_results.append({
                    "filename": filename,
                    "status": "error",
                    "error": "Parsed file not found"
                })
                continue

            data = json.loads(content)
            base_name = filename.replace("_parsed.json", "")

            # Convert to requested format
            if request.format == "csv":
                markets = list(data.get('markets', {}).values())
                df = pd.json_normalize(markets) if markets else pd.DataFrame()
                output_content = df.to_csv(index=False)
                output_filename = f"{base_name}_export.csv"
                await storage.save_file_text("exported", output_filename, output_content)

            elif request.format == "parquet":
                markets = list(data.get('markets', {}).values())
                df = pd.json_normalize(markets) if markets else pd.DataFrame()
                buffer = io.BytesIO()
                df.to_parquet(buffer, index=False)
                output_filename = f"{base_name}_export.parquet"
                await storage.save_file("exported", output_filename, buffer.getvalue())

            else:  # JSON
                output_filename = f"{base_name}_export.json"
                await storage.save_file_text("exported", output_filename, content)

            export_results.append({
                "filename": filename,
                "status": "success",
                "output_file": output_filename,
                "format": request.format,
                "export_timestamp": datetime.utcnow().isoformat()
            })

            logger.info(f"Exported {filename} as {request.format}")

        except Exception as e:
            logger.error(f"Export error for {filename}: {e}")
            export_results.append({
                "filename": filename,
                "status": "error",
                "error": str(e)
            })

    return {
        "total": len(request.files),
        "successful": len([r for r in export_results if r["status"] == "success"]),
        "results": export_results
    }


@app.get("/api/export-file/{filename}")
async def download_exported_file(filename: str):
    """Download exported file"""
    if storage.use_firebase:
        content = await storage.read_file("exported", filename)
        if not content:
            raise HTTPException(status_code=404, detail="File not found")

        media_type = "application/octet-stream"
        if filename.endswith(".json"):
            media_type = "application/json"
        elif filename.endswith(".csv"):
            media_type = "text/csv"

        return Response(content=content, media_type=media_type, headers={
            "Content-Disposition": f"attachment; filename={filename}"
        })
    else:
        file_path = await storage.get_file_path("exported", filename)
        if not file_path:
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(file_path, filename=filename)


# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/api/cache/clear-uploaded")
async def clear_uploaded_cache() -> Dict[str, str]:
    """Clear uploaded files cache"""
    success = await storage.clear_category("uploaded")
    return {
        "status": "success" if success else "error",
        "message": "Uploaded cache cleared" if success else "Failed to clear cache"
    }


@app.post("/api/cache/clear-parsed")
async def clear_parsed_cache() -> Dict[str, str]:
    """Clear parsed files cache"""
    success = await storage.clear_category("parsed")
    return {
        "status": "success" if success else "error",
        "message": "Parsed cache cleared" if success else "Failed to clear cache"
    }


@app.post("/api/cache/clear-exported")
async def clear_exported_cache() -> Dict[str, str]:
    """Clear exported files cache"""
    success = await storage.clear_category("exported")
    return {
        "status": "success" if success else "error",
        "message": "Exported cache cleared" if success else "Failed to clear cache"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENV", "development") == "development"
    )
