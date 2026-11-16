# Otevře emulate.py a Aurela.py naráz. Každé okno je vlastní program.
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
apps = root / "apps"
pythonw = Path(sys.executable).with_name("pythonw.exe")
runner = pythonw if pythonw.exists() else Path(sys.executable)

for name in ("emulate.py", "Aurela.py"):
    subprocess.Popen([str(runner), str(apps / name)], cwd=root)
