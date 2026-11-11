"""Delete only this build's private workspace, never application data or AWS state."""
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[2]
target = root / 'ci-private'
if target.is_symlink() or target.resolve().parent != root.resolve():
    raise SystemExit('Refusing unsafe private-directory cleanup')
if target.exists():
    shutil.rmtree(target)
