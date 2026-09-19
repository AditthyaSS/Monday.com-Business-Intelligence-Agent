"""Read and summarize both configured Monday boards; never writes to Monday."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.sources.monday_api import MondayAPI  # noqa: E402


def main() -> int:
    """Fetch both boards live and print safe shape/metadata only."""

    with MondayAPI() as source:
        for kind in ("deals", "work_orders"):
            snapshot = source.get_board(kind)
            print(f"{kind}: board={snapshot.board_name!r} id={snapshot.board_id} shape={snapshot.df.shape} from_cache={snapshot.from_cache}")
            if snapshot.warnings:
                print("warnings:")
                for warning in snapshot.warnings:
                    print(f"- {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

