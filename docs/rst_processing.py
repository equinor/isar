from pathlib import Path

src_dir = Path("source/api")

for file in src_dir.iterdir():
    print(f"Processing .rst-file: {file}")

    with open(file, "r") as f:
        lines = f.read()

    remove_strs = ["Submodules\n----------", "Subpackages\n-----------"]

    for remove_str in remove_strs:
        lines = lines.replace(remove_str, "")

    lines = lines.replace(" module\n=", "\n")
    lines = lines.replace(" package\n=", "\n")

    with open(file, "w") as f:
        f.write(lines)
