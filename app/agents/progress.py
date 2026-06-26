"""
Progress Agent — Daily Execution Loop

Stages:
  idle                → pick next pending task
  ask_completion      → "Did you complete <topic>?" (1/2/3)
  ask_rating          → rate understanding 1-5
  ask_difficulty_detail → what was difficult? (only when rating <= 2)
  ask_partial         → how much? (25/50/75%)
  ask_reason          → what stopped you? (busy/hard/tired/forgot/confused)
"""

import random
from datetime import datetime, timedelta
from app.state import StudentState

# XP values
XP_BASE       = 50
XP_PARTIAL    = 20
XP_DIFFICULT  = 15   # bonus when subject confidence <= 4
XP_STREAK     = 10   # bonus per day on streak

STREAK_BADGES = {
    3:  "🔥 3-Day Streak",
    7:  "🏆 Week Warrior",
    14: "💪 Fortnight Focus",
    30: "🚀 Month Master",
}

TOPIC_BADGES = {
    1:  "🏅 First Topic",
    10: "⭐ 10 Topics Done",
    25: "📚 25 Topics Done",
}

UNDERSTANDING = {
    "1": "I didn't understand it.",
    "2": "Very difficult.",
    "3": "Mostly understood.",
    "4": "Comfortable.",
    "5": "I can teach someone else.",
}

DIFFICULTY_DETAIL_OPTIONS = {
    "1": "theory",
    "2": "numericals",
    "3": "too many concepts",
    "4": "not enough time",
}

ENCOURAGEMENTS = [
    "Excellent! Keep the momentum going.",
    "One more topic down. You're making real progress.",
    "Consistency is everything. You're proving that.",
    "That's the way. Every topic brings you closer.",
    "You're building a habit. Don't stop now.",
    "Solid work. Stay focused.",
    "Every completed topic reduces exam stress.",
    "Small wins become big results.",
    "Your future self will thank you.",
    "You're ahead of yesterday.",
    "Learning is becoming a habit.",
    "Another milestone completed.",
    "Nice consistency.",
    "You're getting closer to your goal.",
    "That focus is going to pay off.",
    "One topic at a time. You've got this.",
    "Progress compounds. Keep stacking sessions.",
    "Deadlines don't scare prepared students.",
    "You showed up. That's half the battle.",
    "The habit is forming. Don't break the chain.",
    "Momentum is your best study tool right now.",
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_time(raw: str) -> str:
    """Pass-through — schedule times are already formatted strings."""
    return raw


def _schedule_spaced_revisions(s: StudentState, task: dict, rating: int) -> StudentState:
    """
    After completing a topic, inject spaced revision tasks:
      day+1 → quick recap (15 min)
      day+3 → medium revision (20 min)   [only if rating <= 3]
      day+7 → final checkpoint (25 min)  [only if rating <= 4]
    Skips if a revision for the same topic already exists.
    """
    topic   = task.get("topic") or task.get("title", "")
    subject = task.get("subject", "")
    existing = {(t.get("topic"), t.get("spaced_day_offset")) for t in s.tasks if t.get("type") == "revision" and t.get("status") == "pending"}

    next_id = max((t.get("id", 0) for t in s.tasks), default=0) + 1
    added   = []

    schedule = [(1, 15, "Quick recap")]
    if rating <= 3:
        schedule.append((3, 20, "Medium revision"))
    if rating <= 4:
        schedule.append((7, 25, "Final checkpoint"))

    for day_offset, duration, label in schedule:
        rev_title = f"{label}: {topic}"
        if (topic, day_offset) in existing:
            continue
        available_on = (datetime.now() + timedelta(days=day_offset)).isoformat()
        s.tasks.append({
            "id":                        next_id,
            "title":                     rev_title,
            "subject":                   subject,
            "topic":                     topic,
            "type":                      "revision",
            "duration_minutes":          duration,
            "priority":                  "high" if day_offset == 1 else "medium",
            "difficulty":                "easy",
            "energy":                    "low",
            "depends_on":                [task["id"]],
            "recommended_resource_type": "none",
            "status":                    "pending",
            "reason":                    f"Spaced repetition — day+{day_offset}",
            "spaced_day_offset":         day_offset,
            "available_on":              available_on,
            "created_from":              task.get("id"),
        })
        added.append(f"day+{day_offset}")
        next_id += 1
        existing.add(topic)  # prevent duplicates within same call

    # Record in revision_queue for tracking
    s.revision_queue.append({
        "topic":              topic,
        "subject":            subject,
        "rating":             rating,
        "schedules":          added,
        "source_task_id":     task["id"],
        "created_at":         datetime.now().isoformat(),
    })
    return s, added


def _archive_topic(s: StudentState, topic: str, subject: str) -> tuple[StudentState, str]:
    """
    Archive a topic into the knowledge vault.
    Removes pending study/practice tasks for that topic.
    Keeps revision tasks (revision_only mode).
    """
    # Gather all ratings for this topic
    ratings = [
        t.get("understanding_rating", 0)
        for t in s.tasks
        if t.get("topic") == topic and t.get("subject") == subject and t.get("understanding_rating")
    ]
    difficulty_notes = [
        t.get("difficulty_detail", "")
        for t in s.tasks
        if t.get("topic") == topic and t.get("subject") == subject and t.get("difficulty_detail")
    ]
    mastery = round(sum(ratings) / len(ratings), 1) if ratings else 0

    # Check if already in vault
    already = any(v["topic"] == topic and v["subject"] == subject for v in s.knowledge_vault)
    if not already:
        s.knowledge_vault.append({
            "subject":          subject,
            "topic":            topic,
            "mastery":          mastery,
            "ratings":          ratings,
            "difficulty_notes": difficulty_notes,
            "status":           "archived",
            "revision_only":    True,
        })

    # Remove pending study/practice tasks for this topic (keep revisions)
    removed = 0
    s.tasks = [
        t for t in s.tasks
        if not (t.get("topic") == topic and t.get("subject") == subject
                and t.get("type") in ("learning", "practice") and t.get("status") == "pending")
    ]
    s.reschedule_needed = True
    msg = (
        f"🗃️ **{topic}** archived.\n"
        f"  Mastery: {mastery}/5  ·  Revisions still scheduled.\n"
        f"  The topic lives in your Knowledge Vault — future revision tasks remain active."
    )
    return s, msg


def _today_mini_schedule(s: StudentState) -> str:
    """Show today's remaining schedule as a compact checklist."""
    completed_ids = {t.get("id") for t in s.tasks if t.get("status") == "completed"}
    slots = [e for e in s.today_schedule if e.get("type") not in ("fixed", "break")]
    if not slots:
        return ""
    lines = ["\n📋 Today's Schedule:"]
    for entry in slots:
        tid = entry.get("task_id")
        icon = "✔" if tid in completed_ids else "○"
        lines.append(f"  {icon} {entry['start']}–{entry['end']}  {entry['title']}")
    # Estimated finish = end time of last non-fixed slot
    for entry in reversed(s.today_schedule):
        if entry.get("type") not in ("fixed",):
            lines.append(f"  ⏱ Est. finish: {entry['end']}")
            break
    # Daily goal bar
    goal = s.daily_goal_count or len(slots)
    done = s.completed_today
    bar  = "█" * done + "░" * max(goal - done, 0)
    lines.append(f"  📊 [{bar}] {done}/{goal} sessions today")
    return "\n".join(lines)

def _active_task(s: StudentState) -> dict | None:
    if s.active_task_id is None:
        return None
    for t in s.tasks:
        if t.get("id") == s.active_task_id:
            return t
    return None


def _next_pending_task(s: StudentState) -> dict | None:
    for t in s.tasks:
        if t.get("status") == "pending":
            return t
    return None


def _completed_count(s: StudentState) -> int:
    return len([t for t in s.tasks if t.get("status") == "completed"])


def _award_xp(s: StudentState, components: dict) -> tuple[StudentState, str]:
    """Award XP and return a formatted breakdown string."""
    total = sum(components.values())
    s.xp += total
    lines = [f"  +{v} {k}" for k, v in components.items() if v > 0]
    lines.append(f"  ─────────")
    lines.append(f"  +{total} XP total")
    return s, "\n".join(lines)


def _increment_streak(s: StudentState) -> tuple[StudentState, str]:
    s.streak += 1
    new_badges = []
    badge = STREAK_BADGES.get(s.streak)
    if badge and badge not in s.badges:
        s.badges.append(badge)
        new_badges.append(badge)
    count = _completed_count(s)
    topic_badge = TOPIC_BADGES.get(count)
    if topic_badge and topic_badge not in s.badges:
        s.badges.append(topic_badge)
        new_badges.append(topic_badge)
    return s, "  ".join(new_badges)


def _reschedule_task(s: StudentState, task_id: int, extra_minutes: int = 0) -> StudentState:
    for t in s.tasks:
        if t.get("id") == task_id:
            t["status"] = "pending"
            if extra_minutes:
                t["duration_minutes"] = t.get("duration_minutes", 45) + extra_minutes
            t["rescheduled"] = True
    s.reschedule_needed = True
    return s


def _split_task(s: StudentState, task_id: int) -> StudentState:
    for i, t in enumerate(s.tasks):
        if t.get("id") == task_id:
            half = max(t.get("duration_minutes", 45) // 2, 20)
            t["duration_minutes"] = half
            t["status"] = "pending"
            t["title"] = t["title"] + " (Part 1)"
            part2 = dict(t)
            part2["id"] = max(x.get("id", 0) for x in s.tasks) + 1
            part2["title"] = t["title"].replace("Part 1", "Part 2")
            part2["duration_minutes"] = half
            part2["status"] = "pending"
            part2["depends_on"] = [task_id]
            s.tasks.insert(i + 1, part2)
            break
    s.reschedule_needed = True
    return s


def _roadmap(s: StudentState) -> str:
    """Build a visual roadmap grouped by subject."""
    lines = ["📍 Learning Roadmap:"]
    active_id = s.active_task_id
    for subj in s.subjects:
        subj_name = subj["name"]
        subj_tasks = [t for t in s.tasks
                      if t.get("subject") == subj_name and t.get("type") != "break"]
        if not subj_tasks:
            continue
        done = len([t for t in subj_tasks if t.get("status") == "completed"])
        total = len(subj_tasks)
        bar = "█" * done + "░" * (total - done)
        lines.append(f"\n  {subj_name}  [{bar}] {done}/{total}")
        for t in subj_tasks:
            status = t.get("status", "pending")
            tid = t.get("id")
            if status == "completed":
                icon = "✔"
            elif tid == active_id or status == "active":
                icon = "▶"
            else:
                icon = "○"
            lines.append(f"    {icon} {t['title']}")
    return "\n".join(lines)


def _summary(s: StudentState) -> str:
    non_break = [t for t in s.tasks if t.get("type") != "break"]
    done_tasks = [t for t in non_break if t.get("status") == "completed"]
    pending = [t for t in non_break if t.get("status") not in ("completed", "active")]
    pct = int(len(done_tasks) / len(non_break) * 100) if non_break else 0

    hours = s.total_study_minutes // 60
    mins  = s.total_study_minutes % 60
    time_str = f"{hours}h {mins}m" if hours else f"{mins}m"

    lines = [
        "📊 Progress Summary",
        f"  Completed : {len(done_tasks)}/{len(non_break)} tasks ({pct}%)",
        f"  Pending   : {len(pending)} tasks",
        f"  Study time: {time_str}",
        f"  XP        : {s.xp}",
        f"  Streak    : {s.streak} days",
        "",
        "Subject Performance:",
    ]
    for subj in s.subjects:
        s_tasks = [t for t in non_break if t.get("subject") == subj["name"]]
        if not s_tasks:
            continue
        s_done = len([t for t in s_tasks if t.get("status") == "completed"])
        ratio  = s_done / len(s_tasks)
        filled = int(ratio * 5)
        bar    = "█" * filled + "░" * (5 - filled)
        lines.append(f"  {subj['name']:10s} [{bar}] {int(ratio*100)}%")
    if s.badges:
        lines.append(f"\n  Badges: {'  '.join(s.badges)}")
    return "\n".join(lines)


def _end_of_day(s: StudentState) -> str:
    done_tasks = [t for t in s.tasks if t.get("status") == "completed"]
    next_task  = _next_pending_task(s)
    hours = s.total_study_minutes // 60
    mins  = s.total_study_minutes % 60
    time_str = f"{hours}h {mins}m" if hours else f"{mins}m"

    # Estimated days to finish remaining tasks
    pending_non_break = [t for t in s.tasks if t.get("status") == "pending" and t.get("type") != "break"]
    pending_mins = sum(t.get("duration_minutes", 45) for t in pending_non_break)
    avg_daily = max(s.total_study_minutes, 60)   # use actual study time as proxy for daily capacity
    est_days  = max(1, round(pending_mins / avg_daily)) if pending_mins else 0

    lines = [
        "🌙 Day Complete!",
        "",
        "Topics finished today:",
    ]
    for t in done_tasks[-5:]:
        lines.append(f"  ✔ {t['title']}")
    lines += [
        "",
        f"Study time : {time_str}",
        f"XP earned  : {s.xp}",
        f"Streak     : {s.streak} days",
    ]
    if s.badges:
        lines.append(f"Badges     : {'  '.join(s.badges)}")
    if pending_mins:
        lines.append(f"Remaining  : {len(pending_non_break)} tasks (~{pending_mins // 60}h {pending_mins % 60}m, est. {est_days} more day{'s' if est_days != 1 else ''})")
    if next_task:
        lines += ["", f"Tomorrow starts with: {next_task['title']}", "Good night! 😴"]
    else:
        lines += ["", "🎉 All topics complete! Well done.", "Good night! 😴"]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Main node
# ─────────────────────────────────────────────────────────────────────────────

def _handle_time_recovery(s: StudentState, task: dict, actual_minutes: int) -> tuple[StudentState, str]:
    """
    Handle dynamic time recovery when user finishes early.
    Returns updated state and response message.
    """
    estimated = task.get("duration_minutes", 45)
    recovered = estimated - actual_minutes
    
    if recovered <= 5:  # Not enough to do anything meaningful
        return s, ""
    
    s.recovered_time_minutes += recovered
    
    # Time-packing algorithm: find tasks that fit in recovered time
    pending_tasks = [t for t in s.tasks if t.get("status") == "pending"]
    fitting_tasks = [
        t for t in pending_tasks
        if t.get("duration_minutes", 45) <= recovered
    ]
    
    # Sort by priority: revision > practice > short learning units
    def task_score(t):
        type_priority = {"revision": 1, "practice": 2, "learning": 3, "quiz": 2}
        return (
            type_priority.get(t.get("type"), 9),
            t.get("duration_minutes", 45),
        )
    
    fitting_tasks.sort(key=task_score)
    
    # If auto-fill is disabled, offer choices
    if not s.auto_fill_free_time:
        options = []
        option_map = {}  # map choice number to action
        choice_num = 1
        
        # Option: start fitting task
        if fitting_tasks:
            best_fit = fitting_tasks[0]
            options.append(f"{choice_num}. Start: {best_fit['title']} ({best_fit.get('duration_minutes')}min)")
            option_map[str(choice_num)] = ("start_task", best_fit["id"])
            choice_num += 1
        
        # Option: quick recap
        options.append(f"{choice_num}. Quick recap: {task.get('topic', task['title'])} (10 min)")
        option_map[str(choice_num)] = ("recap", task["id"])
        choice_num += 1
        
        # Option: practice MCQs
        if recovered >= 15:
            options.append(f"{choice_num}. Practice {task.get('subject')} MCQs (15 min)")
            option_map[str(choice_num)] = ("practice_mcq", task.get("subject"))
            choice_num += 1
        
        # Option: early break
        options.append(f"{choice_num}. Take early break")
        option_map[str(choice_num)] = ("break", None)
        
        msg = (
            f"\n⏱ You finished {recovered} minutes early!\n\n"
            f"What would you like to do?\n" +
            "\n".join(options) +
            f"\n\nReply 1-{len(options)} or 'continue' to follow schedule."
        )
        
        s.pending_recovery_action = {
            "time_minutes": recovered,
            "completed_task": task,
            "options": options,
            "option_map": option_map,
        }
        s.daily_loop_stage = "handle_recovery_choice"
        
        return s, msg
    
    # Auto-fill enabled: intelligently pack time
    if fitting_tasks:
        best_fit = fitting_tasks[0]
        
        # Auto-start the fitting task
        s.active_task_id = best_fit["id"]
        best_fit["status"] = "active"
        s.daily_loop_stage = "ask_completion"  # will ask about this task next
        
        msg = (
            f"\n⏱ You finished {recovered} minutes early!\n"
            f"   Auto-starting: {best_fit['title']} ({best_fit.get('duration_minutes')} min)\n\n"
            f"Type 'skip' if you'd rather take a break instead, or continue with the task."
        )
        
        # Update schedule: add this task to current time slot
        s.reschedule_needed = True
        
        return s, msg
    
    # No fitting tasks: offer quick activities
    next_task = _next_pending_task(s)
    if next_task:
        next_duration = next_task.get("duration_minutes", 45)
        msg = (
            f"\n⏱ You finished {recovered} minutes early!\n"
            f"   Next unit ({next_task['title']}) needs {next_duration} min (too long).\n\n"
            f"Quick activities:\n"
            f"  • Type 'recap' → 10-min quick recap of {task.get('topic')}\n"
            f"  • Type 'mcq' → 15-min practice MCQs\n"
            f"  • Type 'break' → Take early break\n\n"
            f"Or type 'continue' to follow original schedule."
        )
    else:
        msg = f"\n✨ {recovered} min saved! No pending tasks—enjoy your break."
    
    s.pending_recovery_action = {
        "time_minutes": recovered,
        "completed_task": task,
    }
    s.daily_loop_stage = "handle_recovery_choice"
    
    return s, msg


def progress_node(state: dict) -> dict:
    s = StudentState(**state)
    msg = s.user_message.strip().lower()

    # ── idle: pick next task or handle meta-commands ─────────────────────────
    if s.daily_loop_stage == "idle":
        if "summary" in msg:
            s.agent_response = _summary(s)
        elif "roadmap" in msg:
            s.agent_response = _roadmap(s)
        elif "end of day" in msg or "goodnight" in msg or "good night" in msg:
            s.agent_response = _end_of_day(s)
        elif msg.startswith("archive "):
            # Format: "archive <topic> from <subject>" or "archive <topic>"
            parts = msg[8:].strip()
            topic, subject = parts, ""
            if " from " in parts:
                topic, subject = parts.split(" from ", 1)
            elif s.subjects:
                # guess subject from existing tasks
                for t in s.tasks:
                    if t.get("topic", "").lower() == topic.lower():
                        subject = t.get("subject", "")
                        topic   = t.get("topic", topic)
                        break
            s, archive_msg = _archive_topic(s, topic.strip().title(), subject.strip().title())
            s.agent_response = archive_msg
        elif msg == "vault" or msg == "knowledge vault":
            if not s.knowledge_vault:
                s.agent_response = "🗃️ Knowledge Vault is empty. Complete topics to populate it."
            else:
                lines = ["🗃️ Knowledge Vault:\n"]
                for v in s.knowledge_vault:
                    stars = "★" * round(v.get("mastery", 0)) + "☆" * (5 - round(v.get("mastery", 0)))
                    lines.append(f"  {v['subject']:10s}  {v['topic']:25s}  {stars}  (revision only)")
                s.agent_response = "\n".join(lines)
        else:
            task = _next_pending_task(s)
            if not task:
                s.agent_response = "🎉 All tasks complete!\n\n" + _end_of_day(s)
            else:
                s.active_task_id = task["id"]
                task["status"] = "active"
                s.daily_loop_stage = "ask_completion"
                s.agent_response = (
                    f"📚 **{task['title']}**\n"
                    f"   {task.get('subject','')}  ·  {task.get('duration_minutes',45)} min"
                    f"  ·  Priority: {task.get('priority','?')}\n"
                    f"   Reason: {task.get('reason','')}\n\n"
                    f"Did you complete this topic?\n"
                    f"  1) Yes\n  2) Partially\n  3) No, not yet"
                )

    # ── ask_completion ────────────────────────────────────────────────────────
    elif s.daily_loop_stage == "ask_completion":
        task = _active_task(s)
        if not task:
            s.daily_loop_stage = "idle"
            s.agent_response = "Let's continue. Type anything."
        elif msg in ("1", "yes", "y", "done", "completed", "yeah", "yep"):
            s.daily_loop_stage = "ask_rating"
            s.agent_response = (
                f"Great work! ✅\n\n"
                f"Rate your understanding of **{task['title']}**:\n"
                f"  1 — I didn't understand it\n"
                f"  2 — Very difficult\n"
                f"  3 — Mostly understood\n"
                f"  4 — Comfortable\n"
                f"  5 — I can teach someone else"
            )
        elif msg in ("2", "partially", "partial", "some", "half"):
            s.daily_loop_stage = "ask_partial"
            s.agent_response = (
                f"Good effort! How much of **{task['title']}** did you cover?\n"
                f"  1) Around 25%\n  2) Around 50%\n  3) Around 75%"
            )
        elif msg in ("3", "skip", "later"):
            s.daily_loop_stage = "ask_skip_action"
            s.agent_response = (
                f"What would you like to do with **{task['title']}**?\n"
                f"  1) Skip for now (reschedule for later)\n"
                f"  2) Archive (remove from active plan, keep history)\n"
                f"  3) Mark as not required (outside syllabus)"
            )
        else:
            s.agent_response = "Please reply 1 (Yes), 2 (Partially), or 3 (Skip/Later)."

    # ── ask_rating ────────────────────────────────────────────────────────────
    elif s.daily_loop_stage == "ask_rating":
        task = _active_task(s)
        rating = msg.strip()[:1]
        if rating not in ("1", "2", "3", "4", "5"):
            s.agent_response = "Please rate 1–5."
        else:
            rating_int = int(rating)
            task["status"] = "completed"
            task["understanding_rating"] = rating_int
            actual_time = task.get("duration_minutes", 45)
            s.total_study_minutes += actual_time
            s.reschedule_needed = True
            
            # Check for time recovery
            estimated_time = task.get("original_duration", task.get("duration_minutes", 45))
            if actual_time < estimated_time:
                s, recovery_msg = _handle_time_recovery(s, task, actual_time)
                # recovery_msg will be appended later

            # Update subject confidence based on rating
            old_confidence = 5
            for subj in s.subjects:
                if subj["name"] == task.get("subject"):
                    old_confidence = subj.get("confidence", 5)
                    old = subj.get("confidence", 5)
                    if rating_int >= 4:
                        subj["confidence"] = min(old + 1, 10)
                    elif rating_int <= 2:
                        subj["confidence"] = max(old - 1, 1)
                    new_conf = subj["confidence"]
                    
                    # Trigger decision engine for confidence change
                    if new_conf != old_confidence:
                        from app.agents.decision_engine import decision_engine
                        s = StudentState(**decision_engine(s.model_dump(), "confidence_changed", {
                            "subject": subj["name"],
                            "old_confidence": old_confidence,
                            "new_confidence": new_conf,
                        }))
                    
                    break

            # Update learning unit
            if task.get("learning_unit_id"):
                for unit in s.learning_units:
                    if unit["id"] == task["learning_unit_id"]:
                        unit["status"] = "completed"
                        unit["mastery"] = rating_int
                        unit["actual_time_spent"] = (unit.get("actual_time_spent", 0) + actual_time)
                        unit["attempts"] = unit.get("attempts", 0) + 1
                        unit["last_studied"] = datetime.now().isoformat()
                        unit["completed_at"] = datetime.now().isoformat()
                        
                        # Trigger decision engine for task completion
                        from app.agents.decision_engine import decision_engine
                        s = StudentState(**decision_engine(s.model_dump(), "task_completed", {
                            "task_id": task["id"],
                            "learning_unit_id": unit["id"],
                            "rating": rating_int,
                        }))
                        
                        break

            # XP breakdown
            confidence = next(
                (sub.get("confidence", 5) for sub in s.subjects
                 if sub["name"] == task.get("subject")), 5
            )
            xp_components = {"Completed topic": XP_BASE}
            if confidence <= 4:
                xp_components["Difficult subject bonus"] = XP_DIFFICULT
            if s.streak > 0:
                xp_components[f"Streak bonus ({s.streak}d)"] = XP_STREAK
            if rating_int >= 4:
                xp_components["Good understanding bonus"] = 10
            s, xp_str = _award_xp(s, xp_components)
            s, new_badges = _increment_streak(s)

            # Increment completed_today
            s.completed_today = (s.completed_today or 0) + 1

            # Spaced repetition — schedule day+1/+3/+7 revisions
            s, rev_days = _schedule_spaced_revisions(s, task, rating_int)
            if rev_days:
                rev_note = f"\n📆 Spaced revision scheduled: {', '.join(rev_days)}"
            else:
                rev_note = ""

            encourage = random.choice(ENCOURAGEMENTS)
            lines = [
                f"✅ **{task['title']}** marked complete!",
                f"Understanding: {UNDERSTANDING[rating]}",
                "",
                "XP earned:",
                xp_str,
                "",
                f"🔥 Streak: {s.streak} days  |  Total XP: {s.xp}",
            ]
            if new_badges:
                lines.append(f"🏅 New badge: {new_badges}")
            lines.append(f"\n{encourage}")

            # Spaced revision note
            if rev_note:
                lines.append(rev_note)

            # Smart feedback based on rating
            if rating_int == 5:
                lines.append(f"\nYou're confident in {task.get('topic', task['title'])}. I'll prioritize practice over theory next.")
            elif rating_int == 1:
                lines.append("\nI'll slow things down. Tomorrow we'll review this with the Tutor before moving ahead.")

            # Suggest a break every 3 completions
            if s.completed_today % 3 == 0:
                lines.append(
                    f"\n🟡 You've done {s.completed_today} sessions in a row. "
                    "Take a 20-min break before continuing.\n"
                    "  Stretch, drink water, walk a bit.\nType 'next' when ready."
                )

            # Adapt upcoming practice task based on rating
            # If rating == 5: swap pending practice task for this topic to numericals/MCQ style
            # If rating == 1: swap to concept explanation
            if rating_int >= 4:
                for t in s.tasks:
                    if (t.get("status") == "pending"
                            and t.get("topic") == task.get("topic")
                            and t.get("type") == "practice"):
                        t["title"] = f"Practice {task.get('topic')} — Numericals & MCQs"
                        t["recommended_resource_type"] = "practice"
                        t["reason"] = f"Confidence high ({rating_int}/5) → application-level practice"
                        break
            elif rating_int == 1:
                for t in s.tasks:
                    if (t.get("status") == "pending"
                            and t.get("topic") == task.get("topic")
                            and t.get("type") in ("practice", "revision")):
                        t["title"] = f"Revise {task.get('topic')} with Tutor"
                        t["type"] = "revision"
                        t["recommended_resource_type"] = "explanation"
                        t["reason"] = f"Low understanding ({rating_int}/5) → concept-first revision"
                        break

            # Auto-revision for low rating
            if rating_int <= 2:
                rev_id = max(t.get("id", 0) for t in s.tasks) + 1
                s.tasks.append({
                    "id": rev_id,
                    "title": f"Revise {task.get('topic', task['title'])}",
                    "subject": task.get("subject"),
                    "topic": task.get("topic"),
                    "type": "revision",
                    "duration_minutes": 30,
                    "priority": "high",
                    "difficulty": task.get("difficulty", "medium"),
                    "energy": "medium",
                    "depends_on": [task["id"]],
                    "recommended_resource_type": "explanation",
                    "status": "pending",
                    "reason": f"Auto-scheduled: understanding rated {rating_int}/5",
                    "rescheduled": True,
                })
                lines.append("📌 30-min revision added to upcoming sessions.")
                # Ask what was difficult
                s.active_task_id = task["id"]   # keep reference for context
                s.daily_loop_stage = "ask_difficulty_detail"
                s.agent_response = "\n".join(lines) + (
                    "\n\nWhat specifically was difficult?\n"
                    "  1) Theory / concepts\n"
                    "  2) Numericals / problems\n"
                    "  3) Too many concepts at once\n"
                    "  4) Didn't have enough time"
                )
            else:
                s.active_task_id = None
                s.daily_loop_stage = "idle"
                next_task = _next_pending_task(s)
                # Append today's mini schedule
                mini = _today_mini_schedule(s)
                if mini:
                    lines.append(mini)
                
                # Append time recovery message if exists
                if 'recovery_msg' in locals() and recovery_msg:
                    lines.append(recovery_msg)

                # High mastery (4-5) → set offer_research flag for orchestrator to pick up
                if rating_int >= 4:
                    for t in s.tasks:
                        if t.get("id") == task["id"]:
                            t["offer_research"] = True
                            break

                if next_task:
                    lines.append(f"\n\ud83d\udd13 Next: **{next_task['title']}**")
                    lines.append("Type 'next' to continue, 'roadmap' or 'summary' to review.")
                else:
                    lines.append("\n" + _end_of_day(s))
                s.agent_response = "\n".join(lines)

    # ── ask_difficulty_detail ─────────────────────────────────────────────────
    elif s.daily_loop_stage == "ask_difficulty_detail":
        detail = DIFFICULTY_DETAIL_OPTIONS.get(msg.strip()[:1], "general difficulty")
        # Store on the revision task that was just appended
        for t in reversed(s.tasks):
            if t.get("rescheduled") and t.get("type") == "revision":
                t["difficulty_detail"] = detail
                break
        s.active_task_id = None
        s.daily_loop_stage = "idle"
        next_task = _next_pending_task(s)
        resp = f"Got it — noted as: {detail}. The Tutor Agent will focus on that when you revise.\n"
        if next_task:
            resp += f"\n🔓 Next: **{next_task['title']}**\nType 'next' to continue."
        else:
            resp += "\n" + _end_of_day(s)
        s.agent_response = resp

    # ── ask_partial ───────────────────────────────────────────────────────────
    elif s.daily_loop_stage == "ask_partial":
        task = _active_task(s)
        pct_map = {"1": 25, "2": 50, "3": 75, "25": 25, "50": 50, "75": 75}
        pct = pct_map.get(msg.replace("%", "").strip(), 50)
        extra = max(int((1 - pct / 100) * task.get("duration_minutes", 45)), 15)

        task["status"] = "partial"
        task["completion_pct"] = pct
        partial_mins = int(pct / 100 * task.get("duration_minutes", 45))
        s.total_study_minutes += partial_mins
        s.completed_today = (s.completed_today or 0)  # partial doesn't count as full session
        s = _reschedule_task(s, task["id"], extra_minutes=extra)
        s, xp_str = _award_xp(s, {"Partial completion": XP_PARTIAL})
        s.reschedule_needed = True

        s.active_task_id = None
        s.daily_loop_stage = "idle"
        s.agent_response = (
            f"👍 Good progress on **{task['title']}** ({pct}% done).\n\n"
            f"XP earned:\n{xp_str}\n\n"
            f"Remaining {extra} min added to next session.\n"
            f"Type 'next' to continue."
        )

    # ── ask_skip_action ───────────────────────────────────────────────────────
    elif s.daily_loop_stage == "ask_skip_action":
        task = _active_task(s)
        
        if msg in ("1", "skip", "reschedule"):
            # Skip for now - reschedule
            s = _reschedule_task(s, task["id"])
            s.active_task_id = None
            s.daily_loop_stage = "idle"
            s.agent_response = f"📅 **{task['title']}** rescheduled. We'll revisit it later."
        
        elif msg in ("2", "archive"):
            # Archive - move to vault
            topic = task.get('topic') or task.get('title')
            subject = task.get('subject', '')
            s, archive_msg = _archive_topic(s, topic, subject)
            s.active_task_id = None
            s.daily_loop_stage = "idle"
            s.agent_response = archive_msg
        
        elif msg in ("3", "not required", "outside syllabus"):
            # Mark as not required
            task["status"] = "not_required"
            task["marked_reason"] = "outside syllabus"
            s.active_task_id = None
            s.daily_loop_stage = "idle"
            s.agent_response = (
                f"✓ **{task['title']}** marked as not required.\n"
                f"It won't appear in your schedule anymore."
            )
        else:
            s.agent_response = "Please reply 1 (Skip), 2 (Archive), or 3 (Not Required)."

    # ── ask_post_mastery: offer research after high-rating completion ─────────
    elif s.daily_loop_stage == "ask_post_mastery":
        # Retrieve the topic from recently completed high-rating task
        topic = next(
            (t.get("topic") or t.get("title", "") for t in s.tasks
             if t.get("status") == "completed" and t.get("offer_research") and t.get("research_offered")),
            "this topic"
        )
        s.daily_loop_stage = "idle"

        if msg in ("1", "continue", "next topic"):
            s.agent_response = "Continuing to next topic. Type 'next' when ready."

        elif msg in ("2", "explore", "applications", "real world"):
            s.agent_response = f"Opening Research Agent to explore real-world applications of **{topic}**..."
            s.agent_handoff = {"to": "research", "reason": f"explore applications of {topic}"}
            s.return_to_agent = None
            s.user_message = f"explore {topic}"
            s.intent = "research"
            s.research_mode = "explore"
            s.research_stage = 1
            s.post_mastery_topic = topic

        elif msg in ("3", "build", "project"):
            s.agent_response = f"Opening Research Agent to find project ideas for **{topic}**..."
            s.agent_handoff = {"to": "research", "reason": f"project ideas for {topic}"}
            s.return_to_agent = None
            s.user_message = f"project ideas for {topic}"
            s.intent = "research"
            s.research_mode = "build_mentor"
            s.research_stage = 6
            s.post_mastery_topic = topic

        elif msg in ("4", "paper", "papers", "research papers"):
            s.agent_response = f"Opening Research Agent to find papers on **{topic}**..."
            s.agent_handoff = {"to": "research", "reason": f"papers on {topic}"}
            s.return_to_agent = None
            s.user_message = f"find papers on {topic}"
            s.intent = "research"
            s.research_mode = "paper"
            s.research_stage = 4
            s.post_mastery_topic = topic

        elif msg in ("5", "skip"):
            next_task = _next_pending_task(s)
            if next_task:
                s.agent_response = f"No problem. Type 'next' to continue with **{next_task['title']}**."
            else:
                s.agent_response = _end_of_day(s)
        else:
            s.daily_loop_stage = "ask_post_mastery"  # stay here
            s.agent_response = "Please reply 1-5."

    # ── handle_recovery_choice: user selected recovery action ────────────────
    elif s.daily_loop_stage == "handle_recovery_choice":
        if not s.pending_recovery_action:
            s.daily_loop_stage = "idle"
            s.agent_response = "Let's continue. Type 'next'."
        else:
            recovery = s.pending_recovery_action
            option_map = recovery.get("option_map", {})
            
            if msg in option_map:
                action, data = option_map[msg]
                
                if action == "start_task":
                    # Start the selected task
                    task_id = data
                    for t in s.tasks:
                        if t.get("id") == task_id:
                            s.active_task_id = task_id
                            t["status"] = "active"
                            s.daily_loop_stage = "ask_completion"
                            s.agent_response = (
                                f"Starting: **{t['title']}**\n"
                                f"Duration: {t.get('duration_minutes')} min\n\n"
                                f"Did you complete this topic?\n"
                                f"  1) Yes\n  2) Partially\n  3) No, not yet"
                            )
                            break
                    s.pending_recovery_action = None
                
                elif action == "recap":
                    # Quick recap
                    completed_task = recovery.get("completed_task")
                    s.total_study_minutes += 10
                    s.agent_response = (
                        f"✓ 10-min quick recap scheduled for {completed_task.get('topic')}.\n"
                        f"Review key concepts, formulas, and examples.\n\n"
                        f"Type 'next' to continue."
                    )
                    s.daily_loop_stage = "idle"
                    s.pending_recovery_action = None
                
                elif action == "practice_mcq":
                    # Practice MCQs
                    subject = data
                    s.total_study_minutes += 15
                    s.agent_response = (
                        f"✓ 15-min practice MCQs scheduled for {subject}.\n"
                        f"Focus on recent topics.\n\n"
                        f"Type 'next' to continue."
                    )
                    s.daily_loop_stage = "idle"
                    s.pending_recovery_action = None
                
                elif action == "break":
                    # Early break
                    s.agent_response = (
                        f"☕ Taking early break. Well deserved!\n\n"
                        f"Type 'next' when ready to continue."
                    )
                    s.daily_loop_stage = "idle"
                    s.pending_recovery_action = None
            
            elif msg in ("continue", "skip", "later"):
                # Follow original schedule
                s.agent_response = "Following original schedule. Type 'next' to continue."
                s.daily_loop_stage = "idle"
                s.pending_recovery_action = None
            
            else:
                s.agent_response = f"Please choose an option (1-{len(recovery.get('options', []))}) or 'continue'."

    # ── missed days adaptation (always runs) ──────────────────────────────────
    if s.missed_days >= 3:
        pending = [t for t in s.tasks if t.get("status") == "pending"]
        if pending:
            for t in pending:
                t["duration_minutes"] = max(t.get("duration_minutes", 45) // 2, 20)
            s.missed_days = 0
            s.agent_response = (s.agent_response or "") + (
                "\n\n⚠️ You've missed a few days. Sessions shortened to help you ease back in."
            )

    s.history.append({"role": "user",      "content": s.user_message})
    s.history.append({"role": "assistant", "content": s.agent_response})
    return s.model_dump()
