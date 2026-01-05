import { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';
import OverviewPanel from './components/OverviewPanel';
import FileProcessingPanel from './components/FileProcessingPanel';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

export default function App() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [parsedFiles, setParsedFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Fetch system status
  const fetchSystemStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/system-status`);
      setSystemStatus(response.data);
    } catch (err) {
      console.error('Error fetching system status:', err);
    }
  };

  // Fetch file lists
  const fetchFileLists = async () => {
    try {
      const [uploaded, parsed] = await Promise.all([
        axios.get(`${API_BASE_URL}/uploaded-files`),
        axios.get(`${API_BASE_URL}/parsed-files`)
      ]);
      setUploadedFiles(Array.isArray(uploaded.data) ? uploaded.data : []);
      setParsedFiles(Array.isArray(parsed.data) ? parsed.data : []);
    } catch (err) {
      console.error('Error fetching file lists:', err);
      setUploadedFiles([]);
      setParsedFiles([]);
    }
  };

  // Initial load
  useEffect(() => {
    fetchSystemStatus();
    fetchFileLists();
    const interval = setInterval(() => {
      fetchSystemStatus();
      fetchFileLists();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleFilesSelected = (files) => {
    setSelectedFiles(files);
  };

  const handleUpload = async (files) => {
    setLoading(true);
    setError(null);
    try {
      const formData = new FormData();
      files.forEach(file => {
        formData.append('files', file);
      });

      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      if (response.data.successful > 0) {
        await fetchFileLists();
        await fetchSystemStatus();
      }
      return response.data;
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleParse = async (filesToParse = null) => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post(`${API_BASE_URL}/parse`, {
        files: filesToParse || uploadedFiles.map(f => f.filename)
      });

      await fetchFileLists();
      await fetchSystemStatus();
      return response.data;
    } catch (err) {
      setError(`Parse failed: ${err.message}`);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async (format = 'json') => {
    setLoading(true);
    setError(null);
    try {
      const filesToExport = selectedFiles.length > 0
        ? selectedFiles
        : parsedFiles.map(f => f.filename);

      const response = await axios.post(`${API_BASE_URL}/export`, {
        files: filesToExport,
        format: format,
        include_metadata: true
      });

      await fetchFileLists();
      await fetchSystemStatus();
      return response.data;
    } catch (err) {
      setError(`Export failed: ${err.message}`);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const handleClearCache = async (type) => {
    setLoading(true);
    setError(null);
    try {
      const endpoints = {
        uploaded: `${API_BASE_URL}/cache/clear-uploaded`,
        parsed: `${API_BASE_URL}/cache/clear-parsed`,
        exported: `${API_BASE_URL}/cache/clear-exported`
      };

      await axios.post(endpoints[type]);
      await fetchFileLists();
      await fetchSystemStatus();
    } catch (err) {
      setError(`Failed to clear ${type} cache: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleClearError = () => {
    setError(null);
  };

  return (
    <div className="app-container">
      {/* Background */}
      <div className="background"></div>

      {/* Header */}
      <header className="app-header">
        <h1>Betfair File Parser v3.0</h1>
      </header>

      {/* Main Content */}
      <main className="app-main">
        {systemStatus ? (
          <div className="panels-grid">
            <OverviewPanel
              status={systemStatus}
              onClearCache={handleClearCache}
              loading={loading}
            />
            <FileProcessingPanel
              uploadedFiles={uploadedFiles}
              parsedFiles={parsedFiles}
              selectedFiles={selectedFiles}
              onFilesSelected={handleFilesSelected}
              onUpload={handleUpload}
              onParse={handleParse}
              onExport={handleExport}
              loading={loading}
              error={error}
              onClearError={handleClearError}
            />
          </div>
        ) : (
          <div className="loading-state">
            <div className="spinner"></div>
            <p>Loading...</p>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="app-footer">
        <p>Powered by Chimera - Intake Hub 3.0 - Ascot Wealth Management 2026</p>
      </footer>
    </div>
  );
}
