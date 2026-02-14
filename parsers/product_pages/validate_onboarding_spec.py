import json
import sys
from pathlib import Path


REQUIRED_TOP = ["brand", "country", "sample_urls"]


def validate(spec: dict) -> list[str]:
    errors: list[str] = []

    for key in REQUIRED_TOP:
        if key not in spec:
            errors.append(f"missing top-level key: {key}")

    urls = spec.get("sample_urls", [])
    if not isinstance(urls, list) or len(urls) < 3:
        errors.append("sample_urls must be a list with at least 3 urls")

    has_html_blocks = isinstance(spec.get("html_blocks"), list)
    has_dom_snapshots = isinstance(spec.get("dom_snapshots"), list)

    if not has_html_blocks and not has_dom_snapshots:
        errors.append("provide at least one of: 'html_blocks', 'dom_snapshots'")
        return errors

    if has_html_blocks:
        blocks = spec.get("html_blocks", [])
        if not blocks:
            errors.append("html_blocks must not be empty")
        for i, block in enumerate(blocks):
            if not isinstance(block, dict):
                errors.append(f"html_blocks[{i}] must be an object")
                continue
            for k in ["block_name", "purpose", "html"]:
                if k not in block:
                    errors.append(f"missing html_blocks[{i}].{k}")

    if isinstance(spec.get("initial_data_scripts"), list):
        scripts = spec.get("initial_data_scripts", [])
        for i, s in enumerate(scripts):
            if not isinstance(s, dict):
                errors.append(f"initial_data_scripts[{i}] must be an object")
                continue
            for k in ["script_name", "purpose", "html"]:
                if k not in s:
                    errors.append(f"missing initial_data_scripts[{i}].{k}")

    if has_dom_snapshots:
        snaps = spec.get("dom_snapshots", [])
        if not snaps:
            errors.append("dom_snapshots must not be empty")
        for i, s in enumerate(snaps):
            if not isinstance(s, dict):
                errors.append(f"dom_snapshots[{i}] must be an object")
                continue
            for k in ["snapshot_name", "action", "html"]:
                if k not in s:
                    errors.append(f"missing dom_snapshots[{i}].{k}")

    # Prefer either HAR or script/snapshot evidence for dynamic option logic.
    has_har = bool(spec.get("har_file"))
    has_script_or_snap = bool(spec.get("initial_data_scripts")) or has_dom_snapshots
    if not has_har and not has_script_or_snap:
        errors.append("provide 'har_file' or one of ('initial_data_scripts', 'dom_snapshots')")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python parsers/product_pages/validate_onboarding_spec.py <spec.json>")
        sys.exit(2)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"[ERROR] spec not found: {path}")
        sys.exit(2)

    try:
        spec = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] invalid json: {e}")
        sys.exit(2)

    errors = validate(spec)
    if errors:
        print("[INVALID] onboarding spec")
        for e in errors:
            print(f"- {e}")
        sys.exit(1)

    print("[OK] onboarding spec is valid")


if __name__ == "__main__":
    main()
