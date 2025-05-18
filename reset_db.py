import os
import shutil

# Path to the database file
db_path = 'instance/mealmap.db'

if os.path.exists(db_path):
    print(f"Removing existing database at {db_path}...")
    os.remove(db_path)
    print("Database removed successfully.")
else:
    print("No existing database found.")

# Also remove any -journal or -wal files
for ext in ['-journal', '-wal', '-shm']:
    path = f"{db_path}{ext}"
    if os.path.exists(path):
        os.remove(path)
        print(f"Removed {path}")

print("Database reset complete. Run app.py to create a fresh database.")
