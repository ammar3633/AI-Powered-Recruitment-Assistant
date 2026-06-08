"""
Calendar MCP Server
Manages interview scheduling and calendar operations
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class CalendarMCP:
    """
    MCP Server for calendar operations
    Handles interview scheduling, availability checking, and meeting management
    """

    def __init__(self):
        """Initialize Calendar MCP server"""
        self.scheduled_events: Dict[str, Dict] = {}
        self.availabilities: Dict[str, List[Dict]] = {}  # interviewer_id -> availability slots
        self.server_name = "Calendar MCP"
        logger.info("Calendar MCP Server initialized")

    def schedule_interview(self, interview_data: Dict[str, Any]) -> str:
        """
        Schedule an interview
        
        Args:
            interview_data: Interview details including candidate, job, time, interviewer
            
        Returns:
            Event ID
        """
        import uuid

        event_id = str(uuid.uuid4())
        self.scheduled_events[event_id] = {
            "id": event_id,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
            **interview_data,
        }

        logger.info(
            f"Scheduled interview: {event_id} for "
            f"{interview_data.get('candidate_name')} on {interview_data.get('scheduled_time')}"
        )
        return event_id

    def get_interview(self, event_id: str) -> Optional[Dict]:
        """Get interview details by ID"""
        return self.scheduled_events.get(event_id)

    def update_interview(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update interview details"""
        if event_id not in self.scheduled_events:
            logger.warning(f"Interview not found: {event_id}")
            return False

        self.scheduled_events[event_id].update(updates)
        self.scheduled_events[event_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Updated interview: {event_id}")
        return True

    def cancel_interview(self, event_id: str, reason: str = "") -> bool:
        """Cancel an interview"""
        if event_id not in self.scheduled_events:
            logger.warning(f"Interview not found: {event_id}")
            return False

        self.scheduled_events[event_id]["status"] = "cancelled"
        self.scheduled_events[event_id]["cancellation_reason"] = reason
        self.scheduled_events[event_id]["cancelled_at"] = datetime.now().isoformat()
        logger.info(f"Cancelled interview: {event_id}")
        return True

    def reschedule_interview(self, event_id: str, new_time: str, new_interviewer: Optional[str] = None) -> bool:
        """Reschedule an interview to a new time"""
        if event_id not in self.scheduled_events:
            logger.warning(f"Interview not found: {event_id}")
            return False

        self.scheduled_events[event_id]["scheduled_time"] = new_time
        if new_interviewer:
            self.scheduled_events[event_id]["interviewer"] = new_interviewer
        self.scheduled_events[event_id]["status"] = "rescheduled"
        self.scheduled_events[event_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Rescheduled interview: {event_id} to {new_time}")
        return True

    def add_availability(self, interviewer_id: str, availability_slot: Dict[str, str]) -> bool:
        """
        Add availability slot for an interviewer
        
        Args:
            interviewer_id: ID of interviewer
            availability_slot: Dict with 'start' and 'end' datetime strings
            
        Returns:
            Success status
        """
        if interviewer_id not in self.availabilities:
            self.availabilities[interviewer_id] = []

        self.availabilities[interviewer_id].append(availability_slot)
        logger.info(
            f"Added availability for interviewer {interviewer_id}: "
            f"{availability_slot['start']} to {availability_slot['end']}"
        )
        return True

    def get_availability(self, interviewer_id: str) -> List[Dict]:
        """Get availability slots for an interviewer"""
        return self.availabilities.get(interviewer_id, [])

    def check_availability(self, interviewer_id: str, start_time: str, duration_minutes: int = 60) -> bool:
        """
        Check if an interviewer is available at a specific time
        
        Args:
            interviewer_id: ID of interviewer
            start_time: Start time as ISO string
            duration_minutes: Duration of the meeting in minutes
            
        Returns:
            True if available, False otherwise
        """
        availability_slots = self.get_availability(interviewer_id)

        if not availability_slots:
            logger.warning(f"No availability data for interviewer: {interviewer_id}")
            return False

        try:
            start = datetime.fromisoformat(start_time)
            end = start + timedelta(minutes=duration_minutes)

            for slot in availability_slots:
                slot_start = datetime.fromisoformat(slot["start"])
                slot_end = datetime.fromisoformat(slot["end"])

                if slot_start <= start and end <= slot_end:
                    logger.info(
                        f"Interviewer {interviewer_id} is available at {start_time}"
                    )
                    return True

            logger.info(f"Interviewer {interviewer_id} is NOT available at {start_time}")
            return False
        except Exception as e:
            logger.error(f"Error checking availability: {str(e)}")
            return False

    def find_available_slots(
        self, interviewer_id: str, duration_minutes: int = 60
    ) -> List[Dict]:
        """
        Find available time slots for an interviewer
        
        Args:
            interviewer_id: ID of interviewer
            duration_minutes: Duration needed in minutes
            
        Returns:
            List of available slots
        """
        availability_slots = self.get_availability(interviewer_id)
        available_slots = []

        for slot in availability_slots:
            try:
                slot_start = datetime.fromisoformat(slot["start"])
                slot_end = datetime.fromisoformat(slot["end"])

                # Generate 30-minute intervals within the availability window
                current = slot_start
                while current + timedelta(minutes=duration_minutes) <= slot_end:
                    available_slots.append({
                        "start": current.isoformat(),
                        "end": (current + timedelta(minutes=duration_minutes)).isoformat(),
                    })
                    current += timedelta(minutes=30)
            except Exception as e:
                logger.error(f"Error parsing availability slot: {str(e)}")

        logger.info(f"Found {len(available_slots)} available slots for interviewer {interviewer_id}")
        return available_slots

    def list_scheduled_interviews(self, status: str = "scheduled") -> List[Dict]:
        """List scheduled interviews with optional status filter"""
        interviews = [i for i in self.scheduled_events.values() if i.get("status") == status]
        logger.info(f"Listed {len(interviews)} interviews with status: {status}")
        return interviews

    def get_interviews_for_candidate(self, candidate_id: str) -> List[Dict]:
        """Get all interviews for a candidate"""
        interviews = [i for i in self.scheduled_events.values() if i.get("candidate_id") == candidate_id]
        logger.info(f"Retrieved {len(interviews)} interviews for candidate: {candidate_id}")
        return interviews

    def get_interviews_for_interviewer(self, interviewer_id: str) -> List[Dict]:
        """Get all interviews for an interviewer"""
        interviews = [i for i in self.scheduled_events.values() if i.get("interviewer") == interviewer_id]
        logger.info(f"Retrieved {len(interviews)} interviews for interviewer: {interviewer_id}")
        return interviews

    def get_server_status(self) -> Dict[str, Any]:
        """Get server status and statistics"""
        return {
            "server_name": self.server_name,
            "total_scheduled_interviews": len(self.scheduled_events),
            "total_interviewers_with_availability": len(self.availabilities),
            "last_activity": datetime.now().isoformat(),
        }


# Global Calendar MCP instance
_calendar_mcp: Optional[CalendarMCP] = None


def get_calendar_mcp() -> CalendarMCP:
    """Get or create global Calendar MCP instance"""
    global _calendar_mcp
    if _calendar_mcp is None:
        _calendar_mcp = CalendarMCP()
    return _calendar_mcp
