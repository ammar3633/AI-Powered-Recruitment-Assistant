"""
Core module for AI-Powered Recruitment Assistant
Contains base agent class and communication framework
"""

from .base_agent import BaseAgent
from .communication import (
    AgentMessage,
    AgentResponse,
    MessageBroker,
    MessageType,
    AgentType,
    get_message_broker,
    reset_message_broker,
)

__all__ = [
    "BaseAgent",
    "AgentMessage",
    "AgentResponse",
    "MessageBroker",
    "MessageType",
    "AgentType",
    "get_message_broker",
    "reset_message_broker",
]
