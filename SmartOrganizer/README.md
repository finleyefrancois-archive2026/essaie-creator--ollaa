# 🗂️ Smart File Organizer

A **portable, user-friendly** file organization tool that runs in your browser. No installation required!

## ✨ Features

- **Double-click to run** - Just open `start.bat` (Windows) or `start.sh` (Mac/Linux)
- **Browser dashboard** - Beautiful web interface, no command line needed
- **Safe preview** - See all changes before they happen
- **Duplicate detection** - Finds and handles duplicate files automatically
- **Smart categorization** - Organizes by file type and date
- **Folder merging** - Combine multiple drives/folders into one organized structure
- **One-click rollback** - Undo any operation if needed
- **Portable** - Keep it on a USB drive, works on any computer

## 🚀 Quick Start

### Windows
1. Copy the `SmartOrganizer` folder to your computer or USB drive
2. Double-click `start.bat`
3. Your browser will open automatically to the dashboard
4. Add source folders (from your PC or external drives)
5. Choose a destination base folder
6. Review the planned actions
7. Click "Execute Organization"

### Mac / Linux
1. Copy the `SmartOrganizer` folder to your computer or USB drive
2. Open Terminal and navigate to the folder
3. Run: `chmod +x start.sh && ./start.sh`
4. Your browser will open automatically

## 📋 How It Works

1. **Scan** - Select folders to scan (supports multiple drives)
2. **Plan** - The app analyzes all files and creates an organization plan
3. **Review** - See exactly what will move where, uncheck items to skip
4. **Execute** - Approve and run the organization
5. **Rollback** - Undo if needed

## 🗂️ Organization Structure

Files are organized like this:
```
Destination/
├── Documents/
│   ├── 2024/
│   │   ├── 01/
│   │   └── 02/
│   └── 2025/
├── Images/
├── Videos/
├── Audio/
├── Code/
├── Archives/
└── Other/
```

## 🔒 Safety Features

- **Dry-run by default** - Nothing moves until you approve
- **Duplicate detection** - SHA-256 hashing finds exact duplicates
- **Conflict handling** - Automatically renames files if conflicts exist
- **Audit trail** - Every action is logged for rollback
- **Transaction safety** - Can resume if interrupted

## 📊 Supported File Types

| Category | Extensions |
|----------|-----------|
| Documents | .pdf, .doc, .docx, .txt, .rtf, .xls, .xlsx, .ppt, .pptx |
| Images | .jpg, .png, .gif, .bmp, .svg, .webp, .tiff |
| Videos | .mp4, .avi, .mkv, .mov, .wmv, .flv, .webm |
| Audio | .mp3, .wav, .flac, .aac, .ogg, .wma |
| Archives | .zip, .rar, .7z, .tar, .gz |
| Code | .py, .js, .ts, .java, .cpp, .html, .css, .json |
| And more... | Auto-detected by MIME type |

## 💡 Tips

- **External drives**: Make sure they're connected before scanning
- **Large libraries**: Scanning may take time for thousands of files
- **Duplicates**: Unchecked by default - review before approving
- **Rollback**: Available only until you close the app session

## 🛠️ Technical Details

- **Language**: Python 3.7+
- **Dependencies**: None (uses standard library only)
- **Database**: SQLite (stored in `data/` folder)
- **Server**: Built-in HTTP server (localhost only)
- **Port**: 8787 (auto-finds free port if busy)

## 📁 Folder Structure

```
SmartOrganizer/
├── start.bat          # Windows launcher
├── start.sh           # Mac/Linux launcher
├── src/
│   ├── organizer_core.py   # Core engine
│   └── web_server.py       # Web dashboard
└── data/              # Created automatically
    └── organizer.db   # Audit database
```

## ⚙️ Advanced Usage

### Command Line (Optional)
```bash
# Run with custom port
python src/web_server.py --port 9000
```

### Configuration
Edit `src/organizer_core.py` to customize:
- `CATEGORY_RULES` - File extension mappings
- `IGNORE_PATTERNS` - Folders/files to skip

## 🆘 Troubleshooting

**"Python not found"**
- Install Python from https://python.org
- Check "Add Python to PATH" during installation

**"Port already in use"**
- Close other instances of the app
- The app will auto-find another port

**"Permission denied"**
- Make sure you have read access to source folders
- Make sure you have write access to destination folder

**Files not moving**
- Check that files aren't open in other programs
- Ensure destination drive has enough space

## 📝 License

Free to use for personal and commercial purposes.

---

**Made with ❤️ for organizing chaos into order**
