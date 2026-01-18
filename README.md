# QNX4 File Recovery Tool v3.0

Professional-grade recovery tool for extracting files from QNX4 filesystems (commonly found in Chrysler MyGig infotainment systems) with **complete data integrity and metadata preservation**.

## Features

✅ **Complete filesystem browser** - Extract any file type from QNX4 partitions  
✅ **Full file recovery** - Finds all files (1200+ files typical in MyGig systems)  
✅ **Metadata preservation** - ID3 tags, EXIF data, and all file attributes intact  
✅ **Hierarchical browsing** - Navigate entire directory structure in GUI  
✅ **Visual progress** - Real-time extraction progress with file-by-file status  
✅ **Batch extraction** - Extract individual files, folders, or entire filesystem  
✅ **Professional parsing** - Uses dissect.target forensics library with bug fixes  

## Prerequisites

### Creating a Disk Image (First Time Setup)

Before using this tool, you need to create a disk image of your MyGig/QNX4 drive:

1. **Download HDDRawCopy** - Free tool for creating disk images on Windows https://hddguru.com/software/HDD-Raw-Copy-Tool/
2. **Connect your drive** - Via USB adapter
3. **Run HDDRawCopy** - Select your source drive (usually shows as "HDD" or by size)
4. **Choose destination** - Save as `.img` file (e.g., `MyGig_30GB.img`)
5. **Start copy** - Creates a complete sector-by-sector image (may take 15-30 minutes)

⚠️ **Important:** Use the resulting `.img` file with this recovery tool, not the physical drive directly.

## Quick Start

### 1. Install Dependencies

```bash
pip install dissect.target
```

### 2. Run the Tool

```bash
python mygig_recovery_v3.py
```

## Distribution

This tool includes patched versions of buggy code from dissect.qnxfs. To distribute:

**Include these 3 files:**

- `mygig_recovery_v3.py` - Main GUI application
- `qnx4_patched.py` - Bug fixes for dissect.qnxfs
- `README.md` - This file

**Users only need to:**

1. Install: `pip install dissect.target`
2. Run: `python mygig_recovery_v3.py`

The patch is applied automatically at startup.

## Technical Details

### Bug Fixes Applied

The original `dissect.qnxfs` package (as of v3.20) has two bugs that prevent reading certain QNX4 filesystems:

**Bug #1:** Invalid signature check on extent blocks

```python
# Original (broken):
if xblk.signature != b"IamXblk":
    raise Error("Invalid QNX4 xblk signature")

# Fixed: Removed check (qnx4_xblk doesn't have signature attribute)
```

**Bug #2:** Missing check for end of extent chain

```python
# Original (broken):
while num_extents:
    self.fs.fh.seek((xblk_num - 1) * self.fs.block_size)

# Fixed: Check if xblk_num is 0 (end of chain)
while num_extents and xblk_num:
    self.fs.fh.seek((xblk_num - 1) * self.fs.block_size)
```

I included the patched file because of a bug (listed above) in the dissect.qnxfs file that I wanted to get around.  This patched version is applied at runtime.

## Usage

1. **Browse** - Select your disk image (.img, .raw, .dd)
2. **Scan** - Click "Scan QNX4 Filesystem" to analyze
3. **Extract** - Select files/folders (Shift/Ctrl+Click for multiple) and choose output directory
4. **Progress** - Real-time extraction status with file-by-file updates

💡 **MyGig Tip:** Music files are typically in `/fs2/playlists/` - you can extract the entire folder simply by clicking 'playlists' and then 'Extract Selected' or choose individual files/folders within it.

## Supported Use Cases

- **Music Recovery** - MP3, WMA, WAV, M4A, FLAC, OGG with full ID3 tags
- **Image Recovery** - JPG, PNG, BMP with EXIF metadata
- **Database Recovery** - SQLite databases, configuration files
- **Any File Type** - Complete filesystem access to all files

## Known Issues

- Requires dissect.target (large dependency ~50MB)
- Windows-only GUI (uses tkinter)
- Large images (>10GB) may take 1-2 minutes to scan

## License

This tool uses the dissect.target library which is licensed under AGPL-3.0.

The bug fixes in `qnx4_patched.py` maintain the same license as the original dissect.qnxfs code.

## Credits

- Based on dissect.target by Fox-IT (Netherlands Forensic Institute)
- Bug fixes and GUI by [Your Name]
- QNX4 filesystem documentation from Linux kernel sources

## Changelog

### v3.0 (Current)

- Switched to dissect.target for professional-grade parsing
- Added automatic bug patching for dissect.qnxfs
- **Full filesystem browser** - extract any file type
- **Visual extraction progress** - real-time file-by-file status
- Complete data integrity and metadata preservation
- Hierarchical directory browsing
- Finds all files (1200+ typical vs 200 in v2.0)
- Removed incorrect modification dates
- Streamlined UI with Name/Size/Path columns

### v2.0 (Previous)

- Custom QNX4 parser
- Issues: Missing 85% of files, no metadata, corrupt extents

### v1.0 (Original)

- Basic proof of concept
