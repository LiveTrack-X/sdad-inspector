"""SDAD Inspector public package."""

from .version import __version__

from .snapshot import inspect_project
from .protocols import (
    ProtocolAdapter,
    ProtocolDescriptor,
    register_protocol_adapter,
    registered_protocol_adapters,
)

__all__ = [
    "__version__",
    "ProtocolAdapter",
    "ProtocolDescriptor",
    "inspect_project",
    "register_protocol_adapter",
    "registered_protocol_adapters",
]
