"""
Main orchestration script for AI-Powered Recruitment Assistant
Initializes all agents and MCP servers and orchestrates the recruitment workflow
"""
import logging
from typing import Dict, Any

from config import get_config
from core import get_message_broker, BaseAgent
from agents import (
    ResumeScreeningAgent,
    JobMatchingAgent,
    InterviewCoordinationAgent,
    CandidateRankingAgent,
)
from mcp_servers import get_ats_mcp, get_calendar_mcp, get_resume_parser_mcp

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


class RecruitmentOrchestrator:
    """
    Main orchestrator for the AI-Powered Recruitment Assistant
    Manages agents, MCP servers, and workflow execution
    """

    def __init__(self):
        """Initialize the orchestrator"""
        self.config = get_config()
        self.message_broker = get_message_broker()

        # Initialize MCP servers
        self.ats = get_ats_mcp()
        self.calendar = get_calendar_mcp()
        self.resume_parser = get_resume_parser_mcp()

        # Initialize agents
        self.resume_screening_agent = ResumeScreeningAgent()
        self.job_matching_agent = JobMatchingAgent()
        self.interview_coordination_agent = InterviewCoordinationAgent()
        self.candidate_ranking_agent = CandidateRankingAgent()

        self.agents = [
            self.resume_screening_agent,
            self.job_matching_agent,
            self.interview_coordination_agent,
            self.candidate_ranking_agent,
        ]

        logger.info("RecruitmentOrchestrator initialized")

    def submit_resume(
        self,
        resume_content: str,
        candidate_name: str,
        candidate_email: str,
        candidate_phone: str,
        job_id: str = None,
    ) -> Dict[str, Any]:
        """
        Submit a resume for processing through the recruitment pipeline
        
        Args:
            resume_content: Raw resume text
            candidate_name: Candidate name
            candidate_email: Candidate email
            candidate_phone: Candidate phone
            job_id: Optional specific job ID
            
        Returns:
            Processing result
        """
        logger.info(f"Submitting resume for {candidate_name}")

        # Step 1: Screen the resume
        screening_result = self.resume_screening_agent.execute(
            resume_content=resume_content,
            candidate_name=candidate_name,
            job_id=job_id,
        )

        if screening_result.get("error"):
            logger.error(f"Resume screening failed: {screening_result['error']}")
            return screening_result

        candidate_id = screening_result.get("candidate_id")
        resume_id = screening_result.get("resume_id")
        passes_screening = screening_result.get("passes_screening", False)

        logger.info(
            f"Resume screening complete for {candidate_name}. "
            f"Pass: {passes_screening}, Score: {screening_result.get('screening_score')}"
        )

        if not passes_screening:
            logger.info(f"Candidate {candidate_name} did not pass initial screening")
            return {
                "candidate_id": candidate_id,
                "status": "rejected",
                "screening_result": screening_result,
            }

        # Step 2: Perform job matching
        if job_id:
            matching_result = self.job_matching_agent.execute(
                candidate_id=candidate_id,
                resume_id=resume_id,
                job_id=job_id,
            )

            logger.info(
                f"Job matching complete. Found {matching_result.get('total_matches', 0)} matches"
            )

            if matching_result.get("error"):
                logger.error(f"Job matching failed: {matching_result['error']}")
                return matching_result

            best_match = matching_result.get("best_match")

            if best_match:
                # Step 3: Schedule interview
                interview_result = self.interview_coordination_agent.execute(
                    candidate_id=candidate_id,
                    job_id=best_match["job_id"],
                )

                logger.info(f"Interview scheduled: {interview_result.get('event_id')}")

                return {
                    "candidate_id": candidate_id,
                    "status": "interview_scheduled",
                    "screening_result": screening_result,
                    "matching_result": matching_result,
                    "interview_result": interview_result,
                }

        return {
            "candidate_id": candidate_id,
            "status": "shortlisted",
            "screening_result": screening_result,
        }

    def create_job_posting(
        self,
        title: str,
        description: str,
        required_skills: list,
        required_experience_years: float = 0,
        department: str = "",
        salary_range: str = "",
        location: str = "",
    ) -> Dict[str, Any]:
        """
        Create a new job posting
        
        Args:
            title: Job title
            description: Job description
            required_skills: List of required skills
            required_experience_years: Years of experience required
            department: Department name
            salary_range: Salary range
            location: Job location
            
        Returns:
            Job posting ID
        """
        job_data = {
            "title": title,
            "description": description,
            "required_skills": required_skills,
            "required_experience_years": required_experience_years,
            "department": department,
            "salary_range": salary_range,
            "location": location,
        }

        job_id = self.ats.create_job_posting(job_data)
        logger.info(f"Created job posting: {job_id} - {title}")

        return {"job_id": job_id, "title": title}

    def rank_candidates_for_job(self, job_id: str) -> Dict[str, Any]:
        """
        Rank all candidates for a specific job
        
        Args:
            job_id: ID of the job
            
        Returns:
            Ranking result
        """
        logger.info(f"Starting ranking for job {job_id}")

        ranking_result = self.candidate_ranking_agent.execute(job_id=job_id)

        logger.info(f"Ranking complete for job {job_id}")
        return ranking_result

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system status and statistics
        
        Returns:
            System status dictionary
        """
        status = {
            "ats": self.ats.get_server_status(),
            "calendar": self.calendar.get_server_status(),
            "resume_parser": self.resume_parser.get_server_status(),
            "agents": [agent.get_status() for agent in self.agents],
            "message_broker": {
                "total_messages": len(self.message_broker.get_all_messages()),
                "pending_messages": len(self.message_broker.message_queue),
            },
        }
        return status

    def process_pending_messages(self) -> int:
        """
        Process all pending messages for all agents
        
        Returns:
            Total number of messages processed
        """
        total_processed = 0

        for agent in self.agents:
            count = agent.process_messages()
            total_processed += count
            logger.info(f"Agent {agent.agent_id} processed {count} messages")

        return total_processed


# Singleton instance
_orchestrator: RecruitmentOrchestrator = None


def get_orchestrator() -> RecruitmentOrchestrator:
    """Get or create the global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RecruitmentOrchestrator()
    return _orchestrator

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("AI-POWERED RECRUITMENT ASSISTANT - SYSTEM INITIALIZATION")
    logger.info("=" * 60)

    # Initialize orchestrator
    orchestrator = get_orchestrator()

    # Display system status
    status = orchestrator.get_system_status()
    logger.info("System Status:")
    logger.info(f"  - ATS MCP: {status['ats']}")
    logger.info(f"  - Calendar MCP: {status['calendar']}")
    logger.info(f"  - Resume Parser MCP: {status['resume_parser']}")
    logger.info(f"  - Active Agents: {len(status['agents'])}")
    logger.info(f"  - Message Broker - Total: {status['message_broker']['total_messages']}")

    logger.info("=" * 60)
    logger.info("System initialized successfully!")
    logger.info("=" * 60)
