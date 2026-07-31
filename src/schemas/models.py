from __future__ import annotations

import time 
import uuid 
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, Field 


# we need a way to generate IDs, which are unique. this will be for subtasks, tool calls, plans, and escalation events. 

def new_id(prefix: str) -> str:
    # TODO: return f"{prefix}_" followed by a short random hex string.
    # Hint: uuid.uuid4().hex gives you a 32-char random hex string --
    # you only need the first ~10 characters for readibilty. 
    random_hex = uuid.uuid4().hex[:10]
    return f"{prefix}_{random_hex}"


class Complexity(str, Enum):
    # TODO: three value --low,medium, high.
    # Syntax reminder: NAME = "value"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class SpecialistName(str, Enum):
    #TODO: three values -- low, medium, high.
    # Syntax reminder: NAME = "value"
    LOW = 

