"""
Interview Coordination Agent
Coordinates and schedules interviews with candidates and interviewers
Mohammed Ammar
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from core.base_agent import BaseAgent
from core.communication import AgentMessage
from database import Interview, InterviewStatus, CandidateStatus
from mcp_servers import get_ats_mcp, get_calendar_mcp

logger = logging.getLogger(__name__)

# Interviewer pool with priority order (first available gets assigned)
DEFAULT_INTERVIEWERS = [
    "interviewer_1",
    "interviewer_2",
    "interviewer_3",
    "hiring_manager",
]

# How many days ahead to search for slots
SLOT_SEARCH_DAYS = 7

# Default interview duration in minutes
DEFAULT_DURATION = 60

# Max reschedule attempts before flagging
MAX_RESCHEDULE_ATTEMPTS = 3

# Valid rating range
RATING_MIN = 0.0
RATING_MAX = 5.0


class InterviewCoordinationAgent(BaseAgent):
    """
    Schedules, reschedules, and cancels interviews.
    Records feedback and forwards interview scores to the Ranking Agent.

    Improvements over original:
    - Round-robin interviewer assignment instead of always picking interviewer_1
    - Retry logic when no slot is found for first-choice interviewer
    - Reschedule counter — candidates flagged after MAX_RESCHEDULE_ATTEMPTS
    - Rating validated and clamped before storage
    - interview_rating stored on candidate record so Ranking Agent can use it
    - handle_message routes 'schedule_interview' messages (was missing)
    - All public methods guard against missing candidate / job gracefully
    """

    def __init__(self, agent_id: str = "interview_coordinator_1"):
        super().__init__(
            agent_id=agent_id,
            agent_type="interview_coordination",
            description="Schedules and coordinates interviews between candidates and interviewers",
        )
        self.ats = get_ats_mcp()
        self.calendar = get_calendar_mcp()
        self.default_interview_duration = DEFAULT_DURATION

        # Track how many times each candidate has been rescheduled
        self._reschedule_counts: Dict[str, int] = {}

        # Round-robin pointer for interviewer assignment
        self._interviewer_index = 0

    # ── Public entry point ────────────────────────────────────────────────────

    def execute(
        self,
        candidate_id: str,
        job_id: str,
        interviewer_id: Optional[str] = None,
        interview_type: str = "video",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Schedule an interview for a shortlisted candidate.

        If no interviewer_id is provided, one is assigned via round-robin.
        If the assigned interviewer has no free slots within SLOT_SEARCH_DAYS,
        the agent tries the next interviewer in the pool before giving up.
        """
        logger.info(f"Scheduling interview — candidate: {candidate_id}, job: {job_id}")

        try:
            candidate = self.ats.get_candidate(candidate_id)
            if not candidate:
                return self._error(f"Candidate not found: {candidate_id}", candidate_id=candidate_id)

            job = self.ats.get_job_posting(job_id)
            if not job:
                return self._error(f"Job not found: {job_id}", candidate_id=candidate_id)

            # Assign interviewer + find slot, retrying across pool if needed
            assigned_interviewer, available_slot = self._assign_interviewer_with_slot(interviewer_id)

            if not assigned_interviewer or not available_slot:
                return self._error("No available interviewers or slots", candidate_id=candidate_id)

            meeting_link = self._generate_meeting_link(candidate_id, interview_type)

            interview_data = {
                "candidate_id": candidate_id,
                "candidate_name": candidate.get("name", ""),
                "job_id": job_id,
                "job_title": job.get("title", ""),
                "scheduled_time": available_slot["start"],
                "end_time": available_slot.get("end", ""),
                "interviewer": assigned_interviewer,
                "interview_type": interview_type,
                "meeting_link": meeting_link,
            }

            event_id = self.calendar.schedule_interview(interview_data)
            logger.info(f"Interview event created: {event_id}")

            self.ats.update_candidate(candidate_id, {
                "status": CandidateStatus.INTERVIEW_SCHEDULED.value,
            })

            # Create application record if it doesn't exist
            app_id = self.ats.create_application(candidate_id, job_id)

            result = {
                "success": True,
                "event_id": event_id,
                "candidate_id": candidate_id,
                "candidate_name": candidate.get("name", ""),
                "job_id": job_id,
                "job_title": job.get("title", ""),
                "interviewer": assigned_interviewer,
                "scheduled_time": available_slot["start"],
                "interview_type": interview_type,
                "meeting_link": meeting_link,
                "application_id": app_id,
            }

            logger.info(f"Interview scheduled: {result}")
            return result

        except Exception as e:
            logger.error(f"Error scheduling interview: {e}", exc_info=True)
            self.error_count += 1
            return self._error(str(e), candidate_id=candidate_id)

    def reschedule_interview(
        self,
        event_id: str,
        new_time: str,
        new_interviewer: Optional[str] = None,
        reason: str = "",
    ) -> Dict[str, Any]:
        """
        Reschedule an existing interview.
        Tracks reschedule count per candidate and flags if it exceeds the limit.
        """
        try:
            interview = self.calendar.get_interview(event_id)
            if not interview:
                return self._error(f"Interview not found: {event_id}")

            candidate_id = interview.get("candidate_id", "")

            # Increment reschedule counter
            count = self._reschedule_counts.get(candidate_id, 0) + 1
            self._reschedule_counts[candidate_id] = count

            if count > MAX_RESCHEDULE_ATTEMPTS:
                logger.warning(
                    f"Candidate {candidate_id} has been rescheduled {count} times — flagging"
                )
                self.ats.update_candidate(candidate_id, {"flag": "excessive_reschedules"})

            self.calendar.reschedule_interview(event_id, new_time, new_interviewer)

            logger.info(f"Rescheduled interview {event_id} → {new_time} (attempt #{count})")
            return {
                "success": True,
                "event_id": event_id,
                "new_time": new_time,
                "new_interviewer": new_interviewer,
                "reschedule_count": count,
                "flagged": count > MAX_RESCHEDULE_ATTEMPTS,
                "reason": reason,
            }

        except Exception as e:
            logger.error(f"Error rescheduling interview {event_id}: {e}", exc_info=True)
            self.error_count += 1
            return self._error(str(e))

    def cancel_interview(self, event_id: str, reason: str = "") -> Dict[str, Any]:
        """Cancel an interview and update candidate status."""
        try:
            interview = self.calendar.get_interview(event_id)
            if not interview:
                return self._error(f"Interview not found: {event_id}")

            candidate_id = interview.get("candidate_id")
            self.calendar.cancel_interview(event_id, reason)

            if candidate_id:
                self.ats.update_candidate(candidate_id, {
                    "status": CandidateStatus.SHORTLISTED.value,  # revert to previous stage
                })

            logger.info(f"Cancelled interview {event_id} — reason: {reason or 'not provided'}")
            return {"success": True, "event_id": event_id, "reason": reason}

        except Exception as e:
            logger.error(f"Error cancelling interview {event_id}: {e}", exc_info=True)
            self.error_count += 1
            return self._error(str(e))

    def record_interview_feedback(
        self,
        event_id: str,
        feedback: str,
        rating: float,
    ) -> Dict[str, Any]:
        """
        Record post-interview feedback and rating.

        Rating is validated (0–5) and clamped. The numeric score is stored on
        the candidate record as 'interview_rating' so the Ranking Agent can
        pick it up directly without re-parsing free-text feedback.
        """
        try:
            # Validate and clamp rating
            if not isinstance(rating, (int, float)):
                logger.warning(f"Invalid rating type: {type(rating)} — defaulting to 0")
                rating = 0.0
            rating = round(max(RATING_MIN, min(RATING_MAX, float(rating))), 2)

            self.calendar.update_interview(event_id, {
                "status": InterviewStatus.COMPLETED.value,
                "feedback": feedback,
                "rating": rating,
            })

            interview = self.calendar.get_interview(event_id)
            if not interview:
                return self._error(f"Interview not found after update: {event_id}")

            candidate_id = interview.get("candidate_id")

            if candidate_id:
                self.ats.update_candidate(candidate_id, {
                    "status": CandidateStatus.INTERVIEWED.value,
                    "interview_feedback": feedback,
                    "interview_rating": rating,   # numeric — used by Ranking Agent
                })
                self._send_to_ranking_agent(candidate_id, event_id, rating)

            logger.info(f"Feedback recorded for interview {event_id} — rating: {rating}/5")
            return {
                "success": True,
                "event_id": event_id,
                "candidate_id": candidate_id,
                "rating": rating,
            }

        except Exception as e:
            logger.error(f"Error recording feedback for {event_id}: {e}", exc_info=True)
            self.error_count += 1
            return self._error(str(e))

    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Route incoming inter-agent messages."""
        msg_type = message.message_type.value

        if msg_type in ("ranking_request", "schedule_interview"):
            candidate_id = message.payload.get("candidate_id")
            job_id = message.payload.get("job_id")
            if not candidate_id or not job_id:
                return self._error("Missing candidate_id or job_id in payload")
            return self.execute(candidate_id, job_id)

        elif msg_type == "reschedule_interview":
            event_id = message.payload.get("event_id")
            new_time = message.payload.get("new_time")
            if not event_id or not new_time:
                return self._error("Missing event_id or new_time in payload")
            return self.reschedule_interview(
                event_id,
                new_time,
                message.payload.get("new_interviewer"),
                message.payload.get("reason", ""),
            )

        elif msg_type == "cancel_interview":
            event_id = message.payload.get("event_id")
            if not event_id:
                return self._error("Missing event_id in payload")
            return self.cancel_interview(event_id, message.payload.get("reason", ""))

        elif msg_type == "record_feedback":
            event_id = message.payload.get("event_id")
            feedback = message.payload.get("feedback", "")
            rating = message.payload.get("rating", 0.0)
            if not event_id:
                return self._error("Missing event_id in payload")
            return self.record_interview_feedback(event_id, feedback, rating)

        logger.warning(f"Unknown message type: {msg_type}")
        return {}

    def process_message(self, message: AgentMessage) -> None:
        result = self.handle_message(message)
        logger.info(f"Processed message {message.message_id}: {result}")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _assign_interviewer_with_slot(
        self, preferred: Optional[str]
    ) -> tuple:
        """
        Try to find an interviewer + open slot.
        If preferred is given, try that first.
        Otherwise use round-robin across the pool.
        Falls back to the next available interviewer if no slots found.

        Returns (interviewer_id, slot) or (None, None).
        """
        pool = list(DEFAULT_INTERVIEWERS)

        # Try preferred first
        if preferred:
            pool = [preferred] + [p for p in pool if p != preferred]
        else:
            # Round-robin starting point
            start = self._interviewer_index % len(pool)
            pool = pool[start:] + pool[:start]

        for interviewer_id in pool:
            slot = self._find_available_slot(interviewer_id)
            if slot:
                # Advance round-robin pointer for next call
                if not preferred:
                    self._interviewer_index = (self._interviewer_index + 1) % len(DEFAULT_INTERVIEWERS)
                logger.info(f"Assigned interviewer: {interviewer_id}, slot: {slot['start']}")
                return interviewer_id, slot
            logger.info(f"No slots for {interviewer_id}, trying next")

        return None, None

    def _find_available_slot(self, interviewer_id: str) -> Optional[Dict[str, str]]:
        """Find next available slot for interviewer within SLOT_SEARCH_DAYS."""
        try:
            slots = self.calendar.find_available_slots(
                interviewer_id, self.default_interview_duration
            )
            if slots:
                return slots[0]
        except Exception as e:
            logger.warning(f"Error fetching slots for {interviewer_id}: {e}")
        return None

    def _generate_meeting_link(self, candidate_id: str, interview_type: str) -> str:
        """Generate a meeting link based on interview type."""
        if interview_type == "video":
            return f"https://meet.example.com/interview-{candidate_id}"
        elif interview_type == "phone":
            return ""  # no link needed for phone
        else:
            return ""  # in-person

    def _send_to_ranking_agent(
        self, candidate_id: str, event_id: str, interview_rating: float
    ) -> None:
        """Forward interview score to the Candidate Ranking Agent."""
        self.send_message(
            recipient_agent="candidate_ranking",
            message_type="interview_feedback",
            payload={
                "candidate_id": candidate_id,
                "event_id": event_id,
                "interview_rating": interview_rating,
            },
            priority=2,
        )
        logger.info(f"Interview feedback sent to Ranking Agent — candidate: {candidate_id}, rating: {interview_rating}")

    @staticmethod
    def _error(message: str, **extra) -> Dict[str, Any]:
        """Standardised error response."""
        logger.error(message)
        return {"success": False, "error": message, **extra}
