#!/usr/bin/env python3
"""
Render Mermaid diagrams from markdown files with hash-based caching.

Usage:
    python scripts/render_diagrams.py [--force]

Outputs PNG/SVG files to docs/diagrams/ (gitignored).
Only re-renders diagrams whose content hash has changed.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Configuration
DOCS_DIR = Path("docs")
OUTPUT_DIR = Path("docs/diagrams")
HASH_FILE = OUTPUT_DIR / ".diagram_hashes.json"
OUTPUT_FORMAT = "svg"  # 'svg' or 'png'

# Regex to extract mermaid code blocks
MERMAID_PATTERN = re.compile(
    r"```mermaid\s*\n(.*?)\n```",
    re.DOTALL | re.MULTILINE,
)


def extract_diagrams(md_file: Path) -> list[tuple[str, str]]:
    """Extract all Mermaid diagrams from a markdown file.

    Returns list of (diagram_id, diagram_content) tuples.
    """
    content = md_file.read_text()
    matches = MERMAID_PATTERN.findall(content)

    diagrams = []
    for i, diagram in enumerate(matches):
        # Create unique ID from filename and index
        base_name = md_file.stem
        diagram_id = f"{base_name}_{i + 1}" if len(matches) > 1 else base_name
        diagrams.append((diagram_id, diagram.strip()))

    return diagrams


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of diagram content."""
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def load_hashes() -> dict[str, str]:
    """Load existing diagram hashes from cache file."""
    if HASH_FILE.exists():
        return json.loads(HASH_FILE.read_text())
    return {}


def save_hashes(hashes: dict[str, str]) -> None:
    """Save diagram hashes to cache file."""
    HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    HASH_FILE.write_text(json.dumps(hashes, indent=2))


def check_mmdc_installed() -> bool:
    """Check if mermaid-cli (mmdc) is installed."""
    return shutil.which("mmdc") is not None


def render_diagram(diagram_id: str, content: str, output_path: Path) -> bool:
    """Render a single Mermaid diagram using mmdc.

    Returns True if successful, False otherwise.
    """
    # Write diagram to temp file
    temp_file = output_path.parent / f".{diagram_id}.mmd"
    temp_file.write_text(content)

    try:
        result = subprocess.run(
            [
                "mmdc",
                "-i",
                str(temp_file),
                "-o",
                str(output_path),
                "-b",
                "transparent",
                "-t",
                "default",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            print(f"  ERROR: {result.stderr.strip()}")
            return False

        return True

    except subprocess.TimeoutExpired:
        print("  ERROR: Rendering timed out")
        return False

    except Exception as e:
        print(f"  ERROR: {e}")
        return False

    finally:
        temp_file.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(
        description="Render Mermaid diagrams from markdown"
    )
    parser.add_argument(
        "--force", action="store_true", help="Force re-render all diagrams"
    )
    parser.add_argument(
        "--check", action="store_true", help="Check only, don't render (for CI)"
    )
    args = parser.parse_args()

    # Check for mmdc
    if not check_mmdc_installed():
        print("WARNING: mermaid-cli (mmdc) not installed. Skipping diagram rendering.")
        print("Install with: npm install -g @mermaid-js/mermaid-cli")
        return 0

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load existing hashes
    old_hashes = {} if args.force else load_hashes()
    new_hashes = {}

    # Find all markdown files with diagrams
    all_diagrams = []
    for md_file in DOCS_DIR.glob("*.md"):
        diagrams = extract_diagrams(md_file)
        for diagram_id, content in diagrams:
            all_diagrams.append((md_file, diagram_id, content))

    if not all_diagrams:
        print("No Mermaid diagrams found in docs/")
        return 0

    print(f"Found {len(all_diagrams)} Mermaid diagram(s)")

    # Process each diagram
    rendered = 0
    skipped = 0
    errors = 0
    needs_render = []

    for md_file, diagram_id, content in all_diagrams:
        content_hash = compute_hash(content)
        new_hashes[diagram_id] = content_hash

        output_path = OUTPUT_DIR / f"{diagram_id}.{OUTPUT_FORMAT}"

        # Check if re-render needed
        if old_hashes.get(diagram_id) == content_hash and output_path.exists():
            skipped += 1
            continue

        needs_render.append((md_file, diagram_id, content, output_path))

    if args.check:
        if needs_render:
            print(f"\n{len(needs_render)} diagram(s) need rendering:")
            for md_file, diagram_id, _, _ in needs_render:
                print(f"  - {diagram_id} (from {md_file.name})")
            return 1
        else:
            print("All diagrams up to date.")
            return 0

    # Render diagrams that need updating
    for md_file, diagram_id, content, output_path in needs_render:
        print(f"  Rendering {diagram_id} from {md_file.name}...")

        if render_diagram(diagram_id, content, output_path):
            rendered += 1
        else:
            errors += 1
            # Don't save hash for failed renders
            del new_hashes[diagram_id]

    # Save updated hashes
    save_hashes(new_hashes)

    # Summary
    print("\nDiagram rendering complete:")
    print(f"  Rendered: {rendered}")
    print(f"  Skipped (unchanged): {skipped}")
    if errors:
        print(f"  Errors: {errors}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
