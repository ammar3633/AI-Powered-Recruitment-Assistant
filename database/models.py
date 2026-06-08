"""
Database models for AI-Powered Recruitment Assistant
"""
from datetime import datetime
from typing import List, Optional
from dataclasses import dataclass, field
from enum import Enum


class CandidateStatus(str, Enum):
    """Candidate status in recruitment pipeline"""
    APPLIED = "applied"
    SCREENED = "screened"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    RANKED = "ranked"
    OFFERED = "offered"
    REJECTED = "rejected"


class InterviewStatus(str, Enum):
    """Interview scheduling status"""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"


@dataclass
class Resume:
    """Resume data model"""
    id: str
    candidate_id: str
    name: str
    email: str
    phone: str
    experience_years: float
    skills: List[str] = field(default_factory=list)
    education: List[str] = field(default_factory=list)
    previous_companies: List[str] = field(default_factory=list)
    raw_text: str = ""
    parsed_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "experience_years": self.experience_years,
            "skills": self.skills,
            "education": self.education,
            "previous_companies": self.previous_companies,
        }


@dataclass
class JobPosting:
    """Job posting model"""
    id: str
    title: str
    description: str
    required_skills: List[str] = field(default_factory=list)
    required_experience_years: float = 0.0
    department: str = ""
    salary_range: str = ""
    location: str = ""
    posted_date: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "required_skills": self.required_skills,
            "required_experience_years": self.required_experience_years,
            "department": self.department,
            "salary_range": self.salary_range,
            "location": self.location,
        }


@dataclass
class Candidate:
    """Candidate profile model"""
    id: str
    name: str
    email: str
    phone: str
    resume: Optional[Resume] = None
    status: CandidateStatus = CandidateStatus.APPLIED
    screening_score: float = 0.0
    match_score: float = 0.0
    ranking_score: float = 0.0
    notes: str = ""
    applied_date: datetime = field(default_factory=datetime.now)
    screening_feedback: str = ""
    interview_feedback: str = ""

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status.value,
            "screening_score": self.screening_score,
            "match_score": self.match_score,
            "ranking_score": self.ranking_score,
            "notes": self.notes,
        }


@dataclass
class Interview:
    """Interview scheduling model"""
    id: str
    candidate_id: str
    job_id: str
    scheduled_time: datetime
    interviewer: str
    interview_type: str  # phone, video, in-person
    status: InterviewStatus = InterviewStatus.PENDING
    meeting_link: str = ""
    feedback: str = ""
    rating: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "scheduled_time": self.scheduled_time.isoformat(),
            "interviewer": self.interviewer,
            "interview_type": self.interview_type,
            "status": self.status.value,
            "meeting_link": self.meeting_link,
            "feedback": self.feedback,
            "rating": self.rating,
        }


@dataclass
class MatchResult:
    """Job-Candidate match result"""
    candidate_id: str
    job_id: str
    match_percentage: float
    matched_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    experience_fit: float = 0.0
    reasoning: str = ""

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "match_percentage": self.match_percentage,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "experience_fit": self.experience_fit,
            "reasoning": self.reasoning,
        }


@dataclass
class RankingResult:
    """Candidate ranking result"""
    candidate_id: str
    job_id: str
    rank: int
    final_score: float
    screening_score: float
    match_score: float
    interview_score: float = 0.0
    recommendation: str = ""
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self):
        return {
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "rank": self.rank,
            "final_score": self.final_score,
            "screening_score": self.screening_score,
            "match_score": self.match_score,
            "interview_score": self.interview_score,
            "recommendation": self.recommendation,
        }
