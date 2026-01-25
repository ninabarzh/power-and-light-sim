"""
Async network reachability simulator.

Source of truth:
- network.yml
- device membership
- service exposure
"""

import asyncio
from pathlib import Path

import yaml


class NetworkSimulator:
    def __init__(self, config_path: str = "config/network.yml"):
        self.config_path = Path(config_path)

        self.networks: dict[str, dict] = {}
        self.device_networks: dict[str, set[str]] = {}
        self.services: dict[tuple[str, int], str] = {}

        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------

    async def load(self):
        async with self._lock:
            with open(self.config_path) as f:
                data = yaml.safe_load(f)

            self.networks = {net["name"]: net for net in data.get("networks", [])}

            self.device_networks.clear()
            for network, devices in data.get("connections", {}).items():
                for device in devices:
                    self.device_networks.setdefault(device, set()).add(network)

    # ------------------------------------------------------------------

    async def expose_service(self, node: str, protocol: str, port: int):
        async with self._lock:
            self.services[(node, port)] = protocol

    # ------------------------------------------------------------------

    async def can_reach(
        self,
        src_network: str,
        dst_node: str,
        protocol: str,
        port: int,
    ) -> bool:
        async with self._lock:
            # Service must exist
            if (dst_node, port) not in self.services:
                return False

            if self.services[(dst_node, port)] != protocol:
                return False

            # Source network must overlap destination networks
            dst_networks = self.device_networks.get(dst_node, set())
            return src_network in dst_networks
