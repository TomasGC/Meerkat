"""Research agent exposing two retrieval tools."""

from langchain.agents import AgentExecutor
from langchain.tools import BaseTool, tool


@tool
def search_documents(query: str, top_k: int = 5) -> list[str]:
    """Search the indexed document corpus."""
    return []


@tool
def calculate_risk(exposure: float, probability: float) -> float:
    """Score the risk of an exposure."""
    return exposure * probability


class WebScraperTool(BaseTool):
    """Fetch a page and return its text."""

    name = "web_scraper"
    description = "Fetch a URL and return readable text"

    def _run(self, url: str) -> str:
        return ""


research_agent = None

executor = AgentExecutor(agent=research_agent, tools=[search_documents, calculate_risk])
