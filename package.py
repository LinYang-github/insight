import os
import subprocess
import sys
import shutil

def build_frontend():
    """Build the frontend distribution files."""
    print("==== Step 1: Building Frontend ====")
    frontend_dir = os.path.join(os.getcwd(), 'frontend')
    if not os.path.exists(frontend_dir):
        print(f"Error: Frontend directory not found at {frontend_dir}")
        sys.exit(1)
    
    try:
        # 1. Install dependencies
        print("Installing npm dependencies...")
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True)
        
        # 2. Build production assets
        print("Running npm run build...")
        subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error during frontend build: {e}")
        sys.exit(1)

def package_project():
    """Package the backend and frontend into a single executable using PyInstaller."""
    print("\n==== Step 2: Packaging with PyInstaller ====")
    
    # PyInstaller separator: ';' for Windows, ':' for Unix
    sep = os.pathsep
    
    # We want to bundle frontend/dist into the executable
    # The first part is the source path, the second is the path inside the bundle (relative to sys._MEIPASS)
    add_data = f"frontend/dist{sep}frontend/dist"
    
    # PyInstaller command
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onefile',           # Single executable file
        '--name', 'insight',   # Name of the output file
        '--add-data', add_data,
        '--paths', 'backend',   # Add backend to python path for 'app' imports
        '--clean',
        'backend/run.py'       # Entry point
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        print("\n==== Packaging Complete ====")
        print(f"The standalone executable 'insight' is ready in the 'dist/' folder.")
        print("You can move this file anywhere. Data (insight.db, data/) will be created in its current directory.")
    except subprocess.CalledProcessError as e:
        print(f"Error during packaging: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("Error: PyInstaller not found. Please install it using 'pip install pyinstaller'.")
        sys.exit(1)

if __name__ == "__main__":
    # Ensure we are in the project root
    if not os.path.exists('backend') or not os.path.exists('frontend'):
        print("Error: Please run this script from the project root directory (insight/).")
        sys.exit(1)
        
    build_frontend()
    package_project()
