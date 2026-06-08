Architecture & Design Documentation1.

System Overview
The AI-Powered Recruitment Assistant leverages a decentralized, multi-agent framework designed to fully automate the end-to-end hiring pipeline. By employing asynchronous agent-to-agent communication patterns, the system decouples complex workflows, allowing for highly scalable and independent processing tasks.2. Structural Blueprint

┌─────────────────────────────────────────────────────────────────┐
│                        User Interface (Streamlit)                │
│  ┌─────────────┬──────────────────┬──────────────┬────────────┐  │
│  │ Metrics Hub │ Screening Portal │Interview Hub │ Leaderboard│  │
│  └─────────────┴──────────────────┴──────────────┴────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestration Layer                           │
│                 (RecruitmentOrchestrator)                        │
└─────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                   Collaborative Agent Cluster                    │
│  ┌──────────────┬──────────────┬──────────────┬──────────────┐  │
│  │   Vetting    │   Position   │  Scheduler   │  Evaluation  │  │
│  │    Agent     │ Match Agent  │    Agent     │    Agent     │  │
│  └──────────────┴──────────────┴──────────────┴──────────────┘  │
│                                 ↑↓                               │
│                         Central Message Bus                      │
│                    (Agent Communication Hub)                     │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                 MCP Servers (Data Access Layer)                  │
│  ┌──────────────┬──────────────┬──────────────┐                 │
│  │  ATS Engine  │ Calendar API │Extraction Engine               │
│  │ (Profiles)   │ (Schedules)  │ (Resume Sync)│                 │
│  └──────────────┴──────────────┴──────────────┘                 │
└──────────────────────────────────────────────────────────────────┘
                           ↓
┌──────────────────────────────────────────────────────────────────┐
│                      Persistent Storage                          │
│     (Relational Schemas & Domain Entity Models)                  │
└──────────────────────────────────────────────────────────────────┘
3. Component Deep Dive
3.1 UI Layer (Streamlit)
Core Function: Serves as the interactive interface for talent acquisition teams and hiring managers.

Metrics Hub (dashboard.py): Consolidates operational health parameters, pipeline funnels, and core recruitment metrics.

Screening Portal (screening_portal.py): Manages inbound application processing, file ingestion, and initial profile assessments.

Interview Hub (interview_scheduler.py): Controls coordinator availability, dynamic calendar updates, and panel synchronization.

Leaderboard Dashboard: Visually correlates and contrasts candidate matrix scores.

Key Capabilities: Real-time reactive UI updates, multi-criteria filtering, data persistence exports, and dynamic data ingestion forms.

3.2 Orchestration Layer
RecruitmentOrchestrator (orchestrator.py)
Acts as the central transaction coordinator that routes processes across the agent collective.

[Inbound CV] ──> Vetting Agent ──(Pass)──> Match Agent ──(Match Found)──> Scheduler Agent ──> Evaluation Agent
submit_resume(): Ingestion entry point for unparsed resumes.

create_job_posting(): Provisions new requisitions within the data tier.

rank_candidates_for_job(): Programmatically triggers aggregate scoring routines across candidate pools.

get_system_status(): Queries system health statistics and agent telemetry.

3.3 Collaborative Agent ClusterA. Vetting AgentModule: agents/resume_screening_agent.pyRole: Content normalization, profile entity extraction, missing metadata validation, and initial quality checks.
Formula:$$\text{Score} = (\text{Completeness} \times 0.4) + (\text{Skills} \times 0.3) + (\text{Experience} \times 0.2) + (\text{Data Integrity} \times 0.1)$$Gatekeeper
Logic: Progresses candidates to the next stage if $\text{Score} \ge 0.6$.Messaging: Dispatches a resume_submission payload to the Position Match Agent upon successful verification.

B. Position Match AgentModule: agents/job_matching_agent.pyRole: Maps extracted candidate capabilities against open requisition requirements to evaluate professional experience tenure and skill depth.

Formula:$$\text{Match \%} = \left( (\text{Skill Alignment} \times 0.6) + (\text{Tenure Alignment} \times 0.4) \right) \times 100$$Gatekeeper
Logic: Isolates profiles with a $\text{Match \%} \ge 65\%$ and hands them off to the Evaluation Agent.
Messaging: Translates assessments into a match_result message destined for the Evaluation Agent.
C. Scheduler AgentModule: agents/interview_coordination_agent.pyRole: Negotiates inter-calendar availability, sets aside time allocations, modifies conflicting appointments, and updates evaluation matrices with real-time feedback data.
Capability Set: Automated panelist routing, programmatic video link generation, and structured panel scoring inputs.Messaging: Pulls ranking_request notifications and issues interview_feedback records.
D. Evaluation AgentModule: agents/candidate_ranking_agent.pyRole: Aggregates disparate scoring vectors into a unified index to deliver structured reports and tactical hiring recommendations.Formula:$$\text{Composite Score} = (\text{Vetting Score} \times 0.3) + (\text{Match Score} \times 0.4) + (\text{Interview Score} \times 0.3)$$
4. Message Broker (Inter-Agent Communications)
Module: core/communication.py

Structural Pattern: Message Queue Architecture

Python
# System Event Spectrum
class MessageType(Enum):
    RESUME_SUBMISSION           = "RESUME_SUBMISSION"
    SCREENING_RESULT            = "SCREENING_RESULT"
    JOB_MATCH_REQUEST           = "JOB_MATCH_REQUEST"
    MATCH_RESULT                = "MATCH_RESULT"
    RANKING_REQUEST             = "RANKING_REQUEST"
    RANKING_RESULT              = "RANKING_RESULT"
    INTERVIEW_SCHEDULE_REQUEST  = "INTERVIEW_SCHEDULE_REQUEST"
    INTERVIEW_SCHEDULED         = "INTERVIEW_SCHEDULED"
    INTERVIEW_FEEDBACK          = "INTERVIEW_FEEDBACK"
    STATUS_UPDATE               = "STATUS_UPDATE"
Python
# Event Envelope Layout
@dataclass
class AgentMessage:
    sender_agent: str
    recipient_agent: str
    message_type: MessageType
    payload: dict
    timestamp: datetime
    message_id: str
    priority: int
    requires_response: bool
Broker Capabilities: Strict FIFO processing, deterministic priority queues, conversation history tracking, and native exception isolation.

5. Model Context Protocol (MCP) Infrastructure
5.1 ATS Engine (mcp_servers/ats_mcp.py)
Encapsulates candidate identities, open job requirements, and structural application lifecycles.

create_candidate(data) -> candidate_id

get_candidate(id) -> candidate_data

list_candidates(filters) -> List[Candidate]

create_job_posting(data) -> job_id

5.2 Calendar API (mcp_servers/calendar_mcp.py)
Handles time-slot selection, interviewer availability configurations, and programmatic event orchestration.

schedule_interview(data) -> event_id

check_availability(id, time, duration) -> bool

find_available_slots(id, duration) -> List[Slot]

5.3 Extraction Engine (mcp_servers/resume_parser_mcp.py)
Converts raw file streams into structured, typed data objects via regex patterns and heuristic keyword indices.

parse_resume(content, filename) -> resume_id

validate_resume(resume_id) -> validation_report

compare_resume_to_job(resume_id, requirements) -> match_result

6. Architecture & System Patterns
Agent Architecture: Autonomous entities handling processing blocks via isolated states and message passing.

Message-Driven Architecture: Decoupled asynchronous messaging that protects system stability from single point-of-failure errors.

Repository Design: MCP abstractions act as data access interfaces, separating data store interactions from the core application logic.

Strategy Implementation: Interchangeable scoring mechanics and custom threshold settings that can change at runtime.

7. Operations & Security Safeguards
Error Abstraction & Resiliency
Structured try-except blocks protect all runtime-critical operations.

Configurable exponential backoff retry cycles on the message queue manage transient drops.

Graceful state persistence ensures data isn't lost during abrupt system restarts.

Performance Optimization
Asynchronous network calling and local caching prevent unnecessary database hits on frequently used datasets.

Data mutations are processed via optimized batch queues to prevent connection bottlenecks.

Security Stance
Ensures strict separation of internal logs from Personal Identifiable Information (PII).

Applies deep data validation at boundaries to protect against payload injections.

Production Target Note: Ensure transit encryption (TLS) is active and hook into a centralized Role-Based Access Control (RBAC) model.
