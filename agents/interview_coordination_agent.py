"""
Interview Coordination Agent
Coordinates and schedules interviews with candidates and interviewers
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from core.base_agent import BaseAgent
from core.communication import AgentMessage
from database import Interview, InterviewStatus, CandidateStatus
from mcp_servers import get_ats_mcp, get_calendar_mcp

logger = logging.getLogger(__name__)


class InterviewCoordinationAgent(BaseAgent):
    """
    Interview Coordination Agent
    Schedules interviews and manages interview logistics
    """

    def __init__(self, agent_id: str = "interview_coordinator_1"):
        """Initialize Interview Coordination Agent"""
        super().__init__(
            agent_id=agent_id,
            agent_type="interview_coordination",
            description="Schedules and coordinates interviews between candidates and interviewers",
        )
        self.ats = get_ats_mcp()
        self.calendar = get_calendar_mcp()
        self.default_interview_duration = 60  # minutes

    def execute(self, candidate_id: str, job_id: str, interviewer_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute interview scheduling
        
        Args:
            candidate_id: ID of candidate
            job_id: ID of job position
            interviewer_id: Optional specific interviewer ID
            **kwargs: Additional parameters
            
        Returns:
            Scheduling result
        """
        logger.info(f"Starting interview scheduling for candidate {candidate_id}")

        try:
            # Get candidate information
            candidate = self.ats.get_candidate(candidate_id)
            if not candidate:
                logger.error(f"Candidate not found: {candidate_id}")
                return {"error": "Candidate not found"}

            # Get job information
            job = self.ats.get_job_posting(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return {"error": "Job not found"}

            # Assign interviewer if not specified
            if not interviewer_id:
                interviewer_id = self._assign_interviewer()
                if not interviewer_id:
                    logger.warning("No available interviewers")
                    return {"error": "No available interviewers"}

            # Find available time slot
            available_slot = self._find_available_slot(interviewer_id)
            if not available_slot:
                logger.warning(f"No available slots for interviewer {interviewer_id}")
                return {"error": "No available interview slots"}

            # Schedule the interview
            interview_data = {
                "candidate_id": candidate_id,
                "candidate_name": candidate.get("name", ""),
                "job_id": job_id,
                "job_title": job.get("title", ""),
                "scheduled_time": available_slot["start"],
                "interviewer": interviewer_id,
                "interview_type": "video",
                "meeting_link": f"https://meet.example.com/{candidate_id}",
            }

            event_id = self.calendar.schedule_interview(interview_data)
            logger.info(f"Scheduled interview: {event_id}")

            # Update candidate status
            self.ats.update_candidate(candidate_id, {
                "status": CandidateStatus.INTERVIEW_SCHEDULED.value,
            })

            # Create application for tracking
            app_id = self.ats.create_application(candidate_id, job_id)

            result = {
                "event_id": event_id,
                "candidate_id": candidate_id,
                "job_id": job_id,
                "interviewer": interviewer_id,
                "scheduled_time": available_slot["start"],
                "meeting_link": interview_data["meeting_link"],
                "application_id": app_id,
            }

            logger.info(f"Interview scheduled successfully: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in interview scheduling: {str(e)}")
            self.error_count += 1
            return {
                "error": str(e),
                "candidate_id": candidate_id,
            }

    def reschedule_interview(self, event_id: str, new_time: str, new_interviewer: Optional[str] = None) -> Dict[str, Any]:
        """
        Reschedule an existing interview
        
        Args:
            event_id: ID of the interview to reschedule
            new_time: New interview time (ISO format)
            new_interviewer: Optional new interviewer ID
            
        Returns:
            Rescheduling result
        """
        try:
            interview = self.calendar.get_interview(event_id)
            if not interview:
                logger.error(f"Interview not found: {event_id}")
                return {"error": "Interview not found"}

            # Reschedule in calendar
            self.calendar.reschedule_interview(event_id, new_time, new_interviewer)

            logger.info(f"Rescheduled interview {event_id} to {new_time}")
            return {
                "event_id": event_id,
                "new_time": new_time,
                "new_interviewer": new_interviewer,
                "success": True,
            }

        except Exception as e:
            logger.error(f"Error rescheduling interview: {str(e)}")
            self.error_count += 1
            return {"error": str(e)}

    def cancel_interview(self, event_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Cancel an interview
        
        Args:
            event_id: ID of interview to cancel
            reason: Reason for cancellation
            
        Returns:
            Cancellation result
        """
        try:
            self.calendar.cancel_interview(event_id, reason)
            logger.info(f"Cancelled interview: {event_id}")
            return {"event_id": event_id, "success": True}
        except Exception as e:
            logger.error(f"Error cancelling interview: {str(e)}")
            self.error_count += 1
            return {"error": str(e)}

    def record_interview_feedback(self, event_id: str, feedback: str, rating: float) -> Dict[str, Any]:
        """
        Record interview feedback
        
        Args:
            event_id: ID of interview
            feedback: Interview feedback notes
            rating: Interview rating (0-5)
            
        Returns:
            Result
        """
        try:
            self.calendar.update_interview(event_id, {
                "status": InterviewStatus.COMPLETED.value,
                "feedback": feedback,
                "rating": rating,
            })

            interview = self.calendar.get_interview(event_id)
            candidate_id = interview.get("candidate_id")

            # Update candidate status and send to ranking agent
            if candidate_id:
                self.ats.update_candidate(candidate_id, {
                    "status": CandidateStatus.INTERVIEWED.value,
                    "interview_feedback": feedback,
                })

                # Send interview result to ranking agent
                self._send_to_ranking_agent(candidate_id, event_id, rating)

            logger.info(f"Recorded interview feedback for {event_id}")
            return {"event_id": event_id, "success": True}

        except Exception as e:
            logger.error(f"Error recording interview feedback: {str(e)}")
            self.error_count += 1
            return {"error": str(e)}

    def _assign_interviewer(self) -> Optional[str]:
        """
        Assign an available interviewer
        
        Returns:
            Interviewer ID or None
        """
        # For now, use a default interviewer
        # In production, this would have load balancing logic
        return "interviewer_1"

    def _find_available_slot(self, interviewer_id: str) -> Optional[Dict[str, str]]:
        """
        Find the next available interview slot for an interviewer
        
        Args:
            interviewer_id: ID of interviewer
            
        Returns:
            Available slot dict with 'start' and 'end' times
        """
        slots = self.calendar.find_available_slots(interviewer_id, self.default_interview_duration)

        if slots:
            # Return the first available slot
            return slots[0]

        logger.warning(f"No available slots found for interviewer {interviewer_id}")
        return None

    def _send_to_ranking_agent(self, candidate_id: str, event_id: str, interview_rating: float) -> None:
        """Send interview feedback to Ranking Agent"""
        payload = {
            "candidate_id": candidate_id,
            "event_id": event_id,
            "interview_rating": interview_rating,
        }

        self.send_message(
            recipient_agent="candidate_ranking",
            message_type="interview_feedback",
            payload=payload,
            priority=2,
        )

        logger.info(f"Sent interview feedback to Ranking Agent for candidate {candidate_id}")

    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming messages
        
        Args:
            message: Incoming message
            
        Returns:
            Response data
        """
        if message.message_type.value == "ranking_request":
            candidate_id = message.payload.get("candidate_id")
            job_id = message.payload.get("job_id")

            result = self.execute(candidate_id, job_id)
            return result

        logger.warning(f"Unknown message type: {message.message_type.value}")
        return {}

    def process_message(self, message: AgentMessage) -> None:
        """
        Process a message from the queue
        
        Args:
            message: Message to process
        """
        result = self.handle_message(message)
        logger.info(f"Processed message {message.message_id}: {result}")
