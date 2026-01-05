import { useState, useRef } from 'react';
import '../App.css';

export default function FileProcessingPanel({
  uploadedFiles = [],
  parsedFiles = [],
  selectedFiles = [],
  onFilesSelected,
  onUpload,
  onParse,
  onExport,
  loading,
  error,
  onClearError
}) {
  const [filesToUpload, setFilesToUpload] = useState([]);
  const [uploadedCount, setUploadedCount] = useState(0);
  const [parsedCount, setParsedCount] = useState(0);
  const [exportedCount, setExportedCount] = useState(0);
  const [exportedSize, setExportedSize] = useState(0);
  const [exportFormat, setExportFormat] = useState('json');
  const [selectAll, setSelectAll] = useState(false);
  const fileInputRef = useRef(null);

  // Calculate totals
  const selectedFilesVolume = filesToUpload.reduce((sum, f) => sum + f.size, 0);

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    setFilesToUpload(files);
  };

  const handleSelectFilesClick = () => {
    fileInputRef.current?.click();
  };

  const handleUploadClick = async () => {
    if (filesToUpload.length === 0) return;
    try {
      const result = await onUpload(filesToUpload);
      setUploadedCount(result.successful);
      setFilesToUpload([]);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    } catch (err) {
      console.error('Upload error:', err);
    }
  };

  const handleReset = () => {
    setUploadedCount(0);
    setParsedCount(0);
    setExportedCount(0);
    setExportedSize(0);
    setSelectAll(false);
    setFilesToUpload([]);
    onFilesSelected([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleParseClick = async () => {
    try {
      const result = await onParse();
      setParsedCount(result.successful);
    } catch (err) {
      console.error('Parse error:', err);
    }
  };

  const handleSelectAllChange = (e) => {
    const checked = e.target.checked;
    setSelectAll(checked);
    if (checked) {
      onFilesSelected(parsedFiles.map(f => f.filename));
    } else {
      onFilesSelected([]);
    }
  };

  const handleFileCheckboxChange = (filename, checked) => {
    let newSelected = [...selectedFiles];
    if (checked) {
      if (!newSelected.includes(filename)) {
        newSelected.push(filename);
      }
    } else {
      newSelected = newSelected.filter(f => f !== filename);
    }
    onFilesSelected(newSelected);
    setSelectAll(newSelected.length === parsedFiles.length && parsedFiles.length > 0);
  };

  const handleExportClick = async () => {
    try {
      const result = await onExport(exportFormat);
      setExportedCount(result.successful);
      // Calculate exported size from results
      const size = result.results?.reduce((sum, r) => {
        return sum + (r.size_bytes || 0);
      }, 0) || 0;
      setExportedSize(size);

      // Trigger download for each exported file
      const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
      if (result.results) {
        for (const r of result.results) {
          if (r.status === 'success' && r.output_file) {
            // Create download link
            const link = document.createElement('a');
            link.href = `${apiUrl}/export-file/${r.output_file}`;
            link.download = r.output_file;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
          }
        }
      }
    } catch (err) {
      console.error('Export error:', err);
    }
  };

  const handleViewFile = (filename) => {
    // Open file in new tab
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    window.open(`${apiUrl}/export-file/${filename}`, '_blank');
  };

  return (
    <div className="glass-panel">
      <h2 className="glass-panel-title">File Processing</h2>

      {/* Error Banner - Always at top */}
      {error && (
        <div className="error-banner">
          <span className="error-banner-icon">!</span>
          <span className="error-banner-text">{error}</span>
          <button className="error-banner-close" onClick={onClearError}>x</button>
        </div>
      )}

      {/* File Selection Section */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        onChange={handleFileSelect}
        accept=".bz2,.gz,.tar,.zip,.json"
      />

      <button
        className="glass-button glass-button-primary"
        onClick={handleSelectFilesClick}
        disabled={loading}
        style={{ width: '100%' }}
      >
        Select Files
      </button>

      {filesToUpload.length > 0 && (
        <div className="stats-row">
          <span className="stats-label">{filesToUpload.length} file(s) selected</span>
          <span className="stats-value">{(selectedFilesVolume / (1024 * 1024)).toFixed(2)} MB</span>
        </div>
      )}

      <button
        className="glass-button"
        onClick={handleUploadClick}
        disabled={filesToUpload.length === 0 || loading}
        style={{ width: '100%', marginTop: '0.75rem' }}
      >
        Upload Files
      </button>

      {uploadedCount > 0 && (
        <div className="stats-row">
          <span className="stats-label">Successfully Uploaded</span>
          <span className="stats-value">{uploadedCount} file(s)</span>
        </div>
      )}

      <div className="section-divider" />

      {/* Processing Controls */}
      <div className="action-row">
        <button
          className="glass-button"
          onClick={handleReset}
          disabled={loading}
        >
          Reset
        </button>
        <button
          className="glass-button glass-button-primary"
          onClick={handleParseClick}
          disabled={uploadedFiles.length === 0 || loading}
        >
          Parse Files
        </button>
      </div>

      {parsedCount > 0 && (
        <div className="stats-row">
          <span className="stats-label">Successfully Parsed</span>
          <span className="stats-value">{parsedCount} file(s)</span>
        </div>
      )}

      <div className="section-divider" />

      {/* File List with Select All and Export at top */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <span className="section-title" style={{ margin: 0 }}>Parsed Files ({parsedFiles.length})</span>
        <div className="export-controls">
          <select
            value={exportFormat}
            onChange={(e) => setExportFormat(e.target.value)}
          >
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
            <option value="parquet">Parquet</option>
          </select>
          <button
            className="glass-button glass-button-small"
            onClick={handleExportClick}
            disabled={selectedFiles.length === 0 || loading}
          >
            Export
          </button>
        </div>
      </div>

      {/* File List Header with Select All */}
      <div className="file-list-header">
        <div className="file-list-header-left">
          <input
            type="checkbox"
            className="file-checkbox"
            checked={selectAll}
            onChange={handleSelectAllChange}
            disabled={parsedFiles.length === 0}
          />
          <span>Select All</span>
        </div>
      </div>

      {/* File List */}
      <div className="file-list">
        {parsedFiles.length > 0 ? (
          parsedFiles.map(file => (
            <div key={file.filename} className="file-item">
              <input
                type="checkbox"
                className="file-checkbox"
                checked={selectedFiles.includes(file.filename)}
                onChange={(e) => handleFileCheckboxChange(file.filename, e.target.checked)}
              />
              <div className="file-info">
                <span className="file-name">{file.filename}</span>
                <span className="file-size">{file.size_mb?.toFixed(2) || '0.00'} MB</span>
              </div>
              <div className="file-actions">
                <button
                  className="view-btn"
                  onClick={() => handleViewFile(file.filename)}
                >
                  View
                </button>
              </div>
            </div>
          ))
        ) : (
          <div className="file-list-empty">No parsed files available</div>
        )}
      </div>

      {/* Export button at bottom */}
      <button
        className="glass-button glass-button-primary"
        onClick={handleExportClick}
        disabled={selectedFiles.length === 0 || loading}
        style={{ width: '100%', marginTop: '0.75rem' }}
      >
        Export Selected ({selectedFiles.length})
      </button>

      {/* Export Results */}
      {exportedCount > 0 && (
        <div className="stats-row">
          <span className="stats-label">Successfully Exported</span>
          <span className="stats-value">
            {exportedCount} file(s) - {(exportedSize / (1024 * 1024)).toFixed(2)} MB
          </span>
        </div>
      )}
    </div>
  );
}
