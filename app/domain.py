# app/domain.py
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CaseKey:
    """
    案場識別
    """
    country: str
    location: str

    @property
    def display(self) -> str:
        return f"{self.country}({self.location})"

    @staticmethod
    def from_casescene(cs) -> "CaseKey":
        return CaseKey(cs.country, cs.location)


@dataclass
class EquipmentQuery:
    """
    表示一個「設備清單的查詢條件」
    """
    q: str = ""
    type_id: Optional[int] = None

    def has_text(self) -> bool:
        return bool(self.q.strip())

    def like(self) -> str:
        return f"%{self.q.strip()}%"


@dataclass(frozen=True)
class Location:
    """
    Domain 版本的 Location（Case + Room）
    """
    case: CaseKey
    room_name: Optional[str] = None

    @property
    def full_display(self) -> str:
        if self.room_name:
            return f"{self.case.display} / {self.room_name}"
        return self.case.display
