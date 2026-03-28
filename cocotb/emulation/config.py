# External
import math

# Types
from typing import Final

# Configrable
## memory sizes in btyes
MAIN_MEM_SIZE_IN_WORDS: Final = 4096
## cache configs
CACHE_LINE_SIZE_IN_WORDS: Final = 8
CACHE_MEM_SIZE_IN_WORDS: Final = 1024


# Calcs based on config
## cache line widths
OFFSET_WIDTH = int(math.log2(CACHE_LINE_SIZE_IN_WORDS))
INDEX_WIDTH = int(math.log2(CACHE_MEM_SIZE_IN_WORDS/CACHE_LINE_SIZE_IN_WORDS))
TAG_WIDTH = 32 - (INDEX_WIDTH + OFFSET_WIDTH)
