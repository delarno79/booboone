"""Pre-flight check — verifies every credential and connection before you rely
on the automation. Run this after filling in .env:

    python setup_check.py
"""

from __future__ import annotations

import sys

from autoblog.config import Config
from autoblog.tracker import KeywordTracker


def _ok(msg: str) -> None:
    print(f"  [ OK ] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def main() -> int:
    cfg = Config.from_env()
    print("Booboone Auto-Blog — setup check\n")
    errors = 0

    # 1) Config presence
    print("1) Configuration (.env)")
    problems = cfg.validate()
    if problems:
        for p in problems:
            _fail(p)
        errors += len(problems)
    else:
        _ok("All required settings present.")

    # 2) Keyword file
    print("\n2) Keyword list")
    try:
        tracker = KeywordTracker(cfg.keywords_file, cfg.state_file)
        total = tracker.total_remaining()
        _ok(
            f"{len(tracker.categories())} categories, "
            f"{sum(len(v) for v in tracker.keywords.values())} keywords "
            f"({total} still unpublished)."
        )
    except FileNotFoundError:
        _fail("keywords.json not found. Run: python convert_docx.py <file.docx>")
        errors += 1

    # 3) WordPress connection
    print("\n3) WordPress connection")
    if not problems:
        try:
            from autoblog.wordpress import WordPressClient

            wp = WordPressClient(cfg.wp_url, cfg.wp_user, cfg.wp_app_password)
            user = wp.test_connection()
            _ok(f"Authenticated as '{user.get('name')}' (id={user.get('id')}).")
        except Exception as err:  # noqa: BLE001
            _fail(f"Could not connect: {err}")
            errors += 1
    else:
        print("  [SKIP] Fix configuration first.")

    # 4) DeepSeek reachability
    print("\n4) DeepSeek API")
    if cfg.deepseek_api_key:
        try:
            from openai import OpenAI

            client = OpenAI(
                api_key=cfg.deepseek_api_key, base_url=cfg.deepseek_base_url
            )
            client.models.list()
            _ok("DeepSeek API key accepted.")
        except Exception as err:  # noqa: BLE001
            _fail(f"DeepSeek check failed: {err}")
            errors += 1
    else:
        print("  [SKIP] No DeepSeek key set.")

    # 5) Gemini key (only if images enabled)
    print("\n5) Gemini / Imagen (images)")
    if not cfg.generate_images:
        print("  [SKIP] Image generation is disabled (GENERATE_IMAGES=false).")
    elif cfg.gemini_api_key:
        _ok("Gemini key present. (Image generation is verified on the first run.)")
    else:
        _fail("GENERATE_IMAGES is on but no GEMINI_API_KEY set.")
        errors += 1

    print("\n" + "=" * 48)
    if errors == 0:
        print("All checks passed. You're ready to run: python main.py --dry-run")
        return 0
    print(f"{errors} problem(s) found. Fix the [FAIL] items above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
