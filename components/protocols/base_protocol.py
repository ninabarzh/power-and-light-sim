"""
Base protocol abstraction.

Async-only, library-agnostic.
Protocols expose attacker-meaningful behaviour.
"""


class BaseProtocol:
    def __init__(self, protocol_name: str):
        self.protocol_name = protocol_name
        self.connected: bool = False

    # ------------------------------------------------------------
    # lifecycle
    # ------------------------------------------------------------

    async def connect(self) -> bool:
        """
        Establish protocol session.

        Must set self.connected accordingly.
        """
        raise NotImplementedError

    async def disconnect(self) -> None:
        """
        Tear down protocol session.

        Must leave self.connected = False.
        """
        raise NotImplementedError

    # ------------------------------------------------------------
    # recon
    # ------------------------------------------------------------

    async def probe(self) -> dict[str, object]:
        """
        Perform protocol-level reconnaissance.

        Returns attacker-relevant capabilities, not raw data.
        """
        raise NotImplementedError
