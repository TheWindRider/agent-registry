"""Unit tests for registry_store backends (InMemoryStore)."""

import time

import pytest
from python_a2a import AgentCard, AgentSkill

from registry_store import InMemoryStore, create_store_from_env


def make_card(
    url: str = "https://agent.example.com", name: str = "test-agent"
) -> AgentCard:
    return AgentCard(
        name=name,
        description="A test agent",
        url=url,
        version="1.0.0",
        capabilities={"streaming": False},
        skills=[
            AgentSkill(
                id="echo",
                name="Echo",
                description="Echoes input",
                tags=["test"],
                examples=["hello"],
            )
        ],
    )


class TestInMemoryStore:
    def test_register_and_get(self):
        store = InMemoryStore()
        card = make_card()
        assert store.register(card) is True
        fetched = store.get(card.url)
        assert fetched is not None
        assert fetched.name == card.name
        assert fetched.url == card.url

    def test_register_requires_url(self):
        store = InMemoryStore()
        card = make_card(url="")
        assert store.register(card) is False

    def test_register_is_upsert(self):
        store = InMemoryStore()
        store.register(make_card(name="v1"))
        store.register(make_card(name="v2"))
        card = store.get("https://agent.example.com")
        assert card is not None
        assert card.name == "v2"
        assert len(store.list()) == 1

    def test_unregister(self):
        store = InMemoryStore()
        card = make_card()
        store.register(card)
        assert store.unregister(card.url) is True
        assert store.get(card.url) is None
        assert store.unregister(card.url) is False

    def test_list(self):
        store = InMemoryStore()
        store.register(make_card(url="https://a.example.com"))
        store.register(make_card(url="https://b.example.com"))
        urls = {c.url for c in store.list()}
        assert urls == {"https://a.example.com", "https://b.example.com"}

    def test_heartbeat(self):
        store = InMemoryStore()
        card = make_card()
        store.register(card)
        time.sleep(0.01)
        assert store.heartbeat(card.url) is True
        assert store.heartbeat("https://unknown.example.com") is False

    def test_prune_stale(self):
        store = InMemoryStore()
        card = make_card()
        store.register(card)
        # No sleep: last_seen is now, so nothing is stale within 60s
        assert store.prune_stale(60) == []
        assert store.get(card.url) is not None
        # Simulate staleness by pruning with zero tolerance
        time.sleep(0.01)
        pruned = store.prune_stale(0)
        assert pruned == [card.url]
        assert store.get(card.url) is None


class TestStoreFactory:
    def test_default_is_memory(self, monkeypatch):
        monkeypatch.delenv("REGISTRY_BACKEND", raising=False)
        assert isinstance(create_store_from_env(), InMemoryStore)

    def test_memory_explicit(self, monkeypatch):
        monkeypatch.setenv("REGISTRY_BACKEND", "memory")
        assert isinstance(create_store_from_env(), InMemoryStore)

    def test_invalid_backend_raises(self, monkeypatch):
        monkeypatch.setenv("REGISTRY_BACKEND", "redis")
        with pytest.raises(ValueError):
            create_store_from_env()
