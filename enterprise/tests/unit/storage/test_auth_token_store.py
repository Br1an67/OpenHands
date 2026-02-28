"""Unit tests for AuthTokenStore using SQLite in-memory database."""

import time
from typing import Dict
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select, text
from storage.auth_token_store import (
    ACCESS_TOKEN_EXPIRY_BUFFER,
    LOCK_TIMEOUT_SECONDS,
    AuthTokenStore,
)
from storage.auth_tokens import AuthTokens
from storage.base import Base
from openhands.integrations.service_types import ProviderType


@pytest.fixture
async def async_session_maker_with_lock_support(async_engine):
    """Create an async session maker that supports BEGIN IMMEDIATE for SQLite locks."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    # Create all tables
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Enable WAL mode for better concurrent access handling
    async with async_engine.begin() as conn:
        await conn.execute(text('PRAGMA journal_mode=WAL'))
    
    return async_session_maker


@pytest.fixture
async def auth_token_store(async_session_maker):
    """Create AuthTokenStore instance with test session maker."""
    store = AuthTokenStore(
        keycloak_user_id='test-user-123',
        idp=ProviderType.GITHUB,
    )
    # Patch the a_session_maker to use our test fixture
    with patch('storage.auth_token_store.a_session_maker', async_session_maker):
        yield store


@pytest.fixture
async def auth_token_store_with_tokens(async_session_maker):
    """Create AuthTokenStore instance with test session maker and pre-populated tokens."""
    # First, add a token to the database
    async with async_session_maker() as session:
        async with session.begin():
            token = AuthTokens(
                keycloak_user_id='test-user-123',
                identity_provider=ProviderType.GITHUB.value,
                access_token='test-access-token',
                refresh_token='test-refresh-token',
                access_token_expires_at=int(time.time()) + 3600,
                refresh_token_expires_at=int(time.time()) + 86400,
            )
            session.add(token)
        await session.commit()

    store = AuthTokenStore(
        keycloak_user_id='test-user-123',
        idp=ProviderType.GITHUB,
    )
    with patch('storage.auth_token_store.a_session_maker', async_session_maker):
        yield store


class TestIsTokenExpired:
    """Tests for _is_token_expired method."""

    def test_both_tokens_valid(self):
        """Test when both tokens are valid (not expired)."""
        store = AuthTokenStore(keycloak_user_id='test', idp=ProviderType.GITHUB)
        current_time = int(time.time())
        access_expires = current_time + ACCESS_TOKEN_EXPIRY_BUFFER + 1000
        refresh_expires = current_time + 1000

        access_expired, refresh_expired = store._is_token_expired(
            access_expires, refresh_expires
        )

        assert access_expired is False
        assert refresh_expired is False

    def test_access_token_expired(self):
        """Test when access token is expired but within buffer."""
        store = AuthTokenStore(keycloak_user_id='test', idp=ProviderType.GITHUB)
        current_time = int(time.time())
        # Access token expires within buffer period
        access_expires = current_time + ACCESS_TOKEN_EXPIRY_BUFFER - 100
        refresh_expires = current_time + 10000

        access_expired, refresh_expired = store._is_token_expired(
            access_expires, refresh_expires
        )

        assert access_expired is True
        assert refresh_expired is False

    def test_refresh_token_expired(self):
        """Test when refresh token is expired."""
        store = AuthTokenStore(keycloak_user_id='test', idp=ProviderType.GITHUB)
        current_time = int(time.time())
        access_expires = current_time + ACCESS_TOKEN_EXPIRY_BUFFER + 1000
        refresh_expires = current_time - 100  # Already expired

        access_expired, refresh_expired = store._is_token_expired(
            access_expires, refresh_expires
        )

        assert access_expired is False
        assert refresh_expired is True

    def test_both_tokens_expired(self):
        """Test when both tokens are expired."""
        store = AuthTokenStore(keycloak_user_id='test', idp=ProviderType.GITHUB)
        current_time = int(time.time())
        access_expires = current_time - 100
        refresh_expires = current_time - 100

        access_expired, refresh_expired = store._is_token_expired(
            access_expires, refresh_expires
        )

        assert access_expired is True
        assert refresh_expired is True

    def test_zero_expiration_treated_as_never_expires(self):
        """Test that 0 expiration time is treated as never expires."""
        store = AuthTokenStore(keycloak_user_id='test', idp=ProviderType.GITHUB)
        access_expired, refresh_expired = store._is_token_expired(0, 0)

        assert access_expired is False
        assert refresh_expired is False


class TestLoadTokens:
    """Tests for load_tokens method."""

    @pytest.mark.asyncio
    async def test_load_tokens_returns_none_when_not_found(
        self, async_session_maker
    ):
        """Test load_tokens returns None when no token record exists."""
        store = AuthTokenStore(
            keycloak_user_id='nonexistent-user',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            result = await store.load_tokens()

        assert result is None

    @pytest.mark.asyncio
    async def test_load_tokens_returns_valid_token(
        self, async_session_maker
    ):
        """Test load_tokens returns tokens when they are still valid."""
        current_time = int(time.time())
        
        # Add token to database
        async with async_session_maker() as session:
            async with session.begin():
                token = AuthTokens(
                    keycloak_user_id='test-user-123',
                    identity_provider=ProviderType.GITHUB.value,
                    access_token='valid-access-token',
                    refresh_token='valid-refresh-token',
                    access_token_expires_at=current_time + ACCESS_TOKEN_EXPIRY_BUFFER + 1000,
                    refresh_token_expires_at=current_time + 10000,
                )
                session.add(token)
            await session.commit()

        store = AuthTokenStore(
            keycloak_user_id='test-user-123',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            result = await store.load_tokens()

        assert result is not None
        assert result['access_token'] == 'valid-access-token'
        assert result['refresh_token'] == 'valid-refresh-token'

    @pytest.mark.asyncio
    async def test_load_tokens_returns_token_without_refresh_when_no_callback(
        self, async_session_maker
    ):
        """Test load_tokens returns existing tokens when no refresh callback is provided."""
        current_time = int(time.time())
        
        # Add expired token to database
        async with async_session_maker() as session:
            async with session.begin():
                token = AuthTokens(
                    keycloak_user_id='test-user-123',
                    identity_provider=ProviderType.GITHUB.value,
                    access_token='expired-access-token',
                    refresh_token='valid-refresh-token',
                    access_token_expires_at=current_time - 100,  # Expired
                    refresh_token_expires_at=current_time + 10000,
                )
                session.add(token)
            await session.commit()

        store = AuthTokenStore(
            keycloak_user_id='test-user-123',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            result = await store.load_tokens(check_expiration_and_refresh=None)

        assert result is not None
        assert result['access_token'] == 'expired-access-token'

    # Note: The following tests for the "slow path" (token refresh with lock acquisition)
    # require PostgreSQL-specific syntax (SET LOCAL lock_timeout) and are skipped for SQLite.
    # In production, these would be tested with a real PostgreSQL database or test doubles.


class TestStoreTokens:
    """Tests for store_tokens method."""

    @pytest.mark.asyncio
    async def test_store_tokens_creates_new_record(self, async_session_maker):
        """Test storing tokens when no existing record."""
        store = AuthTokenStore(
            keycloak_user_id='test-user-123',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            await store.store_tokens(
                access_token='new-access-token',
                refresh_token='new-refresh-token',
                access_token_expires_at=1234567890,
                refresh_token_expires_at=1234657890,
            )

        # Verify the token was stored
        async with async_session_maker() as session:
            result = await session.execute(
                select(AuthTokens).where(
                    AuthTokens.keycloak_user_id == 'test-user-123',
                    AuthTokens.identity_provider == ProviderType.GITHUB.value,
                )
            )
            token = result.scalars().first()
            assert token is not None
            assert token.access_token == 'new-access-token'
            assert token.refresh_token == 'new-refresh-token'

    @pytest.mark.asyncio
    async def test_store_tokens_updates_existing_record(self, async_session_maker):
        """Test storing tokens updates existing record."""
        current_time = int(time.time())
        
        # First, create a token
        async with async_session_maker() as session:
            async with session.begin():
                token = AuthTokens(
                    keycloak_user_id='test-user-123',
                    identity_provider=ProviderType.GITHUB.value,
                    access_token='old-access-token',
                    refresh_token='old-refresh-token',
                    access_token_expires_at=current_time + 3600,
                    refresh_token_expires_at=current_time + 86400,
                )
                session.add(token)
            await session.commit()

        # Now update the token
        store = AuthTokenStore(
            keycloak_user_id='test-user-123',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            await store.store_tokens(
                access_token='new-access-token',
                refresh_token='new-refresh-token',
                access_token_expires_at=1234567890,
                refresh_token_expires_at=1234657890,
            )

        # Verify the token was updated
        async with async_session_maker() as session:
            result = await session.execute(
                select(AuthTokens).where(
                    AuthTokens.keycloak_user_id == 'test-user-123',
                    AuthTokens.identity_provider == ProviderType.GITHUB.value,
                )
            )
            token = result.scalars().first()
            assert token is not None
            assert token.access_token == 'new-access-token'
            assert token.refresh_token == 'new-refresh-token'


class TestIsAccessTokenValid:
    """Tests for is_access_token_valid method."""

    @pytest.mark.asyncio
    async def test_is_access_token_valid_returns_false_when_no_tokens(
        self, async_session_maker
    ):
        """Test returns False when no tokens found."""
        store = AuthTokenStore(
            keycloak_user_id='nonexistent-user',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            result = await store.is_access_token_valid()

        assert result is False

    @pytest.mark.asyncio
    async def test_is_access_token_valid_returns_true_for_valid_token(
        self, async_session_maker
    ):
        """Test returns True when token is valid."""
        current_time = int(time.time())
        
        async with async_session_maker() as session:
            async with session.begin():
                token = AuthTokens(
                    keycloak_user_id='test-user-123',
                    identity_provider=ProviderType.GITHUB.value,
                    access_token='valid-access',
                    refresh_token='valid-refresh',
                    access_token_expires_at=current_time + 1000,
                    refresh_token_expires_at=current_time + 10000,
                )
                session.add(token)
            await session.commit()

        store = AuthTokenStore(
            keycloak_user_id='test-user-123',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            result = await store.is_access_token_valid()

        assert result is True

    @pytest.mark.asyncio
    async def test_is_access_token_valid_returns_false_for_expired_token(
        self, async_session_maker
    ):
        """Test returns False when token is expired."""
        current_time = int(time.time())
        
        async with async_session_maker() as session:
            async with session.begin():
                token = AuthTokens(
                    keycloak_user_id='test-user-123',
                    identity_provider=ProviderType.GITHUB.value,
                    access_token='expired-access',
                    refresh_token='valid-refresh',
                    access_token_expires_at=current_time - 100,  # Expired
                    refresh_token_expires_at=current_time + 10000,
                )
                session.add(token)
            await session.commit()

        store = AuthTokenStore(
            keycloak_user_id='test-user-123',
            idp=ProviderType.GITHUB,
        )
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            result = await store.is_access_token_valid()

        assert result is False


class TestGetInstance:
    """Tests for get_instance class method."""

    @pytest.mark.asyncio
    async def test_get_instance_creates_auth_token_store(self, async_session_maker):
        """Test get_instance creates an AuthTokenStore with correct params."""
        with patch('storage.auth_token_store.a_session_maker', async_session_maker):
            store = await AuthTokenStore.get_instance(
                keycloak_user_id='user-123', idp=ProviderType.GITHUB
            )

            assert store.keycloak_user_id == 'user-123'
            assert store.idp == ProviderType.GITHUB


class TestIdentityProviderValue:
    """Tests for identity_provider_value property."""

    def test_identity_provider_value_returns_idp_value(self):
        """Test that identity_provider_value returns the enum value."""
        store = AuthTokenStore(keycloak_user_id='test', idp=ProviderType.GITHUB)
        assert store.identity_provider_value == ProviderType.GITHUB.value

    def test_identity_provider_value_for_different_providers(self):
        """Test identity_provider_value for different providers."""
        for provider in [
            ProviderType.GITHUB,
            ProviderType.GITLAB,
            ProviderType.BITBUCKET,
        ]:
            store = AuthTokenStore(
                keycloak_user_id='test-user',
                idp=provider,
            )
            assert store.identity_provider_value == provider.value


class TestConstants:
    """Tests for module constants."""

    def test_access_token_expiry_buffer_value(self):
        """Test ACCESS_TOKEN_EXPIRY_BUFFER is set to 15 minutes."""
        assert ACCESS_TOKEN_EXPIRY_BUFFER == 900

    def test_lock_timeout_seconds_value(self):
        """Test LOCK_TIMEOUT_SECONDS is set to 5 seconds."""
        assert LOCK_TIMEOUT_SECONDS == 5
