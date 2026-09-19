"""Check Phase 1 configuration without printing secret values."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import get_settings  # noqa: E402


def main() -> int:
    """Validate required settings and report only safe metadata."""

    try:
        settings = get_settings()
    except Exception as exc:
        print(f"Configuration incomplete: {exc.__class__.__name__}")
        return 1
    print("Configuration loaded from server environment.")
    print(f"Monday API version: {settings.monday_api_version}")
    print(f"Deals board ID configured: {bool(settings.deals_board_id)}")
    print(f"Work Orders board ID configured: {bool(settings.work_orders_board_id)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

