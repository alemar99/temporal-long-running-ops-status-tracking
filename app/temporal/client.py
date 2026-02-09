from typing import Optional

from temporalio.client import Client

from app.constants import TEMPORAL_HOST, TEMPORAL_NAMESPACE



_temporal_client: Optional[Client] = None


async def get_temporal_client() -> Client:
    global _temporal_client

    if _temporal_client is None:
        _temporal_client = await Client.connect(
            TEMPORAL_HOST, namespace=TEMPORAL_NAMESPACE
        )

    return _temporal_client

