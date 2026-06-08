"""
ATS (Applicant Tracking System) MCP Server
Manages candidate data, job postings, and recruitment pipeline
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


class ATSMCP:
    """
    MCP Server for ATS operations
    Handles candidate profiles, job postings, and application tracking
    """

    def __init__(self):
        """Initialize ATS MCP server"""
        self.candidates: Dict[str, Dict] = {}
        self.job_postings: Dict[str, Dict] = {}
        self.applications: Dict[str, Dict] = {}
        self.server_name = "ATS MCP"
        logger.info("ATS MCP Server initialized")

    def create_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """
        Create a new candidate profile
        
        Args:
            candidate_data: Candidate information
            
        Returns:
            Candidate ID
        """
        import uuid

        candidate_id = str(uuid.uuid4())
        self.candidates[candidate_id] = {
            "id": candidate_id,
            "created_at": datetime.now().isoformat(),
            **candidate_data,
        }
        logger.info(f"Created candidate: {candidate_id}")
        return candidate_id

    def get_candidate(self, candidate_id: str) -> Optional[Dict]:
        """Get candidate profile by ID"""
        return self.candidates.get(candidate_id)

    def update_candidate(self, candidate_id: str, updates: Dict[str, Any]) -> bool:
        """Update candidate profile"""
        if candidate_id not in self.candidates:
            logger.warning(f"Candidate not found: {candidate_id}")
            return False

        self.candidates[candidate_id].update(updates)
        self.candidates[candidate_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Updated candidate: {candidate_id}")
        return True

    def list_candidates(self, filters: Optional[Dict] = None) -> List[Dict]:
        """
        List candidates with optional filtering
        
        Args:
            filters: Optional filters (status, department, etc.)
            
        Returns:
            List of matching candidates
        """
        candidates = list(self.candidates.values())

        if filters:
            if "status" in filters:
                candidates = [c for c in candidates if c.get("status") == filters["status"]]
            if "department" in filters:
                candidates = [c for c in candidates if c.get("department") == filters["department"]]

        logger.info(f"Listed {len(candidates)} candidates")
        return candidates

    def create_job_posting(self, job_data: Dict[str, Any]) -> str:
        """
        Create a new job posting
        
        Args:
            job_data: Job posting information
            
        Returns:
            Job ID
        """
        import uuid

        job_id = str(uuid.uuid4())
        self.job_postings[job_id] = {
            "id": job_id,
            "created_at": datetime.now().isoformat(),
            "status": "open",
            **job_data,
        }
        logger.info(f"Created job posting: {job_id}")
        return job_id

    def get_job_posting(self, job_id: str) -> Optional[Dict]:
        """Get job posting by ID"""
        return self.job_postings.get(job_id)

    def list_job_postings(self, status: str = "open") -> List[Dict]:
        """List job postings with optional status filter"""
        jobs = [j for j in self.job_postings.values() if j.get("status") == status]
        logger.info(f"Listed {len(jobs)} job postings with status: {status}")
        return jobs

    def create_application(self, candidate_id: str, job_id: str) -> str:
        """
        Create a job application
        
        Args:
            candidate_id: ID of candidate
            job_id: ID of job posting
            
        Returns:
            Application ID
        """
        import uuid

        app_id = str(uuid.uuid4())
        self.applications[app_id] = {
            "id": app_id,
            "candidate_id": candidate_id,
            "job_id": job_id,
            "status": "applied",
            "created_at": datetime.now().isoformat(),
        }
        logger.info(f"Created application: {app_id} (candidate: {candidate_id}, job: {job_id})")
        return app_id

    def get_application(self, app_id: str) -> Optional[Dict]:
        """Get application by ID"""
        return self.applications.get(app_id)

    def update_application_status(self, app_id: str, status: str) -> bool:
        """Update application status"""
        if app_id not in self.applications:
            logger.warning(f"Application not found: {app_id}")
            return False

        self.applications[app_id]["status"] = status
        self.applications[app_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Updated application {app_id} status to: {status}")
        return True

    def get_applications_for_job(self, job_id: str) -> List[Dict]:
        """Get all applications for a specific job"""
        apps = [a for a in self.applications.values() if a.get("job_id") == job_id]
        logger.info(f"Retrieved {len(apps)} applications for job: {job_id}")
        return apps

    def get_applications_for_candidate(self, candidate_id: str) -> List[Dict]:
        """Get all applications for a specific candidate"""
        apps = [a for a in self.applications.values() if a.get("candidate_id") == candidate_id]
        logger.info(f"Retrieved {len(apps)} applications for candidate: {candidate_id}")
        return apps

    def search_candidates(self, query: str) -> List[Dict]:
        """
        Search candidates by name or email
        
        Args:
            query: Search query
            
        Returns:
            List of matching candidates
        """
        query_lower = query.lower()
        results = [
            c
            for c in self.candidates.values()
            if query_lower in c.get("name", "").lower()
            or query_lower in c.get("email", "").lower()
        ]
        logger.info(f"Search found {len(results)} candidates for query: {query}")
        return results

    def get_server_status(self) -> Dict[str, Any]:
        """Get server status and statistics"""
        return {
            "server_name": self.server_name,
            "total_candidates": len(self.candidates),
            "total_job_postings": len(self.job_postings),
            "total_applications": len(self.applications),
            "last_activity": datetime.now().isoformat(),
        }


# Global ATS MCP instance
_ats_mcp: Optional[ATSMCP] = None


def get_ats_mcp() -> ATSMCP:
    """Get or create global ATS MCP instance"""
    global _ats_mcp
    if _ats_mcp is None:
        _ats_mcp = ATSMCP()
    return _ats_mcp
