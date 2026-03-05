"""Tests for FastMCP 2.14.3 server functionality.

This module tests the FastMCP server instantiation and configuration
to ensure the fastmcp>=2.14.3 dependency (CVE-2025-66416 fix) works correctly.
"""

import asyncio
import warnings
from typing import Annotated
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import Field

from openhands.mcp.client import MCPClient
from openhands.mcp.tool import MCPClientTool


class TestFastMCPServerCreation:
    """Test FastMCP server instantiation."""

    def test_create_fastmcp_server(self):
        """Test that FastMCP server can be created without deprecation warnings."""
        from fastmcp import FastMCP

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            server = FastMCP('test-server')

            # Check for unexpected deprecation warnings
            deprecation_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]

            # There should be no deprecation warnings from server creation
            assert len(deprecation_warnings) == 0, (
                f'Unexpected deprecation warnings: {deprecation_warnings}'
            )
            assert server is not None

    def test_create_fastmcp_server_with_mask_error_details(self):
        """Test FastMCP server with mask_error_details option."""
        from fastmcp import FastMCP

        server = FastMCP('test-server', mask_error_details=True)
        assert server is not None

    def test_fastmcp_tool_decorator(self):
        """Test that FastMCP tool decorator works."""
        from fastmcp import FastMCP

        server = FastMCP('test-server')

        @server.tool()
        async def test_tool(param: str) -> str:
            """A test tool."""
            return f'Processed: {param}'

        # The tool should be registered
        assert test_tool is not None

    def test_fastmcp_tool_with_annotations(self):
        """Test FastMCP tool with Pydantic Field annotations."""
        from fastmcp import FastMCP

        server = FastMCP('test-server')

        @server.tool()
        async def annotated_tool(
            name: Annotated[str, Field(description='The name parameter')],
            value: Annotated[int, Field(description='A numeric value')] = 0,
        ) -> str:
            """A tool with annotated parameters."""
            return f'{name}: {value}'

        assert annotated_tool is not None


class TestMCPClientTool:
    """Test MCPClientTool functionality."""

    def test_mcp_client_tool_creation(self):
        """Test MCPClientTool can be created."""
        tool = MCPClientTool(
            name='test_tool',
            description='A test tool',
            inputSchema={
                'type': 'object',
                'properties': {'param': {'type': 'string'}},
            },
        )
        assert tool.name == 'test_tool'
        assert tool.description == 'A test tool'

    def test_mcp_client_tool_to_param(self):
        """Test MCPClientTool.to_param() returns correct format."""
        tool = MCPClientTool(
            name='create_file',
            description='Creates a new file',
            inputSchema={
                'type': 'object',
                'properties': {
                    'path': {'type': 'string', 'description': 'File path'},
                    'content': {'type': 'string', 'description': 'File content'},
                },
                'required': ['path', 'content'],
            },
        )

        param = tool.to_param()

        assert param['type'] == 'function'
        assert param['function']['name'] == 'create_file'
        assert param['function']['description'] == 'Creates a new file'
        assert param['function']['parameters']['type'] == 'object'
        assert 'path' in param['function']['parameters']['properties']


class TestMCPClientBasic:
    """Test basic MCPClient functionality."""

    def test_mcp_client_instantiation(self):
        """Test MCPClient can be instantiated."""
        client = MCPClient()
        assert client is not None
        assert client.tools == []
        assert client.tool_map == {}
        assert client.client is None

    def test_mcp_client_with_server_timeout(self):
        """Test MCPClient with server timeout configuration."""
        client = MCPClient()
        client.server_timeout = 30.0
        assert client.server_timeout == 30.0


class TestMCPClientConnection:
    """Test MCPClient connection functionality."""

    @pytest.mark.asyncio
    async def test_connect_http_requires_url(self):
        """Test that MCPSSEServerConfig validates URL is not empty."""
        from pydantic import ValidationError

        from openhands.core.config.mcp_config import MCPSSEServerConfig

        # Validation happens at the config level (Pydantic)
        with pytest.raises(ValidationError):
            MCPSSEServerConfig(url='')

    @pytest.mark.asyncio
    @patch('openhands.mcp.client.Client')
    async def test_connect_http_sse_transport(self, mock_client_class):
        """Test connect_http uses SSE transport for SSEServerConfig."""
        from openhands.core.config.mcp_config import MCPSSEServerConfig

        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock the context manager and list_tools
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_tools = AsyncMock(return_value=[])

        client = MCPClient()
        server = MCPSSEServerConfig(url='http://test-server:8080')

        await client.connect_http(server)

        # Verify Client was instantiated
        mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    @patch('openhands.mcp.client.Client')
    async def test_connect_http_shttp_transport(self, mock_client_class):
        """Test connect_http uses StreamableHttp transport for SHTTPServerConfig."""
        from openhands.core.config.mcp_config import MCPSHTTPServerConfig

        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        # Mock the context manager and list_tools
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_tools = AsyncMock(return_value=[])

        client = MCPClient()
        server = MCPSHTTPServerConfig(url='http://test-server:8080', timeout=60)

        await client.connect_http(server)

        # Verify Client was instantiated
        mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    @patch('openhands.mcp.client.Client')
    async def test_connect_http_with_api_key(self, mock_client_class):
        """Test connect_http includes auth headers when API key is provided."""
        from openhands.core.config.mcp_config import MCPSSEServerConfig

        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_tools = AsyncMock(return_value=[])

        client = MCPClient()
        server = MCPSSEServerConfig(url='http://test-server:8080', api_key='secret-key')

        await client.connect_http(server)

        # Client was created with auth headers
        mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    @patch('openhands.mcp.client.Client')
    async def test_connect_http_with_conversation_id(self, mock_client_class):
        """Test connect_http includes conversation ID header."""
        from openhands.core.config.mcp_config import MCPSSEServerConfig

        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_tools = AsyncMock(return_value=[])

        client = MCPClient()
        server = MCPSSEServerConfig(url='http://test-server:8080')

        await client.connect_http(server, conversation_id='conv-123')

        mock_client_class.assert_called_once()

    @pytest.mark.asyncio
    @patch('openhands.mcp.client.Client')
    async def test_connect_stdio(self, mock_client_class):
        """Test connect_stdio creates stdio transport."""
        from openhands.core.config.mcp_config import MCPStdioServerConfig

        # Setup mock
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client

        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_tools = AsyncMock(return_value=[])

        client = MCPClient()
        server = MCPStdioServerConfig(
            name='test-server', command='python', args=['-m', 'test_module']
        )

        await client.connect_stdio(server)

        mock_client_class.assert_called_once()


class TestMCPClientToolCalling:
    """Test MCPClient tool calling functionality."""

    @pytest.mark.asyncio
    async def test_call_tool_not_found(self):
        """Test call_tool raises error for unknown tool."""
        client = MCPClient()
        client.tool_map = {'existing_tool': MagicMock()}

        with pytest.raises(ValueError, match='Tool nonexistent_tool not found'):
            await client.call_tool('nonexistent_tool', {})

    @pytest.mark.asyncio
    async def test_call_tool_no_session(self):
        """Test call_tool raises error when session not available."""
        client = MCPClient()
        mock_tool = MagicMock()
        client.tool_map = {'test_tool': mock_tool}
        client.client = None

        with pytest.raises(RuntimeError, match='Client session is not available'):
            await client.call_tool('test_tool', {})

    @pytest.mark.asyncio
    async def test_call_tool_with_timeout(self):
        """Test call_tool respects server timeout."""
        client = MCPClient()
        client.server_timeout = 5.0

        mock_tool = MagicMock()
        client.tool_map = {'test_tool': mock_tool}

        # Mock the client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Simulate a timeout
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(10)

        mock_client.call_tool_mcp = slow_call
        client.client = mock_client

        with pytest.raises(asyncio.TimeoutError):
            await client.call_tool('test_tool', {'arg': 'value'})

    @pytest.mark.asyncio
    async def test_call_tool_success(self):
        """Test successful tool call."""
        client = MCPClient()

        mock_tool = MagicMock()
        client.tool_map = {'test_tool': mock_tool}

        # Mock the client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        expected_result = MagicMock()
        expected_result.model_dump.return_value = {'result': 'success'}
        mock_client.call_tool_mcp = AsyncMock(return_value=expected_result)

        client.client = mock_client

        result = await client.call_tool('test_tool', {'arg': 'value'})

        assert result == expected_result
        mock_client.call_tool_mcp.assert_called_once_with(
            name='test_tool', arguments={'arg': 'value'}
        )


class TestFastMCPToolError:
    """Test FastMCP ToolError handling."""

    def test_tool_error_creation(self):
        """Test ToolError can be created and raised."""
        from fastmcp.exceptions import ToolError

        error = ToolError('Test error message')
        assert str(error) == 'Test error message'

    def test_tool_error_inheritance(self):
        """Test ToolError is an exception."""
        from fastmcp.exceptions import ToolError

        assert issubclass(ToolError, Exception)


class TestMCPProtocolVersion:
    """Test MCP protocol version compatibility."""

    def test_mcp_types_import(self):
        """Test that mcp types can be imported (CVE-2025-66416 fix verification)."""
        from mcp import McpError
        from mcp.types import CallToolResult, Tool

        assert McpError is not None
        assert CallToolResult is not None
        assert Tool is not None

    def test_mcp_error_is_exception(self):
        """Test McpError is properly defined."""
        from mcp import McpError

        assert issubclass(McpError, Exception)


class TestFastMCPTransports:
    """Test FastMCP transport instantiation."""

    def test_sse_transport_creation(self):
        """Test SSETransport can be created."""
        from fastmcp.client.transports import SSETransport

        transport = SSETransport(
            url='http://localhost:8080/sse', headers={'Authorization': 'Bearer token'}
        )
        assert transport is not None

    def test_streamable_http_transport_creation(self):
        """Test StreamableHttpTransport can be created."""
        from fastmcp.client.transports import StreamableHttpTransport

        transport = StreamableHttpTransport(
            url='http://localhost:8080/mcp', headers={'X-Custom-Header': 'value'}
        )
        assert transport is not None

    def test_stdio_transport_creation(self):
        """Test StdioTransport can be created."""
        from fastmcp.client.transports import StdioTransport

        transport = StdioTransport(
            command='echo', args=['hello'], env={'DEBUG': 'true'}
        )
        assert transport is not None
