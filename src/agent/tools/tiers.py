"""Action tiers. The tier is declared in each tool's JSON schema and enforced in registry.py."""
from __future__ import annotations

from enum import Enum


class Tier(str, Enum):
    READ = "read"
    PROPOSE = "propose"
    EXECUTE_WITH_APPROVAL = "execute_with_approval"
    AUTONOMOUS = "autonomous"

    @property
    def writes(self) -> bool:
        return self in (Tier.EXECUTE_WITH_APPROVAL, Tier.AUTONOMOUS)

    @property
    def needs_approval(self) -> bool:
        return self is Tier.EXECUTE_WITH_APPROVAL
