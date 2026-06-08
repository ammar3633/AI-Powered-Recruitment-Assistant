"""
Configuration module for AI-Powered Recruitment Assistant
"""

import os
from dataclasses import dataclass
from typing import Dict, Any

# Environment variables
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8501))

# Agent configuration
AGENT_CONFIG = {
    "resume_screening": {
        "enabled": True,
        "threshold": 0.6,
        "description": "Screens resumes and evaluates candidate fit",
    },
    "job_matching": {
        "enabled": True,
        "threshold": 0.65,
        "description": "Matches candidates to job positions",
    },
    "interview_coordination": {
        "enabled": True,
        "duration_minutes": 60,
        "description": "Schedules and coordinates interviews",
    },
    "candidate_ranking": {
        "enabled": True,
        "weights": {
            "screening": 0.3,
            "matching": 0.4,
            "interview": 0.3,
        },
        "description": "Ranks candidates for a job position",
    },
}

# MCP Server configuration
MCP_SERVERS_CONFIG = {
    "ats_mcp": {
        "enabled": True,
        "name": "ATS MCP Server",
    },
    "calendar_mcp": {
        "enabled": True,
        "name": "Calendar MCP Server",
    },
    "resume_parser_mcp": {
        "enabled": True,
        "name": "Resume Parser MCP Server",
    },
}

DATABASE_CONFIG = {
    "type": "in_memory",  # Options: in_memory, sqlite, postgresql
    "path": "recruitment.db",  # For SQLite
    "connection_string": os.getenv("DATABASE_URL", ""),  # For PostgreSQL
}

# API configuration
API_CONFIG = {
    "base_url": "http://localhost:8501",
    "timeout": 30,
    "max_retries": 3,
}

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(funcName)s() - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": LOG_LEVEL,
            "formatter": "detailed",
            "filename": "recruitment_assistant.log",
        },
    },
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console", "file"],
    },
}

# Scoring weights
SCORING_WEIGHTS = {
    "resume_screening": {
        "completeness": 0.4,
        "skills": 0.3,
        "experience": 0.2,
        "no_errors": 0.1,
    },
    "job_matching": {
        "skills": 0.6,
        "experience": 0.4,
    },
    "candidate_ranking": {
        "screening": 0.3,
        "matching": 0.4,
        "interview": 0.3,
    },
}

# UI configuration
UI_CONFIG = {
    "theme": "light",  # Options: light, dark
    "max_candidates_per_page": 10,
    "max_jobs_per_page": 10,
    "enable_export": True,
}


@dataclass
class AppConfig:
    """Application configuration data class"""

    debug: bool = DEBUG
    log_level: str = LOG_LEVEL
    host: str = HOST
    port: int = PORT
    agent_config: Dict[str, Any] = None
    mcp_servers_config: Dict[str, Any] = None
    database_config: Dict[str, Any] = None
    api_config: Dict[str, Any] = None
    logging_config: Dict[str, Any] = None
    scoring_weights: Dict[str, Any] = None
    ui_config: Dict[str, Any] = None

    def __post_init__(self):
        self.agent_config = AGENT_CONFIG
        self.mcp_servers_config = MCP_SERVERS_CONFIG
        self.database_config = DATABASE_CONFIG
        self.api_config = API_CONFIG
        self.logging_config = LOGGING_CONFIG
        self.scoring_weights = SCORING_WEIGHTS
        self.ui_config = UI_CONFIG

    def get_agent_config(self, agent_type: str) -> Dict[str, Any]:
        """Get configuration for a specific agent"""
        return self.agent_config.get(agent_type, {})

    def get_mcp_config(self, mcp_name: str) -> Dict[str, Any]:
        """Get configuration for a specific MCP server"""
        return self.mcp_servers_config.get(mcp_name, {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            "debug": self.debug,
            "log_level": self.log_level,
            "host": self.host,
            "port": self.port,
            "agents": self.agent_config,
            "mcp_servers": self.mcp_servers_config,
            "database": self.database_config,
            "api": self.api_config,
            "scoring_weights": self.scoring_weights,
            "ui": self.ui_config,
        }


# Global configuration instance
_config: AppConfig = None


def get_config() -> AppConfig:
    """Get global configuration instance"""
    global _config
    if _config is None:
        _config = AppConfig()
    return _config
