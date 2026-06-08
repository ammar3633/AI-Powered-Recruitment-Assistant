"""
ATS (Applicant Tracking System) MCP Server
Manages candidate data, job postings, and recruitment pipeline
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

VALID_APP_STATUSES = {
    "applied", "screening", "shortlisted", "interview_scheduled",
    "interviewed", "offer_sent", "hired", "rejected", "withdrawn"
}

VALID_JOB_STATUSES = {"open", "paused", "closed", "filled"}


class ATSMCP:
    """
    MCP Server for ATS operations
    Handles candidate profiles, job postings, and application tracking
    """

    def __init__(self):
        self.candidates: Dict[str, Dict] = {}
        self.job_postings: Dict[str, Dict] = {}
        self.applications: Dict[str, Dict] = {}
        self.server_name = "ATS MCP"
        logger.info("ATS MCP Server initialized")

    # ------------------------------------------------------------------ #
    # Candidates                                                           #
    # ------------------------------------------------------------------ #

    def create_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """Create a new candidate profile. Returns candidate ID."""
        candidate_id = str(uuid.uuid4())
        email = candidate_data.get("email", "").strip().lower()

        # Duplicate email guard
        if email and self._find_candidate_by_email(email):
            raise ValueError(f"Candidate with email '{email}' already exists.")

        self.candidates[candidate_id] = {
            "id": candidate_id,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "reschedule_count": 0,
            **candidate_data,
            "email": email,  # normalise after spread so it overrides
        }
        logger.info(f"Created candidate: {candidate_id}")
        return candidate_id

    def get_candidate(self, candidate_id: str) -> Optional[Dict]:
        """Get candidate profile by ID."""
        return self.candidates.get(candidate_id)

    def update_candidate(self, candidate_id: str, updates: Dict[str, Any]) -> bool:
        """Update candidate profile. Returns False if candidate not found."""
        if candidate_id not in self.candidates:
            logger.warning(f"Candidate not found: {candidate_id}")
            return False
        # Prevent overwriting immutable fields
        for key in ("id", "created_at"):
            updates.pop(key, None)
        self.candidates[candidate_id].update(updates)
        self.candidates[candidate_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Updated candidate: {candidate_id}")
        return True

    def delete_candidate(self, candidate_id: str) -> bool:
        """Soft-delete a candidate (marks as inactive, keeps record)."""
        if candidate_id not in self.candidates:
            return False
        self.candidates[candidate_id]["status"] = "inactive"
        self.candidates[candidate_id]["deleted_at"] = datetime.now().isoformat()
        logger.info(f"Soft-deleted candidate: {candidate_id}")
        return True

    def list_candidates(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List candidates with optional filtering.
        Supported filter keys: status, department, min_score, flag
        """
        candidates = [c for c in self.candidates.values() if c.get("status") != "inactive"]

        if filters:
            if "status" in filters:
                candidates = [c for c in candidates if c.get("status") == filters["status"]]
            if "department" in filters:
                candidates = [c for c in candidates if c.get("department") == filters["department"]]
            if "min_score" in filters:
                threshold = float(filters["min_score"])
                candidates = [c for c in candidates if float(c.get("screening_score", 0)) >= threshold]
            if "flag" in filters:
                candidates = [c for c in candidates if filters["flag"] in c.get("flags", [])]

        logger.info(f"Listed {len(candidates)} candidates")
        return candidates

    def search_candidates(self, query: str) -> List[Dict]:
        """Search candidates by name, email, or skill."""
        query_lower = query.lower()
        results = []
        for c in self.candidates.values():
            if c.get("status") == "inactive":
                continue
            skills = " ".join(c.get("skills", [])).lower()
            if (
                query_lower in c.get("name", "").lower()
                or query_lower in c.get("email", "").lower()
                or query_lower in skills
            ):
                results.append(c)
        logger.info(f"Search found {len(results)} candidates for query: '{query}'")
        return results

    def flag_candidate(self, candidate_id: str, flag: str) -> bool:
        """Add a flag to a candidate (e.g. 'too_many_reschedules', 'high_priority')."""
        if candidate_id not in self.candidates:
            return False
        flags = self.candidates[candidate_id].setdefault("flags", [])
        if flag not in flags:
            flags.append(flag)
        self.candidates[candidate_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Flagged candidate {candidate_id}: {flag}")
        return True

    # ------------------------------------------------------------------ #
    # Job Postings                                                         #
    # ------------------------------------------------------------------ #

    def create_job_posting(self, job_data: Dict[str, Any]) -> str:
        """Create a new job posting. Returns job ID."""
        job_id = str(uuid.uuid4())
        self.job_postings[job_id] = {
            "id": job_id,
            "created_at": datetime.now().isoformat(),
            "status": "open",
            "applicant_count": 0,
            **job_data,
        }
        logger.info(f"Created job posting: {job_id}")
        return job_id

    def get_job_posting(self, job_id: str) -> Optional[Dict]:
        """Get job posting by ID."""
        return self.job_postings.get(job_id)

    def update_job_status(self, job_id: str, status: str) -> bool:
        """Update job posting status. Validates against allowed values."""
        if job_id not in self.job_postings:
            logger.warning(f"Job not found: {job_id}")
            return False
        if status not in VALID_JOB_STATUSES:
            raise ValueError(f"Invalid job status '{status}'. Must be one of {VALID_JOB_STATUSES}.")
        self.job_postings[job_id]["status"] = status
        self.job_postings[job_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Job {job_id} status → {status}")
        return True

    def list_job_postings(self, status: str = "open") -> List[Dict]:
        """List job postings. Pass status='all' to get every posting."""
        if status == "all":
            jobs = list(self.job_postings.values())
        else:
            jobs = [j for j in self.job_postings.values() if j.get("status") == status]
        logger.info(f"Listed {len(jobs)} job postings (status={status})")
        return jobs

    # ------------------------------------------------------------------ #
    # Applications                                                         #
    # ------------------------------------------------------------------ #

    def create_application(self, candidate_id: str, job_id: str) -> str:
        """
        Create a job application.
        Raises ValueError if candidate/job don't exist or candidate already applied.
        """
        if candidate_id not in self.candidates:
            raise ValueError(f"Candidate '{candidate_id}' not found.")
        if job_id not in self.job_postings:
            raise ValueError(f"Job '{job_id}' not found.")
        if self.job_postings[job_id].get("status") != "open":
            raise ValueError(f"Job '{job_id}' is not accepting applications.")

        # Duplicate application guard
        existing = self.get_applications_for_candidate(candidate_id)
        if any(a["job_id"] == job_id and a["status"] != "withdrawn" for a in existing):
            raise ValueError(f"Candidate '{candidate_id}' already has an active application for job '{job_id}'.")

        app_id = str(uuid.uuid4())
        self.applications[app_id] = {
            "id": app_id,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "status": "applied",
            "status_history": [{"status": "applied", "timestamp": datetime.now().isoformat()}],
            "created_at": datetime.now().isoformat(),
        }
        # Keep applicant_count in sync
        self.job_postings[job_id]["applicant_count"] = (
            self.job_postings[job_id].get("applicant_count", 0) + 1
        )
        logger.info(f"Created application: {app_id} (candidate: {candidate_id}, job: {job_id})")
        return app_id

    def get_application(self, app_id: str) -> Optional[Dict]:
        """Get application by ID."""
        return self.applications.get(app_id)

    def update_application_status(self, app_id: str, status: str) -> bool:
        """
        Update application status with validation and history tracking.
        Returns False if application not found.
        """
        if app_id not in self.applications:
            logger.warning(f"Application not found: {app_id}")
            return False
        if status not in VALID_APP_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of {VALID_APP_STATUSES}.")

        self.applications[app_id]["status"] = status
        self.applications[app_id].setdefault("status_history", []).append(
            {"status": status, "timestamp": datetime.now().isoformat()}
        )
        self.applications[app_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Application {app_id} status → {status}")
        return True

    def get_applications_for_job(self, job_id: str, status: Optional[str] = None) -> List[Dict]:
        """Get all applications for a job, optionally filtered by status."""
        apps = [a for a in self.applications.values() if a.get("job_id") == job_id]
        if status:
            apps = [a for a in apps if a.get("status") == status]
        logger.info(f"Retrieved {len(apps)} applications for job: {job_id}")
        return apps

    def get_applications_for_candidate(self, candidate_id: str) -> List[Dict]:
        """Get all applications for a candidate."""
        apps = [a for a in self.applications.values() if a.get("candidate_id") == candidate_id]
        logger.info(f"Retrieved {len(apps)} applications for candidate: {candidate_id}")
        return apps

    def get_pipeline_summary(self, job_id: str) -> Dict[str, int]:
        """Return a status-count breakdown for all applications on a job."""
        apps = self.get_applications_for_job(job_id)
        summary: Dict[str, int] = {}
        for app in apps:
            s = app.get("status", "unknown")
            summary[s] = summary.get(s, 0) + 1
        return summary

    # ------------------------------------------------------------------ #
    # Server status                                                        #
    # ------------------------------------------------------------------ #

    def get_server_status(self) -> Dict[str, Any]:
        """Get server status and statistics."""
        app_by_status: Dict[str, int] = {}
        for a in self.applications.values():
            s = a.get("status", "unknown")
            app_by_status[s] = app_by_status.get(s, 0) + 1

        return {
            "server_name": self.server_name,
            "total_candidates": len([c for c in self.candidates.values() if c.get("status") != "inactive"]),
            "total_job_postings": len(self.job_postings),
            "open_jobs": len([j for j in self.job_postings.values() if j.get("status") == "open"]),
            "total_applications": len(self.applications),
            "applications_by_status": app_by_status,
            "last_activity": datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _find_candidate_by_email(self, email: str) -> Optional[Dict]:
        """Return the first candidate matching the given email, or None."""
        email = email.strip().lower()
        for c in self.candidates.values():
            if c.get("email", "").lower() == email and c.get("status") != "inactive":
                return c
        return None


# Global singleton
_ats_mcp: Optional[ATSMCP] = None


def get_ats_mcp() -> ATSMCP:
    """Get or create global ATS MCP instance."""
    global _ats_mcp
    if _ats_mcp is None:
        _ats_mcp = ATSMCP()
    return _ats_mcp
