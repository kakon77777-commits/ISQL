from __future__ import annotations

import json
from pathlib import Path

from .code import ISQLCode
from .errors import ISQLNotFoundError, ISQLValidationError
from .memory import MemoryRecord


class MemoryStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.records_dir = self.root / "records"
        self.records_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, address: ISQLCode) -> Path:
        if address.domain != "ADDR":
            raise ISQLValidationError("STORE_KEY_MUST_BE_ADDR")
        return self.records_dir / f"{address.control}{address.payload}.json"

    def put(self, record: MemoryRecord) -> Path:
        path = self._path_for(record.address)
        payload = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(path)
        return path

    def get(self, address: ISQLCode) -> MemoryRecord:
        path = self._path_for(address)
        if not path.exists():
            raise ISQLNotFoundError("MEMORY_RECORD_NOT_FOUND")
        data = json.loads(path.read_text(encoding="utf-8"))
        record = MemoryRecord.from_dict(data)
        if record.address != address:
            raise ISQLValidationError("MEMORY_STORE_ADDRESS_MISMATCH")
        return record
    def find_by_memory_code(self, code: ISQLCode) -> MemoryRecord:
        if code.domain != "MEM":
            raise ISQLValidationError("LOOKUP_CODE_MUST_BE_MEM")
        for path in sorted(self.records_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            record = MemoryRecord.from_dict(data)
            layer = record.layers.get(code.resolution)
            if layer is not None and layer.code == code:
                return record
        raise ISQLNotFoundError("MEMORY_CODE_NOT_FOUND")

