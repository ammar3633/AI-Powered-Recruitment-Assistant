"""
Database module for AI-Powered Recruitment Assistant
"""

# Import all models for easy access
from .models import (
    Resume,
    JobPosting,
    Candidate,
    Interview,
    MatchResult,
    RankingResult,
    CandidateStatus,
    InterviewStatus,
)

__all__ = [
    "Resume",
    "JobPosting",
    "Candidate",
    "Interview",
    "MatchResult",
    "RankingResult",
    "CandidateStatus",
    "InterviewStatus",
]
