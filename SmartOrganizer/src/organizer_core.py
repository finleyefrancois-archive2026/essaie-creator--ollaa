#!/usr/bin/env python3
"""
Smart File Organizer - Core Engine
Handles scanning, categorization, duplicate detection, and safe file moving.
"""

import os
import shutil
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import mimetypes

# === Configuration ===
CATEGORY_RULES = {
    "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx"],
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".raw"],
    "Videos": [".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".wma", ".m4a"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"],
    "Code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".html", ".css", ".json", ".xml", ".sql"],
    "Executables": [".exe", ".msi", ".app", ".dmg", ".deb", ".rpm"],
    "Fonts": [".ttf", ".otf", ".woff", ".woff2"],
    "Other": []
}

IGNORE_PATTERNS = [
    ".git", ".svn", ".hg", "__pycache__", "node_modules", ".DS_Store", 
    "Thumbs.db", "desktop.ini", "$RECYCLE.BIN", "System Volume Information"
]

@dataclass
class FileAction:
    """Represents a single file operation"""
    source: str
    destination: str
    action_type: str  # 'move', 'skip', 'duplicate', 'conflict'
    category: str
    date_folder: str
    file_size: int
    file_hash: Optional[str] = None
    conflict_reason: Optional[str] = None
    status: str = "pending"  # pending, approved, completed, skipped, failed

@dataclass
class OrganizeSession:
    """Represents a complete organization session"""
    session_id: str
    start_time: str
    source_paths: List[str]
    target_base: str
    total_files: int
    total_size: int
    actions: List[FileAction]
    status: str = "planning"  # planning, awaiting_approval, running, completed, rolled_back

class FileOrganizer:
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "organizer.db"
        self.init_database()
        mimetypes.init()
    
    def init_database(self):
        """Initialize SQLite database for audit trail"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                start_time TEXT,
                source_paths TEXT,
                target_base TEXT,
                total_files INTEGER,
                total_size INTEGER,
                status TEXT,
                end_time TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                source TEXT,
                destination TEXT,
                action_type TEXT,
                category TEXT,
                date_folder TEXT,
                file_size INTEGER,
                file_hash TEXT,
                conflict_reason TEXT,
                status TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(session_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_path TEXT,
                new_path TEXT,
                moved_at TEXT,
                session_id TEXT,
                reverted INTEGER DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def calculate_hash(self, filepath: str, chunk_size: 8192) -> str:
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                for chunk in iter(lambda: f.read(chunk_size), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception:
            return ""
    
    def should_ignore(self, path: Path) -> bool:
        """Check if path matches ignore patterns"""
        for part in path.parts:
            if part in IGNORE_PATTERNS or part.startswith('.'):
                if part not in ['.config', '.local']:  # Allow some hidden folders
                    return True
        return False
    
    def get_category(self, filepath: str) -> str:
        """Determine file category based on extension"""
        ext = Path(filepath).suffix.lower()
        
        # Try by extension first
        for category, extensions in CATEGORY_RULES.items():
            if ext in extensions:
                return category
        
        # Fallback to MIME type
        mime_type, _ = mimetypes.guess_type(filepath)
        if mime_type:
            if mime_type.startswith('image/'):
                return 'Images'
            elif mime_type.startswith('video/'):
                return 'Videos'
            elif mime_type.startswith('audio/'):
                return 'Audio'
            elif mime_type.startswith('text/'):
                return 'Documents'
            elif mime_type.startswith('application/'):
                if 'pdf' in mime_type:
                    return 'Documents'
                elif 'zip' in mime_type or 'archive' in mime_type:
                    return 'Archives'
        
        return 'Other'
    
    def get_date_folder(self, filepath: str) -> str:
        """Get date-based folder structure (YYYY/MM)"""
        try:
            stat = os.stat(filepath)
            mtime = datetime.fromtimestamp(stat.st_mtime)
            return f"{mtime.year}/{mtime.month:02d}"
        except Exception:
            return "unknown/date"
    
    def scan_files(self, source_paths: List[str]) -> List[Dict]:
        """Scan all files from source paths"""
        files_info = []
        
        for source_path in source_paths:
            source = Path(source_path)
            if not source.exists():
                continue
            
            for root, dirs, files in os.walk(source):
                # Filter ignored directories
                dirs[:] = [d for d in dirs if not self.should_ignore(Path(d))]
                
                for filename in files:
                    if self.should_ignore(Path(filename)):
                        continue
                    
                    filepath = Path(root) / filename
                    try:
                        stat = filepath.stat()
                        files_info.append({
                            'path': str(filepath.absolute()),
                            'size': stat.st_size,
                            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                            'category': self.get_category(str(filepath)),
                            'date_folder': self.get_date_folder(str(filepath))
                        })
                    except Exception as e:
                        print(f"Error accessing {filepath}: {e}")
        
        return files_info
    
    def detect_duplicates(self, files_info: List[Dict]) -> Dict[str, List[Dict]]:
        """Group files by hash to detect duplicates"""
        # First group by size for efficiency
        size_groups = {}
        for file_info in files_info:
            size = file_info['size']
            if size not in size_groups:
                size_groups[size] = []
            size_groups[size].append(file_info)
        
        # Then hash files with same size
        hash_groups = {}
        for size, group in size_groups.items():
            if len(group) == 1:
                # No possible duplicates for unique sizes
                file_hash = "unique_" + str(size)
                if file_hash not in hash_groups:
                    hash_groups[file_hash] = []
                hash_groups[file_hash].append(group[0])
            else:
                # Calculate hash for potential duplicates
                for file_info in group:
                    try:
                        file_hash = self.calculate_hash(file_info['path'])
                        if file_hash not in hash_groups:
                            hash_groups[file_hash] = []
                        hash_groups[file_hash].append(file_info)
                    except Exception:
                        # If can't hash, treat as unique
                        unique_key = f"error_{file_info['path']}"
                        if unique_key not in hash_groups:
                            hash_groups[unique_key] = []
                        hash_groups[unique_key].append(file_info)
        
        return hash_groups
    
    def plan_organization(self, source_paths: List[str], target_base: str, 
                         conflict_strategy: str = "rename") -> OrganizeSession:
        """Plan the organization without executing"""
        session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        
        # Scan all files
        files_info = self.scan_files(source_paths)
        
        # Detect duplicates
        hash_groups = self.detect_duplicates(files_info)
        
        actions = []
        seen_hashes = set()
        
        for file_hash, group in hash_groups.items():
            for idx, file_info in enumerate(group):
                # Determine action
                if file_hash in seen_hashes and idx > 0:
                    # This is a duplicate
                    action_type = "duplicate"
                    conflict_reason = f"Duplicate of {group[0]['path']}"
                    status = "pending_review"
                else:
                    action_type = "move"
                    conflict_reason = None
                    status = "pending"
                    seen_hashes.add(file_hash)
                
                # Build destination path
                category = file_info['category']
                date_folder = file_info['date_folder']
                filename = Path(file_info['path']).name
                
                dest_path = Path(target_base) / category / date_folder / filename
                
                # Handle conflicts at destination
                if dest_path.exists():
                    if conflict_strategy == "rename":
                        base, ext = os.path.splitext(filename)
                        counter = 1
                        while dest_path.exists():
                            new_name = f"{base}_{counter}{ext}"
                            dest_path = Path(target_base) / category / date_folder / new_name
                            counter += 1
                        conflict_reason = f"Renamed to avoid conflict: {dest_path.name}"
                    elif conflict_strategy == "skip":
                        action_type = "conflict"
                        conflict_reason = "Skipped - file exists at destination"
                        status = "pending_review"
                
                action = FileAction(
                    source=file_info['path'],
                    destination=str(dest_path),
                    action_type=action_type,
                    category=category,
                    date_folder=date_folder,
                    file_size=file_info['size'],
                    file_hash=file_hash if file_hash and not file_hash.startswith(('unique_', 'error_')) else None,
                    conflict_reason=conflict_reason,
                    status=status
                )
                actions.append(action)
        
        total_size = sum(a.file_size for a in actions)
        
        session = OrganizeSession(
            session_id=session_id,
            start_time=datetime.now().isoformat(),
            source_paths=source_paths,
            target_base=target_base,
            total_files=len(actions),
            total_size=total_size,
            actions=actions,
            status="planning"
        )
        
        # Save to database
        self.save_session(session)
        
        return session
    
    def save_session(self, session: OrganizeSession):
        """Save session to database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Save session
        cursor.execute('''
            INSERT OR REPLACE INTO sessions 
            (session_id, start_time, source_paths, target_base, total_files, total_size, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            session.session_id,
            session.start_time,
            json.dumps(session.source_paths),
            session.target_base,
            session.total_files,
            session.total_size,
            session.status
        ))
        
        # Save actions
        cursor.execute('DELETE FROM actions WHERE session_id = ?', (session.session_id,))
        for action in session.actions:
            cursor.execute('''
                INSERT INTO actions 
                (session_id, source, destination, action_type, category, date_folder, 
                 file_size, file_hash, conflict_reason, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                session.session_id,
                action.source,
                action.destination,
                action.action_type,
                action.category,
                action.date_folder,
                action.file_size,
                action.file_hash,
                action.conflict_reason,
                action.status
            ))
        
        conn.commit()
        conn.close()
    
    def load_session(self, session_id: str) -> Optional[OrganizeSession]:
        """Load session from database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        session_row = cursor.fetchone()
        
        if not session_row:
            conn.close()
            return None
        
        cursor.execute('SELECT * FROM actions WHERE session_id = ?', (session_id,))
        action_rows = cursor.fetchall()
        
        conn.close()
        
        actions = []
        for row in action_rows:
            action = FileAction(
                source=row[2],
                destination=row[3],
                action_type=row[4],
                category=row[5],
                date_folder=row[6],
                file_size=row[7],
                file_hash=row[8],
                conflict_reason=row[9],
                status=row[10]
            )
            actions.append(action)
        
        session = OrganizeSession(
            session_id=session_row[0],
            start_time=session_row[1],
            source_paths=json.loads(session_row[2]),
            target_base=session_row[3],
            total_files=session_row[4],
            total_size=session_row[5],
            actions=actions,
            status=session_row[6]
        )
        
        return session
    
    def execute_session(self, session_id: str, approved_actions: List[int]) -> Dict:
        """Execute approved actions from a session"""
        session = self.load_session(session_id)
        if not session:
            return {"success": False, "error": "Session not found"}
        
        results = {"completed": 0, "skipped": 0, "failed": 0, "details": []}
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        session.status = "running"
        self.save_session(session)
        
        for idx, action in enumerate(session.actions):
            if idx not in approved_actions and action.status != "pending_review":
                action.status = "skipped"
                results["skipped"] += 1
                continue
            
            try:
                # Create destination directory
                dest_path = Path(action.destination)
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Perform move
                if action.action_type == "duplicate":
                    # Skip duplicates by default unless explicitly approved
                    if idx not in approved_actions:
                        action.status = "skipped"
                        results["skipped"] += 1
                        continue
                
                if Path(action.source).exists():
                    # Atomic move with fallback
                    try:
                        shutil.move(str(action.source), str(action.destination))
                        action.status = "completed"
                        results["completed"] += 1
                        
                        # Record history for rollback
                        cursor.execute('''
                            INSERT INTO file_history 
                            (original_path, new_path, moved_at, session_id)
                            VALUES (?, ?, ?, ?)
                        ''', (action.source, action.destination, 
                             datetime.now().isoformat(), session_id))
                    except Exception as move_error:
                        # Fallback: copy then delete
                        shutil.copy2(str(action.source), str(action.destination))
                        os.unlink(str(action.source))
                        action.status = "completed"
                        results["completed"] += 1
                        
                        cursor.execute('''
                            INSERT INTO file_history 
                            (original_path, new_path, moved_at, session_id)
                            VALUES (?, ?, ?, ?)
                        ''', (action.source, action.destination, 
                             datetime.now().isoformat(), session_id))
                else:
                    action.status = "skipped"
                    action.conflict_reason = "Source file no longer exists"
                    results["skipped"] += 1
                
            except Exception as e:
                action.status = "failed"
                action.conflict_reason = str(e)
                results["failed"] += 1
            
            results["details"].append(asdict(action))
        
        # Update session status
        if results["failed"] == 0:
            session.status = "completed"
        else:
            session.status = "completed_with_errors"
        
        # Update actions in database
        for idx, action in enumerate(session.actions):
            cursor.execute('''
                UPDATE actions SET status = ?, conflict_reason = ?
                WHERE session_id = ? AND source = ? AND destination = ?
            ''', (action.status, action.conflict_reason, session_id, 
                  action.source, action.destination))
        
        conn.commit()
        conn.close()
        
        return results
    
    def rollback_session(self, session_id: str) -> Dict:
        """Rollback a completed session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT original_path, new_path FROM file_history 
            WHERE session_id = ? AND reverted = 0
        ''', (session_id,))
        
        history = cursor.fetchall()
        results = {"restored": 0, "failed": 0, "details": []}
        
        for original, new_path in history:
            try:
                if Path(new_path).exists():
                    Path(original).parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(new_path), str(original))
                    
                    cursor.execute('''
                        UPDATE file_history SET reverted = 1 
                        WHERE original_path = ? AND new_path = ?
                    ''', (original, new_path))
                    
                    results["restored"] += 1
                    results["details"].append({"original": original, "restored": True})
            except Exception as e:
                results["failed"] += 1
                results["details"].append({"original": original, "error": str(e)})
        
        conn.commit()
        conn.close()
        
        return results
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM sessions')
        total_sessions = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(total_files) FROM sessions')
        total_files = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT SUM(total_size) FROM sessions')
        total_size = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM file_history WHERE reverted = 0')
        files_moved = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_sessions": total_sessions,
            "total_files_organized": total_files,
            "total_size_processed": total_size,
            "files_currently_moved": files_moved
        }

# Export for use in other modules
__all__ = ['FileOrganizer', 'OrganizeSession', 'FileAction']
