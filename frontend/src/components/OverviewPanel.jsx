import '../App.css';

export default function OverviewPanel({ status, onClearCache, loading }) {
  if (!status || !status.cache_status) {
    return null;
  }

  const cache = status.cache_status;

  return (
    <div className="glass-panel">
      <h2 className="glass-panel-title">Overview</h2>

      {/* Files in Cache (Uploaded) */}
      <div className="metric-row">
        <span className="metric-label">Files in Cache</span>
        <span className="metric-value">{cache.uploaded_files_count}</span>
      </div>
      <div className="metric-row">
        <span className="metric-label">Total Volume</span>
        <span className="metric-value">{cache.uploaded_files_size_mb.toFixed(1)} MB</span>
      </div>
      <button
        className="glass-button glass-button-secondary"
        onClick={() => onClearCache('uploaded')}
        disabled={loading || cache.uploaded_files_count === 0}
        style={{ width: '100%', marginTop: '0.5rem' }}
      >
        Clear Cache
      </button>

      <div className="section-divider" />

      {/* Parsed Files in Cache */}
      <div className="metric-row">
        <span className="metric-label">Parsed Files in Cache</span>
        <span className="metric-value">{cache.parsed_files_count}</span>
      </div>
      <div className="metric-row">
        <span className="metric-label">Total Volume</span>
        <span className="metric-value">{cache.parsed_files_size_mb.toFixed(1)} MB</span>
      </div>
      <button
        className="glass-button glass-button-secondary"
        onClick={() => onClearCache('parsed')}
        disabled={loading || cache.parsed_files_count === 0}
        style={{ width: '100%', marginTop: '0.5rem' }}
      >
        Clear Parsed Files
      </button>

      <div className="section-divider" />

      {/* Exported Files */}
      <div className="metric-row">
        <span className="metric-label">Exported Files</span>
        <span className="metric-value">{cache.exported_files_count}</span>
      </div>
      <div className="metric-row">
        <span className="metric-label">Total Volume</span>
        <span className="metric-value">{cache.exported_files_size_mb.toFixed(1)} MB</span>
      </div>
      <button
        className="glass-button glass-button-secondary"
        onClick={() => onClearCache('exported')}
        disabled={loading || cache.exported_files_count === 0}
        style={{ width: '100%', marginTop: '0.5rem' }}
      >
        Clear Exported Files Cache
      </button>

      <div className="section-divider" />

      {/* System Status */}
      <div className="metric-row">
        <span className="metric-label">API Status</span>
        <span className="metric-value with-indicator">
          <span className={`status-dot ${status.api_status === 'online' ? 'online' : 'error'}`} />
          {status.api_status}
        </span>
      </div>
      <div className="metric-row">
        <span className="metric-label">App Health</span>
        <span className="metric-value with-indicator">
          <span className={`status-dot ${status.app_health === 'normal' ? 'online' : 'warning'}`} />
          {status.app_health}
        </span>
      </div>
      <div className="metric-row">
        <span className="metric-label">Export Storage</span>
        <span className="metric-value">{status.storage_backend}</span>
      </div>
    </div>
  );
}
