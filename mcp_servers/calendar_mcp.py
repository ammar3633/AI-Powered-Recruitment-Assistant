"""
Calendar MCP Server
Manages interview scheduling and calendar operations
Mohammed Ammar
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

# Business hours (24h format)
BUSINESS_HOUR_START = 9   # 9:00 AM
BUSINESS_HOUR_END   = 18  # 6:00 PM

# Slot generation interval in minutes
SLOT_INTERVAL = 30

# How many days ahead to auto-generate availability if none exists
AUTO_AVAILABILITY_DAYS = 7


class CalendarMCP:
    """
    MCP Server for calendar operations.

    Improvements over original:
    - Conflict detection: blocks double-booking the same interviewer
    - Auto-availability: generates default business-hour slots when none exist
    - find_available_slots filters out already-booked times
    - list_scheduled_interviews accepts 'all' as status to return everything
    - reschedule stores previous time in history for audit trail
    - get_server_status includes per-status breakdown and busiest interviewer
    - All datetime parsing centralised in one helper with consistent error handling
    """

    def __init__(self):
        self.scheduled_events: Dict[str, Dict] = {}
        self.availabilities: Dict[str, List[Dict]] = {}
        self.server_name = "Calendar MCP"
        logger.info("Calendar MCP Server initialised")

    # ── Scheduling ────────────────────────────────────────────────────────────

    def schedule_interview(self, interview_data: Dict[str, Any]) -> str:
        """
        Schedule an interview after checking for conflicts.
        Raises ValueError if the interviewer is already booked at that time.
        Returns the new event ID.
        """
        interviewer_id  = interview_data.get("interviewer", "")
        scheduled_time  = interview_data.get("scheduled_time", "")
        duration        = interview_data.get("duration_minutes", 60)

        # Conflict check
        if interviewer_id and scheduled_time:
            conflict = self._detect_conflict(interviewer_id, scheduled_time, duration)
            if conflict:
                raise ValueError(
                    f"Interviewer {interviewer_id} is already booked at {scheduled_time} "
                    f"(conflicts with event {conflict})"
                )

        event_id = str(uuid.uuid4())
        self.scheduled_events[event_id] = {
            "id": event_id,
            "created_at": datetime.now().isoformat(),
            "status": "scheduled",
            "duration_minutes": duration,
            "reschedule_history": [],
            **interview_data,
        }

        logger.info(
            f"Scheduled interview {event_id} — "
            f"{interview_data.get('candidate_name')} at {scheduled_time}"
        )
        return event_id

    def get_interview(self, event_id: str) -> Optional[Dict]:
        """Get interview details by ID. Returns None if not found."""
        event = self.scheduled_events.get(event_id)
        if not event:
            logger.warning(f"Interview not found: {event_id}")
        return event

    def update_interview(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Apply partial updates to an existing interview record."""
        if event_id not in self.scheduled_events:
            logger.warning(f"Update failed — interview not found: {event_id}")
            return False

        self.scheduled_events[event_id].update(updates)
        self.scheduled_events[event_id]["updated_at"] = datetime.now().isoformat()
        logger.info(f"Updated interview {event_id}: {list(updates.keys())}")
        return True

    def cancel_interview(self, event_id: str, reason: str = "") -> bool:
        """
        Cancel an interview. Cancelled events are retained for audit purposes
        but excluded from availability conflict checks.
        """
        if event_id not in self.scheduled_events:
            logger.warning(f"Cancel failed — interview not found: {event_id}")
            return False

        self.scheduled_events[event_id].update({
            "status": "cancelled",
            "cancellation_reason": reason or "No reason provided",
            "cancelled_at": datetime.now().isoformat(),
        })
        logger.info(f"Cancelled interview {event_id} — reason: {reason or 'not provided'}")
        return True

    def reschedule_interview(
        self, event_id: str, new_time: str, new_interviewer: Optional[str] = None
    ) -> bool:
        """
        Reschedule an interview to a new time.
        Stores the old time in reschedule_history for audit trail.
        Runs conflict check for the new time before applying.
        """
        if event_id not in self.scheduled_events:
            logger.warning(f"Reschedule failed — interview not found: {event_id}")
            return False

        event       = self.scheduled_events[event_id]
        interviewer = new_interviewer or event.get("interviewer", "")
        duration    = event.get("duration_minutes", 60)

        # Conflict check for new slot (exclude this event from check)
        conflict = self._detect_conflict(interviewer, new_time, duration, exclude_event_id=event_id)
        if conflict:
            raise ValueError(
                f"Cannot reschedule: {interviewer} is already booked at {new_time} "
                f"(conflicts with event {conflict})"
            )

        # Preserve history
        history_entry = {
            "previous_time": event.get("scheduled_time"),
            "previous_interviewer": event.get("interviewer"),
            "rescheduled_at": datetime.now().isoformat(),
        }
        event.setdefault("reschedule_history", []).append(history_entry)

        event["scheduled_time"] = new_time
        event["status"]         = "rescheduled"
        event["updated_at"]     = datetime.now().isoformat()
        if new_interviewer:
            event["interviewer"] = new_interviewer

        logger.info(f"Rescheduled interview {event_id} → {new_time}")
        return True

    # ── Availability ──────────────────────────────────────────────────────────

    def add_availability(self, interviewer_id: str, availability_slot: Dict[str, str]) -> bool:
        """
        Add an availability window for an interviewer.
        Slot must have 'start' and 'end' ISO datetime strings.
        Overlapping slots are merged to avoid duplicate free-time entries.
        """
        if "start" not in availability_slot or "end" not in availability_slot:
            logger.error("Availability slot missing 'start' or 'end' keys")
            return False

        start = self._parse_dt(availability_slot["start"])
        end   = self._parse_dt(availability_slot["end"])
        if not start or not end or end <= start:
            logger.error(f"Invalid availability window: {availability_slot}")
            return False

        slots = self.availabilities.setdefault(interviewer_id, [])

        # Simple overlap merge: if new slot overlaps an existing one, extend it
        for existing in slots:
            ex_start = self._parse_dt(existing["start"])
            ex_end   = self._parse_dt(existing["end"])
            if ex_start and ex_end and not (end <= ex_start or start >= ex_end):
                existing["start"] = min(ex_start, start).isoformat()
                existing["end"]   = max(ex_end, end).isoformat()
                logger.info(f"Merged overlapping availability for {interviewer_id}")
                return True

        slots.append({"start": start.isoformat(), "end": end.isoformat()})
        logger.info(f"Added availability for {interviewer_id}: {start} → {end}")
        return True

    def get_availability(self, interviewer_id: str) -> List[Dict]:
        """Return availability windows for an interviewer."""
        slots = self.availabilities.get(interviewer_id)
        if not slots:
            # Auto-generate default business-hour availability for the next N days
            slots = self._generate_default_availability(interviewer_id)
        return slots

    def check_availability(
        self, interviewer_id: str, start_time: str, duration_minutes: int = 60
    ) -> bool:
        """
        Check whether an interviewer is free at start_time for duration_minutes.
        Returns False if there is any conflicting booked event.
        """
        start = self._parse_dt(start_time)
        if not start:
            return False
        end = start + timedelta(minutes=duration_minutes)

        # Must fall within an availability window
        in_window = False
        for slot in self.get_availability(interviewer_id):
            s = self._parse_dt(slot["start"])
            e = self._parse_dt(slot["end"])
            if s and e and s <= start and end <= e:
                in_window = True
                break

        if not in_window:
            return False

        # Must not conflict with a booked event
        return not self._detect_conflict(interviewer_id, start_time, duration_minutes)

    def find_available_slots(
        self, interviewer_id: str, duration_minutes: int = 60
    ) -> List[Dict]:
        """
        Return all free slots for an interviewer, excluding already-booked times.
        Slots are generated at SLOT_INTERVAL-minute intervals within availability windows.
        Only future slots are returned.
        """
        now = datetime.now()
        available = []

        for window in self.get_availability(interviewer_id):
            w_start = self._parse_dt(window["start"])
            w_end   = self._parse_dt(window["end"])
            if not w_start or not w_end:
                continue

            current = max(w_start, now)
            # Align to next SLOT_INTERVAL boundary
            remainder = current.minute % SLOT_INTERVAL
            if remainder:
                current += timedelta(minutes=SLOT_INTERVAL - remainder)
            current = current.replace(second=0, microsecond=0)

            while current + timedelta(minutes=duration_minutes) <= w_end:
                slot_end = current + timedelta(minutes=duration_minutes)
                conflict = self._detect_conflict(
                    interviewer_id, current.isoformat(), duration_minutes
                )
                if not conflict:
                    available.append({
                        "start": current.isoformat(),
                        "end": slot_end.isoformat(),
                    })
                current += timedelta(minutes=SLOT_INTERVAL)

        logger.info(
            f"Found {len(available)} free slots for {interviewer_id} "
            f"(duration: {duration_minutes}min)"
        )
        return available

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_scheduled_interviews(self, status: str = "scheduled") -> List[Dict]:
        """
        List interviews filtered by status.
        Pass status='all' to return every event regardless of status.
        Sorted by scheduled_time ascending.
        """
        if status == "all":
            interviews = list(self.scheduled_events.values())
        else:
            interviews = [
                e for e in self.scheduled_events.values()
                if e.get("status") == status
            ]

        interviews.sort(key=lambda x: x.get("scheduled_time", ""))
        logger.info(f"Listed {len(interviews)} interviews (status={status})")
        return interviews

    def get_interviews_for_candidate(self, candidate_id: str) -> List[Dict]:
        """Return all interviews for a candidate, sorted by scheduled_time."""
        results = [
            e for e in self.scheduled_events.values()
            if e.get("candidate_id") == candidate_id
        ]
        results.sort(key=lambda x: x.get("scheduled_time", ""))
        return results

    def get_interviews_for_interviewer(self, interviewer_id: str) -> List[Dict]:
        """Return all non-cancelled interviews for an interviewer."""
        results = [
            e for e in self.scheduled_events.values()
            if e.get("interviewer") == interviewer_id
            and e.get("status") != "cancelled"
        ]
        results.sort(key=lambda x: x.get("scheduled_time", ""))
        return results

    def get_server_status(self) -> Dict[str, Any]:
        """Return server health stats including per-status breakdown."""
        status_counts: Dict[str, int] = {}
        for event in self.scheduled_events.values():
            s = event.get("status", "unknown")
            status_counts[s] = status_counts.get(s, 0) + 1

        # Find busiest interviewer
        load: Dict[str, int] = {}
        for event in self.scheduled_events.values():
            if event.get("status") not in ("cancelled",):
                iid = event.get("interviewer", "unknown")
                load[iid] = load.get(iid, 0) + 1
        busiest = max(load, key=load.get) if load else None

        return {
            "server_name": self.server_name,
            "status": "online",
            "total_events": len(self.scheduled_events),
            "by_status": status_counts,
            "interviewers_with_availability": len(self.availabilities),
            "busiest_interviewer": busiest,
            "busiest_interviewer_load": load.get(busiest, 0) if busiest else 0,
            "last_activity": datetime.now().isoformat(),
        }

    # ── Private helpers ───────────────────────────────────────────────────────

    def _detect_conflict(
        self,
        interviewer_id: str,
        start_time: str,
        duration_minutes: int,
        exclude_event_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Check whether any active event overlaps the proposed slot for this interviewer.
        Returns the conflicting event_id, or None if the slot is free.
        """
        start = self._parse_dt(start_time)
        if not start:
            return None
        end = start + timedelta(minutes=duration_minutes)

        for eid, event in self.scheduled_events.items():
            if eid == exclude_event_id:
                continue
            if event.get("status") == "cancelled":
                continue
            if event.get("interviewer") != interviewer_id:
                continue

            ev_start = self._parse_dt(event.get("scheduled_time", ""))
            ev_duration = event.get("duration_minutes", 60)
            if not ev_start:
                continue
            ev_end = ev_start + timedelta(minutes=ev_duration)

            # Overlap: intervals (start, end) and (ev_start, ev_end) overlap
            # when start < ev_end AND end > ev_start
            if start < ev_end and end > ev_start:
                return eid

        return None

    def _generate_default_availability(self, interviewer_id: str) -> List[Dict]:
        """
        Auto-generate weekday business-hour availability for the next
        AUTO_AVAILABILITY_DAYS days if no availability has been set.
        Stored so subsequent calls reuse the same windows.
        """
        slots = []
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        for day_offset in range(AUTO_AVAILABILITY_DAYS):
            day = today + timedelta(days=day_offset)
            if day.weekday() >= 5:  # skip Saturday (5) and Sunday (6)
                continue
            slot = {
                "start": day.replace(hour=BUSINESS_HOUR_START).isoformat(),
                "end":   day.replace(hour=BUSINESS_HOUR_END).isoformat(),
            }
            slots.append(slot)

        self.availabilities[interviewer_id] = slots
        logger.info(
            f"Auto-generated {len(slots)} availability windows for {interviewer_id}"
        )
        return slots

    @staticmethod
    def _parse_dt(value: Any) -> Optional[datetime]:
        """Safely parse an ISO datetime string. Returns None on failure."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value))
        except (ValueError, TypeError) as e:
            logger.warning(f"Could not parse datetime '{value}': {e}")
            return None


# ── Singleton ─────────────────────────────────────────────────────────────────

_calendar_mcp: Optional[CalendarMCP] = None


def get_calendar_mcp() -> CalendarMCP:
    """Return the global CalendarMCP instance, creating it if necessary."""
    global _calendar_mcp
    if _calendar_mcp is None:
        _calendar_mcp = CalendarMCP()
    return _calendar_mcp
