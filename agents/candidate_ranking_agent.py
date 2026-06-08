"""
Candidate Ranking Agent
Ranks candidates based on screening, match, and interview scores
"""

from typing import Dict, Any, List
from datetime import datetime
import logging

from core.base_agent import BaseAgent
from core.communication import AgentMessage
from database import RankingResult, CandidateStatus
from mcp_servers import get_ats_mcp

logger = logging.getLogger(__name__)


class CandidateRankingAgent(BaseAgent):
    """
    Candidate Ranking Agent
    Ranks candidates for a given job position
    """

    def __init__(self, agent_id: str = "candidate_ranker_1"):
        """Initialize Candidate Ranking Agent"""
        super().__init__(
            agent_id=agent_id,
            agent_type="candidate_ranking",
            description="Ranks candidates based on screening, matching, and interview performance",
        )
        self.ats = get_ats_mcp()
        self.rankings: Dict[str, List[RankingResult]] = {}  # job_id -> list of rankings

    def execute(self, job_id: str, **kwargs) -> Dict[str, Any]:
        """
        Execute candidate ranking for a specific job
        
        Args:
            job_id: ID of job position
            **kwargs: Additional parameters
            
        Returns:
            Ranking result
        """
        logger.info(f"Starting candidate ranking for job {job_id}")

        try:
            # Get job information
            job = self.ats.get_job_posting(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return {"error": "Job not found"}

            # Get all applications for this job
            applications = self.ats.get_applications_for_job(job_id)
            logger.info(f"Found {len(applications)} applications for job {job_id}")

            if not applications:
                logger.info("No applications to rank")
                return {"job_id": job_id, "rankings": []}

            # Collect candidates with scores
            candidates_with_scores = []
            for app in applications:
                candidate_id = app.get("candidate_id")
                candidate = self.ats.get_candidate(candidate_id)

                if candidate:
                    candidates_with_scores.append({
                        "candidate_id": candidate_id,
                        "candidate": candidate,
                        "application": app,
                    })

            # Rank candidates
            ranked_candidates = self._rank_candidates(candidates_with_scores, job_id)

            # Store rankings
            self.rankings[job_id] = ranked_candidates

            # Update candidate statuses
            for rank_result in ranked_candidates:
                self.ats.update_candidate(rank_result.candidate_id, {
                    "status": CandidateStatus.RANKED.value,
                    "ranking_score": rank_result.final_score,
                })

            result = {
                "job_id": job_id,
                "total_candidates_ranked": len(ranked_candidates),
                "rankings": [r.to_dict() for r in ranked_candidates],
                "top_candidate": ranked_candidates[0].to_dict() if ranked_candidates else None,
            }

            logger.info(f"Ranking complete for job {job_id}: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in candidate ranking: {str(e)}")
            self.error_count += 1
            return {
                "error": str(e),
                "job_id": job_id,
            }

    def rank_candidate(
        self,
        candidate_id: str,
        job_id: str,
        screening_score: float,
        match_score: float,
        interview_score: float = 0.0,
    ) -> RankingResult:
        """
        Calculate ranking score for a single candidate
        
        Args:
            candidate_id: ID of candidate
            job_id: ID of job
            screening_score: Resume screening score (0-100)
            match_score: Job match score (0-100)
            interview_score: Interview performance score (0-100)
            
        Returns:
            RankingResult
        """
        # Normalize scores to 0-1 range
        screening_norm = screening_score / 100
        match_norm = match_score / 100
        interview_norm = interview_score / 100

        # Calculate weighted final score
        # Weights: screening 30%, match 40%, interview 30%
        final_score = (screening_norm * 0.3 + match_norm * 0.4 + interview_norm * 0.3) * 100

        # Generate recommendation
        recommendation = self._generate_recommendation(final_score, screening_score, match_score, interview_score)

        ranking = RankingResult(
            candidate_id=candidate_id,
            job_id=job_id,
            rank=0,  # Will be set during bulk ranking
            final_score=final_score,
            screening_score=screening_score,
            match_score=match_score,
            interview_score=interview_score,
            recommendation=recommendation,
        )

        return ranking

    def _rank_candidates(self, candidates_with_scores: List[Dict], job_id: str) -> List[RankingResult]:
        """
        Rank multiple candidates for a job
        
        Args:
            candidates_with_scores: List of candidate data dicts
            job_id: ID of job
            
        Returns:
            Sorted list of RankingResult objects
        """
        rankings = []

        for item in candidates_with_scores:
            candidate = item["candidate"]
            candidate_id = candidate["id"]

            # Get scores from candidate data
            screening_score = candidate.get("screening_score", 0)
            match_score = candidate.get("match_score", 0)
            interview_score = candidate.get("interview_feedback", "")  # Will be 0 if no feedback yet

            # Parse interview score if available (for now assume 0)
            interview_score = 0.0

            ranking = self.rank_candidate(
                candidate_id=candidate_id,
                job_id=job_id,
                screening_score=screening_score,
                match_score=match_score,
                interview_score=interview_score,
            )

            rankings.append(ranking)

        # Sort by final score in descending order
        rankings.sort(key=lambda x: x.final_score, reverse=True)

        # Assign ranks
        for idx, ranking in enumerate(rankings, 1):
            ranking.rank = idx

        logger.info(f"Ranked {len(rankings)} candidates for job {job_id}")
        return rankings

    def _generate_recommendation(
        self,
        final_score: float,
        screening_score: float,
        match_score: float,
        interview_score: float,
    ) -> str:
        """
        Generate a recommendation based on scores
        
        Args:
            final_score: Final weighted score
            screening_score: Screening score
            match_score: Job match score
            interview_score: Interview score
            
        Returns:
            Recommendation string
        """
        if final_score >= 80:
            return "STRONG_RECOMMEND"
        elif final_score >= 65:
            if match_score >= 70 and screening_score >= 60:
                return "RECOMMEND"
            else:
                return "CONSIDER"
        elif final_score >= 50:
            return "CONSIDER"
        else:
            return "NOT_RECOMMENDED"

    def get_rankings_for_job(self, job_id: str) -> List[RankingResult]:
        """Get rankings for a specific job"""
        return self.rankings.get(job_id, [])

    def get_top_candidates(self, job_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get top candidates for a job
        
        Args:
            job_id: ID of job
            limit: Number of top candidates to return
            
        Returns:
            List of top candidates
        """
        rankings = self.get_rankings_for_job(job_id)
        return [r.to_dict() for r in rankings[:limit]]

    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """
        Handle incoming messages
        
        Args:
            message: Incoming message
            
        Returns:
            Response data
        """
        if message.message_type.value == "match_result":
            # Receive match results from Job Matching Agent
            candidate_id = message.payload.get("candidate_id")
            job_id = message.payload.get("job_id")
            match_score = message.payload.get("match_score", 0)

            logger.info(f"Received match result for candidate {candidate_id}: {match_score}%")
            return {"status": "received"}

        elif message.message_type.value == "interview_feedback":
            # Receive interview feedback from Interview Coordination Agent
            candidate_id = message.payload.get("candidate_id")
            interview_rating = message.payload.get("interview_rating", 0)

            logger.info(f"Received interview feedback for candidate {candidate_id}: {interview_rating}")
            return {"status": "received"}

        elif message.message_type.value == "ranking_request":
            # Request to rank candidates for a job
            job_id = message.payload.get("job_id")
            result = self.execute(job_id)
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
