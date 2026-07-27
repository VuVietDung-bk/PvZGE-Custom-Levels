import json
import sys
import os

def convert_lod_json(old_path, new_path):
    # Kiểm tra file input tồn tại
    if not os.path.exists(old_path):
        print(f"❌ Lỗi: Không tìm thấy file '{old_path}'")
        sys.exit(1)

    # Đọc file JSON gốc
    with open(old_path, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ Lỗi JSON: {e}")
            sys.exit(1)

    objects = data.get("objects", [])
    new_objects = []
    dynamic_zombies = []
    wave_manager_props_ref = None
    waves_per_flag = None
    wave_count = None

    print("🔍 Đang xử lý file...")

    # 1️⃣ Ghi nhớ giá trị gốc từ LevelOfTheDayModuleProperties
    for obj in objects:
        if obj.get("objclass") == "LevelOfTheDayModuleProperties":
            objdata = obj["objdata"]
            point_increment = objdata.get("PointIncrementPerWave", 200)
            starting_points = objdata.get("StartingPoints", 200)
            zombie_pool = objdata.get("ZombiePool", [])
            wave_manager_props_ref = objdata.get("WaveManagerProps")
            waves_per_flag = objdata.get("WavesPerFlag")

            print(f"➡️  Đã ghi nhận PointIncrementPerWave={point_increment}, StartingPoints={starting_points}, WavesPerFlag={waves_per_flag}")

            # Ghi giá trị này vào DynamicZombies (append)
            for i in range(3):
                dynamic_zombies.append({})
            for i in range(4):
                dynamic_zombies.append({
                    "PointIncrementPerWave": point_increment,
                    "StartingPoints": starting_points,
                    "StartingWave": 0,
                    "ZombiePool": zombie_pool
                })
        else:
            new_objects.append(obj)

    # 2️⃣ Đọc số lượng Waves từ WaveManagerProps
    for obj in new_objects:
        if obj.get("aliases") == ["WaveManagerProps"]:
            objdata = obj.get("objdata", {})
            waves = objdata.get("Waves", [])
            wave_count = len(waves)
            print(f"➡️  Đã phát hiện WaveCount={wave_count} từ WaveManagerProps")

            # Ghi thêm FlagWaveInterval và WaveCount
            if waves_per_flag is not None:
                objdata["FlagWaveInterval"] = waves_per_flag
            objdata["WaveCount"] = wave_count

    # 3️⃣ Cập nhật LevelDefinition (thêm WrittenBy, MusicType, xóa VictoryModule)
    for obj in new_objects:
        if obj.get("objclass") == "LevelDefinition":
            objdata = obj["objdata"]
            if "VictoryModule" in objdata:
                print("➡️  Xóa VictoryModule khỏi LevelDefinition")
                objdata.pop("VictoryModule")

            objdata.setdefault("WrittenBy", "hinanarukami")
            objdata.setdefault("MusicType", "MiniGame_A")

    # 4️⃣ Thêm DynamicPlantfood cho các Wave có AdditionalPlantfood
    for obj in new_objects:
        objdata = obj.get("objdata", {})
        if "AdditionalPlantfood" in objdata:
            if "DynamicPlantfood" not in objdata:
                objdata["DynamicPlantfood"] = [0, 0, 0, 1, 1, 1, 1]
                print(f"🌿  Thêm DynamicPlantfood vào {obj.get('aliases')}")

    # 5️⃣ Tạo object NewWaves mới
    new_waves_obj = {
        "aliases": ["NewWaves"],
        "objclass": "WaveManagerModuleProperties",
        "objdata": {
            "WaveManagerProps": wave_manager_props_ref or "RTID(WaveManagerProps@CurrentLevel)",
            "DynamicZombies": dynamic_zombies
        }
    }

    # 6️⃣ Thay thế hoặc thêm NewWaves
    final_objects = []
    replaced = False
    for obj in new_objects:
        if obj.get("aliases") == ["NewWaves"]:
            print("➡️  Thay thế object NewWaves cũ bằng phiên bản mới")
            final_objects.append(new_waves_obj)
            replaced = True
        else:
            final_objects.append(obj)

    if not replaced:
        print("➡️  Không tìm thấy NewWaves cũ, thêm object mới vào cuối danh sách")
        final_objects.append(new_waves_obj)

    # Cập nhật lại danh sách object
    data["objects"] = final_objects

    # 7️⃣ Ghi file kết quả
    with open(new_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print(f"✅ Đã chuyển đổi thành công! File mới lưu tại: {new_path}")


def main():
    if len(sys.argv) != 3:
        print("⚙️  Cách dùng:")
        print("   python convert_lod.py <đường_dẫn_input.json> <đường_dẫn_output.json>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]
    convert_lod_json(input_path, output_path)


if __name__ == "__main__":
    main()