"""
Agent-to-Agent Communication Framework
Handles inter-agent communication and message passing
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of inter-agent messages"""
    RESUME_SUBMISSION = "resume_submission"
    SCREENING_RESULT = "screening_result"
    JOB_MATCH_REQUEST = "job_match_request"
    MATCH_RESULT = "match_result"
    RANKING_REQUEST = "ranking_request"
    RANKING_RESULT = "ranking_result"
    INTERVIEW_SCHEDULE_REQUEST = "interview_schedule_request"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_FEEDBACK = "interview_feedback"
    STATUS_UPDATE = "status_update"


class AgentType(str, Enum):
    """Types of agents in the system"""
    RESUME_SCREENING = "resume_screening"
    JOB_MATCHING = "job_matching"
    INTERVIEW_COORDINATION = "interview_coordination"
    CANDIDATE_RANKING = "candidate_ranking"


@dataclass
class AgentMessage:
    """Inter-agent message structure"""
    sender_agent: str
    recipient_agent: str
    message_type: MessageType
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    message_id: str = ""
    priority: int = 0  # Higher number = higher priority
    requires_response: bool = False

    def to_dict(self) -> Dict:
        """Convert message to dictionary"""
        return {
            "sender_agent": self.sender_agent,
            "recipient_agent": self.recipient_agent,
            "message_type": self.message_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "priority": self.priority,
            "requires_response": self.requires_response,
        }

    def to_json(self) -> str:
        """Convert message to JSON string"""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict) -> "AgentMessage":
        """Create message from dictionary"""
        return cls(
            sender_agent=data["sender_agent"],
            recipient_agent=data["recipient_agent"],
            message_type=MessageType(data["message_type"]),
            payload=data.get("payload", {}),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat())),
            message_id=data.get("message_id", ""),
            priority=data.get("priority", 0),
            requires_response=data.get("requires_response", False),
        )


@dataclass
class AgentResponse:
    """Response to an inter-agent message"""
    original_message_id: str
    sender_agent: str
    recipient_agent: str
    status: str  # "success", "error", "pending"
    result: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert response to dictionary"""
        return {
            "original_message_id": self.original_message_id,
            "sender_agent": self.sender_agent,
            "recipient_agent": self.recipient_agent,
            "status": self.status,
            "result": self.result,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        }


class MessageBroker:
    """
    Central message broker for agent communication
    Manages message passing and routing between agents
    """

    def __init__(self):
        self.message_queue: List[AgentMessage] = []
        self.message_history: List[AgentMessage] = []
        self.response_handlers: Dict[str, Callable] = {}
        self.agent_handlers: Dict[str, Callable] = {}
        self.pending_responses: Dict[str, AgentResponse] = {}

    def register_agent_handler(self, agent_type: str, handler: Callable) -> None:
        """
        Register a handler for an agent type
        
        Args:
            agent_type: Type of agent
            handler: Callable that processes messages for this agent
        """
        self.agent_handlers[agent_type] = handler
        logger.info(f"Registered handler for agent: {agent_type}")

    def send_message(self, message: AgentMessage) -> str:
        """
        Send a message to another agent
        
        Args:
            message: AgentMessage to send
            
        Returns:
            message_id: Unique identifier of the message
        """
        # Generate unique message ID
        import uuid
        message.message_id = str(uuid.uuid4())

        # Add to queue
        self.message_queue.append(message)
        self.message_history.append(message)

        logger.info(
            f"Message sent from {message.sender_agent} to {message.recipient_agent}. "
            f"Type: {message.message_type.value}, ID: {message.message_id}"
        )

        # Process message if handler exists
        if message.recipient_agent in self.agent_handlers:
            try:
                response = self.agent_handlers[message.recipient_agent](message)
                if response:
                    self.pending_responses[message.message_id] = response
                    logger.info(f"Response received for message {message.message_id}")
            except Exception as e:
                logger.error(f"Error processing message {message.message_id}: {str(e)}")

        return message.message_id

    def get_pending_messages(self, agent_type: str) -> List[AgentMessage]:
        """
        Get all pending messages for an agent
        
        Args:
            agent_type: Type of agent
            
        Returns:
            List of pending messages
        """
        pending = [msg for msg in self.message_queue if msg.recipient_agent == agent_type]
        return sorted(pending, key=lambda x: x.priority, reverse=True)

    def get_message_by_id(self, message_id: str) -> Optional[AgentMessage]:
        """Get a message by its ID"""
        for msg in self.message_history:
            if msg.message_id == message_id:
                return msg
        return None

    def get_response(self, message_id: str) -> Optional[AgentResponse]:
        """Get the response for a message"""
        return self.pending_responses.get(message_id)

    def clear_processed_messages(self, agent_type: str) -> None:
        """Remove processed messages from queue"""
        self.message_queue = [
            msg for msg in self.message_queue if msg.recipient_agent != agent_type
        ]

    def get_agent_communication_history(self, agent_type: str) -> List[AgentMessage]:
        """Get all messages involving a specific agent"""
        return [
            msg
            for msg in self.message_history
            if msg.sender_agent == agent_type or msg.recipient_agent == agent_type
        ]

    def get_all_messages(self) -> List[AgentMessage]:
        """Get complete message history"""
        return self.message_history.copy()


# Global message broker instance
_message_broker: Optional[MessageBroker] = None


def get_message_broker() -> MessageBroker:
    """Get or create the global message broker"""
    global _message_broker
    if _message_broker is None:
        _message_broker = MessageBroker()
    return _message_broker


def reset_message_broker() -> None:
    """Reset the message broker (useful for testing)"""
    global _message_broker
    _message_broker = None
