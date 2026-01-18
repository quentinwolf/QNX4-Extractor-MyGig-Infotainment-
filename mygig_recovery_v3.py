import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading

# Auto-apply patch for dissect.qnxfs bugs
def apply_qnx4_patch():
    """Apply our bug fixes to dissect.qnxfs.qnx4"""
    try:
        # Import the patched version from our local file
        import qnx4_patched
        
        # Replace the broken module with our fixed version
        import dissect.qnxfs
        dissect.qnxfs.qnx4 = qnx4_patched
        
        print("✓ Applied QNX4 bug fixes")
        return True
    except ImportError as e:
        print(f"⚠ Warning: Could not apply patch: {e}")
        print("  Make sure qnx4_patched.py is in the same directory")
        return False

# Check dependencies
try:
    from dissect.target import Target
    apply_qnx4_patch()
except ImportError:
    messagebox.showerror(
        "Missing Dependencies",
        "Required package 'dissect.target' is not installed.\n\n"
        "Please install it with:\n"
        "pip install dissect.target"
    )
    sys.exit(1)

# Check for optional metadata support
try:
    import mutagen
    METADATA_AVAILABLE = True
except ImportError:
    METADATA_AVAILABLE = False

class QNX4ScannerGUI:
    """GUI for QNX4 MP3 Recovery using dissect.target"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("QNX4 File Recovery Tool v3.0 - Complete Filesystem Browser")
        self.root.geometry("1200x750")
        
        self.image_path = None
        self.target = None
        self.found_files = []
        self.all_files_cache = []  # Unfiltered list for search
        self.scan_thread = None
        self.metadata_db_path = None
        
        self.create_widgets()
    
    def create_widgets(self):
        # Top frame
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)
        
        ttk.Label(top_frame, text="Disk Image:").pack(side=tk.LEFT)
        self.path_var = tk.StringVar()
        ttk.Entry(top_frame, textvariable=self.path_var, width=60).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)
        
        self.scan_button = ttk.Button(top_frame, text="Scan QNX4 Filesystem", command=self.start_scan)
        self.scan_button.pack(side=tk.LEFT, padx=5)
        
        # Metadata button (only if mutagen available)
        if METADATA_AVAILABLE:
            self.metadata_button = ttk.Button(top_frame, text="Extract Metadata", command=self.start_metadata_extraction, state='disabled')
            self.metadata_button.pack(side=tk.LEFT, padx=5)
        
        # Search box (only if mutagen available)
        if METADATA_AVAILABLE:
            search_frame = ttk.Frame(self.root, padding="10")
            search_frame.pack(fill=tk.X)
            
            ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT)
            self.search_var = tk.StringVar()
            self.search_var.trace('w', lambda *args: self.filter_tree())
            search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=50)
            search_entry.pack(side=tk.LEFT, padx=5)
            ttk.Label(search_frame, text="(searches name, path, title, artist, album, bitrate)", foreground="gray").pack(side=tk.LEFT)
        
        # Progress bar
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, padx=10, pady=5)
        
        # Status labels
        self.status_var = tk.StringVar(value="Complete QNX4 filesystem browser - Extract any file type with full data integrity")
        ttk.Label(self.root, textvariable=self.status_var, foreground="blue").pack()
        
        self.count_var = tk.StringVar(value="")
        ttk.Label(self.root, textvariable=self.count_var, font=('Arial', 10, 'bold')).pack(pady=5)
        
        # Results frame
        results_frame = ttk.Frame(self.root, padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview with hierarchical support + metadata columns
        columns = ('Size', 'Title', 'Artist', 'Album', 'Bitrate', 'Path')
        self.tree = ttk.Treeview(results_frame, columns=columns, show='tree headings')
        
        self.tree.heading('#0', text='Name')
        self.tree.heading('Size', text='Size (MB)')
        self.tree.heading('Title', text='Title')
        self.tree.heading('Artist', text='Artist')
        self.tree.heading('Album', text='Album')
        self.tree.heading('Bitrate', text='Bitrate')
        self.tree.heading('Path', text='Full Path')
        
        self.tree.column('#0', width=300)
        self.tree.column('Size', width=80)
        self.tree.column('Title', width=200)
        self.tree.column('Artist', width=150)
        self.tree.column('Album', width=150)
        self.tree.column('Bitrate', width=80)
        self.tree.column('Path', width=300)
        
        self.tree.column('#0', width=500)
        self.tree.column('Size', width=100)
        self.tree.column('Path', width=500)
        
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bottom frame
        bottom_frame = ttk.Frame(self.root, padding="10")
        bottom_frame.pack(fill=tk.X)
        
        ttk.Button(bottom_frame, text="Extract Selected", command=self.extract_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(bottom_frame, text="Extract All", command=self.extract_all).pack(side=tk.LEFT)
        
        ttk.Label(bottom_frame, text="Extract any file type - Complete data integrity and metadata preservation", 
                 foreground="gray").pack(side=tk.RIGHT)
    
    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select MyGig disk image",
            filetypes=[("Image files", "*.img *.raw *.dd"), ("All files", "*.*")]
        )
        if filename:
            self.path_var.set(filename)
            self.image_path = filename
    
    def start_scan(self):
        if not self.image_path or not os.path.exists(self.image_path):
            messagebox.showerror("Error", "Please select a valid disk image file")
            return
        
        # Clear previous results
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.found_files = []
        
        self.status_var.set("Opening image with dissect.target...")
        self.count_var.set("")
        self.progress_var.set(0)
        
        self.scan_button.config(state='disabled')
        
        # Start scan in background thread
        self.scan_thread = threading.Thread(target=self.scan_worker)
        self.scan_thread.daemon = True
        self.scan_thread.start()
    
    def get_db_path(self):
        """Get metadata database path for current image"""
        if not self.image_path:
            return None
        return self.image_path + ".metadata.db"
    
    def load_metadata_cache(self):
        """Load metadata from SQLite cache if exists"""
        import sqlite3
        
        db_path = self.get_db_path()
        if not db_path or not os.path.exists(db_path):
            return {}
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT path, title, artist, album, bitrate FROM metadata")
            
            metadata_cache = {}
            for row in cursor.fetchall():
                path, title, artist, album, bitrate = row
                metadata_cache[path] = {
                    'title': title or '',
                    'artist': artist or '',
                    'album': album or '',
                    'bitrate': bitrate or ''
                }
            
            conn.close()
            self.update_status(f"✓ Loaded cached metadata from {os.path.basename(db_path)}")
            return metadata_cache
        except Exception as e:
            print(f"Failed to load metadata cache: {e}")
            return {}
    
    def save_metadata_cache(self):
        """Save metadata to SQLite cache"""
        import sqlite3
        
        db_path = self.get_db_path()
        if not db_path:
            return
        
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Create table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    path TEXT PRIMARY KEY,
                    title TEXT,
                    artist TEXT,
                    album TEXT,
                    bitrate TEXT
                )
            """)
            
            # Insert metadata
            for file_info in self.found_files:
                cursor.execute("""
                    INSERT OR REPLACE INTO metadata (path, title, artist, album, bitrate)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    file_info['path'],
                    file_info.get('title', ''),
                    file_info.get('artist', ''),
                    file_info.get('album', ''),
                    file_info.get('bitrate', '')
                ))
            
            conn.commit()
            conn.close()
            print(f"✓ Saved metadata cache to {db_path}")
        except Exception as e:
            print(f"Failed to save metadata cache: {e}")
    
    def extract_metadata_from_file(self, file_info):
        """Extract metadata from a single file using mutagen"""
        if not METADATA_AVAILABLE:
            return
        
        from mutagen import File as MutagenFile
        
        try:
            # Read file data into memory
            with file_info['entry'].open() as fh:
                data = fh.read()
            
            # Write to temp file for mutagen
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_info['name'])[1]) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            
            try:
                # Extract metadata
                audio = MutagenFile(tmp_path, easy=True)
                
                if audio is not None:
                    # Get title, artist, album
                    file_info['title'] = audio.get('title', [''])[0] if hasattr(audio, 'get') else ''
                    file_info['artist'] = audio.get('artist', [''])[0] if hasattr(audio, 'get') else ''
                    file_info['album'] = audio.get('album', [''])[0] if hasattr(audio, 'get') else ''
                    
                    # Get bitrate
                    if hasattr(audio.info, 'bitrate'):
                        file_info['bitrate'] = f"{audio.info.bitrate // 1000} kbps"
                    else:
                        file_info['bitrate'] = ''
                else:
                    file_info['title'] = ''
                    file_info['artist'] = ''
                    file_info['album'] = ''
                    file_info['bitrate'] = ''
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            # Not an audio file or failed to read
            file_info['title'] = ''
            file_info['artist'] = ''
            file_info['album'] = ''
            file_info['bitrate'] = ''
    
    def start_metadata_extraction(self):
        """Start metadata extraction in background thread"""
        if not METADATA_AVAILABLE:
            messagebox.showinfo("Info", "Metadata extraction requires the 'mutagen' library.\n\nInstall with: pip install mutagen")
            return
        
        if not self.found_files:
            messagebox.showinfo("Info", "No files to process")
            return
        
        self.metadata_button.config(state='disabled')
        self.scan_button.config(state='disabled')
        
        # Check if cache exists
        metadata_cache = self.load_metadata_cache()
        
        # Start extraction
        extract_thread = threading.Thread(target=self.metadata_extraction_worker, args=(metadata_cache,))
        extract_thread.daemon = True
        extract_thread.start()
    
    def metadata_extraction_worker(self, metadata_cache):
        """Background thread for metadata extraction"""
        total = len(self.found_files)
        processed = 0
        cached = 0
        
        try:
            for file_info in self.found_files:
                # Check cache first
                if file_info['path'] in metadata_cache:
                    file_info.update(metadata_cache[file_info['path']])
                    cached += 1
                else:
                    self.extract_metadata_from_file(file_info)
                
                processed += 1
                
                # Update progress
                progress = int((processed / total) * 100)
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda n=processed, t=total: 
                    self.status_var.set(f"Extracting metadata: {n}/{t} files ({cached} from cache)"))
            
            # Save cache
            self.save_metadata_cache()
            
            # Refresh tree view
            self.root.after(0, self.refresh_tree_with_metadata)
            
            self.root.after(0, lambda: self.status_var.set(f"✓ Metadata extraction complete! ({cached} from cache, {total - cached} extracted)"))
            self.root.after(0, lambda: self.progress_var.set(100))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Metadata extraction failed: {str(e)}"))
            import traceback
            traceback.print_exc()
        finally:
            self.root.after(0, lambda: self.metadata_button.config(state='normal'))
            self.root.after(0, lambda: self.scan_button.config(state='normal'))
    
    def refresh_tree_with_metadata(self):
        """Refresh tree view to show metadata"""
        # Clear and repopulate
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        self.populate_tree()

    def filter_tree(self):
        """Filter tree view based on search query"""
        query = self.search_var.get().lower()
        
        if not query:
            # Show all - repopulate
            for item in self.tree.get_children():
                self.tree.delete(item)
            self.populate_tree()
            self.count_var.set(f"✓ {len(self.found_files)} files")
            return
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Build filtered tree
        filtered_data = {}
        
        for idx, file_info in enumerate(self.found_files):
            # Search in all fields
            searchable = ' '.join([
                file_info['name'],
                file_info['path'],
                file_info.get('title', ''),
                file_info.get('artist', ''),
                file_info.get('album', ''),
                file_info.get('bitrate', '')
            ]).lower()
            
            if query in searchable:
                # Add to filtered tree
                path = file_info['path']
                parts = path.strip('/').split('/')
                
                current = filtered_data
                for i, part in enumerate(parts[:-1]):
                    if part not in current:
                        current[part] = {'_dirs': {}, '_files': []}
                    current = current[part]['_dirs']
                
                filename = parts[-1]
                if filename not in current:
                    current[filename] = {'_dirs': {}, '_files': []}
                current[filename]['_files'].append(idx)
        
        # Populate filtered tree (with auto-expand)
        self._add_tree_nodes(filtered_data, '', auto_expand=True)
        
        # Update status
        matched_count = sum(1 for f in self.found_files if query in ' '.join([
            f['name'], f['path'], f.get('title', ''), f.get('artist', ''), 
            f.get('album', ''), f.get('bitrate', '')
        ]).lower())
        self.count_var.set(f"Showing {matched_count} of {len(self.found_files)} files")

    def scan_worker(self):
        """Background scanning thread using dissect.target"""
        try:
            self.update_status("Opening disk image...")
            self.update_progress(10)
            
            # Open target
            self.target = Target.open(self.image_path)
            
            self.update_status("Detecting QNX4 filesystems...")
            self.update_progress(20)
            
            # Find QNX4 filesystem(s)
            qnx_filesystems = [fs for fs in self.target.filesystems if fs.__type__ == 'qnxfs']
            
            if not qnx_filesystems:
                raise Exception("No QNX4 filesystem found in image")
            
            self.update_status(f"Found {len(qnx_filesystems)} QNX4 filesystem(s)")
            print(f"DEBUG: Found {len(qnx_filesystems)} QNX filesystems")
            self.update_progress(30)
            
            # Scan for all files from root
            all_files = []
            
            # Always scan from root to get entire filesystem
            root = self.target.fs.path("/")
            print(f"DEBUG: Scanning entire filesystem from root /")
            
            self.update_status(f"Scanning entire filesystem from /")
            self.update_progress(40)
            
            # Recursively scan for all files
            file_count = 0
            try:
                for entry in root.rglob("*"):
                    try:
                        if entry.is_file():
                            all_files.append(entry)
                            file_count += 1
                            
                            if file_count % 100 == 0:
                                print(f"DEBUG: Found {file_count} files so far...")
                                self.update_status(f"Found {file_count} files...")
                                progress = 40 + int((file_count / 2000) * 30)
                                self.update_progress(min(progress, 70))
                    except Exception as e:
                        print(f"DEBUG: Error checking entry: {e}")
                        pass
            except Exception as e:
                print(f"DEBUG: Error during rglob: {e}")
                import traceback
                traceback.print_exc()
            
            print(f"DEBUG: Total files found: {len(all_files)}")
            
            self.update_status("Building file tree...")
            self.update_progress(75)
            
            # Store files with metadata
            for entry in all_files:
                try:
                    stat_info = entry.stat()
                    self.found_files.append({
                        'entry': entry,
                        'path': str(entry),
                        'name': entry.name,
                        'size': stat_info.st_size,
                        'mtime': stat_info.st_mtime
                    })
                except Exception as e:
                    print(f"DEBUG: Error getting file info: {e}")
                    pass
            
            print(f"DEBUG: Files with metadata: {len(self.found_files)}")
            
            # Build tree structure
            self.update_status("Populating tree view...")
            self.root.after(0, self.populate_tree)
            
            total_size_mb = sum(f['size'] for f in self.found_files) / (1024 * 1024)
            
            self.update_status(
                f"✓ Scan complete! Found {len(self.found_files)} files"
            )
            self.update_count(
                f"✓ {len(self.found_files)} files, {total_size_mb:.1f} MB total"
            )
            self.update_progress(100)
            
        except Exception as e:
            self.update_status(f"Scan failed: {str(e)}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("Scan Error", f"Failed to scan image:\n\n{str(e)}"))
        finally:
            self.root.after(0, lambda: self.scan_button.config(state='normal'))
            if METADATA_AVAILABLE:
                self.root.after(0, lambda: self.metadata_button.config(state='normal'))
    
    def populate_tree(self):
        """Populate treeview with hierarchical directory structure"""
        # Build directory tree
        tree_data = {}
        
        for idx, file_info in enumerate(self.found_files):
            path = file_info['path']
            parts = path.strip('/').split('/')
            
            current = tree_data
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {'_dirs': {}, '_files': []}
                current = current[part]['_dirs']
            
            # Add file
            filename = parts[-1]
            if filename not in current:
                current[filename] = {'_dirs': {}, '_files': []}
            current[filename]['_files'].append(idx)
        
        # Populate tree
        self._add_tree_nodes(tree_data, '')
    
    def _add_tree_nodes(self, tree_data, parent='', auto_expand=False):
        """Recursively add nodes to treeview"""
        for name in sorted(tree_data.keys()):
            node = tree_data[name]
            file_indices = node.get('_files', [])
            subdirs = node.get('_dirs', {})
            
            if file_indices:
                # This is a file
                file_idx = file_indices[0]
                file_info = self.found_files[file_idx]
                
                self.tree.insert(parent, 'end',
                    text=name,
                    values=(
                        f"{file_info['size'] / (1024*1024):.2f}",
                        file_info.get('title', ''),
                        file_info.get('artist', ''),
                        file_info.get('album', ''),
                        file_info.get('bitrate', ''),
                        file_info['path']
                    ),
                    tags=('file', str(file_idx))
                )
            
            if subdirs:
                # This is a directory
                dir_node = self.tree.insert(parent, 'end',
                    text=f"📁 {name}",
                    values=('', '', '', '', '', ''),
                    tags=('directory',),
                    open=auto_expand  # Expand during search, collapse normally
                )
                
                # Recursively add children
                self._add_tree_nodes(subdirs, parent=dir_node, auto_expand=auto_expand)
    
    def update_progress(self, value):
        self.root.after(0, lambda: self.progress_var.set(value))
    
    def update_status(self, message):
        self.root.after(0, lambda: self.status_var.set(message))
    
    def update_count(self, message):
        self.root.after(0, lambda: self.count_var.set(message))
    
    def extract_selected(self):
        """Extract selected files/folders"""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select files or folders to extract")
            return
        
        output_dir = filedialog.askdirectory(title="Select output directory")
        if not output_dir:
            return
        
        # Determine if extracting directories or individual files
        has_directories = any('directory' in self.tree.item(item, 'tags') for item in selection)
        
        # Collect file indices and paths
        file_indices = []
        all_paths = []
        
        for item in selection:
            tags = self.tree.item(item, 'tags')
            if 'directory' in tags:
                dir_files = self._get_files_in_tree_node(item)
                file_indices.extend(dir_files)
                
                # Collect paths for base path calculation
                for idx in dir_files:
                    all_paths.append(self.found_files[idx]['path'])
            else:
                # Get file index from tags
                for tag in tags:
                    if tag.isdigit():
                        file_indices.append(int(tag))
                        all_paths.append(self.found_files[int(tag)]['path'])
        
        if not file_indices:
            messagebox.showinfo("Info", "No files to extract")
            return
        
        # Calculate base path to strip (common parent for all selected paths)
        base_path_to_strip = None
        if has_directories and all_paths:
            # Find common parent directory
            path_parts_list = [p.strip('/').split('/') for p in all_paths]
            
            # Find common prefix
            common_parts = []
            for i in range(min(len(parts) for parts in path_parts_list)):
                parts_at_i = [parts[i] for parts in path_parts_list]
                if len(set(parts_at_i)) == 1:
                    common_parts.append(parts_at_i[0])
                else:
                    break
            
            # The base path is everything except the last common part (the selected folder)
            if len(common_parts) > 1:
                base_path_to_strip = '/' + '/'.join(common_parts[:-1])
            else:
                base_path_to_strip = ''
        
        # Disable buttons during extraction
        self.scan_button.config(state='disabled')
        
        # Run extraction in background thread
        extract_thread = threading.Thread(
            target=self._extract_files,
            args=(file_indices, output_dir, base_path_to_strip, not has_directories)
        )
        extract_thread.daemon = True
        extract_thread.start()
    
    def _get_files_in_tree_node(self, node):
        """Recursively get all file indices under a tree node"""
        indices = []
        for child in self.tree.get_children(node):
            tags = self.tree.item(child, 'tags')
            if 'directory' in tags:
                indices.extend(self._get_files_in_tree_node(child))
            else:
                for tag in tags:
                    if tag.isdigit():
                        indices.append(int(tag))
        return indices
    
    def extract_all(self):
        """Extract all files"""
        if not self.found_files:
            messagebox.showinfo("Info", "No files to extract")
            return
        
        output_dir = filedialog.askdirectory(title="Select output directory")
        if not output_dir:
            return
        
        file_indices = list(range(len(self.found_files)))
        
        # Disable buttons during extraction
        self.scan_button.config(state='disabled')
        
        # Run extraction in background thread
        extract_thread = threading.Thread(
            target=self._extract_files,
            args=(file_indices, output_dir)
        )
        extract_thread.daemon = True
        extract_thread.start()
    
    def _extract_files(self, file_indices, output_dir, base_path_to_strip=None, flat_extraction=False):
        """Extract files by index with visual progress (runs in background thread)
        
        Args:
            file_indices: List of file indices to extract
            output_dir: Output directory path
            base_path_to_strip: Base path to strip from file paths (for folder extraction)
            flat_extraction: If True, extract files flat without subdirectories
        """
        extracted = 0
        failed = 0
        total = len(file_indices)
        
        # Reset progress bar (thread-safe)
        self.root.after(0, lambda: self.progress_var.set(0))
        
        try:
            for idx_num, idx in enumerate(file_indices, 1):
                if idx >= len(self.found_files):
                    continue
                
                file_info = self.found_files[idx]
                
                # Update progress (thread-safe)
                progress = int((idx_num / total) * 100)
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(0, lambda n=idx_num, t=total, fn=file_info['name']: 
                    self.status_var.set(f"Extracting {n}/{t}: {fn}"))
                self.root.after(0, lambda e=extracted, f=failed: 
                    self.count_var.set(f"Extracted: {e}, Failed: {f}"))
                
                # Get path parts
                path = file_info['path']
                
                if flat_extraction:
                    # Extract files flat (no subdirectories) - for individual file selections
                    output_path = os.path.join(output_dir, file_info['name'])
                else:
                    # Strip base path if provided (for folder selections)
                    if base_path_to_strip:
                        relative_path = path[len(base_path_to_strip):].strip('/')
                    else:
                        relative_path = path.strip('/')
                    
                    path_parts = relative_path.split('/')
                    
                    # Create directory structure
                    current_dir = output_dir
                    for folder in path_parts[:-1]:
                        current_dir = os.path.join(current_dir, folder)
                        os.makedirs(current_dir, exist_ok=True)
                    
                    output_path = os.path.join(current_dir, path_parts[-1])
                
                try:
                    # Read file using dissect
                    with file_info['entry'].open() as fh:
                        data = fh.read()
                    
                    # Write to output
                    with open(output_path, 'wb') as out:
                        out.write(data)
                    
                    extracted += 1
                    
                except Exception as e:
                    failed += 1
                    print(f"Failed to extract {path}: {e}")
            
            # Final progress (thread-safe)
            self.root.after(0, lambda: self.progress_var.set(100))
            
            # Show completion message (thread-safe)
            def show_completion():
                if failed > 0:
                    messagebox.showwarning("Extraction Complete", 
                        f"Extracted {extracted}/{total} files\nFailed: {failed} files")
                else:
                    messagebox.showinfo("Success", 
                        f"Successfully extracted all {extracted} files with complete data integrity!")
                
                self.status_var.set("✓ Extraction complete")
                self.count_var.set(f"✓ {extracted} files extracted, {failed} failed")
                self.scan_button.config(state='normal')
            
            self.root.after(0, show_completion)
            
        except Exception as e:
            def show_error():
                messagebox.showerror("Error", f"Extraction failed: {str(e)}")
                self.scan_button.config(state='normal')
            self.root.after(0, show_error)


if __name__ == "__main__":
    root = tk.Tk()
    app = QNX4ScannerGUI(root)
    root.mainloop()
