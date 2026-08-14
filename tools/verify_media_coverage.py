#!/usr/bin/env python3
"""
Verify media coverage for Category B questions in Prawko B.
Maps .wmv database references to <stem>.mp4 on disk, and images (.jpg, .png, .webp) to disk assets.
"""

import sqlite3
from pathlib import Path

PROJECT_B_ROOT = Path("c:/Users/idsid/Documents/GitHub/b")
MEDIA_DIR = PROJECT_B_ROOT / "media"
DB_PATH = PROJECT_B_ROOT / "data" / "prawko.sqlite"


def run_verification():
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Query Category B active questions with media
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
            # For videos: check <stem>.mp4, <media_name>, or prefix variants
            target_mp4 = MEDIA_DIR / f"{stem}.mp4"
            target_raw = MEDIA_DIR / media_name
            target_v1 = MEDIA_DIR / f"1_{stem}.mp4"

            if target_mp4.exists() or target_raw.exists() or target_v1.exists():
                found_count += 1
                video_found += 1
            else:
                missing_count += 1
                missing_videos.append((q_id, media_name))
        else:
            image_total += 1
            # For images: original filename, jpg, png, webp, or stem matches
            target_img = MEDIA_DIR / media_name
            target_jpg = MEDIA_DIR / f"{stem}.jpg"
            target_png = MEDIA_DIR / f"{stem}.png"
            target_webp = MEDIA_DIR / f"{stem}.webp"

            if target_img.exists() or target_jpg.exists() or target_png.exists() or target_webp.exists():
                found_count += 1
                image_found += 1
            else:
                missing_count += 1
                missing_images.append((q_id, media_name))

    print("\n==================================================")
    print("      PRAWKO B — MEDIA COVERAGE AUDIT REPORT      ")
    print("==================================================")
    print(f"Total Category B Questions with Media: {total_count}")
    print(f"  - Video Questions Expected:  {video_total}")
    print(f"  - Image Questions Expected:  {image_total}\n")

    print(f"Total Media Found on Disk:  {found_count} / {total_count} ({(found_count/total_count*100):.2f}%)" if total_count else "0%")
    print(f"  - Videos Found (.mp4):    {video_found} / {video_total} ({(video_found/video_total*100):.2f}%)" if video_total else "N/A")
    print(f"  - Images Found:          {image_found} / {image_total} ({(image_found/image_total*100):.2f}%)" if image_total else "N/A")
    print(f"Total Missing Files:        {missing_count}")

    if missing_videos:
        print(f"\nMissing Videos ({len(missing_videos)} total):")
        for q_id, m in missing_videos:
            print(f"  - Question #{q_id}: {m}")

    if missing_images:
        print(f"\nMissing Images ({len(missing_images)} total):")
        for q_id, m in missing_images:
            print(f"  - Question #{q_id}: {m}")

    print("==================================================\n")
    return {
        "total": total_count,
        "found": found_count,
        "missing": missing_count,
        "video_found": video_found,
        "video_total": video_total,
        "image_found": image_found,
        "image_total": image_total
    }


if __name__ == "__main__":
    run_verification()
