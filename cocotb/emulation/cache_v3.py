# External 
from dataclasses import dataclass, field

# Data Types & Consts
from typing import (Callable, Awaitable, Dict, List)
from axi_request_types import (axi_and_coherence_request, axi_request)
from msi_v2 import (MSIState, ProcessorEvent, SnoopEvent, CoherenceCmd, TransitionResult) 
from config import (CACHE_LINE_SIZE_IN_WORDS, OFFSET_WIDTH, INDEX_WIDTH, TAG_WIDTH)

# Functions
from msi_v2 import (on_processor_event, on_snoop_event)
from util import (apply_wstrb)


@dataclass
class CacheLine:
    """
    Represents a single cache line with tag, state, and data:
        - 32 bits long
        - tag, index, and offset size are determined by memory sizes in config
        - Structure: [ Tag | Index | Offset ]
    """

    tag: int = 0
    state: MSIState = MSIState.INVALID
    data: List[int] = field(default_factory=lambda: [0] * CACHE_LINE_SIZE_IN_WORDS)

    def __post_init__(self):
        # Calculate maximum values based on bit widths
        # A width of 10 bits means a max value of (2^10) - 1
        max_tag = (1 << TAG_WIDTH) - 1

        if not (0 <= self.tag <= max_tag):
            raise ValueError(f"Tag {self.tag} exceeds {TAG_WIDTH}-bit limit ({max_tag})")
        
