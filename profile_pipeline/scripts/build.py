"""
插件打包脚本。

用法：
 python3 scripts/build.py <plugin_dir> <output_zip>

例：
 python3 scripts/build.py profile_generator /tmp/profile_generator.zip

行为：
 1. 读 plugin_dir/metadata.yaml 当前版本号
 2. 生成新版本号 = 当前基础号 + 秒级时间戳（HHMMSS）
    例：0.2.0 → 0.2.0-20260915-143022
    每次打包都会变（秒级粒度）
 3. 同步写入 metadata.yaml 和 main.py 的 @register
 4. 打包 zip（含 subdir 结构）
 5. 打印 git add 提示

版本号格式：MAJOR.MINOR.PATCH-YYYYMMDD-HHMMSS
"""

import argparse
import re
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path


DATETIME_FMT = "%Y%m%d-%H%M%S"
# 匹配：
#   0.2.0
#   0.2.0-20260915（旧格式，只有日期）
#   0.2.0-20260915-143022（新格式，日期+时间）
VERSION_PATTERN = re.compile(
    r"^(\d+\.\d+\.\d+)(?:-(\d{8}(?:-\d{6})?))?$",
    re.MULTILINE,
)


def next_version(current: str) -> str:
    """生成带秒级时间戳的新版本号（每次打包都变）。

    格式：MAJOR.MINOR.PATCH-YYYYMMDD-HHMMSS
    例：0.2.0       → 0.2.0-20260915-143022
        0.2.0-20260915-143022 → 0.2.0-20260915-143023（下一秒）
    """
    now = datetime.now().strftime(DATETIME_FMT)
    match = VERSION_PATTERN.match(current)
    if not match:
        print(f"⚠️  当前版本号 '{current}' 格式不标准，直接用时间戳")
        return f"0.1.0-{now}"

    base, existing_timestamp = match.groups()
    if existing_timestamp == now:
        # 同一秒重打（极少触发）：强行 +1 秒
        print(f"⚠️  同一秒重打，强行 +1 秒")
        new_dt = datetime.strptime(now, DATETIME_FMT) + timedelta(seconds=1)
        now = new_dt.strftime(DATETIME_FMT)

    return f"{base}-{now}"


def update_metadata(metadata_path: Path, new_version: str) -> None:
    """更新 metadata.yaml 的 version 字段。"""
    content = metadata_path.read_text(encoding="utf-8")
    new_content = re.sub(
        r"^version:\s*.*$",
        f"version: {new_version}",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    if new_content == content:
        return
    metadata_path.write_text(new_content, encoding="utf-8")
    print(f"✓ {metadata_path}: version → {new_version}")


def update_main(main_path: Path, new_version: str) -> None:
    """更新 main.py 中 @register 的第四个参数（version 字符串）。"""
    content = main_path.read_text(encoding="utf-8")
    pattern = re.compile(r'(@register\([^)]*?)"[^"]*"\s*\)', re.DOTALL)
    new_content = pattern.sub(
        lambda m: re.sub(r'"[^"]*"\s*\)$', f'"{new_version}")', m.group(0), count=1),
        content,
        count=1,
    )
    if new_content == content:
        return
    main_path.write_text(new_content, encoding="utf-8")
    print(f"✓ {main_path}: @register version → {new_version}")


def build_zip(plugin_dir: Path, output_zip: Path) -> None:
    """打包插件 zip（含 subdir 结构）。

    自动包含 plugin_dir 同级的 shared/ 目录（如果存在）——
    这样 plugin_dir/main.py 的 from shared.xxx import 能正确解析。
    """
    pack_root = plugin_dir.parent
    include_shared = (pack_root / "shared").is_dir()

    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(plugin_dir.rglob("*")):
            if not path.is_file():
                continue
            if "__pycache__" in path.parts:
                continue
            arcname = path.relative_to(pack_root)
            zf.write(path, arcname)
            print(f"  + {arcname}")

        if include_shared:
            shared_dir = pack_root / "shared"
            for path in sorted(shared_dir.rglob("*")):
                if not path.is_file():
                    continue
                if "__pycache__" in path.parts:
                    continue
                arcname = path.relative_to(pack_root)
                zf.write(path, arcname)
                print(f"  + {arcname}")


def main():
    parser = argparse.ArgumentParser(
        description="插件打包脚本（自动同步版本号 + 打 zip）",
    )
    parser.add_argument("plugin_dir", help="插件目录路径（绝对或相对）")
    parser.add_argument("output_zip", help="输出 zip 路径")
    parser.add_argument(
        "--no-bump",
        action="store_true",
        help="只打包，不升级版本号",
    )
    args = parser.parse_args()

    plugin_dir = Path(args.plugin_dir).resolve()
    if not plugin_dir.is_dir():
        print(f"❌ 插件目录不存在：{plugin_dir}")
        sys.exit(1)

    metadata_path = plugin_dir / "metadata.yaml"
    if not metadata_path.exists():
        print(f"❌ 找不到 metadata.yaml：{metadata_path}")
        sys.exit(1)

    current_version = ""
    content = metadata_path.read_text(encoding="utf-8")
    match = re.search(r"^version:\s*(\S+)", content, re.MULTILINE)
    if match:
        current_version = match.group(1).strip()

    if args.no_bump:
        new_version = current_version
        print(f"  --no-bump：保持版本号 {new_version}")
    else:
        new_version = next_version(current_version)
        print(f"  版本号：{current_version} → {new_version}")

    if not args.no_bump:
        update_metadata(metadata_path, new_version)
        candidates = list(plugin_dir.glob("main.py"))
        if candidates:
            update_main(candidates[0], new_version)

    output_zip = Path(args.output_zip).resolve()
    print(f"\n打包到 {output_zip}：")
    build_zip(plugin_dir, output_zip)

    print(f"\n✓ 完成：{output_zip}")
    if not args.no_bump:
        print(f"\n⚠️  记得 git commit（版本号已变更）：")
        print(f"   git add {plugin_dir}")
        print(f"   git commit -m \"{plugin_dir.name}: bump version to {new_version}\"")


if __name__ == "__main__":
    main()