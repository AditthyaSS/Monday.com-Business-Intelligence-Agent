"""Interfaces and value objects for board data sources."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

import pandas as pd

BoardKind = Literal["deals", "work_orders"]


@dataclass
class BoardSnapshot:
    """A raw board read and the metadata needed to explain its freshness."""

    df: pd.DataFrame
    fetched_at: datetime
    board_id: str
    board_name: str
    from_cache: bool = False
    warnings: list[str] = field(default_factory=list)


class BoardSource(Protocol):
    """Read-only interface used by later normalization and analytics phases."""

    def get_board(self, kind: BoardKind) -> BoardSnapshot:
        """Fetch a raw board snapshot."""

