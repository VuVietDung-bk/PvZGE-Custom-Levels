import os
import json
import json5  # pip install json5

def collect_objclasses(root_folder):
    """
    Scan all .json and .json5 files under root_folder recursively,
    extract every "objclass" value,
    and save the unique ones into collected_objclasses.json.
    """
    collected = set()
    total_files = 0
    matched_files = 0

    for dirpath, _, filenames in os.walk(root_folder):
        for fname in filenames:
            if not fname.lower().endswith((".json", ".json5")):
                continue

            total_files += 1
            fpath = os.path.join(dirpath, fname)

            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                try:
                    data = json.loads(content)
                except Exception:
                    # fallback: parse as JSON5
                    data = json5.loads(content)

                # recursively find all objclass keys
                stack = [data]
                found = False
                while stack:
                    node = stack.pop()
                    if isinstance(node, dict):
                        if "objclass" in node:
                            collected.add(node["objclass"])
                            found = True
                        stack.extend(node.values())
                    elif isinstance(node, list):
                        stack.extend(node)
                if found:
                    matched_files += 1

            except Exception as e:
                print(f"[!] Error reading {fpath}: {e}")

    print(f"\n✅ Scanned {total_files} files. Found 'objclass' in {matched_files} files.\n")
    print("=== Unique objclass values detected ===")
    for c in sorted(collected):
        print(c)
    print("\nTotal unique objclass:", len(collected))

    # Save as JSON
    output_path = os.path.join(os.getcwd(), "collected_objclasses.json")
    try:
        with open(output_path, "w", encoding="utf-8") as outfile:
            json.dump(sorted(list(collected)), outfile, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved result to: {output_path}")
    except Exception as e:
        print(f"[!] Failed to save JSON: {e}")

if __name__ == "__main__":
    folder = input("Enter folder path to scan: ").strip()
    if not os.path.isdir(folder):
        print("❌ Invalid folder path.")
    else:
        collect_objclasses(folder)