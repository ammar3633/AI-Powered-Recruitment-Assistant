# Architecture & Design Documentation

## System Overview

The AI-Powered Recruitment Assistant is built on a distributed, multi-agent architecture designed to automate the entire recruitment pipeline. The system uses agent-to-agent communication patterns for asynchronous workflow execution.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        UI Layer (Streamlit)                      │
│  ┌─────────────┬──────────────────┬──────────────┬────────────┐  │
│  │  Dashboard  │ Screening Portal │Interview Sch.│  Ranking   │  │
│  └─────────────┴──────────────────┴──────────────┴────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                           │
│              (RecruitmentOrchestrator)                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                  Agent Layer (Multi-Agent System)                │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │   Resume     │   Job        │ Interview    │ Candidate    │  │
│  │ Screening    │  Matching    │ Coordination │  Ranking     │  │
│  │   Agent      │   Agent      │   Agent      │   Agent      │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                 ↑↓                               │
│                          Message Broker                          │
│                    (Agent Communication Hub)                     │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                 MCP Servers Layer (Data Layer)                   │
│  ┌──────────────┬──────────────┬──────────────┐                 │
│  │  ATS MCP     │ Calendar MCP │ Resume Parser│                 │
│  │  (Candidates)│ (Interviews) │  MCP         │                 │
│  └──────────────┴──────────────┴──────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                   Data Models & Database                          │
│  (Candidate, Resume, Job, Interview, Match, Ranking)            │
└──────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. UI Layer (Streamlit)

**Purpose**: Provide intuitive interfaces for recruiters and hiring managers

**Components**:
- **Dashboard** (`dashboard.py`): Main overview with metrics and pipeline visualization
- **Screening Portal** (`screening_portal.py`): Resume submission and candidate evaluation
- **Interview Scheduler** (`interview_scheduler.py`): Interview management and scheduling
- **Ranking Dashboard**: Candidate comparison and ranking visualization

**Key Features**:
- Real-time metrics and updates
- Interactive forms for data input
- Status tracking and filtering
- Export capabilities

### 2. Orchestration Layer

**RecruitmentOrchestrator** (`orchestrator.py`)

Manages the entire workflow and coordinates between agents:

```python
orchestrator.submit_resume()
    ↓
Resume Screening Agent
    ↓ (if passes)
Job Matching Agent
    ↓ (if matches)
Interview Coordination Agent
    ↓
Candidate Ranking Agent
```

**Key Methods**:
- `submit_resume()`: Entry point for resume processing
- `create_job_posting()`: Create new job positions
- `rank_candidates_for_job()`: Rank candidates for a job
- `get_system_status()`: Retrieve system metrics

### 3. Agent Layer (Multi-Agent System)

#### 3.1 Resume Screening Agent
**File**: `agents/resume_screening_agent.py`

**Responsibilities**:
- Parse resume content
- Extract candidate information
- Validate resume quality
- Calculate screening score
- Determine initial qualification

**Scoring Algorithm**:
```
Score = (Completeness × 0.4) + (Skills × 0.3) + (Experience × 0.2) + (No Errors × 0.1)
```

**Output**: Passes screening if Score ≥ 0.6

**Communication**:
- Receives: None
- Sends: `resume_submission` to Job Matching Agent

#### 3.2 Job Matching Agent
**File**: `agents/job_matching_agent.py`

**Responsibilities**:
- Analyze candidate skills vs job requirements
- Calculate skill match percentage
- Assess experience fit
- Generate match reasoning
- Route to ranking agent

**Matching Algorithm**:
```
Match % = (Skill Match × 0.6) + (Experience Match × 0.4) × 100
```

**Output**: Routes candidates with Match % ≥ 65% to Ranking Agent

**Communication**:
- Receives: `resume_submission` from Resume Screening Agent
- Sends: `match_result` to Candidate Ranking Agent

#### 3.3 Interview Coordination Agent
**File**: `agents/interview_coordination_agent.py`

**Responsibilities**:
- Check interviewer availability
- Schedule interviews
- Manage time slots
- Handle rescheduling
- Record interview feedback

**Features**:
- Automatic interviewer assignment
- Availability-based scheduling
- Meeting link generation
- Feedback recording

**Communication**:
- Receives: `ranking_request` from Ranking Agent
- Sends: `interview_feedback` to Ranking Agent

#### 3.4 Candidate Ranking Agent
**File**: `agents/candidate_ranking_agent.py`

**Responsibilities**:
- Aggregate multiple scores
- Calculate final ranking
- Generate recommendations
- Produce ranking reports

**Ranking Algorithm**:
```
Final Score = (Screening Score × 0.3) + (Match Score × 0.4) + (Interview Score × 0.3)
Recommendation:
  - Score ≥ 80: STRONG_RECOMMEND
  - Score ≥ 65: RECOMMEND
  - Score ≥ 50: CONSIDER
  - Score < 50: NOT_RECOMMENDED
```

**Communication**:
- Receives: `match_result` from Job Matching Agent
- Receives: `interview_feedback` from Interview Coordination Agent
- Sends: Final rankings to orchestrator

### 4. Message Broker (Agent Communication)

**File**: `core/communication.py`

**Architecture**: Message Queue Pattern

**Message Types**:
```python
enum MessageType:
    RESUME_SUBMISSION
    SCREENING_RESULT
    JOB_MATCH_REQUEST
    MATCH_RESULT
    RANKING_REQUEST
    RANKING_RESULT
    INTERVIEW_SCHEDULE_REQUEST
    INTERVIEW_SCHEDULED
    INTERVIEW_FEEDBACK
    STATUS_UPDATE
```

**Message Structure**:
```python
{
    "sender_agent": str,
    "recipient_agent": str,
    "message_type": MessageType,
    "payload": Dict,
    "timestamp": datetime,
    "message_id": str,
    "priority": int,
    "requires_response": bool
}
```

**Features**:
- FIFO queue management
- Priority-based processing
- Message history tracking
- Response handling
- Error management

### 5. MCP Servers Layer

#### 5.1 ATS MCP (Applicant Tracking System)
**File**: `mcp_servers/ats_mcp.py`

**Data Structures**:
- Candidates: Profile, contact, skills, experience
- Job Postings: Title, requirements, department, location
- Applications: Status tracking, history

**Key Operations**:
- CRUD for candidates and jobs
- Application lifecycle management
- Search and filtering
- Status tracking

**API Methods**:
```python
create_candidate(data) → candidate_id
get_candidate(id) → candidate_data
update_candidate(id, updates) → bool
list_candidates(filters) → List[Candidate]
create_job_posting(data) → job_id
get_job_posting(id) → job_data
create_application(candidate_id, job_id) → app_id
```

#### 5.2 Calendar MCP
**File**: `mcp_servers/calendar_mcp.py`

**Functionality**:
- Interview scheduling
- Availability management
- Time slot allocation
- Meeting link generation

**Key Operations**:
- Schedule/reschedule/cancel interviews
- Manage interviewer availability
- Find available slots
- Track interview status

**API Methods**:
```python
schedule_interview(data) → event_id
add_availability(interviewer_id, slot) → bool
check_availability(id, time, duration) → bool
find_available_slots(id, duration) → List[Slot]
get_interviews_for_candidate(id) → List[Interview]
```

#### 5.3 Resume Parser MCP
**File**: `mcp_servers/resume_parser_mcp.py`

**Capabilities**:
- Text extraction from resumes
- Information parsing (skills, education, experience)
- Resume validation
- Job-resume comparison

**Extraction Patterns**:
- Email: Regex pattern matching
- Phone: Pattern matching for various formats
- Skills: Keyword matching from predefined list
- Experience: Duration extraction
- Education: Degree keyword detection

**Key Operations**:
- Parse resume text
- Extract candidate profile
- Validate resume quality
- Compare to job requirements

**API Methods**:
```python
parse_resume(content, filename) → resume_id
extract_candidate_profile(resume_id) → profile
validate_resume(resume_id) → validation_report
compare_resume_to_job(resume_id, requirements) → match_result
```

### 6. Data Layer

**File**: `database/models.py`

**Core Models**:

```python
@dataclass
class Resume:
    id, candidate_id, name, email, phone
    experience_years, skills, education
    previous_companies, raw_text, parsed_at

@dataclass
class JobPosting:
    id, title, description
    required_skills, required_experience_years
    department, salary_range, location, posted_date

@dataclass
class Candidate:
    id, name, email, phone
    resume, status, screening_score
    match_score, ranking_score, notes

@dataclass
class Interview:
    id, candidate_id, job_id
    scheduled_time, interviewer, interview_type
    status, meeting_link, feedback, rating

@dataclass
class MatchResult:
    candidate_id, job_id, match_percentage
    matched_skills, missing_skills
    experience_fit, reasoning

@dataclass
class RankingResult:
    candidate_id, job_id, rank, final_score
    screening_score, match_score, interview_score
    recommendation
```

## Workflow Sequence

### Complete Recruitment Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. RESUME SUBMISSION                                             │
│    User uploads resume via UI                                   │
│    → Sent to Resume Screening Agent                             │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. RESUME SCREENING                                              │
│    - Parse resume (Resume Parser MCP)                           │
│    - Extract information (skills, experience)                   │
│    - Validate quality                                           │
│    - Calculate screening score                                  │
│    - Create candidate profile (ATS MCP)                         │
└─────────────────────────────────────────────────────────────────┘
                    ↓ (if passes)
┌─────────────────────────────────────────────────────────────────┐
│ 3. JOB MATCHING                                                   │
│    - Get open jobs (ATS MCP)                                    │
│    - Compare skills against requirements                        │
│    - Calculate match score                                      │
│    - Identify best matching position                            │
│    - Send to Ranking Agent                                      │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. CANDIDATE RANKING                                             │
│    - Receive match results                                      │
│    - Aggregate scores                                           │
│    - Generate initial ranking                                   │
│    - Request interview scheduling                               │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. INTERVIEW COORDINATION                                        │
│    - Check interviewer availability (Calendar MCP)              │
│    - Find suitable time slots                                   │
│    - Schedule interview                                         │
│    - Generate meeting link                                      │
│    - Send invitations                                           │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. INTERVIEW CONDUCTION                                          │
│    - Interviewer conducts interview                             │
│    - Records feedback and rating                                │
│    - Sends results to Ranking Agent                             │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. FINAL RANKING & RECOMMENDATION                                │
│    - Update ranking with interview score                        │
│    - Generate final recommendations                             │
│    - Export ranking report                                      │
│    - Update candidate status                                    │
└─────────────────────────────────────────────────────────────────┘
```

## Design Patterns Used

### 1. Agent Pattern
- Autonomous agents with independent state
- Encapsulated responsibilities
- Message-driven communication

### 2. Message Queue Pattern
- Asynchronous communication
- Decoupled systems
- Priority-based processing

### 3. Repository Pattern
- MCP servers act as repositories
- Centralized data access
- Abstraction of data storage

### 4. Factory Pattern
- Singleton instances for MCP servers
- Global orchestrator instance
- Message broker creation

### 5. Strategy Pattern
- Different scoring strategies
- Pluggable algorithms
- Configurable thresholds

## Configuration Management

**Config File**: `config.py`

**Configuration Areas**:
- Agent thresholds and weights
- MCP server settings
- Database connection
- Logging configuration
- Scoring algorithms
- UI preferences

**Loading**:
```python
from config import get_config
config = get_config()
agent_config = config.get_agent_config("resume_screening")
```

## Error Handling & Resilience

**Error Handling Strategy**:
- Try-catch blocks in critical sections
- Graceful degradation
- Error logging and reporting
- Fallback mechanisms

**Resilience Features**:
- Message retry logic
- Timeout handling
- Graceful shutdown
- State persistence

## Performance Considerations

**Optimization Areas**:
- Message batching
- Caching frequently accessed data
- Async operations
- Database query optimization

**Scalability**:
- Horizontal scaling of agents
- Message broker clustering (future)
- Database indexing
- Load balancing (future)

## Security Considerations

**Implemented**:
- Logging without sensitive data
- Input validation
- Error messages without leaking internals

**Recommended (Production)**:
- Authentication/Authorization
- Data encryption at rest
- TLS for communication
- Audit logging
- Role-based access control

## Testing Strategy

**Test Types**:
- Unit tests for individual agents
- Integration tests for workflows
- System tests for end-to-end scenarios

**Test File**: `example_usage.py`
- Demonstrates system usage
- Validates workflows
- Provides test cases

## Deployment Architecture

**Current**: Single-instance in-memory
**Future Options**:
- Containerized (Docker)
- Kubernetes orchestration
- Distributed deployment
- Message queue (RabbitMQ/Kafka)
- Database backend (PostgreSQL)

## Monitoring & Observability

**Logging**:
- Structured logging at each stage
- Agent activity tracking
- Message broker metrics

**Metrics**:
- Processing times
- Success/failure rates
- Queue depths
- System utilization

**Status Endpoints**:
- System status API
- Agent status
- MCP server status
- Message broker statistics

---

**Version**: 1.0.0
**Last Updated**: January 2024
