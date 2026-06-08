"""
Resume Parser MCP Server
Handles resume parsing and extraction of candidate information
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ResumeParserMCP:
    """
    MCP Server for resume parsing
    Handles parsing, extraction, and analysis of resume documents
    """

    def __init__(self):
        """Initialize Resume Parser MCP server"""
        self.parsed_resumes: Dict[str, Dict] = {}
        self.server_name = "Resume Parser MCP"
        logger.info("Resume Parser MCP Server initialized")

    def parse_resume(self, resume_content: str, file_name: str = "") -> str:
        """
        Parse a resume document
        
        Args:
            resume_content: Raw resume text content
            file_name: Optional file name
            
        Returns:
            Resume ID
        """
        import uuid
        import re

        resume_id = str(uuid.uuid4())

        # Extract basic information from resume content
        parsed_data = self._extract_information(resume_content)

        self.parsed_resumes[resume_id] = {
            "id": resume_id,
            "file_name": file_name,
            "raw_content": resume_content,
            "parsed_at": datetime.now().isoformat(),
            **parsed_data,
        }

        logger.info(f"Parsed resume: {resume_id} from file: {file_name}")
        return resume_id

    def _extract_information(self, resume_text: str) -> Dict[str, Any]:
        """
        Extract key information from resume text
        Uses pattern matching for demonstration
        
        Args:
            resume_text: Raw resume text
            
        Returns:
            Dictionary with extracted information
        """
        import re

        data = {
            "name": "",
            "email": "",
            "phone": "",
            "experience_years": 0,
            "skills": [],
            "education": [],
            "previous_companies": [],
        }

        # Extract email
        email_pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
        email_match = re.search(email_pattern, resume_text)
        if email_match:
            data["email"] = email_match.group()

        # Extract phone number
        phone_pattern = r"(\+\d{1,3}[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{4}"
        phone_match = re.search(phone_pattern, resume_text)
        if phone_match:
            data["phone"] = phone_match.group()

        # Extract skills (look for common skill keywords)
        skill_keywords = [
            "python",
            "java",
            "javascript",
            "c\\+\\+",
            "sql",
            "machine learning",
            "data science",
            "aws",
            "azure",
            "docker",
            "kubernetes",
            "react",
            "angular",
            "nodejs",
            "django",
            "flask",
            "rest api",
            "agile",
            "git",
            "mongodb",
            "postgresql",
        ]

        text_lower = resume_text.lower()
        data["skills"] = [keyword for keyword in skill_keywords if keyword in text_lower]

        # Extract education (look for degree keywords)
        education_keywords = [
            "bachelor",
            "master",
            "phd",
            "bs",
            "ms",
            "btech",
            "mtech",
        ]
        data["education"] = [
            keyword for keyword in education_keywords if keyword.lower() in text_lower
        ]

        # Extract experience years (look for patterns like "5 years experience")
        exp_pattern = r"(\d+)\s+years?\s+of\s+experience"
        exp_match = re.search(exp_pattern, text_lower)
        if exp_match:
            data["experience_years"] = float(exp_match.group(1))

        logger.debug(f"Extracted data from resume: {data}")
        return data

    def get_parsed_resume(self, resume_id: str) -> Optional[Dict]:
        """Get parsed resume by ID"""
        return self.parsed_resumes.get(resume_id)

    def extract_candidate_profile(self, resume_id: str) -> Optional[Dict]:
        """
        Extract a candidate profile from parsed resume
        
        Args:
            resume_id: ID of parsed resume
            
        Returns:
            Candidate profile dictionary
        """
        resume = self.get_parsed_resume(resume_id)
        if not resume:
            logger.warning(f"Resume not found: {resume_id}")
            return None

        profile = {
            "resume_id": resume_id,
            "name": resume.get("name", ""),
            "email": resume.get("email", ""),
            "phone": resume.get("phone", ""),
            "experience_years": resume.get("experience_years", 0),
            "skills": resume.get("skills", []),
            "education": resume.get("education", []),
            "previous_companies": resume.get("previous_companies", []),
        }

        logger.info(f"Extracted candidate profile from resume: {resume_id}")
        return profile

    def validate_resume(self, resume_id: str) -> Dict[str, Any]:
        """
        Validate parsed resume quality
        
        Args:
            resume_id: ID of parsed resume
            
        Returns:
            Validation report
        """
        resume = self.get_parsed_resume(resume_id)
        if not resume:
            logger.warning(f"Resume not found: {resume_id}")
            return {"valid": False, "errors": ["Resume not found"]}

        errors = []
        warnings = []

        # Check for required fields
        if not resume.get("email"):
            errors.append("Email not found")
        if not resume.get("phone"):
            errors.append("Phone number not found")
        if not resume.get("skills"):
            warnings.append("No skills detected")

        # Check data quality
        if resume.get("experience_years", 0) < 0:
            errors.append("Invalid experience years")

        validation_result = {
            "resume_id": resume_id,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "completeness_score": self._calculate_completeness(resume),
        }

        logger.info(f"Validation result for resume {resume_id}: {validation_result}")
        return validation_result

    def _calculate_completeness(self, resume: Dict) -> float:
        """Calculate completeness score for a resume (0-100)"""
        score = 0
        total_checks = 5

        if resume.get("name"):
            score += 1
        if resume.get("email"):
            score += 1
        if resume.get("phone"):
            score += 1
        if resume.get("skills"):
            score += 1
        if resume.get("experience_years", 0) > 0:
            score += 1

        return (score / total_checks) * 100

    def compare_resume_to_job(
        self, resume_id: str, job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare a resume against job requirements
        
        Args:
            resume_id: ID of parsed resume
            job_requirements: Job requirements dict with required_skills, required_experience_years, etc.
            
        Returns:
            Comparison result with match score
        """
        resume = self.get_parsed_resume(resume_id)
        if not resume:
            logger.warning(f"Resume not found: {resume_id}")
            return {"match_percentage": 0, "errors": ["Resume not found"]}

        resume_skills = set(resume.get("skills", []))
        required_skills = set(job_requirements.get("required_skills", []))
        resume_experience = resume.get("experience_years", 0)
        required_experience = job_requirements.get("required_experience_years", 0)

        # Calculate skill match
        if required_skills:
            matched_skills = resume_skills.intersection(required_skills)
            skill_match_percentage = (len(matched_skills) / len(required_skills)) * 100
        else:
            skill_match_percentage = 100

        # Calculate experience match
        if resume_experience >= required_experience:
            experience_match_percentage = 100
        else:
            experience_match_percentage = (resume_experience / required_experience * 100) if required_experience > 0 else 100

        # Overall match
        overall_match = (skill_match_percentage + experience_match_percentage) / 2

        result = {
            "resume_id": resume_id,
            "job_id": job_requirements.get("job_id", ""),
            "match_percentage": overall_match,
            "skill_match_percentage": skill_match_percentage,
            "experience_match_percentage": experience_match_percentage,
            "matched_skills": list(resume_skills.intersection(required_skills)),
            "missing_skills": list(required_skills - resume_skills),
            "experience_fit": resume_experience >= required_experience,
        }

        logger.info(f"Resume comparison: {result}")
        return result

    def search_resumes(self, query: str, field: str = "all") -> List[Dict]:
        """
        Search parsed resumes
        
        Args:
            query: Search query
            field: Field to search in (name, email, skills, education, all)
            
        Returns:
            List of matching resumes
        """
        query_lower = query.lower()
        results = []

        for resume in self.parsed_resumes.values():
            match = False

            if field in ["all", "name"]:
                if query_lower in resume.get("name", "").lower():
                    match = True
            if field in ["all", "email"]:
                if query_lower in resume.get("email", "").lower():
                    match = True
            if field in ["all", "skills"]:
                if any(query_lower in skill.lower() for skill in resume.get("skills", [])):
                    match = True
            if field in ["all", "education"]:
                if any(query_lower in edu.lower() for edu in resume.get("education", [])):
                    match = True

            if match:
                results.append(resume)

        logger.info(f"Search found {len(results)} resumes for query: {query}")
        return results

    def get_server_status(self) -> Dict[str, Any]:
        """Get server status and statistics"""
        return {
            "server_name": self.server_name,
            "total_parsed_resumes": len(self.parsed_resumes),
            "last_activity": datetime.now().isoformat(),
        }


# Global Resume Parser MCP instance
_resume_parser_mcp: Optional[ResumeParserMCP] = None


def get_resume_parser_mcp() -> ResumeParserMCP:
    """Get or create global Resume Parser MCP instance"""
    global _resume_parser_mcp
    if _resume_parser_mcp is None:
        _resume_parser_mcp = ResumeParserMCP()
    return _resume_parser_mcp
