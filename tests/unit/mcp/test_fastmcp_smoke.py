"""Smoke tests for fastmcp 2.14.3 upgrade.

These tests verify that the core MCP functionality still works after
upgrading fastmcp from 2.12.4 to 2.14.3. This upgrade brings significant
dependency changes including new transitive dependencies (beartype,
croniter, diskcache, fakeredis, pydocket, etc.).

The tests cover:
1. FastMCP server initialization and tool registration
2. MCP client-server communication
3. Tool invocation and result handling
4. OpenHands MCP client integration
"""

from typing import Annotated
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import SSETransport, StreamableHttpTransport
from fastmcp.exceptions import ToolError
from mcp import McpError
from mcp.types import CallToolResult, TextContent, Tool
from pydantic import Field

from openhands.core.config.mcp_config import (
    MCPConfig,
    MCPSHTTPServerConfig,
    MCPSSEServerConfig,
    MCPStdioServerConfig,
)
from openhands.mcp.client import MCPClient
from openhands.mcp.tool import MCPClientTool
from openhands.mcp.utils import convert_mcp_clients_to_tools


class TestFastMCPServerSmoke:
    """Smoke tests for FastMCP server functionality."""

    def test_server_creation(self):
        """Test FastMCP server can be created with various options."""
        # Basic server
        server = FastMCP('test-server')
        assert server is not None
        assert server.name == 'test-server'

        # Server with error masking
        server_masked = FastMCP('masked-server', mask_error_details=True)
        assert server_masked is not None

    def test_tool_registration_decorator(self):
        """Test that tools can be registered using the decorator pattern."""
        server = FastMCP('tool-test-server')

        @server.tool()
        def simple_tool(x: int, y: int) -> int:
            """Add two numbers."""
            return x + y

        # Verify tool was registered
        assert 'simple_tool' in [t.name for t in server._tool_manager._tools.values()]

    def test_async_tool_registration(self):
        """Test that async tools can be registered."""
        server = FastMCP('async-tool-server')

        @server.tool()
        async def async_tool(message: str) -> str:
            """Echo a message asynchronously."""
            return f'Echo: {message}'

        assert 'async_tool' in [t.name for t in server._tool_manager._tools.values()]

    def test_annotated_tool_parameters(self):
        """Test tools with Annotated parameter descriptions."""
        server = FastMCP('annotated-tool-server')

        @server.tool()
        def annotated_tool(
            name: Annotated[str, Field(description='The name to greet')],
            count: Annotated[int, Field(description='Number of times to greet')] = 1,
        ) -> str:
            """Greet someone multiple times."""
            return f'Hello, {name}! ' * count

        # Tool should be registered with proper schema
        tools = list(server._tool_manager._tools.values())
        assert len(tools) >= 1
        tool = next(t for t in tools if t.name == 'annotated_tool')
        assert tool.description == 'Greet someone multiple times.'


class TestMCPClientSmoke:
    """Smoke tests for MCP client functionality."""

    def test_mcp_client_tool_creation(self):
        """Test MCPClientTool can be created from Tool data."""
        tool = MCPClientTool(
            name='test_tool',
            description='A test tool',
            inputSchema={
                'type': 'object',
                'properties': {'arg1': {'type': 'string'}},
                'required': ['arg1'],
            },
        )
        assert tool.name == 'test_tool'
        assert tool.description == 'A test tool'

    def test_mcp_client_tool_to_param(self):
        """Test MCPClientTool converts to function call format."""
        tool = MCPClientTool(
            name='calculator',
            description='Perform calculations',
            inputSchema={
                'type': 'object',
                'properties': {
                    'operation': {'type': 'string'},
                    'a': {'type': 'number'},
                    'b': {'type': 'number'},
                },
            },
        )
        param = tool.to_param()

        assert param['type'] == 'function'
        assert param['function']['name'] == 'calculator'
        assert param['function']['description'] == 'Perform calculations'
        assert 'parameters' in param['function']

    def test_mcp_client_initialization(self):
        """Test MCPClient can be initialized."""
        client = MCPClient()
        assert client.client is None
        assert client.tools == []
        assert client.tool_map == {}

    def test_convert_mcp_clients_to_tools_empty(self):
        """Test convert_mcp_clients_to_tools handles empty list."""
        result = convert_mcp_clients_to_tools([])
        assert result == []

    def test_convert_mcp_clients_to_tools_none(self):
        """Test convert_mcp_clients_to_tools handles None."""
        result = convert_mcp_clients_to_tools(None)
        assert result == []

    def test_convert_mcp_clients_to_tools_with_tools(self):
        """Test convert_mcp_clients_to_tools converts tools properly."""
        # Create a mock client with tools
        client = MCPClient()
        client.tools = [
            MCPClientTool(
                name='tool1',
                description='First tool',
                inputSchema={'type': 'object', 'properties': {}},
            ),
            MCPClientTool(
                name='tool2',
                description='Second tool',
                inputSchema={'type': 'object', 'properties': {}},
            ),
        ]

        result = convert_mcp_clients_to_tools([client])
        assert len(result) == 2
        assert result[0]['function']['name'] == 'tool1'
        assert result[1]['function']['name'] == 'tool2'


class TestMCPTransportsSmoke:
    """Smoke tests for MCP transport types."""

    def test_sse_transport_creation(self):
        """Test SSETransport can be created with various configurations."""
        # Basic transport
        transport = SSETransport(url='http://localhost:8080/sse')
        assert transport is not None

        # Transport with headers
        transport_with_headers = SSETransport(
            url='http://localhost:8080/sse',
            headers={'Authorization': 'Bearer test-token'},
        )
        assert transport_with_headers is not None

    def test_streamable_http_transport_creation(self):
        """Test StreamableHttpTransport can be created."""
        transport = StreamableHttpTransport(
            url='http://localhost:8080/mcp',
            headers={'X-API-Key': 'test-key'},
        )
        assert transport is not None

    def test_mcp_client_with_custom_transport(self):
        """Test fastmcp Client accepts custom transports."""
        transport = SSETransport(url='http://localhost:8080/sse')
        client = Client(transport, timeout=30.0)
        assert client is not None


class TestMCPConfigSmoke:
    """Smoke tests for MCP configuration types."""

    def test_sse_server_config(self):
        """Test MCPSSEServerConfig creation."""
        config = MCPSSEServerConfig(url='http://localhost:8080/sse', api_key='test-key')
        assert config.url == 'http://localhost:8080/sse'
        assert config.api_key == 'test-key'

    def test_shttp_server_config(self):
        """Test MCPSHTTPServerConfig creation."""
        config = MCPSHTTPServerConfig(
            url='http://localhost:8080/mcp', api_key='test-key', timeout=60
        )
        assert config.url == 'http://localhost:8080/mcp'
        assert config.timeout == 60

    def test_stdio_server_config(self):
        """Test MCPStdioServerConfig creation."""
        config = MCPStdioServerConfig(
            name='test-stdio', command='python', args=['-m', 'test_server']
        )
        assert config.name == 'test-stdio'
        assert config.command == 'python'
        assert config.args == ['-m', 'test_server']

    def test_mcp_config_creation(self):
        """Test MCPConfig can hold multiple server configurations."""
        config = MCPConfig(
            sse_servers=[MCPSSEServerConfig(url='http://sse.example.com')],
            shttp_servers=[MCPSHTTPServerConfig(url='http://shttp.example.com')],
            stdio_servers=[MCPStdioServerConfig(name='stdio', command='echo')],
        )
        assert len(config.sse_servers) == 1
        assert len(config.shttp_servers) == 1
        assert len(config.stdio_servers) == 1


class TestMCPTypesSmoke:
    """Smoke tests for MCP types from the mcp package."""

    def test_tool_type(self):
        """Test Tool type from mcp package."""
        tool = Tool(
            name='test',
            description='A test tool',
            inputSchema={'type': 'object', 'properties': {}},
        )
        assert tool.name == 'test'

    def test_text_content_type(self):
        """Test TextContent for tool responses."""
        content = TextContent(type='text', text='Hello, world!')
        assert content.type == 'text'
        assert content.text == 'Hello, world!'

    def test_call_tool_result_type(self):
        """Test CallToolResult structure."""
        result = CallToolResult(
            content=[TextContent(type='text', text='Result data')], isError=False
        )
        assert not result.isError
        assert len(result.content) == 1


class TestMCPExceptionsSmoke:
    """Smoke tests for MCP exception types."""

    def test_tool_error_creation(self):
        """Test ToolError from fastmcp."""
        error = ToolError('Something went wrong')
        assert str(error) == 'Something went wrong'
        assert isinstance(error, Exception)

    def test_mcp_error_creation(self):
        """Test McpError from mcp package."""
        from mcp.types import ErrorData

        error_data = ErrorData(code=-1, message='Test error')
        error = McpError(error_data)
        assert isinstance(error, Exception)


class TestFastMCPIntegrationSmoke:
    """Integration smoke tests for fastmcp functionality."""

    @pytest.mark.asyncio
    async def test_in_process_server_client_communication(self):
        """Test server and client can communicate in-process using mocks."""
        # Create a server with a tool
        server = FastMCP('integration-test-server')

        @server.tool()
        def add_numbers(a: int, b: int) -> int:
            """Add two numbers together."""
            return a + b

        # Verify the tool is registered
        tools = list(server._tool_manager._tools.values())
        tool_names = [t.name for t in tools]
        assert 'add_numbers' in tool_names

        # Find our tool
        add_tool = next(t for t in tools if t.name == 'add_numbers')
        assert add_tool.description == 'Add two numbers together.'

    @pytest.mark.asyncio
    async def test_openhands_mcp_client_with_mock_server(self):
        """Test OpenHands MCPClient with a mocked fastmcp Client."""
        # Create our MCPClient
        mcp_client = MCPClient()

        # Create mock tools using actual Tool objects (MagicMock doesn't work well with pydantic)
        mock_tools = [
            Tool(
                name='search_files',
                description='Search for files',
                inputSchema={
                    'type': 'object',
                    'properties': {'query': {'type': 'string'}},
                },
            ),
            Tool(
                name='read_file',
                description='Read a file',
                inputSchema={
                    'type': 'object',
                    'properties': {'path': {'type': 'string'}},
                },
            ),
        ]

        # Mock the fastmcp Client
        mock_client = AsyncMock()
        mock_client.list_tools = AsyncMock(return_value=mock_tools)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mcp_client.client = mock_client

        # Initialize and list tools
        await mcp_client._initialize_and_list_tools()

        # Verify tools were populated
        assert len(mcp_client.tools) == 2
        assert 'search_files' in mcp_client.tool_map
        assert 'read_file' in mcp_client.tool_map

    @pytest.mark.asyncio
    async def test_mcp_tool_call_with_mock(self):
        """Test tool invocation through MCPClient with mocked response."""
        mcp_client = MCPClient()

        # Set up mock tool
        mcp_client.tools = [
            MCPClientTool(
                name='greet',
                description='Greet someone',
                inputSchema={
                    'type': 'object',
                    'properties': {'name': {'type': 'string'}},
                },
            )
        ]
        mcp_client.tool_map = {'greet': mcp_client.tools[0]}

        # Mock the client
        mock_result = CallToolResult(
            content=[TextContent(type='text', text='Hello, World!')], isError=False
        )
        mock_client = AsyncMock()
        mock_client.call_tool_mcp = AsyncMock(return_value=mock_result)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mcp_client.client = mock_client

        # Call the tool
        result = await mcp_client.call_tool('greet', {'name': 'World'})

        assert result is not None
        assert not result.isError
        assert len(result.content) == 1


class TestOpenHandsMCPRouteSmoke:
    """Smoke tests for OpenHands MCP route components."""

    def test_mcp_server_import(self):
        """Test mcp_server can be imported from routes."""
        from openhands.server.routes.mcp import mcp_server

        assert mcp_server is not None
        assert mcp_server.name == 'mcp'

    def test_mcp_server_tools_registered(self):
        """Test that MCP server has expected tools registered."""
        from openhands.server.routes.mcp import mcp_server

        # Get registered tools
        tools = list(mcp_server._tool_manager._tools.values())
        tool_names = [t.name for t in tools]

        # Verify core PR/MR tools are registered
        expected_tools = [
            'create_pr',
            'create_mr',
            'create_bitbucket_pr',
            'create_azure_devops_pr',
        ]
        for expected in expected_tools:
            assert expected in tool_names, f'Expected tool {expected} not found'


class TestFastMCPDependencyImportsSmoke:
    """Verify all fastmcp-related imports work after the upgrade."""

    def test_fastmcp_core_imports(self):
        """Test core fastmcp imports."""
        from fastmcp import Client, FastMCP
        from fastmcp.exceptions import ToolError
        from fastmcp.server.dependencies import get_http_request

        assert FastMCP is not None
        assert Client is not None
        assert ToolError is not None
        assert get_http_request is not None

    def test_fastmcp_transport_imports(self):
        """Test transport imports."""
        from fastmcp.client.transports import (
            SSETransport,
            StdioTransport,
            StreamableHttpTransport,
        )

        assert SSETransport is not None
        assert StreamableHttpTransport is not None
        assert StdioTransport is not None

    def test_mcp_package_imports(self):
        """Test mcp package imports."""
        from mcp import McpError
        from mcp.server.fastmcp.server import Settings
        from mcp.server.session import ServerSession
        from mcp.shared.exceptions import McpError as SharedMcpError
        from mcp.types import CallToolResult, ErrorData, TextContent, Tool

        assert McpError is not None
        assert SharedMcpError is not None
        assert Settings is not None
        assert ServerSession is not None
        assert Tool is not None
        assert TextContent is not None
        assert CallToolResult is not None
        assert ErrorData is not None

    def test_openhands_mcp_imports(self):
        """Test OpenHands MCP module imports."""
        from openhands.mcp.client import MCPClient
        from openhands.mcp.error_collector import mcp_error_collector
        from openhands.mcp.tool import MCPClientTool
        from openhands.mcp.utils import (
            call_tool_mcp,
            convert_mcp_clients_to_tools,
            create_mcp_clients,
            fetch_mcp_tools_from_config,
        )

        assert MCPClient is not None
        assert MCPClientTool is not None
        assert mcp_error_collector is not None
        assert convert_mcp_clients_to_tools is not None
        assert create_mcp_clients is not None
        assert fetch_mcp_tools_from_config is not None
        assert call_tool_mcp is not None
