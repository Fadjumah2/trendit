# Trendit: Google Business Profile Digital Worker

An automated digital worker for managing Google Business Profiles with minimal human-in-the-loop, built using Google's Agent Development Kit (ADK) and Model Context Protocol (MCP).

## Dependencies

- `google-adk==0.3.0`
- `mcp[cli]==1.5.0`
- `beautifulsoup4`
- `requests`
- `html2text`

## Structure

- `src/agent.py`: ADK Agent definition.
- `src/mcp_server.py`: MCP Server for tool and resource exposure.
- `src/business_logic.py`: Core logic for GBP management.
