"""
Script: wrap_wave_scheduler.py
Mục đích: Duyệt tất cả file .json5 trong My Levels, tìm các RTID references xuất hiện
nhiều lần trong WaveManagerProps (alias "WaveManagerProps" với objclass WaveManagerProperties),
kiểm tra xem objclass của chúng có phải SpawnZombiesJitteredWaveActionProps không,
nếu đúng thì wrap bằng WaveSchedulerProps.

Logic:
- Wrap: Đổi alias SpawnZombies từ [RefName] -> [RefNameZom], thêm WaveSchedulerProps
  với alias [RefName] trỏ đến RTID(RefNameZom@CurrentLevel)
- Waves không cần thay đổi vì WaveScheduler mang alias cũ
- Xử lý từ object cuối lên đầu để tránh offset khi chèn text
"""

import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(r"C:\Users\admin\Downloads\PvZGE custom levels\My Levels")


def strip_comments(text: str) -> str:
    """Loai bo comment // va /* */ de parse JSON."""
    result = []
    i = 0
    in_string = False
    while i < len(text):
        c = text[i]
        if in_string:
            result.append(c)
            if c == '\\':
                i += 1
                if i < len(text):
                    result.append(text[i])
            elif c == '"':
                in_string = False
            i += 1
        else:
            if c == '"':
                in_string = True
                result.append(c)
                i += 1
            elif text[i:i+2] == '//':
                while i < len(text) and text[i] != '\n':
                    result.append(' ')
                    i += 1
            elif text[i:i+2] == '/*':
                i += 2
                while i < len(text) and text[i:i+2] != '*/':
                    if text[i] == '\n':
                        result.append('\n')
                    else:
                        result.append(' ')
                    i += 1
                i += 2
            else:
                result.append(c)
                i += 1
    return ''.join(result)


def remove_trailing_commas(text: str) -> str:
    return re.sub(r',(\s*[\}\]])', r'\1', text)


def parse_json5(text: str):
    import json
    cleaned = strip_comments(text)
    cleaned = remove_trailing_commas(cleaned)
    return json.loads(cleaned)


def find_objects_array_start(text: str) -> int:
    idx = text.find('"objects"')
    if idx < 0:
        return -1
    idx = text.find('[', idx)
    return idx


def find_nth_object_in_array(text: str, array_start: int, n: int) -> tuple:
    """
    Tim object thu n (0-indexed) trong mang JSON bat dau tai array_start.
    Tra ve (start, end) cua block { ... }.
    Chay trong text goc (co comment), dem ngoac chinh xac.
    """
    i = array_start + 1
    obj_count = 0

    while i < len(text):
        while i < len(text) and text[i] in ' \t\n\r':
            i += 1

        if i >= len(text) or text[i] == ']':
            break

        if text[i] == '{':
            obj_start = i
            depth = 0
            in_str = False
            j = i
            while j < len(text):
                c = text[j]
                if in_str:
                    if c == '\\':
                        j += 1
                    elif c == '"':
                        in_str = False
                elif c == '"':
                    in_str = True
                elif c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        obj_end = j + 1
                        if obj_count == n:
                            return obj_start, obj_end
                        obj_count += 1
                        i = obj_end
                        break
                j += 1
            else:
                break
        elif text[i] == ',':
            i += 1
        else:
            i += 1

    return -1, -1


def get_indent_at(text: str, pos: int) -> str:
    """Lay indent (khoang trang) cua dong chua vi tri pos."""
    line_start = text.rfind('\n', 0, pos)
    if line_start < 0:
        line_start = 0
    else:
        line_start += 1
    indent = ''
    for ch in text[line_start:pos]:
        if ch in (' ', '\t'):
            indent += ch
        else:
            break
    return indent


def format_scheduler_indented(alias: str, zom_name: str, indent: str) -> str:
    return (
        f'{indent}{{\n'
        f'{indent}  "aliases": [\n'
        f'{indent}    "{alias}"\n'
        f'{indent}  ],\n'
        f'{indent}  "objclass": "WaveSchedulerProps",\n'
        f'{indent}  "objdata": {{\n'
        f'{indent}    "TimeBeforeFirst": {{\n'
        f'{indent}      "Max": 0.1,\n'
        f'{indent}      "Min": 0.1\n'
        f'{indent}    }},\n'
        f'{indent}    "TimeBetween": {{\n'
        f'{indent}      "Max": 1,\n'
        f'{indent}      "Min": 1\n'
        f'{indent}    }},\n'
        f'{indent}    "Repeat": {{\n'
        f'{indent}      "Max": 1,\n'
        f'{indent}      "Min": 1\n'
        f'{indent}    }},\n'
        f'{indent}    "RewardWhenEnded": false,\n'
        f'{indent}    "SuppressRewardState": false,\n'
        f'{indent}    "Events": ["RTID({zom_name}@CurrentLevel)"]\n'
        f'{indent}  }}\n'
        f'{indent}}}'
    )


def do_wrap_all(text: str, wraps: list) -> tuple:
    """
    wraps: list of (obj_index_in_objects_array, ref_name, new_zom_name)
    Xu ly tu object co index cao nhat xuong thap nhat de tranh offset.
    Tra ve (new_text, list_of_success_names)
    """
    import json
    # Parse de lay objects
    try:
        data = parse_json5(text)
    except Exception as e:
        return text, []

    objects = data.get("objects", [])
    objects_start = find_objects_array_start(text)
    if objects_start < 0:
        return text, []

    # Sap xep wrap theo index giam dan (xu ly tu cuoi len dau)
    wraps_sorted = sorted(wraps, key=lambda x: x[0], reverse=True)

    success = []
    modified = text

    for obj_idx, ref_name, new_zom_name in wraps_sorted:
        # Tim lai objects_start trong modified text (co the thay doi vi tri)
        objects_start_cur = find_objects_array_start(modified)
        if objects_start_cur < 0:
            continue

        block_start, block_end = find_nth_object_in_array(modified, objects_start_cur, obj_idx)
        if block_start < 0:
            print(f"    [{ref_name}] Khong tim duoc block tai index {obj_idx}")
            continue

        block_text = modified[block_start:block_end]

        # Doi alias ref_name -> new_zom_name trong block (chi lan dau tien)
        old_pat = re.compile(r'("aliases"\s*:\s*\[(?:[^"]*"[^"]*")*?[^"]*)"' + re.escape(ref_name) + r'"')
        # Cach don gian hon: doi "RefName" -> "RefNameZom" trong phan aliases
        # Tim vi tri cua "aliases" trong block roi doi
        aliases_match = re.search(r'"aliases"\s*:\s*\[([^\]]*)\]', block_text)
        if not aliases_match:
            print(f"    [{ref_name}] Khong tim duoc aliases trong block")
            continue

        old_aliases_section = aliases_match.group(0)
        new_aliases_section = old_aliases_section.replace(f'"{ref_name}"', f'"{new_zom_name}"', 1)
        if old_aliases_section == new_aliases_section:
            print(f"    [{ref_name}] Khong doi duoc alias")
            continue

        new_block_text = block_text.replace(old_aliases_section, new_aliases_section, 1)

        # Lay indent
        indent = get_indent_at(modified, block_start)

        # Tao scheduler text
        scheduler_text = format_scheduler_indented(ref_name, new_zom_name, indent)

        # Tim dau phay sau block (neu co)
        after_block = modified[block_end:]
        p = 0
        while p < len(after_block) and after_block[p] in ' \t\n\r':
            p += 1

        if p < len(after_block) and after_block[p] == ',':
            # Co dau phay sau block: giu nguyen dau phay do, chen scheduler sau no
            # Ket qua: ...new_block,\n    scheduler,\n    next_obj...
            comma_abs_pos = block_end + p  # vi tri dau phay trong modified
            # Phan truoc scheduler: tu dau den het dau phay
            before = modified[:block_start] + new_block_text + modified[block_end:comma_abs_pos + 1]
            # Phan sau scheduler: phan con lai
            after = modified[comma_abs_pos + 1:]
            modified = before + "\n" + scheduler_text + "," + after
        else:
            # Khong co dau phay (object cuoi hoac trailing comma JSON5)
            # Kiem tra xem ky tu tiep theo co phai ] khong
            if p < len(after_block) and after_block[p] == ']':
                # Object cuoi: them dau phay sau block de chen scheduler, giu trailing comma
                modified = (
                    modified[:block_start] +
                    new_block_text +
                    ",\n" + scheduler_text + "\n" +
                    modified[block_end:]
                )
            else:
                modified = (
                    modified[:block_start] +
                    new_block_text +
                    ",\n" + scheduler_text +
                    modified[block_end:]
                )

        success.append(ref_name)
        print(f"    [{ref_name}] Wrap thanh cong (index {obj_idx})")

    return modified, success


def process_file(filepath: Path) -> tuple:
    """Xu ly mot file. Tra ve (changed, report)."""
    original_text = filepath.read_text(encoding="utf-8")

    try:
        data = parse_json5(original_text)
    except Exception as e:
        return False, f"  [SKIP] Parse error: {e}"

    objects = data.get("objects", [])
    if not objects:
        return False, "  [SKIP] Khong co objects"

    # Tim WaveManagerProperties
    wave_manager = None
    wave_module = None
    for obj in objects:
        if obj.get("objclass") == "WaveManagerProperties":
            wave_manager = obj
        if obj.get("objclass") == "WaveManagerModuleProperties":
            wave_module = obj

    if not wave_manager:
        return False, "  [SKIP] Khong tim thay WaveManagerProperties"

    # Skip neu WaveManagerModuleProperties khong co DynamicZombies
    if wave_module is None:
        return False, "  [SKIP] Khong co WaveManagerModuleProperties"
    dynamic_zombies = wave_module.get("objdata", {}).get("DynamicZombies", [])
    has_dynamic = any(isinstance(dz, dict) and len(dz) > 0 for dz in dynamic_zombies)
    if not has_dynamic:
        return False, "  [SKIP] WaveManagerModuleProperties khong co DynamicZombies hop le"


    waves = wave_manager.get("objdata", {}).get("Waves", [])
    if not waves:
        return False, "  [SKIP] Khong co Waves"

    # Dem RTID(@CurrentLevel)
    rtid_pattern = re.compile(r'RTID\((\w+)@CurrentLevel\)')
    ref_counter = Counter()
    for wave in waves:
        if isinstance(wave, list):
            for ref in wave:
                if isinstance(ref, str):
                    m = rtid_pattern.match(ref)
                    if m:
                        ref_counter[m.group(1)] += 1
        elif isinstance(wave, str):
            m = rtid_pattern.match(wave)
            if m:
                ref_counter[m.group(1)] += 1

    repeated = [name for name, cnt in ref_counter.items() if cnt >= 2]
    if not repeated:
        return False, "  [SKIP] Khong co reference nao xuat hien >= 2 lan"

    print(f"  Repeated: {repeated}")

    # Map alias -> (index, obj)
    alias_to_info = {}
    for i, obj in enumerate(objects):
        for alias in obj.get("aliases", []):
            alias_to_info[alias] = (i, obj)

    wraps = []  # (obj_idx, ref_name, new_zom_name)

    for ref_name in repeated:
        info = alias_to_info.get(ref_name)
        if info is None:
            print(f"  [{ref_name}] Khong tim thay object")
            continue

        obj_idx, obj = info
        objclass = obj.get("objclass", "")

        if objclass != "SpawnZombiesJitteredWaveActionProps":
            print(f"  [{ref_name}] objclass = {objclass!r} (bo qua)")
            continue

        # Kiem tra da co WaveSchedulerProps nao reference den ref_name chua
        already_wrapped = False
        for o in objects:
            if o.get("objclass") == "WaveSchedulerProps":
                events = o.get("objdata", {}).get("Events", [])
                for ev in events:
                    if isinstance(ev, str) and f"RTID({ref_name}@CurrentLevel)" in ev:
                        already_wrapped = True
                        break
                # Cung check alias cua WaveScheduler
                if ref_name in o.get("aliases", []):
                    already_wrapped = True
                    break
            if already_wrapped:
                break

        if already_wrapped:
            print(f"  [{ref_name}] Da duoc wrap roi (bo qua)")
            continue

        # Skip neu co AdditionalPlantfood (PlantFoodSpawner)
        objdata = obj.get("objdata", {})
        if objdata.get("AdditionalPlantfood") is not None:
            print(f"  [{ref_name}] Co AdditionalPlantfood -> BAO CAO THU CONG (skip wrap)")
            continue

        new_zom_name = ref_name + "Zom"
        print(f"  [{ref_name}] SE WRAP -> [{new_zom_name}] + WaveScheduler[{ref_name}]")
        wraps.append((obj_idx, ref_name, new_zom_name))

    if not wraps:
        return False, "  Khong co gi can wrap"

    modified_text, success_names = do_wrap_all(original_text, wraps)

    if success_names:
        filepath.write_text(modified_text, encoding="utf-8")
        return True, f"  Da wrap thanh cong: {success_names}"
    else:
        return False, "  Wrap that bai (tat ca deu that bai)"



def find_all_json5_files(root: Path):
    return sorted(root.rglob("*.json5"))


def main():
    files = find_all_json5_files(ROOT)
    print(f"Tim thay {len(files)} file .json5\n")

    total_changed = 0
    changed_files = []

    for filepath in files:
        rel = filepath.relative_to(ROOT)
        print(f"[{rel}]")
        changed, report = process_file(filepath)
        print(report)
        if changed:
            total_changed += 1
            changed_files.append(str(rel))
            print(f"  => DA CAP NHAT FILE")
        print()

    print(f"\n{'='*60}")
    print(f"TONG KET: {total_changed}/{len(files)} file duoc cap nhat")
    if changed_files:
        print("\nDanh sach file da thay doi:")
        for f in changed_files:
            print(f"  - {f}")


if __name__ == "__main__":
    main()
