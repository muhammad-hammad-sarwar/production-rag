from dataclasses import dataclass, field
from typing import Optional, Any

@dataclass
class Metadata:
    page: Optional[list[int]]
    source_file: str

@dataclass
class Segment:
    text: str
    kind: str
    metadata: dict[str, Any] = field(default_factory=dict)