
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import app modules if needed, 
# but simple script might just inspect DB directly or use app context.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.dataset import Dataset

def cleanup_orphaned_files(dry_run=True):
    """
    Scan uploads directory and delete files that are not referenced by any Dataset record.
    """
    app = create_app()
    with app.app_context():
        # 1. Get all valid file paths from DB
        datasets = Dataset.query.all()
        # Normalize paths to absolute
        valid_paths = set()
        for ds in datasets:
            if ds.filepath:
                valid_paths.add(os.path.abspath(ds.filepath))
        
        print(f"Found {len(valid_paths)} referenced files in Database.")
        
        # 2. Scan Upload Directory
        # Assuming uploads are in the base directory of where datasets are stored.
        # We need to know where PROJECT_ROOT/uploads is.
        # Let's infer one path from DB to find the root, or use Config.
        # Ideally, look at Config.UPLOAD_FOLDER if it existed, or just common locations.
        # Based on previous context, files are likely in `backend/uploads` or user specified.
        # Let's check a sample dataset or just assume `backend/uploads` relative to this script.
        
        base_upload_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../uploads'))
        if not os.path.exists(base_upload_dir):
            print(f"Upload directory {base_upload_dir} does not exist. Nothing to clean.")
            return

        orphaned_files = []
        for root, dirs, files in os.walk(base_upload_dir):
            for file in files:
                if file.startswith('.'): continue # Skip hidden files
                full_path = os.path.abspath(os.path.join(root, file))
                
                if full_path not in valid_paths:
                    orphaned_files.append(full_path)
        
        print(f"Found {len(orphaned_files)} orphaned files.")
        
        for f in orphaned_files:
            if dry_run:
                print(f"[Dry Run] would delete: {f}")
            else:
                try:
                    os.remove(f)
                    print(f"Deleted: {f}")
                except Exception as e:
                    print(f"Error deleting {f}: {e}")

if __name__ == "__main__":
    dry_run = '--dry-run' in sys.argv
    cleanup_orphaned_files(dry_run=dry_run)
    if dry_run:
        print("\nRun without --dry-run to actually delete files.")
