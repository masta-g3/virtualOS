"""Shared fixtures for pyagents tests."""

import pytest
from unittest.mock import MagicMock
from pathlib import Path

from virtual_agent import VirtualFileSystem, AgentDeps


@pytest.fixture
def vfs():
    """Fresh VirtualFileSystem for each test."""
    return VirtualFileSystem()


@pytest.fixture
def deps(vfs, tmp_path):
    """AgentDeps with VFS and temp workspace."""
    return AgentDeps(fs=vfs, user_name="test", workspace_path=tmp_path)


@pytest.fixture
def mock_ctx(deps):
    """Mock RunContext with deps attached."""
    ctx = MagicMock()
    ctx.deps = deps
    return ctx
