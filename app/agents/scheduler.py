"""
Scheduler Agent

Builds:
  1. today_schedule  — time-blocked slots from NOW until sleep
  2. day_plan        — multi-day breakdown until deadline

Re-triggered whenever:
  - Planner first generates tasks
  - Progress agent sets reschedule_needed = True
  - User explicitly asks to reschedule / schedule
"""

import re
from datetime import datetime, timedelta, date
from app.state import StudentState


# ─────────────────────────────────────────────────────────────────────────────
# Time helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_time(raw: str) -> datetime | None:
    if not raw or str(raw).strip().lower() in ("no", "none", "n/a", ""):
        return None
    raw = str(raw).strip().upper().replace(".", ":").replace("-", ":")
    today = datetime.now().date()
    formats = ["%I%p", "%I:%M%p", "%I %p", "%H:%M", "%H"]
    raw_clean = raw.replace(" ", "")
    for fmt in formats:
        for candidate in (raw_clean, raw):
            try:
                t = datetime.strptime(candidate, fmt)
                return datetime.combine(today, t.time())
            except ValueError:
                continue
    return None


def _parse_range(raw: str) -> tuple[datetime | None, datetime | None]:
    if not raw or str(raw).strip().lower() in ("no", "none", ""):
        return None, None
    for sep in ("-", "to", "–"):
        if sep in str(raw).lower():
            parts = str(raw).lower().split(sep, 1)
            return _parse_time(parts[0].strip()), _parse_time(parts[1].strip())
    return None, None


def _fmt(dt: datetime) -> str:
    """Windows-safe 12-hour time format."""
    h = int(dt.strftime("%I"))
    m = dt.strftime("%M")
    period = dt.strftime("%p")
    return f"{h}:{m} {period}"


def _add(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)


def _deadline_days(deadline_str: str | None) -> int:
    """Parse deadline like '10 days', 'tomorrow', '3' into number of days."""
    if not deadline_str:
        return 7
    s = str(deadline_str).lower().strip()
    if "tomorrow" in s:
        return 1
    nums = re.findall(r"\d+", s)
    return int(nums[0]) if nums else 7


# ─────────────────────────────────────────────────────────────────────────────
# Blocked interval computation
# ─────────────────────────────────────────────────────────────────────────────

def _blocked_intervals(routine: dict, wake: datetime, sleep: datetime) -> list[tuple[datetime, datetime, str]]:
    blocked = []

    def add(start, end, label):
        if start and end and end > start:
            blocked.append((start, end, label))

    for key, label in [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")]:
        t = _parse_time(routine.get(key, ""))
        if t:
            add(t, _add(t, 30), label)

    cs, ce = _parse_range(routine.get("college_hours", ""))
    if cs and ce:
        add(cs, ce, "College / Office")
        travel_raw = routine.get("travel", "")
        if travel_raw and str(travel_raw).lower() not in ("no", "none", ""):
            nums = re.findall(r"\d+", str(travel_raw))
            travel_min = int(nums[0]) if nums else 30
            add(_add(cs, -travel_min), cs, "Travel to college")
            add(ce, _add(ce, travel_min), "Travel back")

    gym_raw = routine.get("gym", "")
    if gym_raw and str(gym_raw).lower() not in ("no", "none", ""):
        gym_t = _parse_time(str(gym_raw))
        if gym_t:
            add(gym_t, _add(gym_t, 60), "Gym")

    prayer_raw = routine.get("prayer", "")
    if prayer_raw and str(prayer_raw).lower() not in ("no", "none", ""):
        prayer_t = _parse_time(str(prayer_raw))
        if prayer_t:
            add(prayer_t, _add(prayer_t, 20), "Prayer / Meditation")

    add(_add(sleep, -30), sleep, "Wind-down")

    return sorted(blocked, key=lambda x: x[0])


def _free_slots(
    now: datetime,
    sleep: datetime,
    blocked: list[tuple[datetime, datetime, str]],
) -> list[tuple[datetime, datetime]]:
    cursor = now
    free = []
    for bstart, bend, _ in blocked:
        if cursor >= sleep:
            break
        if bstart <= cursor:
            cursor = max(cursor, bend)
            continue
        slot_end = min(bstart, sleep)
        if (slot_end - cursor).total_seconds() >= 20 * 60:
            free.append((cursor, slot_end))
        cursor = max(bend, bstart)
    if cursor < sleep and (sleep - cursor).total_seconds() >= 20 * 60:
        free.append((cursor, sleep))
    return free


# ─────────────────────────────────────────────────────────────────────────────
# Schedule builder  (produces list of slot dicts with real start/end datetimes)
# ─────────────────────────────────────────────────────────────────────────────

def _build_schedule(
    free_slots: list[tuple[datetime, datetime]],
    pending_tasks: list[dict],
    blocked: list[tuple[datetime, datetime, str]],
    break_minutes: int,
    focus_minutes: int,
) -> list[dict]:
    schedule = []

    # Fixed routine slots
    for bstart, bend, blabel in blocked:
        schedule.append({
            "start":    _fmt(bstart),
            "end":      _fmt(bend),
            "_start_dt": bstart,
            "title":    blabel,
            "type":     "fixed",
            "task_id":  None,
            "subject":  "",
        })

    task_queue = [t for t in pending_tasks if t.get("type") != "break"]
    task_idx = 0
    tasks_since_break = 0

    for slot_start, slot_end in free_slots:
        cursor = slot_start
        while cursor < slot_end and task_idx < len(task_queue):
            if tasks_since_break >= 2:
                break_end = _add(cursor, break_minutes)
                if break_end <= slot_end:
                    schedule.append({
                        "start":     _fmt(cursor),
                        "end":       _fmt(break_end),
                        "_start_dt": cursor,
                        "title":     "Break",
                        "type":      "break",
                        "task_id":   None,
                        "subject":   "",
                    })
                    cursor = break_end
                tasks_since_break = 0
                continue

            task = task_queue[task_idx]
            duration = task.get("duration_minutes", focus_minutes)
            task_end = _add(cursor, duration)

            if task_end > slot_end:
                break  # doesn't fit — move to next slot

            schedule.append({
                "start":    _fmt(cursor),
                "end":      _fmt(task_end),
                "_start_dt": cursor,
                "title":    task["title"],
                "subject":  task.get("subject", ""),
                "type":     task.get("type", "learning"),
                "priority": task.get("priority", "medium"),
                "task_id":  task.get("id"),
                "reason":   task.get("reason", ""),
            })
            cursor = task_end
            task_idx += 1
            tasks_since_break += 1

    schedule.sort(key=lambda e: e.get("_start_dt", datetime.max))
    # Remove internal datetime before saving to state
    for e in schedule:
        e.pop("_start_dt", None)
    return schedule, task_idx  # return how many tasks were scheduled today


# ─────────────────────────────────────────────────────────────────────────────
# Multi-day plan builder
# ─────────────────────────────────────────────────────────────────────────────

def _build_day_plan(
    all_tasks: list[dict],
    routine: dict,
    wake_time: str,
    sleep_time: str,
    focus_min: int,
    break_min: int,
    deadline_days: int,
) -> list[dict]:
    """Distribute all pending tasks across deadline_days days, interleaving subjects."""
    today = datetime.now().date()
    pending = [t for t in all_tasks if t.get("status") == "pending" and t.get("type") != "break"]

    def _free_minutes_per_day() -> int:
        ref  = datetime.combine(today, datetime.strptime("6:00 AM", "%I:%M %p").time())
        wake  = _parse_time(wake_time)  or ref.replace(hour=6)
        sleep = _parse_time(sleep_time) or ref.replace(hour=23)
        blocked = _blocked_intervals(routine, wake, sleep)
        free    = _free_slots(wake, sleep, blocked)
        return int(sum((e - s).total_seconds() / 60 for s, e in free))

    free_per_day   = _free_minutes_per_day()
    study_capacity = max(free_per_day - 30, 60)

    # Interleave: group tasks by subject, then round-robin across subjects
    subj_buckets: dict[str, list] = {}
    for t in pending:
        subj_buckets.setdefault(t.get("subject", "General"), []).append(t)
    subjects_order = list(subj_buckets.keys())

    interleaved: list[dict] = []
    while any(subj_buckets.values()):
        for subj in subjects_order:
            if subj_buckets.get(subj):
                interleaved.append(subj_buckets[subj].pop(0))

    day_plan = []
    task_pool_idx = 0

    for day_num in range(1, deadline_days + 1):
        day_date  = today + timedelta(days=day_num - 1)
        label     = day_date.strftime("%A, %d %b")
        day_tasks: list[dict] = []
        minutes_used = 0

        while task_pool_idx < len(interleaved):
            t   = interleaved[task_pool_idx]
            dur = t.get("duration_minutes", focus_min)
            if minutes_used + dur > study_capacity:
                break
            day_tasks.append({
                "id":               t["id"],
                "title":            t["title"],
                "subject":          t.get("subject", ""),
                "duration_minutes": dur,
                "type":             t.get("type", "learning"),
            })
            minutes_used     += dur
            task_pool_idx    += 1

        if not day_tasks and task_pool_idx >= len(interleaved):
            break

        # Add travel micro-study if travel time exists
        travel_raw = routine.get("travel", "")
        travel_note = ""
        if travel_raw and str(travel_raw).lower() not in ("no", "none", ""):
            nums = re.findall(r"\d+", str(travel_raw))
            travel_min = int(nums[0]) if nums else 30
            travel_note = f"  🚌 During travel ({travel_min} min): watch video / review flashcards"

        day_plan.append({
            "day":           day_num,
            "date":          label,
            "tasks":         day_tasks,
            "total_minutes": minutes_used,
            "travel_note":   travel_note,
        })

    return day_plan


# ─────────────────────────────────────────────────────────────────────────────
# Render helpers
# ─────────────────────────────────────────────────────────────────────────────

ICON = {
    "fixed":    "🔒",
    "break":    "☕",
    "learning": "📖",
    "practice": "✏️",
    "revision": "🔄",
    "research": "🔍",
    "coding":   "💻",
}


def _schedule_to_text(schedule: list[dict], now: datetime, daily_goal: int, completed_today: int) -> str:
    if not schedule:
        return "No study slots available right now. Try again later or adjust your routine."

    study_slots = [e for e in schedule if e["type"] not in ("fixed", "break")]
    remaining = [e for e in study_slots if e.get("task_id") is not None]

    # Estimate finish time = end of last study/break slot
    last_end = ""
    for e in reversed(schedule):
        if e["type"] != "fixed":
            last_end = e["end"]
            break

    lines = [
        f"📅 Today's Schedule  (current time: {_fmt(now)})",
        "",
    ]

    for entry in schedule:
        icon = ICON.get(entry["type"], "📌")
        subj = f"  [{entry['subject']}]" if entry.get("subject") else ""
        lines.append(f"  {entry['start']} – {entry['end']}  {icon} {entry['title']}{subj}")

    lines.append("")
    if last_end:
        lines.append(f"⏱ Estimated finish: {last_end}")

    done_bar = "█" * completed_today + "░" * max(daily_goal - completed_today, 0)
    lines.append(f"📊 Today's goal: [{done_bar}] {completed_today}/{daily_goal} sessions")

    return "\n".join(lines)


def _day_plan_to_text(day_plan: list[dict], intensity: str = "moderate") -> str:
    intensity_label = {
        "tight":   "⚡ Tight deadline — high daily load",
        "moderate": "📅 Moderate pace",
        "relaxed":  "🌿 Relaxed pace — spaced repetition",
    }
    lines = [f"📆 Study Plan until your deadline  ({intensity_label.get(intensity, '')})\n"]
    for day in day_plan:
        lines.append(f"── {day['date']}  ({day['total_minutes']} min) ──")
        for t in day["tasks"]:
            icon = ICON.get(t.get("type", "learning"), "📌")
            lines.append(f"  {icon} {t['title']}  ({t['duration_minutes']} min)  [{t['subject']}]")
        if day.get("travel_note"):
            lines.append(day["travel_note"])
        lines.append("")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Node
# ─────────────────────────────────────────────────────────────────────────────

def scheduler_node(state: dict) -> dict:
    s = StudentState(**state)

    now = datetime.now().replace(second=0, microsecond=0)

    wake  = _parse_time(s.wake_time  or s.routine.get("wake_time",  "6 AM"))
    sleep = _parse_time(s.sleep_time or s.routine.get("sleep_time", "11 PM"))
    if not wake:
        wake  = now.replace(hour=6,  minute=0)
    if not sleep:
        sleep = now.replace(hour=23, minute=0)

    if now >= sleep:
        s.agent_response = "It's past your sleep time. Rest well — I'll plan tomorrow when you wake up. 😴"
        s.reschedule_needed = False
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    start_from = max(now, wake)

    # Focus / break durations
    focus_min = 45
    break_min = 10
    if s.focus_duration:
        nums = re.findall(r"\d+", s.focus_duration)
        if nums:
            focus_min = int(nums[0])
    if s.break_duration:
        nums = re.findall(r"\d+", str(s.break_duration))
        if nums:
            break_min = int(nums[0])

    blocked = _blocked_intervals(s.routine, wake, sleep)

    # Pending tasks — sort by structured_strategy priority_order, then learning_path order
    strat_priority = []
    if s.structured_strategy:
        strat_priority = s.structured_strategy.get("priority_order", [])

    def _task_sort_key(t: dict):
        subj = t.get("subject", "")
        # Primary: subject priority from strategy
        subj_rank = strat_priority.index(subj) if subj in strat_priority else len(strat_priority)
        # Secondary: learning path order within subject
        lp_rank = 999
        if s.learning_path:
            for item in s.learning_path:
                if item.get("subject") == subj and item.get("title") == t.get("topic"):
                    lp_rank = item.get("learning_order", 999)
                    break
        return (subj_rank, lp_rank)

    def _is_available(t: dict, now_dt: datetime) -> bool:
        ao = t.get("available_on")
        if not ao:
            return True
        try:
            ao_dt = datetime.fromisoformat(ao)
        except Exception:
            try:
                ao_dt = datetime.strptime(ao, "%Y-%m-%d")
            except Exception:
                return True
        return ao_dt <= now

    pending = sorted(
        [t for t in s.tasks if t.get("status") == "pending" and _is_available(t, now)],
        key=_task_sort_key
    )

    free = _free_slots(start_from, sleep, blocked)
    schedule, tasks_today = _build_schedule(free, pending, blocked, break_min, focus_min)

    s.today_schedule = schedule
    s.last_scheduled_at = now.isoformat()
    s.today_date = now.date().isoformat()
    s.reschedule_needed = False

    # Daily goal = study task slots scheduled today
    if not s.daily_goal_count:
        s.daily_goal_count = tasks_today

    # Multi-day plan (only build once or on reschedule)
    deadline_days = _deadline_days(s.deadline)
    s.day_plan = _build_day_plan(
        s.tasks, s.routine, s.wake_time or "6 AM", s.sleep_time or "11 PM",
        focus_min, break_min, deadline_days,
    )

    s.agent_response = _schedule_to_text(schedule, now, s.daily_goal_count, s.completed_today)

    # Append multi-day plan if user asked for schedule (not just a reschedule trigger)
    if "schedule" in (s.user_message or "").lower() or "plan" in (s.user_message or "").lower():
        from app.agents.planner import _deadline_intensity
        s.agent_response += "\n\n" + _day_plan_to_text(s.day_plan, _deadline_intensity(s.deadline))

    # Water reminders
    water_raw = s.routine.get("water_interval", "")
    if water_raw and "no" not in str(water_raw).lower() and "none" not in str(water_raw).lower():
        nums = re.findall(r"\d+", str(water_raw))
        if nums:
            interval_min = int(nums[0]) * 60 if "hour" in str(water_raw).lower() else int(nums[0])
            reminders = []
            cursor = start_from
            while cursor < sleep:
                cursor = _add(cursor, interval_min)
                if cursor < sleep:
                    reminders.append(f"  {_fmt(cursor)}  💧 Drink water")
            if reminders:
                s.agent_response += "\n\nWater reminders:\n" + "\n".join(reminders)

    s.history.append({"role": "assistant", "content": s.agent_response})
    print(f"[Scheduler] Built {len(schedule)} slots from {_fmt(start_from)}, {tasks_today} study tasks today")
    return s.model_dump()
