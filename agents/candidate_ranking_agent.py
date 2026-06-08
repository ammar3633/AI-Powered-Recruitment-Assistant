"""
Candidate Ranking Agent
Ranks candidates based on screening, match, and interview scores
Mohammed Ammar
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from core.base_agent import BaseAgent
from core.communication import AgentMessage
from database import RankingResult, CandidateStatus
from mcp_servers import get_ats_mcp

logger = logging.getLogger(__name__)


# Scoring weights
WEIGHT_SCREENING = 0.30
WEIGHT_MATCH = 0.40
WEIGHT_INTERVIEW = 0.30

# When no interview score exists, redistribute interview weight
WEIGHT_SCREENING_NO_INTERVIEW = 0.45
WEIGHT_MATCH_NO_INTERVIEW = 0.55

# Recommendation thresholds
THRESHOLD_STRONG   = 80.0
THRESHOLD_RECOMMEND = 65.0
THRESHOLD_CONSIDER  = 50.0


class CandidateRankingAgent(BaseAgent):
    """
    Ranks candidates for a job position using a weighted scoring model.
    Weights: screening 30%, job match 40%, interview 30%.
    If no interview score is available, weight is redistributed to
    screening (45%) and match (55%) to avoid penalising early-stage candidates.
    """

    def __init__(self, agent_id: str = "candidate_ranker_1"):
        super().__init__(
            agent_id=agent_id,
            agent_type="candidate_ranking",
            description="Ranks candidates based on screening, matching, and interview performance",
        )
        self.ats = get_ats_mcp()
        self.rankings: Dict[str, List[RankingResult]] = {}  # job_id -> sorted rankings

    # ── Public entry point ────────────────────────────────────────────────────

    def execute(self, job_id: str, **kwargs) -> Dict[str, Any]:
        """
        Rank all candidates who applied to a given job.

        Returns a dict with:
          - job_id
          - total_candidates_ranked
          - rankings (list of dicts)
          - top_candidate (dict or None)
          - score_summary (avg / max / min across ranked candidates)
        """
        logger.info(f"Starting candidate ranking for job {job_id}")

        try:
            job = self.ats.get_job_posting(job_id)
            if not job:
                logger.error(f"Job not found: {job_id}")
                return {"error": "Job not found", "job_id": job_id}

            applications = self.ats.get_applications_for_job(job_id)
            if not applications:
                logger.info(f"No applications for job {job_id}")
                return {"job_id": job_id, "rankings": [], "total_candidates_ranked": 0}

            candidates_data = self._collect_candidates(applications)
            ranked = self._rank_candidates(candidates_data, job_id)

            self.rankings[job_id] = ranked

            # Persist updated status + score back to ATS
            for r in ranked:
                self.ats.update_candidate(r.candidate_id, {
                    "status": CandidateStatus.RANKED.value,
                    "ranking_score": round(r.final_score, 2),
                })

            ranked_dicts = [r.to_dict() for r in ranked]

            result = {
                "job_id": job_id,
                "total_candidates_ranked": len(ranked),
                "rankings": ranked_dicts,
                "top_candidate": ranked_dicts[0] if ranked_dicts else None,
                "score_summary": self._score_summary(ranked),
            }

            logger.info(f"Ranking complete for job {job_id} — {len(ranked)} candidates")
            return result

        except Exception as e:
            logger.error(f"Error ranking candidates for job {job_id}: {e}", exc_info=True)
            self.error_count += 1
            return {"error": str(e), "job_id": job_id}

    def rank_candidate(
        self,
        candidate_id: str,
        job_id: str,
        screening_score: float,
        match_score: float,
        interview_score: Optional[float] = None,
    ) -> RankingResult:
        """
        Compute a weighted final score for a single candidate.

        interview_score is Optional. When None or 0.0, the interview weight
        is redistributed between screening and match so early-stage candidates
        are not unfairly penalised.

        Scores are expected in the 0–100 range.
        """
        screening_score  = self._clamp(screening_score)
        match_score      = self._clamp(match_score)

        has_interview = interview_score is not None and interview_score > 0.0
        interview_score = self._clamp(interview_score or 0.0)

        if has_interview:
            final_score = (
                screening_score * WEIGHT_SCREENING
                + match_score   * WEIGHT_MATCH
                + interview_score * WEIGHT_INTERVIEW
            )
        else:
            # Redistribute interview weight — don't punish pre-interview candidates
            final_score = (
                screening_score * WEIGHT_SCREENING_NO_INTERVIEW
                + match_score   * WEIGHT_MATCH_NO_INTERVIEW
            )

        final_score = round(final_score, 2)

        recommendation = self._generate_recommendation(
            final_score, screening_score, match_score, interview_score, has_interview
        )

        return RankingResult(
            candidate_id=candidate_id,
            job_id=job_id,
            rank=0,  # assigned during bulk sort
            final_score=final_score,
            screening_score=screening_score,
            match_score=match_score,
            interview_score=interview_score,
            recommendation=recommendation,
        )

    def get_rankings_for_job(self, job_id: str) -> List[RankingResult]:
        """Return cached rankings for a job (empty list if not yet ranked)."""
        return self.rankings.get(job_id, [])

    def get_top_candidates(self, job_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Return the top-N candidates for a job as serialisable dicts."""
        return [r.to_dict() for r in self.get_rankings_for_job(job_id)[:limit]]

    def handle_message(self, message: AgentMessage) -> Dict[str, Any]:
        """Route incoming inter-agent messages."""
        msg_type = message.message_type.value

        if msg_type == "match_result":
            candidate_id = message.payload.get("candidate_id")
            match_score  = message.payload.get("match_score", 0)
            logger.info(f"Match result received — candidate {candidate_id}: {match_score}%")
            return {"status": "received"}

        elif msg_type == "interview_feedback":
            candidate_id   = message.payload.get("candidate_id")
            interview_score = message.payload.get("interview_rating", 0)
            logger.info(f"Interview feedback received — candidate {candidate_id}: {interview_score}")
            return {"status": "received"}

        elif msg_type == "ranking_request":
            job_id = message.payload.get("job_id")
            if not job_id:
                return {"error": "ranking_request missing job_id"}
            return self.execute(job_id)

        logger.warning(f"Unknown message type: {msg_type}")
        return {}

    def process_message(self, message: AgentMessage) -> None:
        result = self.handle_message(message)
        logger.info(f"Processed message {message.message_id}: {result}")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _collect_candidates(self, applications: List[Dict]) -> List[Dict]:
        """Fetch candidate records for a list of applications, skip missing ones."""
        result = []
        for app in applications:
            candidate_id = app.get("candidate_id")
            if not candidate_id:
                continue
            candidate = self.ats.get_candidate(candidate_id)
            if candidate:
                result.append({"candidate": candidate, "application": app})
            else:
                logger.warning(f"Candidate not found: {candidate_id}")
        return result

    def _rank_candidates(self, candidates_data: List[Dict], job_id: str) -> List[RankingResult]:
        """Score, sort, and assign ranks to a list of candidates."""
        rankings = []

        for item in candidates_data:
            candidate    = item["candidate"]
            candidate_id = candidate.get("id")
            if not candidate_id:
                continue

            screening_score = float(candidate.get("screening_score") or 0)
            match_score     = float(candidate.get("match_score") or 0)

            # Parse interview score — could be a numeric rating or absent
            raw_interview = candidate.get("interview_rating") or candidate.get("interview_score")
            interview_score = self._parse_interview_score(raw_interview)

            ranking = self.rank_candidate(
                candidate_id=candidate_id,
                job_id=job_id,
                screening_score=screening_score,
                match_score=match_score,
                interview_score=interview_score,
            )
            rankings.append(ranking)

        # Sort descending by final score; use screening score as tiebreaker
        rankings.sort(key=lambda r: (r.final_score, r.screening_score), reverse=True)

        for idx, r in enumerate(rankings, 1):
            r.rank = idx

        logger.info(f"Ranked {len(rankings)} candidates for job {job_id}")
        return rankings

    def _parse_interview_score(self, raw: Any) -> Optional[float]:
        """
        Convert various interview score formats to a 0–100 float.
        Handles: None, int/float (assumed 0–100), 0–5 star ratings (scaled up),
        and string representations of numbers.
        Returns None if parsing fails or value is zero/absent.
        """
        if raw is None:
            return None
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return None

        if value <= 0:
            return None

        # Star ratings (0–5) — scale to 0–100
        if value <= 5:
            return round(value * 20, 2)

        # Already in 0–100 range
        return round(self._clamp(value), 2)

    def _generate_recommendation(
        self,
        final_score: float,
        screening_score: float,
        match_score: float,
        interview_score: float,
        has_interview: bool,
    ) -> str:
        """
        Map scores to a recommendation label.

        Rules (applied in order):
        1. Any score below 30 in screening or match → NOT_RECOMMENDED regardless of final.
        2. Final >= 80 → STRONG_RECOMMEND (must also have screening >= 70 and match >= 70).
        3. Final >= 65 → RECOMMEND if both screening and match >= 55, else CONSIDER.
        4. Final >= 50 → CONSIDER.
        5. Below 50 → NOT_RECOMMENDED.

        For pre-interview candidates (has_interview=False), the bar for
        STRONG_RECOMMEND is slightly relaxed (final >= 78) since the interview
        component hasn't been factored in yet.
        """
        # Hard disqualification
        if screening_score < 30 or match_score < 30:
            return "NOT_RECOMMENDED"

        strong_threshold = 78.0 if not has_interview else THRESHOLD_STRONG

        if final_score >= strong_threshold and screening_score >= 70 and match_score >= 70:
            return "STRONG_RECOMMEND"

        if final_score >= THRESHOLD_RECOMMEND:
            if screening_score >= 55 and match_score >= 55:
                return "RECOMMEND"
            return "CONSIDER"

        if final_score >= THRESHOLD_CONSIDER:
            return "CONSIDER"

        return "NOT_RECOMMENDED"

    def _score_summary(self, rankings: List[RankingResult]) -> Dict[str, float]:
        """Return avg / max / min of final scores across all ranked candidates."""
        if not rankings:
            return {"avg": 0.0, "max": 0.0, "min": 0.0}
        scores = [r.final_score for r in rankings]
        return {
            "avg": round(sum(scores) / len(scores), 2),
            "max": round(max(scores), 2),
            "min": round(min(scores), 2),
        }

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        """Clamp a value to [lo, hi]."""
        return max(lo, min(hi, value))
