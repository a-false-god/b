#!/usr/bin/env python3
"""
WMV -> MP4 Media Converter using ffmpeg.
Converts video media files to h264 MP4 format with resolution <= 1024x576 and no audio stream.
"""

import argparse
import subprocess
from pathlib import Path

def convert_wmv_to_mp4(src_path: Path, dst_path: Path) -> bool:
    """Convert a single WMV file to MP4 (H.264 <=1024x576, no audio, faststart)."""
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
            subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            continue
    return False

def main():
    parser = argparse.ArgumentParser(description="Convert WMV videos to optimized MP4")
    parser.add_argument("--src-dir", default="data/raw_media", help="Input directory containing raw media")
    parser.add_argument("--out-dir", default="media", help="Output directory for MP4 media")
    args = parser.parse_args()

    src_dir = Path(args.src_dir)
    out_dir = Path(args.out_dir)

    if not src_dir.exists():
        print(f"Source directory {src_dir} does not exist.")
        return

    for src_file in src_dir.rglob("*.wmv"):
        rel_path = src_file.relative_to(src_dir)
        dst_file = out_dir / rel_path.with_suffix(".mp4")
        print(f"Converting {src_file} -> {dst_file}...")
        convert_wmv_to_mp4(src_file, dst_file)

if __name__ == "__main__":
    main()
