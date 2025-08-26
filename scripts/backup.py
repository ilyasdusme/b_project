import os
import shutil
from datetime import datetime


def main():
    # Project root (this file is in scripts/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    db_path = os.path.join(base_dir, 'blog.db')
    images_src = os.path.join(base_dir, 'static', 'images')

    backups_dir = os.path.join(base_dir, 'backups')
    os.makedirs(backups_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    target_dir = os.path.join(backups_dir, timestamp)
    os.makedirs(target_dir, exist_ok=True)

    # Copy database
    if os.path.exists(db_path):
        shutil.copy2(db_path, os.path.join(target_dir, 'blog.db'))
        print(f"[OK] Copied database to {os.path.join(target_dir, 'blog.db')}")
    else:
        print("[WARN] blog.db not found; skipping DB backup")

    # Copy images folder (if exists)
    if os.path.isdir(images_src):
        images_dst = os.path.join(target_dir, 'images')
        shutil.copytree(images_src, images_dst)
        print(f"[OK] Copied images to {images_dst}")
    else:
        print("[WARN] static/images/ not found; skipping images backup")

    # Additionally, create a zip archive of this backup directory for easy download
    zip_base = os.path.join(backups_dir, f"backup-{timestamp}")
    archive_path = shutil.make_archive(zip_base, 'zip', target_dir)
    print(f"[OK] Created archive: {archive_path}")

    print("[DONE] Backup completed successfully.")


if __name__ == '__main__':
    main()
