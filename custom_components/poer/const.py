"""Constants for Airly integration."""

from __future__ import annotations

import logging
from typing import Final

DOMAIN: Final = "poer"
ISMOCK: Final = False
CNURL: Final = "https://open2.poersmart.com"  # "http://10.11.0.150:6666"
EUURL: Final = "https://open.poersmart.com"  # "http://10.11.0.150:6666"


_LOGGER = logging.getLogger(__name__)
