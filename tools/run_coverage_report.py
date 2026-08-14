#!/usr/bin/env python3
import sqlite3
from pathlib import Path

PROJECT_B_ROOT = Path("c:/Users/idsid/Documents/GitHub/b")
MEDIA_DIR = PROJECT_B_ROOT / "media"
DB_PATH = PROJECT_B_ROOT / "data" / "prawko.sqlite"
REPORT_PATH = PROJECT_B_ROOT / "data" / "coverage_results.txt"

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, media, media_kind, scope
        FROM questions
        WHERE categories LIKE '%"B"%' AND media IS NOT NULL AND TRIM(media) != ''
    """)
    rows = cursor.fetchall()
    conn.close()

    total_count = len(rows)
    found_count = 0
    missing_count = 0

    video_total = 0
    video_found = 0
    image_total = 0
    image_found = 0

    missing_videos = []
    missing_images = []

    for q_id, media_name, media_kind, scope in rows:
        stem = Path(media_name).stem
        ext = Path(media_name).suffix.lower()

        is_video = (media_kind == "video") or ext in (".wmv", ".mp4", ".avi")

        if is_video:
            video_total += 1
            target_mp4 = MEDIA_DIR / f"{stem}.mp4"
            target_raw = MEDIA_DIR / media_name

            if target_mp4.exists() or target_raw.exists():
                found_count += 1
                video_found += 1
            else:
                missing_count += 1
                missing_videos.append((q_id, media_name))
        else:
            image_total += 1
            target_img = MEDIA_DIR / media_name
            target_jpg = MEDIA_DIR / f"{stem}.jpg"
            target_png = MEDIA_DIR / f"{stem}.png"

            if target_img.exists() or target_jpg.exists() or target_png.exists():
                found_count += 1
                image_found += 1
            else:
                missing_count += 1
                missing_images.append((q_id, media_name))

    output_lines = [
        "==================================================",
        "      PRAWKO B — MEDIA COVERAGE AUDIT REPORT      ",
        "==================================================",
        f"Total Category B Questions with Media: {total_count}",
        f"  - Video Questions Expected:  {video_total}",
        f"  - Image Questions Expected:  {image_total}\n",
        f"Total Media Found on Disk:  {found_count} / {total_count} ({(found_count/total_count*100):.2f}%)" if total_count else "0%",
        f"  - Videos Found (.mp4):    {video_found} / {video_total} ({(video_found/video_total*100):.2f}%)" if video_total else "N/A",
        f"  - Images Found:          {image_found} / {image_total} ({(image_found/image_total*100):.2f}%)" if image_total else "N/A",
        f"Total Missing Files:        {missing_count}",
    ]

    if missing_videos:
        output_lines.append(f"\nMissing Videos ({len(missing_videos)} total):")
        for q_id, m in missing_videos[:20]:
            output_lines.append(f"  - Question #{q_id}: {m}")

    if missing_images:
        output_lines.append(f"\nMissing Images ({len(missing_images)} total):")
        for q_id, m in missing_images[:20]:
            output_lines.append(f"  - Question #{q_id}: {m}")

    output_lines.append("==================================================")
    
    text = "\n".join(output_lines)
    REPORT_PATH.write_text(text, encoding="utf-8")
    print(text)

if __name__ == "__main__":
    main()
