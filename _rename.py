"""One-off rename script: intelliwrite -> neo-scripting."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))

# Order matters: more-specific patterns first
REPLACEMENTS = [
    ("INTELLIWRITE", "NEO SCRIPTING"),
    ("IntelliWrite", "Neo Scripting"),
    ("Intelliwrite", "Neo Scripting"),
    ("intelliwrite-mcp", "neo-scripting-mcp"),
    ("intelliwrite-neon", "neo-scripting-neon"),
    ("intelliwrite-api", "neo-scripting-api"),
    ("intelliwrite-frontend", "neo-scripting-frontend"),
    ("intelliwrite.ai", "neo-scripting.ai"),
    ("intelliwrite_", "neo_scripting_"),
    ("intelliwrite", "neo-scripting"),
]

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
SKIP_FILES = {"_rename.py"}
# Binary/lock files we still want to edit text-in-place: package-lock.json is fine.
# Skip actual binaries.
BINARY_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".woff", ".woff2", ".ttf"}

def process_file(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in BINARY_EXTS:
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, PermissionError):
        return False
    original = content
    for old, new in REPLACEMENTS:
        content = content.replace(old, new)
    if content != original:
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        return True
    return False

changed = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for fn in filenames:
        if fn in SKIP_FILES:
            continue
        full = os.path.join(dirpath, fn)
        if process_file(full):
            changed.append(os.path.relpath(full, ROOT))

for c in changed:
    print(c)
print(f"\nTotal files changed: {len(changed)}")
