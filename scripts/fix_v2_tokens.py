import os
from pathlib import Path

def fix_placeholder_bug(directory: Path):
    print(f"Scanning directory: {directory}")
    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue
            
            filepath = Path(root) / file
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            old_str = 'or "ya29" in normalized'
            new_str = 'or normalized == "ya29...."'
            
            if old_str in content:
                content = content.replace(old_str, new_str)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Fixed: {filepath}")

if __name__ == "__main__":
    v2_dir = Path("backend/tools/integration_tools_v2")
    fix_placeholder_bug(v2_dir)
    print("Done fixing token validation bug in V2 tools.")
