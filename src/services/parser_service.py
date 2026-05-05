import json

from src.domain.models import Segment


class CutsParserService:
    def parse(self, raw: str) -> list[Segment]:
        data = json.loads(raw)

        if isinstance(data, dict):
            data = data.get("segments", data.get("cuts", []))

        return [
            self._parse_item(item)
            for item in data
            if isinstance(item, dict)
        ]

    def _parse_item(self, item: dict) -> Segment:
        start = self._parse_timestamp(item.get("start", item.get("inicio", 0)))
        end = self._parse_timestamp(item.get("end", item.get("fin", 0)))
        return Segment(start=start, end=end)

    def _parse_timestamp(self, value: int | float | str) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        parts = [float(p) for p in str(value).split(":")]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return float(parts[0])
