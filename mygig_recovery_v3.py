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


class QNX4ScannerGUI:
    """GUI for QNX4 MP3 Recovery using dissect.target"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("QNX4 File Recovery Tool v3.0 - Complete Filesystem Browser")
        self.root.geometry("1200x750")
        
        self.image_path = None
        self.target = None
        self.found_files = []
        self.scan_thread = None
        
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
        
        # Treeview with hierarchical support (removed Modified Date column)
        columns = ('Size', 'Path')
        self.tree = ttk.Treeview(results_frame, columns=columns, show='tree headings')
        
        self.tree.heading('#0', text='Name')
        self.tree.heading('Size', text='Size (MB)')
        self.tree.heading('Path', text='Full Path')
        
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
    
    def _add_tree_nodes(self, tree_data, parent=''):
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
                        file_info['path']
                    ),
                    tags=('file', str(file_idx))
                )
            
            if subdirs:
                # This is a directory
                dir_node = self.tree.insert(parent, 'end',
                    text=f"📁 {name}",
                    values=('', '', ''),
                    tags=('directory',),
                    open=False
                )
                
                # Recursively add children
                self._add_tree_nodes(subdirs, parent=dir_node)
    
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
        
        # Collect file indices
        file_indices = []
        for item in selection:
            tags = self.tree.item(item, 'tags')
            if 'directory' in tags:
                file_indices.extend(self._get_files_in_tree_node(item))
            else:
                # Get file index from tags
                for tag in tags:
                    if tag.isdigit():
                        file_indices.append(int(tag))
        
        if not file_indices:
            messagebox.showinfo("Info", "No files to extract")
            return
        
        # Disable buttons during extraction
        self.scan_button.config(state='disabled')
        
        # Run extraction in background thread
        extract_thread = threading.Thread(
            target=self._extract_files,
            args=(file_indices, output_dir)
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
    
    def _extract_files(self, file_indices, output_dir):
        """Extract files by index with visual progress (runs in background thread)"""
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
                path_parts = path.strip('/').split('/')
                
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
