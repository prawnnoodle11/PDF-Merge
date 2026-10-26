#!/usr/bin/env python3
"""Merge multiple PDF files into one, preserving a guaranteed order.

Install dependency:
    pip install pypdf

Usage examples:
    # Merge all PDFs in the default draft folder
    python merge_pdfs.py -o merged.pdf

    # Merge a folder, ordered naturally (file2 before file10)
    python merge_pdfs.py -d ./pdfs -o merged.pdf

    # Merge explicit files in the exact order given
    python merge_pdfs.py a.pdf b.pdf c.pdf -o merged.pdf

    # Merge files in the order listed in a text file (one path per line)
    python merge_pdfs.py -l order.txt -o merged.pdf

    # Sort a folder by modified time instead of name
    python merge_pdfs.py -d ./pdfs --sort mtime -o merged.pdf
"""

import argparse
import re
import sys
from pathlib import Path

from pypdf import PdfWriter, PdfReader

# Default input folder used when no files, --directory, or --list is given
DEFAULT_INPUT_DIR = Path(r"D:\Desktop_D\Documents\My-Personal-Workspace\AI_Development\PDF_Merger\draft")


def natural_key(path: Path):
    """Natural sort key: 'file2.pdf' < 'file10.pdf'."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", path.name)]


def collect_files(args) -> list[Path]:
    """Build the ordered list of input PDFs."""
    if args.list:
        # Order defined exactly by the list file
        lines = Path(args.list).read_text(encoding="utf-8").splitlines()
        files = [Path(l.strip()) for l in lines
                 if l.strip() and not l.strip().startswith("#")]
    elif args.directory:
        files = [p for p in Path(args.directory).iterdir()
                 if p.is_file() and p.suffix.lower() == ".pdf"]
        if args.sort == "name":
            files.sort(key=natural_key)
        elif args.sort == "mtime":
            files.sort(key=lambda p: p.stat().st_mtime)
        elif args.sort == "ctime":
            files.sort(key=lambda p: p.stat().st_ctime)
    else:
        # Explicit files: keep the exact order given on the command line
        files = [Path(f) for f in args.files]

    return files


def merge_pdfs(files: list[Path], output: Path, bookmarks: bool = True) -> None:
    writer = PdfWriter()

    for idx, f in enumerate(files, start=1):
        if not f.exists():
            raise FileNotFoundError(f"Not found: {f}")
        reader = PdfReader(str(f))
        if reader.is_encrypted:
            # Works for PDFs with an empty user password
            if reader.decrypt("") == 0:
                raise ValueError(f"Encrypted PDF needs a password: {f}")

        start_page = len(writer.pages)
        for page in reader.pages:
            writer.add_page(page)

        if bookmarks and len(reader.pages) > 0:
            writer.add_outline_item(f.stem, start_page)

        print(f"[{idx}/{len(files)}] {f.name}  ({len(reader.pages)} pages)")

    with open(output, "wb") as fh:
        writer.write(fh)

    print(f"\nMerged {len(files)} files -> {output}  ({len(writer.pages)} pages)")


def main():
    p = argparse.ArgumentParser(description="Merge PDFs in a guaranteed order.")
    p.add_argument("files", nargs="*", help="PDF files, merged in the order given")
    p.add_argument("-d", "--directory",
                   help=f"Merge all PDFs in this folder (default: {DEFAULT_INPUT_DIR})")
    p.add_argument("-l", "--list", help="Text file listing PDFs, one per line, in order")
    p.add_argument("--sort", choices=["name", "mtime", "ctime"], default="name",
                   help="Sort order when using --directory (default: name, natural)")
    p.add_argument("-o", "--output", default="merged.pdf", help="Output file")
    p.add_argument("--no-bookmarks", action="store_true",
                   help="Do not add a bookmark per source file")
    args = p.parse_args()

    if not (args.files or args.directory or args.list):
        args.directory = str(DEFAULT_INPUT_DIR)
        if not DEFAULT_INPUT_DIR.is_dir():
            p.error(f"Default input folder not found: {DEFAULT_INPUT_DIR}")

    output = Path(args.output)
    files = collect_files(args)
    # Never include the output file itself if it sits in the input folder
    files = [f for f in files if f.resolve() != output.resolve()]

    if not files:
        sys.exit("No PDF files found.")

    print("Merge order:")
    for i, f in enumerate(files, 1):
        print(f"  {i}. {f}")
    print()

    merge_pdfs(files, output, bookmarks=not args.no_bookmarks)


if __name__ == "__main__":
    main()
