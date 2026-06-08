"""
Base Agent class and framework for AI-Powered Recruitment Assistant
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from datetime import datetime
import logging
import json

from .communication import (
    AgentMessage,
    AgentResponse,
    MessageBroker,
    get_message_broker,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all agents in the recruitment system
    Provides common functionality for agent initialization, message handling, and communication
    """

    def __init__(self, agent_id: str, agent_type: str, description: str = ""):
        """
        Initialize the agent
        
        Args:
            agent_id: Unique identifier for the agent
            agent_type: Type of agent (e.g., 'resume_screening')
            description: Description of what the agent does
        """
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.description = description
        self.message_broker = get_message_broker()
        self.created_at = datetime.now()
        self.processing_count = 0
        self.error_count = 0
        self.last_activity = datetime.now()

        # Register this agent with the message broker
        self.message_broker.register_agent_handler(self.agent_type, self._handle_message)

        logger.info(f"Initialized agent: {self.agent_id} (type: {self.agent_type})")

    def send_message(
        self,
        recipient_agent: str,
        message_type: str,
        payload: Dict[str, Any],
        priority: int = 0,
        requires_response: bool = False,
    ) -> str:
        """
        Send a message to another agent
        
        Args:
            recipient_agent: Type of recipient agent
            message_type: Type of message
            payload: Message payload
            priority: Message priority
            requires_response: Whether a response is required
            
        Returns:
            message_id: Unique identifier of the sent message
        """
        from .communication import MessageType

        message = AgentMessage(
            sender_agent=self.agent_type,
            recipient_agent=recipient_agent,
            message_type=MessageType(message_type),
            payload=payload,
            priority=priority,
            requires_response=requires_response,
        )

        message_id = self.message_broker.send_message(message)
        logger.info(
            f"Agent {self.agent_id} sent message to {recipient_agent}: {message_type}"
        )
        return message_id

    def get_pending_messages(self) -> List[AgentMessage]:
        """Get all pending messages for this agent"""
        return self.message_broker.get_pending_messages(self.agent_type)

    def process_messages(self) -> int:
        """
        Process all pending messages for this agent
        
        Returns:
            Number of messages processed
        """
        pending_messages = self.get_pending_messages()
        count = 0

        for message in pending_messages:
            try:
                self._process_single_message(message)
                count += 1
                self.processing_count += 1
            except Exception as e:
                logger.error(f"Error processing message {message.message_id}: {str(e)}")
                self.error_count += 1

        self.message_broker.clear_processed_messages(self.agent_type)
        self.last_activity = datetime.now()
        return count

    def _handle_message(self, message: AgentMessage) -> Optional[AgentResponse]:
        """
        Handle incoming message (internal use)
        
        Args:
            message: The incoming message
            
        Returns:
            AgentResponse if message requires response, else None
        """
        try:
            result = self.handle_message(message)

            if message.requires_response:
                response = AgentResponse(
                    original_message_id=message.message_id,
                    sender_agent=self.agent_type,
                    recipient_agent=message.sender_agent,
                    status="success",
                    result=result,
                )
                return response
        except Exception as e:
            logger.error(f"Error in message handling: {str(e)}")
            if message.requires_response:
                return AgentResponse(
                    original_message_id=message.message_id,
                    sender_agent=self.agent_type,
                    recipient_agent=message.sender_agent,
                    status="error",
                    error_message=str(e),
                )
        return None

    def _process_single_message(self, message: AgentMessage) -> None:
        """Process a single message (internal use)"""
        self.process_message(message)

    @abstractmethod
    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle an incoming message from another agent
        Must be implemented by subclasses
        
        Args:
            message: The incoming AgentMessage
            
        Returns:
            Dictionary with processing result
        """
        pass

    @abstractmethod
    def process_message(self, message: AgentMessage) -> None:
        """
        Process a message from the queue
        Must be implemented by subclasses
        
        Args:
            message: The message to process
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the agent's main functionality
        Must be implemented by subclasses
        
        Returns:
            Dictionary with execution results
        """
        pass

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the agent"""
        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "processing_count": self.processing_count,
            "error_count": self.error_count,
            "pending_messages": len(self.get_pending_messages()),
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, type={self.agent_type})"
