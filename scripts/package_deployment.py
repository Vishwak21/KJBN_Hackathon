"""Create a source + compiled UI zip for console-based deployment."""

import subprocess
import zipfile
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[1]
npm = shutil.which("npm.cmd") or shutil.which("npm")
subprocess.run([npm, "ci"], cwd=root / "frontend", check=True)
subprocess.run([npm, "run", "build"], cwd=root / "frontend", check=True)
files = subprocess.check_output(["git", "ls-files"], cwd=root, text=True).splitlines()
with zipfile.ZipFile(root / "deployment-bundle.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        path = root / name
        if path.is_file():
            archive.write(path, name)
    for path in (root / "frontend" / "dist").rglob("*"):
        if path.is_file():
            archive.write(path, path.relative_to(root))
print("Created deployment-bundle.zip (no environment file or database).")
