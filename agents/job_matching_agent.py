"""
Job Matching Agent
Matches candidates to suitable job positions
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

from core.base_agent import BaseAgent
from core.communication import AgentMessage
from database import MatchResult, CandidateStatus
from mcp_servers import get_resume_parser_mcp, get_ats_mcp

logger = logging.getLogger(__name__)


class JobMatchingAgent(BaseAgent):
    """
    Job Matching Agent
    Matches candidates to job positions based on requirements
    """

    def __init__(self, agent_id: str = "job_matcher_1"):
        """Initialize Job Matching Agent"""
        super().__init__(
            agent_id=agent_id,
            agent_type="job_matching",
            description="Matches candidates to job positions based on skills and experience",
        )
        self.resume_parser = get_resume_parser_mcp()
        self.ats = get_ats_mcp()
        self.match_threshold = 0.65  # 65% match required

    def execute(self, candidate_id: str, resume_id: str, job_id: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute job matching
        
        Args:
            candidate_id: ID of candidate
            resume_id: ID of parsed resume
            job_id: Optional specific job ID to match against
            **kwargs: Additional parameters
            
        Returns:
            Matching result
        """
        logger.info(f"Starting job matching for candidate {candidate_id}")

        try:
            # Get candidate and resume information
            candidate = self.ats.get_candidate(candidate_id)
            if not candidate:
                logger.error(f"Candidate not found: {candidate_id}")
                return {"error": "Candidate not found"}

            resume = self.resume_parser.get_parsed_resume(resume_id)
            if not resume:
                logger.error(f"Resume not found: {resume_id}")
                return {"error": "Resume not found"}

            # Get available jobs
            if job_id:
                jobs = [self.ats.get_job_posting(job_id)] if self.ats.get_job_posting(job_id) else []
            else:
                jobs = self.ats.list_job_postings(status="open")

            logger.info(f"Matching candidate against {len(jobs)} open positions")

            # Perform matching for each job
            matches = []
            best_match = None
            best_match_score = 0

            for job in jobs:
                if not job:
                    continue

                match_result = self._match_candidate_to_job(candidate_id, resume, job)

                if match_result["match_percentage"] >= self.match_threshold:
                    matches.append(match_result)

                    if match_result["match_percentage"] > best_match_score:
                        best_match = match_result
                        best_match_score = match_result["match_percentage"]

            logger.info(f"Found {len(matches)} matching positions")

            # Update candidate status and match score
            if matches:
                avg_match = sum(m["match_percentage"] for m in matches) / len(matches)
                self.ats.update_candidate(candidate_id, {
                    "status": CandidateStatus.SHORTLISTED.value,
                    "match_score": avg_match,
                })

                # Send best match to Ranking Agent
                if best_match:
                    self._send_to_ranking_agent(candidate_id, best_match)

            result = {
                "candidate_id": candidate_id,
                "total_matches": len(matches),
                "best_match": best_match,
                "all_matches": matches,
            }

            return result

        except Exception as e:
            logger.error(f"Error in job matching: {str(e)}")
            self.error_count += 1
            return {
                "error": str(e),
                "candidate_id": candidate_id,
            }

    def _match_candidate_to_job(self, candidate_id: str, resume: Dict, job: Dict) -> Dict[str, Any]:
        """
        Match a candidate to a specific job
        
        Args:
            candidate_id: ID of candidate
            resume: Parsed resume data
            job: Job posting data
            
        Returns:
            Match result with percentage and details
        """
        resume_skills = set(resume.get("skills", []))
        required_skills = set(job.get("required_skills", []))
        resume_experience = resume.get("experience_years", 0)
        required_experience = job.get("required_experience_years", 0)

        # Calculate skill match
        if required_skills:
            matched_skills = list(resume_skills.intersection(required_skills))
            missing_skills = list(required_skills - resume_skills)
            skill_match = len(matched_skills) / len(required_skills)
        else:
            matched_skills = []
            missing_skills = []
            skill_match = 1.0

        # Calculate experience match
        if required_experience > 0:
            experience_match = min(resume_experience / required_experience, 1.0)
        else:
            experience_match = 1.0

        # Overall match percentage
        match_percentage = (skill_match * 0.6 + experience_match * 0.4) * 100

        # Reasoning
        reasoning = self._generate_reasoning(matched_skills, missing_skills, resume_experience, required_experience)

        return {
            "candidate_id": candidate_id,
            "job_id": job.get("id", ""),
            "job_title": job.get("title", ""),
            "match_percentage": match_percentage,
            "skill_match_percentage": skill_match * 100,
            "experience_match_percentage": experience_match * 100,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "reasoning": reasoning,
        }

    def _generate_reasoning(
        self,
        matched_skills: List[str],
        missing_skills: List[str],
        resume_experience: float,
        required_experience: float,
    ) -> str:
        """Generate reasoning for the match decision"""
        reasoning_parts = []

        if matched_skills:
            reasoning_parts.append(f"Matched skills: {', '.join(matched_skills)}")

        if missing_skills:
            reasoning_parts.append(f"Missing skills: {', '.join(missing_skills)}")

        if resume_experience >= required_experience:
            reasoning_parts.append(
                f"Experience meets requirement: {resume_experience} years (required: {required_experience})"
            )
        else:
            reasoning_parts.append(
                f"Experience below requirement: {resume_experience} years (required: {required_experience})"
            )

        return "; ".join(reasoning_parts)

    def _send_to_ranking_agent(self, candidate_id: str, match_result: Dict) -> None:
        """Send matched candidate to Ranking Agent"""
        payload = {
            "candidate_id": candidate_id,
            "job_id": match_result["job_id"],
            "match_score": match_result["match_percentage"],
        }

        self.send_message(
            recipient_agent="candidate_ranking",
            message_type="match_result",
            payload=payload,
            priority=2,
        )

        logger.info(f"Sent candidate {candidate_id} to Ranking Agent for job {match_result['job_id']}")

    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming messages
        
        Args:
            message: Incoming message
            
        Returns:
            Response data
        """
        if message.message_type.value == "resume_submission":
            candidate_id = message.payload.get("candidate_id")
            resume_id = message.payload.get("resume_id")
            job_id = message.payload.get("job_id")

            result = self.execute(candidate_id, resume_id, job_id)
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
