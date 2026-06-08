"""
Resume Screening Agent
Evaluates resumes and screens candidates based on job requirements
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

from core.base_agent import BaseAgent
from core.communication import AgentMessage
from database import Candidate, CandidateStatus, Resume
from mcp_servers import get_resume_parser_mcp, get_ats_mcp

logger = logging.getLogger(__name__)


class ResumeScreeningAgent(BaseAgent):
    """
    Resume Screening Agent
    Screens incoming resumes and evaluates candidate fit
    """

    def __init__(self, agent_id: str = "resume_screener_1"):
        """Initialize Resume Screening Agent"""
        super().__init__(
            agent_id=agent_id,
            agent_type="resume_screening",
            description="Screens resumes and evaluates candidate fit for initial qualification",
        )
        self.resume_parser = get_resume_parser_mcp()
        self.ats = get_ats_mcp()
        self.screening_threshold = 0.6  # 60% score required to pass initial screening

    def execute(self, resume_content: str, candidate_name: str, job_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute resume screening
        
        Args:
            resume_content: Raw resume text
            candidate_name: Name of candidate
            job_id: Optional job ID for role-specific screening
            **kwargs: Additional parameters
            
        Returns:
            Screening result
        """
        logger.info(f"Starting resume screening for {candidate_name}")

        try:
            # Parse the resume
            resume_id = self.resume_parser.parse_resume(resume_content)
            logger.info(f"Parsed resume with ID: {resume_id}")

            # Extract candidate profile
            profile = self.resume_parser.extract_candidate_profile(resume_id)

            # Validate resume
            validation = self.resume_parser.validate_resume(resume_id)
            logger.info(f"Resume validation: {validation}")

            # Calculate screening score
            screening_score = self._calculate_screening_score(validation, profile)

            # Create candidate in ATS
            candidate_data = {
                "name": profile.get("name", candidate_name),
                "email": profile.get("email", ""),
                "phone": profile.get("phone", ""),
                "status": "applied",
                "skills": profile.get("skills", []),
                "experience_years": profile.get("experience_years", 0),
            }

            candidate_id = self.ats.create_candidate(candidate_data)
            logger.info(f"Created candidate in ATS with ID: {candidate_id}")

            # Determine if candidate passes screening
            passes_screening = screening_score >= self.screening_threshold
            status = CandidateStatus.SHORTLISTED if passes_screening else CandidateStatus.REJECTED

            # Update candidate status in ATS
            self.ats.update_candidate(candidate_id, {
                "status": status.value,
                "screening_score": screening_score,
            })

            result = {
                "candidate_id": candidate_id,
                "resume_id": resume_id,
                "screening_score": screening_score,
                "passes_screening": passes_screening,
                "candidate_profile": profile,
                "validation_report": validation,
            }

            logger.info(f"Screening result: {result}")

            # If passes screening, send to Job Matching Agent
            if passes_screening and job_id:
                self._send_to_job_matching(candidate_id, resume_id, job_id)

            return result

        except Exception as e:
            logger.error(f"Error in resume screening: {str(e)}")
            self.error_count += 1
            return {
                "error": str(e),
                "candidate_name": candidate_name,
            }

    def _calculate_screening_score(self, validation: Dict, profile: Dict) -> float:
        """
        Calculate screening score based on resume quality and completeness
        
        Args:
            validation: Resume validation report
            profile: Extracted candidate profile
            
        Returns:
            Screening score (0-1)
        """
        score = 0.0

        # Completeness score weight: 40%
        completeness = validation.get("completeness_score", 0) / 100
        score += completeness * 0.4

        # Skills weight: 30%
        skills_count = len(profile.get("skills", []))
        skills_score = min(skills_count / 10, 1.0)  # Cap at 10 skills
        score += skills_score * 0.3

        # Experience weight: 20%
        experience_years = profile.get("experience_years", 0)
        experience_score = min(experience_years / 10, 1.0)  # Cap at 10 years
        score += experience_score * 0.2

        # No errors weight: 10%
        has_errors = len(validation.get("errors", [])) > 0
        error_score = 0.0 if has_errors else 1.0
        score += error_score * 0.1

        return min(score, 1.0)

    def _send_to_job_matching(self, candidate_id: str, resume_id: str, job_id: str) -> None:
        """Send shortlisted candidate to Job Matching Agent"""
        payload = {
            "candidate_id": candidate_id,
            "resume_id": resume_id,
            "job_id": job_id,
        }

        self.send_message(
            recipient_agent="job_matching",
            message_type="resume_submission",
            payload=payload,
            priority=2,
        )

        logger.info(f"Sent candidate {candidate_id} to Job Matching Agent")

    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming messages
        
        Args:
            message: Incoming message
            
        Returns:
            Response data
        """
        if message.message_type.value == "resume_submission":
            # Handle incoming resume submission
            resume_content = message.payload.get("resume_content", "")
            candidate_name = message.payload.get("candidate_name", "Unknown")
            job_id = message.payload.get("job_id")

            result = self.execute(resume_content, candidate_name, job_id)
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
