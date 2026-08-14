#!/usr/bin/env python3
"""
Targeted script to resolve missing media assets cleanly without WinError locks.
"""

import sqlite3
import shutil
import subprocess
from pathlib import Path

PROJECT_B_ROOT = Path(__file__).resolve().parent.parent
FILMY_ROOT = Path("c:/Users/idsid/Documents/GitHub/filmy")
MEDIA_DIR = PROJECT_B_ROOT / "media"
DB_PATH = PROJECT_B_ROOT / "data" / "prawko.sqlite"


def convert_wmv_to_mp4(src_path: Path, dst_path: Path) -> bool:
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    encoder_configs = [("h264_qsv", "nv12"), ("h264_amf", "nv12"), ("libx264", "yuv420p")]
    for encoder, pix_fmt in encoder_configs:
        cmd = [
            "ffmpeg", "-y", "-i", str(src_path),
            "-vf", "scale='min(1024,iw)':'-2'",
            "-c:v", encoder, "-an", "-pix_fmt", pix_fmt,
            "-movflags", "+faststart", str(dst_path)
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except Exception:
            continue
    return False


def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, media, media_kind
        FROM questions
        WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != ''
    """)
    rows = cursor.fetchall()
    conn.close()

    # Collect all available source files across filmy folder
    filmy_files = [p for p in FILMY_ROOT.rglob("*") if p.is_file() and not p.name.startswith('.')]

    fixed_count = 0

    for q_id, media_name, media_kind in rows:
        stem = Path(media_name).stem.lower()
        ext = Path(media_name).suffix.lower()
        is_video = (media_kind == "video") or ext in (".wmv", ".mp4", ".avi")

        # Check target in MEDIA_DIR
        target_file = MEDIA_DIR / (f"{stem}.mp4" if is_video else media_name)
        if target_file.exists() and target_file.stat().st_size > 0:
            continue

        # Look for exact stem match in filmy source folder
        exact_matches = [f for f in filmy_files if f.stem.lower() == stem]

        if not is_video:
            for cand in exact_matches:
                if cand.suffix.lower() in ('.jpg', '.jpeg', '.png', '.webp'):
                    try:
                        dst = MEDIA_DIR / media_name
                        if cand.resolve() != dst.resolve():
                            shutil.copy2(cand, dst)
                            fixed_count += 1
                            print(f"Fixed Image Q#{q_id}: copied {cand.name} -> {media_name}")
                            break
                    except Exception as e:
                        print(f"Skipped copy {cand.name}: {e}")
        else:
            for cand in exact_matches:
                if cand.suffix.lower() in ('.wmv', '.avi', '.mov', '.mp4'):
                    dst_mp4 = MEDIA_DIR / f"{stem}.mp4"
                    try:
                        if cand.suffix.lower() == '.mp4' and cand.resolve() != dst_mp4.resolve():
                            shutil.copy2(cand, dst_mp4)
                            fixed_count += 1
                            print(f"Fixed Video Q#{q_id}: copied {cand.name} -> {dst_mp4.name}")
                            break
                        elif cand.suffix.lower() != '.mp4':
                            if convert_wmv_to_mp4(cand, dst_mp4):
                                fixed_count += 1
                                print(f"Fixed Video Q#{q_id}: converted {cand.name} -> {dst_mp4.name}")
                                break
                    except Exception as e:
                        print(f"Skipped video {cand.name}: {e}")

    print(f"\nTotal missing items fixed: {fixed_count}")


if __name__ == "__main__":
    main()
