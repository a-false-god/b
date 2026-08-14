#!/usr/bin/env python3
"""
Process raw media files (scans uncompressed folders and all ZIP archives in filmy):
1. Detect uncompressed media folder 'multimedia_do_pytan' and all *.zip archives in filmy directory.
2. Fix CP437/CP1250 encoding issues for ZIP filenames.
3. Flatten directory structure to c:/Users/idsid/Documents/GitHub/b/media
4. Transcode WMV videos to MP4 (H.264, <=1024x576, no audio, ffmpeg with -movflags +faststart).
5. Hardware encoder order: h264_qsv (nv12) -> h264_amf (nv12) -> libx264 (yuv420p).
6. Concurrency 3 workers.
7. Extract/copy JPG/PNG/WEBP images directly.
"""

import os
import shutil
import sqlite3
import subprocess
import zipfile
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

PROJECT_B_ROOT = Path(__file__).resolve().parent.parent
FILMY_ROOT = Path("c:/Users/idsid/Documents/GitHub/filmy")
UNCOMPRESSED_DIR = FILMY_ROOT / "multimedia_do_pytan"
MEDIA_DIR = PROJECT_B_ROOT / "media"
DB_PATH = PROJECT_B_ROOT / "data" / "prawko.sqlite"
TEMP_EXTRACT_DIR = FILMY_ROOT / "tmp_media_extract"
NUM_WORKERS = 3


def decode_zip_filename(raw_filename: str) -> str:
    """Fix ZIP filename encoding issue (CP437 -> UTF-8 or CP1250)."""
    try:
        raw_bytes = raw_filename.encode("cp437")
    except UnicodeEncodeError:
        return raw_filename

    for encoding in ("utf-8", "cp1250", "iso-8859-2"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue

    return raw_filename


def convert_wmv_to_mp4(src_path: Path, dst_path: Path) -> bool:
    """Convert WMV video to optimized MP4 using ffmpeg with fallback hardware encoders."""
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    encoder_configs = [
        ("h264_qsv", "nv12"),
        ("h264_amf", "nv12"),
        ("libx264", "yuv420p")
    ]

    for encoder, pix_fmt in encoder_configs:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(src_path),
            "-vf", "scale='min(1024,iw)':'-2'",
            "-c:v", encoder,
            "-an",
            "-pix_fmt", pix_fmt,
            "-movflags", "+faststart",
            str(dst_path)
        ]
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            continue

    print(f"Error converting {src_path} -> {dst_path} across all encoders.")
    return False


def transcode_task(src_video: Path, dst_mp4: Path, base_name: str, stem: str, is_temp: bool = False):
    """Worker task to convert single video and clean up temp file if needed."""
    try:
        success = convert_wmv_to_mp4(src_video, dst_mp4)
        return success, base_name, stem
    finally:
        if is_temp and src_video.exists():
            try:
                src_video.unlink()
            except Exception:
                pass


def process_archive():
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

    extracted_images = 0
    converted_videos = 0
    skipped_count = 0
    failed_conversions = 0
    video_tasks = []

    # 1. Check uncompressed directory
    if UNCOMPRESSED_DIR.exists():
        print(f"Scanning uncompressed folder at {UNCOMPRESSED_DIR}...")
        all_files = list(UNCOMPRESSED_DIR.rglob("*"))

        for index, file_path in enumerate(all_files, 1):
            if file_path.is_dir() or file_path.name.startswith('.'):
                continue

            base_name = file_path.name
            ext = file_path.suffix.lower()
            stem = file_path.stem

            if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                dst_img = MEDIA_DIR / base_name
                if not dst_img.exists():
                    shutil.copy2(file_path, dst_img)
                    extracted_images += 1
                else:
                    skipped_count += 1

            elif ext in ('.wmv', '.avi', '.mov', '.mp4'):
                dst_mp4 = MEDIA_DIR / f"{stem}.mp4"
                if dst_mp4.exists() and dst_mp4.stat().st_size > 0:
                    skipped_count += 1
                    continue

                video_tasks.append((file_path, dst_mp4, base_name, stem, False))

    # 2. Scan all ZIP archives in FILMY_ROOT (e.g. cz 2)
    zip_files = list(FILMY_ROOT.glob("*.zip"))
    print(f"\nFound {len(zip_files)} ZIP archive(s) in {FILMY_ROOT}: {[z.name for z in zip_files]}")

    for zip_path in zip_files:
        print(f"Scanning zip archive {zip_path.name}...")
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                infolist = zf.infolist()
                for index, member in enumerate(infolist, 1):
                    fixed_filename = decode_zip_filename(member.filename)
                    base_name = Path(fixed_filename).name

                    if not base_name or base_name.startswith('.') or member.is_dir():
                        continue

                    ext = Path(base_name).suffix.lower()
                    stem = Path(base_name).stem

                    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
                        dst_img = MEDIA_DIR / base_name
                        if not dst_img.exists():
                            with zf.open(member) as src, open(dst_img, 'wb') as dst:
                                dst.write(src.read())
                            extracted_images += 1
                        else:
                            skipped_count += 1

                    elif ext in ('.wmv', '.avi', '.mov'):
                        dst_mp4 = MEDIA_DIR / f"{stem}.mp4"
                        if dst_mp4.exists() and dst_mp4.stat().st_size > 0:
                            skipped_count += 1
                            continue

                        tmp_src = TEMP_EXTRACT_DIR / f"{zip_path.stem}_{index}_{base_name}"
                        with zf.open(member) as src, open(tmp_src, 'wb') as dst:
                            dst.write(src.read())

                        video_tasks.append((tmp_src, dst_mp4, base_name, stem, True))
        except Exception as e:
            print(f"Error scanning {zip_path.name}: {e}")

    total_videos_to_convert = len(video_tasks)
    print(f"\nProcessed {extracted_images} new images, {skipped_count} existing items skipped.")
    print(f"Queueing {total_videos_to_convert} missing videos for transcoding using {NUM_WORKERS} workers...\n")

    if total_videos_to_convert > 0:
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            future_to_video = {
                executor.submit(transcode_task, src_vid, dst_mp4, bname, sname, is_temp): (bname, sname)
                for src_vid, dst_mp4, bname, sname, is_temp in video_tasks
            }

            completed = 0
            for future in as_completed(future_to_video):
                completed += 1
                bname, sname = future_to_video[future]
                try:
                    success, res_bname, res_sname = future.result()
                    if success:
                        converted_videos += 1
                        print(f"[{completed}/{total_videos_to_convert}] Transcoded: {res_bname} -> {res_sname}.mp4")
                    else:
                        failed_conversions += 1
                        print(f"[{completed}/{total_videos_to_convert}] FAILED: {res_bname}")
                except Exception as exc:
                    failed_conversions += 1
                    print(f"[{completed}/{total_videos_to_convert}] Exception for {bname}: {exc}")

    print("\n================ Processing Summary ================")
    print(f"Images Copied/Extracted: {extracted_images}")
    print(f"Videos Transcoded: {converted_videos}")
    print(f"Files Skipped (Already Exist): {skipped_count}")
    print(f"Failed Conversions: {failed_conversions}")
    print("====================================================")


if __name__ == "__main__":
    process_archive()
