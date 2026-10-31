from pathlib import Path
import hashlib
import shutil

project = Path("/Users/kacperwarych/Desktop/hackathon reactive ai")
staged = Path("/Users/kacperwarych/Documents/ChatGPT/hackathon reactive ai/outputs/investigation-implementation")
app = project / "app.py"
assert hashlib.sha256(app.read_bytes()).hexdigest() == "43152ca2f77554556240cafc9b07231454870b6cc26762a3a74f808ea6c75857", "app.py changed; rebase the integration before installing"
shutil.copy2(app, Path("/tmp/decision-investigation-app-before.py"))
files = [("investigations.py", "src/decision_memory/investigations.py"),
         ("investigation_ui.py", "src/decision_memory/investigation_ui.py"),
         ("test_investigations.py", "tests/test_investigations.py"),
         ("test_investigation_ui.py", "tests/test_investigation_ui.py"),
         ("INVESTIGATIONS.md", "INVESTIGATIONS.md"),
         ("app.py", "app.py")]
for source, destination in files:
    target = project / destination
    if source != "app.py":
        assert not target.exists(), f"New file already exists: {target}"
for source, destination in files:
    shutil.copy2(staged / source, project / destination)
print("Installed 2 modules, 2 test files, investigation guide, and coordinated app integration.")
