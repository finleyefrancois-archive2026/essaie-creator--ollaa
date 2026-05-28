#!/usr/bin/env python3
"""
Smart File Organizer - Web Server & Dashboard
Provides a browser-based interface for reviewing and approving file organization.
"""

import os
import sys
import json
import socket
import webbrowser
from pathlib import Path
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))
from organizer_core import FileOrganizer

# === Configuration ===
DEFAULT_PORT = 8787
HOST = "localhost"

class OrganizerHandler(SimpleHTTPRequestHandler):
    organizer = None
    current_session = None
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/" or path == "/index.html":
            self.send_dashboard()
        elif path == "/api/sessions":
            self.send_json({"sessions": []})  # Could list past sessions
        elif path.startswith("/api/session/"):
            session_id = path.split("/")[-1]
            self.get_session(session_id)
        elif path == "/api/stats":
            self.send_json(self.organizer.get_statistics())
        else:
            super().do_GET()
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        
        try:
            data = json.loads(post_data) if post_data else {}
        except json.JSONDecodeError:
            self.send_error(400, "Invalid JSON")
            return
        
        if path == "/api/scan":
            self.scan_files(data)
        elif path == "/api/execute":
            self.execute_session(data)
        elif path == "/api/rollback":
            self.rollback_session(data)
        else:
            self.send_error(404, "Not Found")
    
    def send_dashboard(self):
        """Serve the main dashboard HTML"""
        html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart File Organizer</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .content { padding: 30px; }
        .section { margin-bottom: 30px; }
        .section h2 { 
            color: #333; 
            margin-bottom: 15px; 
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        input[type="text"], input[type="number"] {
            flex: 1;
            min-width: 200px;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        input:focus { outline: none; border-color: #667eea; }
        button {
            padding: 12px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        button.success { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        button.danger { background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        .stat-card h3 { color: #666; font-size: 0.9em; margin-bottom: 10px; }
        .stat-card .value { 
            font-size: 2em; 
            font-weight: bold; 
            color: #667eea;
        }
        .file-list {
            max-height: 500px;
            overflow-y: auto;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
        }
        .file-item {
            display: flex;
            align-items: center;
            padding: 15px;
            border-bottom: 1px solid #f0f0f0;
            transition: background 0.2s;
        }
        .file-item:hover { background: #f8f9fa; }
        .file-item:last-child { border-bottom: none; }
        .file-checkbox {
            width: 20px;
            height: 20px;
            margin-right: 15px;
            cursor: pointer;
        }
        .file-info { flex: 1; }
        .file-name { 
            font-weight: 600; 
            color: #333;
            word-break: break-all;
        }
        .file-path { 
            font-size: 0.85em; 
            color: #666; 
            margin-top: 5px;
        }
        .file-meta {
            display: flex;
            gap: 15px;
            margin-top: 8px;
            font-size: 0.85em;
        }
        .badge {
            padding: 3px 10px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: 600;
        }
        .badge-category { background: #e3f2fd; color: #1976d2; }
        .badge-duplicate { background: #ffebee; color: #c62828; }
        .badge-conflict { background: #fff3e0; color: #e65100; }
        .actions-bar {
            position: sticky;
            bottom: 0;
            background: white;
            padding: 20px;
            border-top: 2px solid #e0e0e0;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
        }
        .selection-info {
            font-size: 0.9em;
            color: #666;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            width: 0%;
            transition: width 0.3s;
        }
        .hidden { display: none; }
        .alert {
            padding: 15px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .alert-info { background: #e3f2fd; color: #1976d2; border-left: 4px solid #1976d2; }
        .alert-success { background: #e8f5e9; color: #2e7d32; border-left: 4px solid #2e7d32; }
        .alert-warning { background: #fff3e0; color: #e65100; border-left: 4px solid #e65100; }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .spinner {
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto 20px;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗂️ Smart File Organizer</h1>
            <p>Organize, merge, and deduplicate your files with confidence</p>
        </div>
        
        <div class="content">
            <!-- Statistics -->
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <h3>Sessions</h3>
                    <div class="value" id="statSessions">0</div>
                </div>
                <div class="stat-card">
                    <h3>Files Organized</h3>
                    <div class="value" id="statFiles">0</div>
                </div>
                <div class="stat-card">
                    <h3>Data Processed</h3>
                    <div class="value" id="statSize">0 MB</div>
                </div>
                <div class="stat-card">
                    <h3>Active Moves</h3>
                    <div class="value" id="statMoved">0</div>
                </div>
            </div>
            
            <!-- Scan Section -->
            <div class="section">
                <h2>1. Select Source Folders</h2>
                <div class="alert alert-info">
                    💡 Add folders from your PC or external drives. The app will scan all files without moving anything yet.
                </div>
                <div class="input-group">
                    <input type="text" id="sourcePath" placeholder="Enter folder path (e.g., C:\\Users\\Name\\Downloads or /home/user/files)">
                    <button onclick="addSourcePath()">Add Folder</button>
                </div>
                <div id="sourceList" style="margin-bottom: 15px;"></div>
                
                <h2 style="margin-top: 30px;">2. Choose Destination Base</h2>
                <div class="input-group">
                    <input type="text" id="destPath" placeholder="Base folder for organized files (e.g., D:\\Organized or /mnt/drive/organized)">
                    <button onclick="startScan()" id="scanBtn">🔍 Scan & Plan</button>
                </div>
            </div>
            
            <!-- Review Section -->
            <div class="section hidden" id="reviewSection">
                <h2>3. Review & Approve Actions</h2>
                <div class="alert alert-warning">
                    ⚠️ Review the planned actions below. Uncheck items you want to skip. Duplicates are unchecked by default.
                </div>
                
                <div class="file-list" id="fileList">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading preview...</p>
                    </div>
                </div>
                
                <div class="actions-bar">
                    <div class="selection-info">
                        <span id="selectedCount">0</span> of <span id="totalCount">0</span> actions selected
                        <span id="totalSize" style="margin-left: 15px; font-weight: 600;"></span>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="selectAll()">Select All</button>
                        <button onclick="selectSafeOnly()">Select Safe Only</button>
                        <button class="success" onclick="executeOrganization()" id="executeBtn">✅ Execute Organization</button>
                    </div>
                </div>
            </div>
            
            <!-- Progress Section -->
            <div class="section hidden" id="progressSection">
                <h2>4. Progress</h2>
                <div class="progress-bar">
                    <div class="progress-fill" id="progressFill"></div>
                </div>
                <p id="progressText" style="margin-top: 10px; text-align: center;">Starting...</p>
                <div id="progressDetails" style="margin-top: 20px; max-height: 300px; overflow-y: auto;"></div>
            </div>
            
            <!-- Rollback Section -->
            <div class="section hidden" id="rollbackSection">
                <h2>Undo Last Operation</h2>
                <div class="alert alert-info">
                    ↩️ Need to undo? You can rollback the last completed session to restore files to their original locations.
                </div>
                <button class="danger" onclick="rollbackLastSession()">🔄 Rollback Last Session</button>
            </div>
        </div>
    </div>
    
    <script>
        let sourcePaths = [];
        let currentSessionId = null;
        let sessionActions = [];
        
        // Load statistics on page load
        loadStats();
        setInterval(loadStats, 30000); // Refresh every 30 seconds
        
        function loadStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('statSessions').textContent = data.total_sessions || 0;
                    document.getElementById('statFiles').textContent = data.total_files_organized || 0;
                    const sizeMB = ((data.total_size_processed || 0) / (1024 * 1024)).toFixed(1);
                    document.getElementById('statSize').textContent = sizeMB + ' MB';
                    document.getElementById('statMoved').textContent = data.files_currently_moved || 0;
                });
        }
        
        function addSourcePath() {
            const input = document.getElementById('sourcePath');
            const path = input.value.trim();
            if (!path) return;
            
            if (!sourcePaths.includes(path)) {
                sourcePaths.push(path);
                renderSourceList();
            }
            input.value = '';
        }
        
        function renderSourceList() {
            const container = document.getElementById('sourceList');
            if (sourcePaths.length === 0) {
                container.innerHTML = '<p style="color: #666; font-style: italic;">No folders added yet</p>';
                return;
            }
            
            container.innerHTML = sourcePaths.map((path, idx) => `
                <div style="display: flex; justify-content: space-between; padding: 8px 12px; background: #f8f9fa; margin-bottom: 8px; border-radius: 6px;">
                    <span style="font-family: monospace; font-size: 0.9em;">${path}</span>
                    <button onclick="removeSourcePath(${idx})" style="padding: 4px 10px; font-size: 0.8em; background: #ff6b6b;">Remove</button>
                </div>
            `).join('');
        }
        
        function removeSourcePath(idx) {
            sourcePaths.splice(idx, 1);
            renderSourceList();
        }
        
        function startScan() {
            if (sourcePaths.length === 0) {
                alert('Please add at least one source folder');
                return;
            }
            
            const destPath = document.getElementById('destPath').value.trim();
            if (!destPath) {
                alert('Please enter a destination base folder');
                return;
            }
            
            const btn = document.getElementById('scanBtn');
            btn.disabled = true;
            btn.textContent = 'Scanning...';
            
            fetch('/api/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    source_paths: sourcePaths,
                    target_base: destPath
                })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    currentSessionId = data.session_id;
                    sessionActions = data.actions;
                    showReviewSection();
                } else {
                    alert('Scan failed: ' + (data.error || 'Unknown error'));
                }
                btn.disabled = false;
                btn.textContent = '🔍 Scan & Plan';
            })
            .catch(err => {
                alert('Error: ' + err.message);
                btn.disabled = false;
                btn.textContent = '🔍 Scan & Plan';
            });
        }
        
        function showReviewSection() {
            document.getElementById('reviewSection').classList.remove('hidden');
            document.getElementById('rollbackSection').classList.remove('hidden');
            renderFileList();
        }
        
        function renderFileList() {
            const container = document.getElementById('fileList');
            document.getElementById('totalCount').textContent = sessionActions.length;
            updateSelectionInfo();
            
            if (sessionActions.length === 0) {
                container.innerHTML = '<div class="alert alert-info">No files to organize. All files might already be in place or filtered out.</div>';
                return;
            }
            
            container.innerHTML = sessionActions.map((action, idx) => {
                const isChecked = action.action_type !== 'duplicate' && action.action_type !== 'conflict';
                const badges = [];
                if (action.action_type === 'duplicate') {
                    badges.push('<span class="badge badge-duplicate">Duplicate</span>');
                } else if (action.action_type === 'conflict') {
                    badges.push('<span class="badge badge-conflict">Conflict</span>');
                }
                badges.push(`<span class="badge badge-category">${action.category}</span>`);
                
                const sizeStr = formatSize(action.file_size);
                
                return `
                    <div class="file-item">
                        <input type="checkbox" class="file-checkbox" 
                               data-idx="${idx}" 
                               ${isChecked ? 'checked' : ''}
                               onchange="updateSelectionInfo()">
                        <div class="file-info">
                            <div class="file-name">${escapeHtml(action.source.split('/').pop() || action.source.split('\\\\').pop())}</div>
                            <div class="file-path">${escapeHtml(action.source)}</div>
                            <div class="file-path" style="color: #667eea;">→ ${escapeHtml(action.destination)}</div>
                            <div class="file-meta">
                                <span>${sizeStr}</span>
                                <span>${action.date_folder}</span>
                                ${badges.join('')}
                                ${action.conflict_reason ? `<span style="color: #e65100; font-size: 0.8em;">${escapeHtml(action.conflict_reason)}</span>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }
        
        function selectAll() {
            document.querySelectorAll('.file-checkbox').forEach(cb => cb.checked = true);
            updateSelectionInfo();
        }
        
        function selectSafeOnly() {
            document.querySelectorAll('.file-checkbox').forEach(cb => {
                const idx = parseInt(cb.dataset.idx);
                const action = sessionActions[idx];
                cb.checked = action.action_type === 'move' && !action.conflict_reason;
            });
            updateSelectionInfo();
        }
        
        function updateSelectionInfo() {
            const checkboxes = document.querySelectorAll('.file-checkbox:checked');
            const total = checkboxes.length;
            const size = checkboxes.reduce((sum, cb) => {
                const idx = parseInt(cb.dataset.idx);
                return sum + (sessionActions[idx]?.file_size || 0);
            }, 0);
            
            document.getElementById('selectedCount').textContent = total;
            document.getElementById('totalSize').textContent = `(${formatSize(size)})`;
        }
        
        function executeOrganization() {
            const checkboxes = document.querySelectorAll('.file-checkbox:checked');
            const approvedIndices = Array.from(checkboxes).map(cb => parseInt(cb.dataset.idx));
            
            if (approvedIndices.length === 0) {
                alert('Please select at least one action to execute');
                return;
            }
            
            if (!confirm(`Execute ${approvedIndices.length} file operations? This will move files to their organized locations.`)) {
                return;
            }
            
            document.getElementById('reviewSection').classList.add('hidden');
            document.getElementById('progressSection').classList.remove('hidden');
            
            fetch('/api/execute', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    session_id: currentSessionId,
                    approved_actions: approvedIndices
                })
            })
            .then(r => r.json())
            .then(data => {
                showProgress(data);
            })
            .catch(err => {
                alert('Error executing: ' + err.message);
                document.getElementById('progressSection').classList.add('hidden');
                document.getElementById('reviewSection').classList.remove('hidden');
            });
        }
        
        function showProgress(results) {
            const total = results.completed + results.skipped + results.failed;
            const percent = total > 0 ? Math.round((results.completed / total) * 100) : 0;
            
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('progressText').textContent = 
                `Completed: ${results.completed} | Skipped: ${results.skipped} | Failed: ${results.failed}`;
            
            const detailsContainer = document.getElementById('progressDetails');
            if (results.details && results.details.length > 0) {
                detailsContainer.innerHTML = results.details.slice(0, 50).map(d => `
                    <div style="padding: 8px; border-bottom: 1px solid #f0f0f0; font-size: 0.85em;">
                        <strong>${d.status.toUpperCase()}</strong>: ${d.source.split('/').pop() || d.source.split('\\\\').pop()}
                        ${d.conflict_reason ? `<br><small style="color: #666;">${d.conflict_reason}</small>` : ''}
                    </div>
                `).join('');
                
                if (results.details.length > 50) {
                    detailsContainer.innerHTML += `<div style="padding: 10px; text-align: center; color: #666;">... and ${results.details.length - 50} more</div>`;
                }
            }
            
            setTimeout(() => {
                loadStats();
                alert(`Organization complete!\\nCompleted: ${results.completed}\\nSkipped: ${results.skipped}\\nFailed: ${results.failed}`);
            }, 1000);
        }
        
        function rollbackLastSession() {
            if (!currentSessionId) {
                alert('No session to rollback');
                return;
            }
            
            if (!confirm('Are you sure you want to rollback the last session? This will move all files back to their original locations.')) {
                return;
            }
            
            fetch('/api/rollback', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({session_id: currentSessionId})
            })
            .then(r => r.json())
            .then(data => {
                alert(`Rollback complete!\\nRestored: ${data.restored}\\nFailed: ${data.failed}`);
                loadStats();
            })
            .catch(err => {
                alert('Rollback failed: ' + err.message);
            });
        }
        
        function formatSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>'''
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def scan_files(self, data):
        source_paths = data.get('source_paths', [])
        target_base = data.get('target_base', '')
        
        if not source_paths or not target_base:
            self.send_json({"success": False, "error": "Missing source_paths or target_base"})
            return
        
        try:
            session = self.organizer.plan_organization(source_paths, target_base)
            self.current_session = session
            
            self.send_json({
                "success": True,
                "session_id": session.session_id,
                "actions": [asdict(a) for a in session.actions],
                "total_files": session.total_files,
                "total_size": session.total_size
            })
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})
    
    def execute_session(self, data):
        session_id = data.get('session_id')
        approved_actions = data.get('approved_actions', [])
        
        if not session_id:
            self.send_json({"success": False, "error": "Missing session_id"})
            return
        
        try:
            results = self.organizer.execute_session(session_id, approved_actions)
            self.send_json({"success": True, **results})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})
    
    def rollback_session(self, data):
        session_id = data.get('session_id')
        
        if not session_id:
            self.send_json({"success": False, "error": "Missing session_id"})
            return
        
        try:
            results = self.organizer.rollback_session(session_id)
            self.send_json({"success": True, **results})
        except Exception as e:
            self.send_json({"success": False, "error": str(e)})
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass


def find_free_port(start_port: int) -> int:
    """Find a free port starting from start_port"""
    port = start_port
    while port < start_port + 100:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                return port
        except OSError:
            port += 1
    raise RuntimeError("Could not find a free port")


def open_browser(port: int):
    """Open browser after a short delay"""
    time.sleep(1.5)
    webbrowser.open(f'http://{HOST}:{port}')


def run_server(port: int = None):
    """Run the web server"""
    if port is None:
        port = find_free_port(DEFAULT_PORT)
    
    # Initialize organizer
    script_dir = Path(__file__).parent
    data_dir = script_dir / "data"
    data_dir.mkdir(exist_ok=True)
    
    OrganizerHandler.organizer = FileOrganizer(str(data_dir))
    
    server = HTTPServer((HOST, port), OrganizerHandler)
    print(f"\n{'='*60}")
    print(f"🗂️  Smart File Organizer started!")
    print(f"{'='*60}")
    print(f"🌐 Open your browser to: http://{HOST}:{port}")
    print(f"📁 Data directory: {data_dir.absolute()}")
    print(f"{'='*60}")
    print("\nPress Ctrl+C to stop the server\n")
    
    # Start browser in background thread
    browser_thread = threading.Thread(target=open_browser, args=(port,), daemon=True)
    browser_thread.start()
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Smart File Organizer Server")
    parser.add_argument("--port", type=int, help=f"Port to run server (default: {DEFAULT_PORT})")
    args = parser.parse_args()
    
    run_server(args.port)
