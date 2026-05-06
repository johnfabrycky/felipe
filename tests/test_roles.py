import pytest
from unittest.mock import AsyncMock, MagicMock
from bot.services.roles_service import RolesService


@pytest.fixture
def mock_supabase():
    # Create a deep mock of the Supabase client chain
    supabase = MagicMock()
    # Mock chain: supabase.table().upsert().execute()
    supabase.table.return_value.upsert.return_value.execute = AsyncMock()
    return supabase


@pytest.fixture
def service(mock_supabase):
    return RolesService(mock_supabase)


@pytest.mark.asyncio
async def test_update_resident_status_success(mock_supabase, service):
    """Test standard house role update without an email."""
    # Arrange
    mock_execute = mock_supabase.table().upsert().execute
    mock_execute.return_value.data = [{"id": 1}]  # Simulate successful DB return

    # Act
    result = await service.update_resident_status(
        discord_id=123456789, username="TestUser", role_slug="koinonian"
    )

    # Assert
    assert result is True
    mock_supabase.table.assert_called_with("residents")
    mock_supabase.table().upsert.assert_called_with(
        {
            "discord_id": "123456789",
            "username": "TestUser",
            "community_role": "koinonian",
        }
    )


@pytest.mark.asyncio
async def test_update_resident_status_alumni_with_email(mock_supabase, service):
    """Test alumni role update including an email."""
    # Arrange
    mock_execute = mock_supabase.table().upsert().execute
    mock_execute.return_value.data = [{"id": 2}]

    # Act
    result = await service.update_resident_status(
        discord_id=987654321,
        username="AlumniUser",
        role_slug="alumni",
        email="alumni@example.com",
    )

    # Assert
    assert result is True
    mock_supabase.table().upsert.assert_called_with(
        {
            "discord_id": "987654321",
            "username": "AlumniUser",
            "community_role": "alumni",
            "email": "alumni@example.com",
        }
    )


@pytest.mark.asyncio
async def test_update_resident_status_failure(mock_supabase, service):
    """Test handling of database exceptions."""
    # Arrange
    mock_execute = mock_supabase.table().upsert().execute
    mock_execute.side_effect = Exception("Database connection lost")

    # Act
    result = await service.update_resident_status(
        discord_id=111, username="FailUser", role_slug="suttonite"
    )

    # Assert
    assert result is False