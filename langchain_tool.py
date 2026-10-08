"""LangChain tool that replaces GoogleSearchAPIWrapper.results()."""

from langchain_core.tools import ToolException, tool

from cse_to_serp import cse_list


@tool
def google_search(query: str) -> list[dict]:
    """Search Google and return the top results with title, link, snippet."""
    try:  # 2 attempts and a 20 s timeout bound each search
        return cse_list(q=query, num=10, gl="us", hl="en",
                        attempts=2, timeout=20)["items"]
    except Exception as exc:
        raise ToolException(f"Google search failed: {exc}") from exc


google_search.handle_tool_error = True  # the agent gets the error as text
