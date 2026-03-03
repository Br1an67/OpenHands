# tests/test_condenser_max_step_experiment_v1.py

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from experiments.experiment_manager import SaaSExperimentManager

# SUT imports (update the module path if needed)
from experiments.experiment_versions._004_condenser_max_step_experiment import (
    handle_condenser_max_step_experiment__v1,
)
from pydantic import SecretStr

from openhands.sdk import LLM, Agent
from openhands.sdk.context.condenser import LLMSummarizingCondenser


def make_agent() -> Agent:
    """Build a minimal valid Agent."""
    llm = LLM(
        usage_id='primary-llm',
        model='provider/model',
        api_key=SecretStr('sk-test'),
    )
    return Agent(llm=llm)


def _patch_variant_async(monkeypatch, return_value):
    """Patch the internal variant getter to return a specific value (async)."""

    async def mock_get_variant(user_id, conv_id):
        return return_value

    monkeypatch.setattr(
        'experiments.experiment_versions._004_condenser_max_step_experiment._get_condenser_max_step_variant',
        mock_get_variant,
        raising=True,
    )


@pytest.mark.asyncio
async def test_control_variant_sets_condenser_with_max_size_120(monkeypatch):
    _patch_variant_async(monkeypatch, 'control')
    agent = make_agent()
    conv_id = uuid4()

    result = await handle_condenser_max_step_experiment__v1('user-1', conv_id, agent)

    # Should be a new Agent instance with a condenser installed
    assert result is not agent
    assert isinstance(result.condenser, LLMSummarizingCondenser)

    # The condenser should have its own LLM (usage_id overridden to "condenser")
    assert result.condenser.llm.usage_id == 'condenser'
    # The original agent LLM remains unchanged
    assert agent.llm.usage_id == 'primary-llm'

    # Control: max_size = 120, keep_first = 4
    assert result.condenser.max_size == 120
    assert result.condenser.keep_first == 4


@pytest.mark.asyncio
async def test_treatment_variant_sets_condenser_with_max_size_80(monkeypatch):
    _patch_variant_async(monkeypatch, 'treatment')
    agent = make_agent()
    conv_id = uuid4()

    result = await handle_condenser_max_step_experiment__v1('user-2', conv_id, agent)

    assert result is not agent
    assert isinstance(result.condenser, LLMSummarizingCondenser)
    assert result.condenser.llm.usage_id == 'condenser'
    assert result.condenser.max_size == 80
    assert result.condenser.keep_first == 4


@pytest.mark.asyncio
async def test_none_variant_returns_original_agent_without_changes(monkeypatch):
    _patch_variant_async(monkeypatch, None)
    agent = make_agent()
    conv_id = uuid4()

    result = await handle_condenser_max_step_experiment__v1('user-3', conv_id, agent)

    # No changes—same instance and no condenser attribute added
    assert result is agent
    assert getattr(result, 'condenser', None) is None


@pytest.mark.asyncio
async def test_unknown_variant_returns_original_agent_without_changes(monkeypatch):
    _patch_variant_async(monkeypatch, 'weird-variant')
    agent = make_agent()
    conv_id = uuid4()

    result = await handle_condenser_max_step_experiment__v1('user-4', conv_id, agent)

    assert result is agent
    assert getattr(result, 'condenser', None) is None


@pytest.mark.asyncio
@patch('experiments.experiment_manager.ENABLE_EXPERIMENT_MANAGER', False)
async def test_run_agent_variant_tests_v1_noop_when_manager_disabled():
    """If ENABLE_EXPERIMENT_MANAGER is False, the method returns the exact same agent and does not call the handler."""
    agent = make_agent()
    conv_id = uuid4()

    result = await SaaSExperimentManager.run_agent_variant_tests__v1(
        user_id='user-123',
        conversation_id=conv_id,
        agent=agent,
    )

    # Same object returned (no copy)
    assert result is agent


@pytest.mark.asyncio
@patch('experiments.experiment_manager.ENABLE_EXPERIMENT_MANAGER', True)
@patch('experiments.experiment_manager.EXPERIMENT_SYSTEM_PROMPT_EXPERIMENT', True)
async def test_run_agent_variant_tests_v1_calls_handler_and_sets_system_prompt(
    monkeypatch,
):
    """When enabled, it should call the condenser experiment handler and set the long-horizon system prompt."""
    agent = make_agent()
    conv_id = uuid4()

    _patch_variant_async(monkeypatch, 'treatment')

    result: Agent = await SaaSExperimentManager.run_agent_variant_tests__v1(
        user_id='user-abc',
        conversation_id=conv_id,
        agent=agent,
    )

    # Should be a different instance than the original (copied after handler runs)
    assert result is not agent
    assert result.system_prompt_filename == 'system_prompt_long_horizon.j2'


@pytest.mark.asyncio
@patch('experiments.experiment_manager.ENABLE_EXPERIMENT_MANAGER', True)
@patch('experiments.experiment_manager.EXPERIMENT_SYSTEM_PROMPT_EXPERIMENT', True)
async def test_run_agent_variant_tests_v1_preserves_planning_agent_system_prompt():
    """Planning agents should retain their specialized system prompt and not be overwritten by the experiment."""
    # Arrange
    planning_agent = make_agent().model_copy(
        update={'system_prompt_filename': 'system_prompt_planning.j2'}
    )
    conv_id = uuid4()

    # Act
    result: Agent = await SaaSExperimentManager.run_agent_variant_tests__v1(
        user_id='user-planning',
        conversation_id=conv_id,
        agent=planning_agent,
    )

    # Assert
    assert result.system_prompt_filename == 'system_prompt_planning.j2'
