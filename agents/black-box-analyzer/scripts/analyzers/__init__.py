#!/usr/bin/env python3
"""Analyzers package for universal project type analysis.

Each analyzer handles a specific project type:
- APIAnalyzer: REST/GraphQL/gRPC APIs
- CLIAnalyzer: Command-line applications
- MobileAnalyzer: Android/iOS apps
- DesktopAnalyzer: Windows/Mac/Linux desktop apps
- FrontendAnalyzer: React/Vue/Angular
- FullstackAnalyzer: Next.js/Remix/SvelteKit
- LLMAnalyzer: LangChain/CrewAI agents
- SQLAnalyzer: SQL projects (stored procedures, triggers)
- ServerlessAnalyzer: AWS Lambda, Azure Functions, Cloud Functions
- WorkerAnalyzer: Celery, Sidekiq, Bull, asynq
- MessageQueueAnalyzer: Kafka, RabbitMQ, SQS, Service Bus
- SmartContractAnalyzer: Solidity, Rust/Solana, Move
"""

from .base_analyzer import BaseAnalyzer
from .api_analyzer import APIAnalyzer
from .cli_analyzer import CLIAnalyzer
from .mobile_analyzer import MobileAnalyzer
from .desktop_analyzer import DesktopAnalyzer
from .frontend_analyzer import FrontendAnalyzer
from .fullstack_analyzer import FullstackAnalyzer
from .llm_analyzer import LLMAnalyzer
from .sql_analyzer import SQLAnalyzer
from .event_driven import ServerlessAnalyzer, WorkerAnalyzer, MessageQueueAnalyzer
from .blockchain import SmartContractAnalyzer

__all__ = [
    "BaseAnalyzer",
    "APIAnalyzer",
    "CLIAnalyzer",
    "MobileAnalyzer",
    "DesktopAnalyzer",
    "FrontendAnalyzer",
    "FullstackAnalyzer",
    "LLMAnalyzer",
    "SQLAnalyzer",
    "ServerlessAnalyzer",
    "WorkerAnalyzer",
    "MessageQueueAnalyzer",
    "SmartContractAnalyzer",
]
