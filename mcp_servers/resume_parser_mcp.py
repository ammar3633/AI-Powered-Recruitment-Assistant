"""
Resume Parser MCP Server
Handles resume parsing and extraction of candidate information
"""

from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import logging
import re
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Skill taxonomy — grouped for weighted matching
# ---------------------------------------------------------------------------
SKILL_GROUPS: Dict[str, List[str]] = {
    "languages":   ["python", "java", "javascript", "typescript", "c++", "c#", "go", "ruby", "swift", "kotlin", "rust", "scala", "php", "r"],
    "web":         ["react", "angular", "vue", "nodejs", "django", "flask", "fastapi", "spring", "express", "html", "css"],
    "data":        ["machine learning", "deep learning", "data science", "nlp", "computer vision", "pandas", "numpy", "tensorflow", "pytorch", "scikit-learn"],
    "databases":   ["sql", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "cassandra", "dynamodb"],
    "cloud":       ["aws", "azure", "gcp", "google cloud", "heroku", "cloudflare"],
    "devops":      ["docker", "kubernetes", "terraform", "ansible", "jenkins", "github actions", "ci/cd", "linux"],
    "practices":   ["rest api", "graphql", "agile", "scrum", "git", "tdd", "microservices", "system design"],
}

ALL_SKILLS: List[str] = [skill for group in SKILL_GROUPS.values() for skill in group]

EDUCATION_LEVELS: Dict[str, int] = {
    "phd": 4, "doctorate": 4,
    "master": 3, "ms": 3, "mtech": 3, "mba": 3, "m.tech": 3,
    "bachelor": 2, "bs": 2, "btech": 2, "b.tech": 2, "be": 2,
    "diploma": 1, "associate": 1,
}

# Regex patterns compiled once
_EMAIL_RE    = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
_PHONE_RE    = re.compile(r"(\+\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{4}")
_EXP_RE      = re.compile(r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+(?:of\s+)?experience", re.IGNORECASE)
_EXP_SINCE_RE = re.compile(r"(?:since|from)\s+(20\d{2}|19\d{2})", re.IGNORECASE)
_NAME_RE     = re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})", re.MULTILINE)
_COMPANY_RE  = re.compile(
    r"(?:at|@|with|for|worked at|employed at)\s+([A-Z][A-Za-z0-9\s&.,]{2,40}?)(?:\s*[,|\n|–|-]|$)",
    re.MULTILINE
)
_LINKEDIN_RE = re.compile(r"linkedin\.com/in/([A-Za-z0-9\-_%]+)", re.IGNORECASE)
_GITHUB_RE   = re.compile(r"github\.com/([A-Za-z0-9\-_%]+)", re.IGNORECASE)


class ResumeParserMCP:
    """
    MCP Server for resume parsing.
    Handles parsing, extraction, scoring, and comparison of resume documents.
    """

    def __init__(self):
        self.parsed_resumes: Dict[str, Dict] = {}
        self.server_name = "Resume Parser MCP"
        logger.info("Resume Parser MCP Server initialized")

    # ------------------------------------------------------------------ #
    # Core parse / retrieve                                                #
    # ------------------------------------------------------------------ #

    def parse_resume(self, resume_content: str, file_name: str = "") -> str:
        """
        Parse a resume document and store the result.

        Returns:
            Resume ID
        """
        if not resume_content or not resume_content.strip():
            raise ValueError("resume_content cannot be empty.")

        resume_id = str(uuid.uuid4())
        parsed_data = self._extract_information(resume_content)

        self.parsed_resumes[resume_id] = {
            "id": resume_id,
            "file_name": file_name,
            "raw_content": resume_content,
            "parsed_at": datetime.now().isoformat(),
            **parsed_data,
        }
        logger.info(f"Parsed resume: {resume_id} (file: '{file_name}')")
        return resume_id

    def get_parsed_resume(self, resume_id: str) -> Optional[Dict]:
        """Get parsed resume by ID."""
        return self.parsed_resumes.get(resume_id)

    def extract_candidate_profile(self, resume_id: str) -> Optional[Dict]:
        """Build a clean candidate profile dict from a parsed resume."""
        resume = self.get_parsed_resume(resume_id)
        if not resume:
            logger.warning(f"Resume not found: {resume_id}")
            return None

        return {
            "resume_id": resume_id,
            "name": resume.get("name", ""),
            "email": resume.get("email", ""),
            "phone": resume.get("phone", ""),
            "linkedin": resume.get("linkedin", ""),
            "github": resume.get("github", ""),
            "experience_years": resume.get("experience_years", 0),
            "skills": resume.get("skills", []),
            "skill_groups": resume.get("skill_groups", {}),
            "education": resume.get("education", []),
            "education_level": resume.get("education_level", 0),
            "previous_companies": resume.get("previous_companies", []),
            "completeness_score": resume.get("completeness_score", 0),
        }

    # ------------------------------------------------------------------ #
    # Validation                                                           #
    # ------------------------------------------------------------------ #

    def validate_resume(self, resume_id: str) -> Dict[str, Any]:
        """Validate parsed resume quality and return a detailed report."""
        resume = self.get_parsed_resume(resume_id)
        if not resume:
            return {"valid": False, "errors": ["Resume not found"]}

        errors: List[str] = []
        warnings: List[str] = []

        if not resume.get("email"):
            errors.append("Email not found")
        if not resume.get("phone"):
            warnings.append("Phone number not found")
        if not resume.get("name"):
            warnings.append("Name could not be extracted")
        if not resume.get("skills"):
            warnings.append("No skills detected")
        if resume.get("experience_years", 0) == 0:
            warnings.append("No experience duration found — may be a fresher or unparseable")
        if resume.get("experience_years", 0) > 50:
            errors.append("Experience years value is unrealistically high")
        if len(resume.get("raw_content", "")) < 100:
            warnings.append("Resume content is very short — may be incomplete")

        completeness = self._calculate_completeness(resume)

        return {
            "resume_id": resume_id,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "completeness_score": completeness,
            "quality_grade": self._quality_grade(completeness, errors, warnings),
        }

    # ------------------------------------------------------------------ #
    # Job matching                                                         #
    # ------------------------------------------------------------------ #

    def compare_resume_to_job(
        self, resume_id: str, job_requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Compare a resume against job requirements.

        Scoring:
          - Skill match  60 %  (with bonus for nice-to-have skills)
          - Experience   40 %  (capped at 100; extra exp gives small bonus)
          - Education    bonus up to +5 points on final score
        """
        resume = self.get_parsed_resume(resume_id)
        if not resume:
            return {"match_percentage": 0, "errors": ["Resume not found"]}

        resume_skills: Set[str] = set(s.lower() for s in resume.get("skills", []))
        required_skills: Set[str] = set(s.lower() for s in job_requirements.get("required_skills", []))
        nice_to_have: Set[str]    = set(s.lower() for s in job_requirements.get("nice_to_have_skills", []))

        resume_exp   = float(resume.get("experience_years", 0))
        required_exp = float(job_requirements.get("required_experience_years", 0))
        min_edu      = job_requirements.get("min_education_level", 0)  # 0–4 scale

        # --- Skill score ---
        if required_skills:
            matched_required  = resume_skills & required_skills
            matched_nice      = resume_skills & nice_to_have
            skill_score = (len(matched_required) / len(required_skills)) * 100
            # Nice-to-have bonus (up to 10 extra points)
            if nice_to_have:
                skill_score = min(100, skill_score + (len(matched_nice) / len(nice_to_have)) * 10)
        else:
            matched_required  = set()
            matched_nice      = set()
            skill_score = 100.0

        # --- Experience score ---
        if required_exp > 0:
            if resume_exp >= required_exp:
                exp_score = min(100, 100 + (resume_exp - required_exp) * 2)  # small bonus for extra exp
            else:
                exp_score = (resume_exp / required_exp) * 100
        else:
            exp_score = 100.0

        # --- Education bonus ---
        edu_level   = resume.get("education_level", 0)
        edu_bonus   = 5 if edu_level >= min_edu and min_edu > 0 else 0

        # --- Final weighted score ---
        overall = min(100, skill_score * 0.60 + exp_score * 0.40 + edu_bonus)

        return {
            "resume_id":               resume_id,
            "job_id":                  job_requirements.get("job_id", ""),
            "match_percentage":        round(overall, 2),
            "skill_score":             round(skill_score, 2),
            "experience_score":        round(exp_score, 2),
            "education_bonus":         edu_bonus,
            "matched_required_skills": sorted(matched_required),
            "matched_nice_to_have":    sorted(matched_nice),
            "missing_required_skills": sorted(required_skills - resume_skills),
            "experience_fit":          resume_exp >= required_exp,
            "education_fit":           edu_level >= min_edu,
        }

    # ------------------------------------------------------------------ #
    # Search                                                               #
    # ------------------------------------------------------------------ #

    def search_resumes(self, query: str, field: str = "all") -> List[Dict]:
        """Search parsed resumes by name, email, skill, education, or company."""
        query_lower = query.lower()
        results = []

        for resume in self.parsed_resumes.values():
            if field in ("all", "name") and query_lower in resume.get("name", "").lower():
                results.append(resume); continue
            if field in ("all", "email") and query_lower in resume.get("email", "").lower():
                results.append(resume); continue
            if field in ("all", "skills") and any(query_lower in s.lower() for s in resume.get("skills", [])):
                results.append(resume); continue
            if field in ("all", "education") and any(query_lower in e.lower() for e in resume.get("education", [])):
                results.append(resume); continue
            if field in ("all", "company") and any(query_lower in c.lower() for c in resume.get("previous_companies", [])):
                results.append(resume); continue

        logger.info(f"Search found {len(results)} resumes for query: '{query}' (field={field})")
        return results

    # ------------------------------------------------------------------ #
    # Server status                                                        #
    # ------------------------------------------------------------------ #

    def get_server_status(self) -> Dict[str, Any]:
        """Return server statistics."""
        total = len(self.parsed_resumes)
        avg_completeness = 0.0
        if total:
            avg_completeness = sum(
                r.get("completeness_score", 0) for r in self.parsed_resumes.values()
            ) / total

        return {
            "server_name":          self.server_name,
            "total_parsed_resumes": total,
            "avg_completeness":     round(avg_completeness, 1),
            "last_activity":        datetime.now().isoformat(),
        }

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _extract_information(self, text: str) -> Dict[str, Any]:
        """Extract all structured fields from raw resume text."""
        text_lower = text.lower()

        data: Dict[str, Any] = {
            "name":               self._extract_name(text),
            "email":              "",
            "phone":              "",
            "linkedin":           "",
            "github":             "",
            "experience_years":   0.0,
            "skills":             [],
            "skill_groups":       {},
            "education":          [],
            "education_level":    0,
            "previous_companies": [],
            "completeness_score": 0.0,
        }

        # Email
        m = _EMAIL_RE.search(text)
        if m:
            data["email"] = m.group().lower()

        # Phone
        m = _PHONE_RE.search(text)
        if m:
            data["phone"] = m.group().strip()

        # LinkedIn / GitHub
        m = _LINKEDIN_RE.search(text)
        if m:
            data["linkedin"] = f"linkedin.com/in/{m.group(1)}"
        m = _GITHUB_RE.search(text)
        if m:
            data["github"] = f"github.com/{m.group(1)}"

        # Experience years — try explicit "N years" first, then "since YYYY"
        data["experience_years"] = self._extract_experience(text_lower)

        # Skills with grouping
        found_skills, skill_groups = self._extract_skills(text_lower)
        data["skills"]       = found_skills
        data["skill_groups"] = skill_groups

        # Education — detect all levels, keep highest
        found_edu, max_level = self._extract_education(text_lower)
        data["education"]       = found_edu
        data["education_level"] = max_level

        # Companies
        data["previous_companies"] = self._extract_companies(text)

        # Completeness
        data["completeness_score"] = self._calculate_completeness(data)

        return data

    def _extract_name(self, text: str) -> str:
        """Attempt to pull the candidate's name from the top of the resume."""
        m = _NAME_RE.search(text)
        return m.group(1).strip() if m else ""

    def _extract_experience(self, text_lower: str) -> float:
        """Parse experience years from text. Falls back to 'since YYYY' calculation."""
        m = _EXP_RE.search(text_lower)
        if m:
            return min(float(m.group(1)), 50.0)

        # "Since 2018" or "from 2015"
        m = _EXP_SINCE_RE.search(text_lower)
        if m:
            years = datetime.now().year - int(m.group(1))
            return max(0.0, min(float(years), 50.0))

        return 0.0

    def _extract_skills(self, text_lower: str) -> tuple:
        """Return (flat skill list, grouped skill dict)."""
        found: List[str] = []
        groups: Dict[str, List[str]] = {}
        for group_name, skills in SKILL_GROUPS.items():
            matched = [s for s in skills if s in text_lower]
            if matched:
                groups[group_name] = matched
                found.extend(matched)
        return found, groups

    def _extract_education(self, text_lower: str) -> tuple:
        """Return (list of detected degree keywords, highest level int)."""
        found: List[str] = []
        max_level = 0
        for keyword, level in EDUCATION_LEVELS.items():
            if keyword in text_lower:
                found.append(keyword)
                if level > max_level:
                    max_level = level
        return found, max_level

    def _extract_companies(self, text: str) -> List[str]:
        """Extract previous company names heuristically."""
        matches = _COMPANY_RE.findall(text)
        companies = list({c.strip() for c in matches if len(c.strip()) > 2})
        return companies[:10]  # cap to avoid noise

    def _calculate_completeness(self, resume: Dict) -> float:
        """
        Calculate completeness score 0–100.
        Weighted: email 25, name 20, skills 20, experience 15, phone 10, education 10.
        """
        score = 0.0
        if resume.get("email"):         score += 25
        if resume.get("name"):          score += 20
        if resume.get("skills"):        score += 20
        if resume.get("experience_years", 0) > 0: score += 15
        if resume.get("phone"):         score += 10
        if resume.get("education"):     score += 10
        return round(score, 1)

    def _quality_grade(self, completeness: float, errors: List, warnings: List) -> str:
        """Return A/B/C/D/F grade based on completeness and issues."""
        if errors:
            return "F"
        if completeness >= 90 and len(warnings) == 0:
            return "A"
        if completeness >= 75:
            return "B"
        if completeness >= 50:
            return "C"
        if completeness >= 25:
            return "D"
        return "F"


# Global singleton
_resume_parser_mcp: Optional[ResumeParserMCP] = None


def get_resume_parser_mcp() -> ResumeParserMCP:
    """Get or create global Resume Parser MCP instance."""
    global _resume_parser_mcp
    if _resume_parser_mcp is None:
        _resume_parser_mcp = ResumeParserMCP()
    return _resume_parser_mcp
