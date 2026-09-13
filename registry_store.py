"""Registry state storage backends for the A2A agent registry.

The registry keeps a mapping of agent URL -> AgentCard plus a last-seen
timestamp used for stale-agent pruning. This module abstracts that state
behind a small interface so the registry can run:

* ``InMemoryStore``   - default; single-process, ideal for local dev/tests.
* ``FirestoreStore``  - production; multi-instance safe on Cloud Run.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from python_a2a import AgentCard

logger = logging.getLogger(__name__)

# Firestore document field names
_FIELD_CARD = "card"
_FIELD_LAST_SEEN = "last_seen"


class RegistryStore(ABC):
    """Interface for registry state storage."""

    @abstractmethod
    def register(self, agent_card: AgentCard) -> bool:
        """Store (or overwrite) an agent card. Returns True on success."""

    @abstractmethod
    def unregister(self, agent_url: str) -> bool:
        """Remove an agent by URL. Returns True if it existed."""

    @abstractmethod
    def get(self, agent_url: str) -> Optional[AgentCard]:
        """Fetch a single agent card by URL, or None."""

    @abstractmethod
    def list(self) -> List[AgentCard]:
        """List all registered agent cards."""

    @abstractmethod
    def heartbeat(self, agent_url: str) -> bool:
        """Refresh the last-seen timestamp. Returns True if agent exists."""

    @abstractmethod
    def prune_stale(self, max_age_seconds: float) -> List[str]:
        """Remove agents silent for longer than max_age_seconds.

        Returns the list of pruned agent URLs.
        """


class InMemoryStore(RegistryStore):
    """Thread-safe in-memory implementation (single process)."""

    def __init__(self) -> None:
        self._agents: Dict[str, AgentCard] = {}
        self._last_seen: Dict[str, float] = {}

    def register(self, agent_card: AgentCard) -> bool:
        if not agent_card.url:
            return False
        self._agents[agent_card.url] = agent_card
        self._last_seen[agent_card.url] = time.time()
        return True

    def unregister(self, agent_url: str) -> bool:
        existed = agent_url in self._agents
        self._agents.pop(agent_url, None)
        self._last_seen.pop(agent_url, None)
        return existed

    def get(self, agent_url: str) -> Optional[AgentCard]:
        return self._agents.get(agent_url)

    def list(self) -> List[AgentCard]:
        return list(self._agents.values())

    def heartbeat(self, agent_url: str) -> bool:
        if agent_url not in self._agents:
            return False
        self._last_seen[agent_url] = time.time()
        return True

    def prune_stale(self, max_age_seconds: float) -> List[str]:
        now = time.time()
        stale = [
            url
            for url, last_seen in self._last_seen.items()
            if now - last_seen > max_age_seconds
        ]
        for url in stale:
            self._agents.pop(url, None)
            self._last_seen.pop(url, None)
        return stale


class FirestoreStore(RegistryStore):
    """Firestore-backed store: one document per agent in a collection.

    Document ID is the agent URL; fields are the serialized agent card and a
    ``last_seen`` server timestamp. Safe for multiple Cloud Run instances.
    """

    def __init__(
        self, project: Optional[str] = None, collection: str = "agents"
    ) -> None:
        from google.cloud import firestore  # imported lazily

        self._collection_name = collection
        project = (
            project or os.getenv("GCP_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
        )
        kwargs = {"project": project} if project else {}
        self._db = firestore.Client(**kwargs)
        self._collection = self._db.collection(collection)
        logger.info(
            "FirestoreStore initialized (project=%s, collection=%s)",
            project or "<default>",
            collection,
        )

    def register(self, agent_card: AgentCard) -> bool:
        if not agent_card.url:
            return False
        self._collection.document(agent_card.url).set(
            {
                _FIELD_CARD: agent_card.to_dict(),
                _FIELD_LAST_SEEN: time.time(),
            },
            merge=True,
        )
        return True

    def unregister(self, agent_url: str) -> bool:
        doc = self._collection.document(agent_url)
        snapshot = doc.get()
        if not snapshot.exists:
            return False
        doc.delete()
        return True

    def get(self, agent_url: str) -> Optional[AgentCard]:
        snapshot = self._collection.document(agent_url).get()
        if not snapshot.exists:
            return None
        return self._snapshot_to_card(snapshot)

    def list(self) -> List[AgentCard]:
        cards: List[AgentCard] = []
        for snapshot in self._collection.stream():
            card = self._snapshot_to_card(snapshot)
            if card is not None:
                cards.append(card)
        return cards

    def heartbeat(self, agent_url: str) -> bool:
        doc_ref = self._collection.document(agent_url)
        snapshot = doc_ref.get()
        if not snapshot.exists:
            return False
        doc_ref.set({_FIELD_LAST_SEEN: time.time()}, merge=True)
        return True

    def prune_stale(self, max_age_seconds: float) -> List[str]:
        cutoff = time.time() - max_age_seconds
        stale: List[str] = []
        # Firestore requires an inequality filter to be ordered by the same
        # field, so order by last_seen ascending.
        query = self._collection.where(_FIELD_LAST_SEEN, "<", cutoff).order_by(
            _FIELD_LAST_SEEN
        )
        batch = self._db.batch()
        for snapshot in query.stream():
            stale.append(snapshot.id)
            batch.delete(snapshot.reference)
        if stale:
            batch.commit()
        return stale

    @staticmethod
    def _snapshot_to_card(snapshot) -> Optional[AgentCard]:
        data = snapshot.to_dict() or {}
        card_dict = data.get(_FIELD_CARD)
        if not card_dict:
            logger.warning(
                "Firestore doc %s has no card payload; skipping", snapshot.id
            )
            return None
        try:
            return AgentCard.from_dict(card_dict)
        except Exception:  # noqa: BLE001 - corrupt docs must not kill list()
            logger.exception("Failed to parse agent card from doc %s", snapshot.id)
            return None


def create_store_from_env() -> RegistryStore:
    """Build the configured store from REGISTRY_BACKEND (default: memory)."""
    backend = os.getenv("REGISTRY_BACKEND", "memory").strip().lower()
    if backend == "firestore":
        return FirestoreStore()
    if backend in ("memory", "inmemory", "in-memory", ""):
        return InMemoryStore()
    raise ValueError(
        f"Unsupported REGISTRY_BACKEND '{backend}'. Use 'memory' or 'firestore'."
    )
