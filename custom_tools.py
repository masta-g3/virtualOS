"""
Custom tools for the agent.

Define functions following this pattern:

    def my_tool(ctx, arg: str) -> str:
        '''Docstring becomes tool description for LLM.'''
        return "result"

Access agent state via ctx.deps:
    - ctx.deps.fs: VirtualFileSystem (read, write, list_dir, etc.)
    - ctx.deps.workspace_path: Host workspace Path

Add your tools to the TOOLS list at bottom.
"""
from pydantic_ai import RunContext


def web_search(ctx, query: str) -> str:
    """
    Search the web for information.

    Args:
        query: Search query string
    """
    # TODO: Implement with your preferred search API
    return f"[web_search not implemented] Query: {query}"


TOOLS = [web_search]
