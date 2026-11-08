"""Read-block planning and register-support detection (no HA / pymodbus imports).

Documented registers are merged into blocks of at most ``max_count`` registers,
optimistically reading through small undocumented gaps. If the device rejects a
block with "illegal address", the block is split recursively until every
supported register is covered by a readable block and every unsupported one is
identified. The resulting block list is what gets polled afterwards.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass

from .errors import UnsupportedRegister
from .registers import Table

ReadFn = Callable[[Table, int, int], Awaitable[list[int]]]


@dataclass(frozen=True, slots=True)
class Block:
    """A contiguous read request."""

    table: Table
    start: int
    count: int

    @property
    def end(self) -> int:
        """Last address (inclusive)."""
        return self.start + self.count - 1

    def as_dict(self) -> dict[str, int | str]:
        """Serialise for storage."""
        return {"table": str(self.table), "start": self.start, "count": self.count}

    @classmethod
    def from_dict(cls, data: dict) -> Block:
        """Deserialise from storage."""
        return cls(Table(data["table"]), int(data["start"]), int(data["count"]))


def group_addresses(addresses: Iterable[int], max_count: int, max_gap: int) -> list[list[int]]:
    """Greedily group sorted addresses into spans <= max_count with gaps <= max_gap."""
    groups: list[list[int]] = []
    for address in sorted(set(addresses)):
        if groups:
            current = groups[-1]
            if address - current[0] < max_count and address - current[-1] - 1 <= max_gap:
                current.append(address)
                continue
        groups.append([address])
    return groups


@dataclass
class DetectionResult:
    """Outcome of probing one table."""

    blocks: list[Block]
    values: dict[int, int]
    unsupported: list[int]


async def detect_blocks(
    read: ReadFn,
    table: Table,
    addresses: Iterable[int],
    *,
    max_count: int,
    max_gap: int,
) -> DetectionResult:
    """Find readable blocks covering every supported address.

    Communication errors propagate (detection must then be retried later).
    """
    result = DetectionResult(blocks=[], values={}, unsupported=[])

    async def probe(group: list[int]) -> None:
        start, count = group[0], group[-1] - group[0] + 1
        try:
            raw = await read(table, start, count)
        except UnsupportedRegister:
            if len(group) == 1:
                result.unsupported.append(group[0])
                return
            mid = len(group) // 2
            await probe(group[:mid])
            await probe(group[mid:])
            return
        result.blocks.append(Block(table, start, count))
        for address in group:
            result.values[address] = raw[address - start]

    for group in group_addresses(addresses, max_count, max_gap):
        await probe(group)
    result.blocks.sort(key=lambda b: b.start)
    result.unsupported.sort()
    return result
