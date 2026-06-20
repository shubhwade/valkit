import os

path = r"c:\Users\Shubh\OneDrive\Documents\Desktop\telmus\telmus\__init__.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("0.1.13", "0.1.14")
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

path = r"c:\Users\Shubh\OneDrive\Documents\Desktop\telmus\pyproject.toml"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("0.1.13", "0.1.14")
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

path = r"c:\Users\Shubh\OneDrive\Documents\Desktop\telmus\docs\changelog.md"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()
content = content.replace("## v0.1.13 - Dashboard Layout and Versioning Polish", "## v0.1.14 - Terminal ASCII Charts\n- Added native ASCII bar charts directly in the terminal for `scan` and `compare` commands\n- Added Unicode fallback handling for legacy Windows terminals\n\n## v0.1.13 - Dashboard Layout and Versioning Polish")
with open(path, "w", encoding="utf-8") as f:
    f.write(content)

print("Version bumped to 0.1.14")
