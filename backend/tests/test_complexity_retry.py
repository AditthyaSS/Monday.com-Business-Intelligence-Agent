import httpx

from app.config import Settings
from app.sources.monday_api import MondayAPI


def test_complexity_error_halves_page_size() -> None:
    limits: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        if "BoardMetadata" in body["query"]:
            return httpx.Response(200, json={"data": {"boards": [{"id": "1", "name": "Deals", "columns": []}]}})
        limit = body["variables"]["limit"]
        limits.append(limit)
        if limit > 25:
            return httpx.Response(200, json={"errors": [{"message": "query complexity limit exceeded"}]})
        return httpx.Response(200, json={"data": {"boards": [{"items_page": {"cursor": None, "items": []}}]}})

    config = Settings(
        monday_api_token="token",
        monday_api_version="2026-01",
        gemini_api_key="unused",
        gemini_model="unused",
        deals_board_id="1",
        work_orders_board_id="2",
    )
    api = MondayAPI(config, httpx.Client(transport=httpx.MockTransport(handler)), sleep=lambda _: None)
    api.get_board("deals")
    assert limits == [200, 100, 50, 25]

