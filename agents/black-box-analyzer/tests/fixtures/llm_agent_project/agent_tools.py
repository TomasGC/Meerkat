#!/usr/bin/env python3
"""LangChain agent tools example."""

from langchain.tools import tool, BaseTool
from langchain.agents import AgentExecutor, initialize_agent
from langchain.prompts import PromptTemplate, ChatPromptTemplate
from langchain.chains import LLMChain


@tool
def search_documents(query: str, limit: int = 10) -> str:
    """Search documents in the knowledge base.

    Args:
        query: Search query string
        limit: Maximum number of results

    Returns:
        Search results as JSON string
    """
    # Simulate document search
    results = []
    for i in range(limit):
        results.append({
            "id": i,
            "title": f"Document {i}",
            "content": f"Content for {query}"
        })
    return str(results)


@tool
def calculate_risk(exposure: float, probability: float) -> float:
    """Calculate risk score.

    Args:
        exposure: Financial exposure amount
        probability: Probability of occurrence (0-1)

    Returns:
        Risk score (exposure * probability)
    """
    return exposure * probability


class WebScraperTool(BaseTool):
    """Custom web scraping tool."""

    name = "web_scraper"
    description = "Scrape content from web pages"

    def _run(self, url: str) -> str:
        """Execute web scraping."""
        # Simulate scraping
        return f"Content from {url}"

    async def _arun(self, url: str) -> str:
        """Async execution."""
        return self._run(url)


# Agent setup
def create_agent():
    """Create LangChain agent with tools."""
    tools = [search_documents, calculate_risk, WebScraperTool()]

    agent = initialize_agent(
        tools=tools,
        agent_type="zero-shot-react-description",
        verbose=True
    )

    return AgentExecutor(agent=agent, tools=tools)


# Prompt templates
search_prompt = PromptTemplate(
    template="Search for documents related to: {query}",
    input_variables=["query"]
)

analysis_prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a financial analyst."),
    ("user", "Analyze risk for: {scenario}")
])

# Chain
analysis_chain = LLMChain(prompt=analysis_prompt)
