"""Generate checksum pins for files listed in manifest.yaml."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.yaml"
CHECKSUMS = ROOT / "checksums.txt"


def manifest_paths() -> list[Path]:
    manifest = yaml.safe_load(MANIFEST.read_text())
    files = manifest.get("files", [])
    paths: list[Path] = []
    for item in files:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            raise ValueError("manifest files entries must contain a string path")
        paths.append(ROOT / item["path"])
    return paths


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checksum_lines() -> list[str]:
    lines: list[str] = []
    for path in manifest_paths():
        if not path.exists():
            raise FileNotFoundError(path.relative_to(ROOT))
        lines.append(f"{checksum(path)}  {path.relative_to(ROOT)}")
    return lines


def write_checksums() -> None:
    CHECKSUMS.write_text("\n".join(checksum_lines()) + "\n")


def check() -> bool:
    expected = CHECKSUMS.read_text().splitlines()
    return expected == checksum_lines()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Rewrite checksums.txt")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.write:
        write_checksums()
        return 0
    if check():
        return 0
    print("checksums.txt is stale; run `make update-checksums`")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
