"""
Knowledge Tracking Utilities

Functions to update and maintain learning unit knowledge profiles:
- Update quiz scores
- Track practice history
- Store resources (videos, notes, diagrams)
- Calculate mastery progression
- Generate knowledge reports
"""

from datetime import datetime
from app.state import StudentState


def update_quiz_score(state: dict, unit_id: int, score: int, questions: int, correct: int, time_spent: int) -> dict:
    """
    Update learning unit with quiz performance.
    
    Args:
        state: Current state
        unit_id: Learning unit ID
        score: Score percentage (0-100)
        questions: Total questions attempted
        correct: Correct answers
        time_spent: Time in minutes
    """
    s = StudentState(**state)
    
    for unit in s.learning_units:
        if unit["id"] == unit_id:
            # Update quiz score
            unit["quiz_score"] = score
            unit["quiz_attempts"] = unit.get("quiz_attempts", 0) + 1
            
            # Add to history
            if "quiz_history" not in unit:
                unit["quiz_history"] = []
            
            unit["quiz_history"].append({
                "date": datetime.now().isoformat(),
                "score": score,
                "questions": questions,
                "correct": correct,
                "incorrect": questions - correct,
                "time_spent": time_spent,
            })
            
            # Update mastery based on quiz score
            if score >= 80:
                unit["mastery"] = min(unit.get("mastery", 0) + 1, 5)
            elif score < 50:
                unit["mastery"] = max(unit.get("mastery", 3) - 1, 0)
            
            # Update last accessed
            unit["last_accessed"] = datetime.now().isoformat()
            
            break
    
    return s.model_dump()


def update_practice_history(state: dict, unit_id: int, score: int, questions_attempted: int, time_spent: int) -> dict:
    """
    Track practice session performance.
    """
    s = StudentState(**state)
    
    for unit in s.learning_units:
        if unit["id"] == unit_id:
            if "practice_history" not in unit:
                unit["practice_history"] = []
            
            unit["practice_history"].append({
                "date": datetime.now().isoformat(),
                "score": score,
                "time_spent": time_spent,
                "questions_attempted": questions_attempted,
            })
            
            # Update mastery
            avg_score = sum(h["score"] for h in unit["practice_history"]) / len(unit["practice_history"])
            unit["mastery"] = round(avg_score / 20)  # Convert 0-100 to 0-5
            
            # Update last accessed
            unit["last_accessed"] = datetime.now().isoformat()
            
            break
    
    return s.model_dump()


def add_resource_to_unit(state: dict, unit_id: int, resource_type: str, resource_data: dict) -> dict:
    """
    Add a resource (video, diagram, note, practice link) to a learning unit.
    
    Args:
        resource_type: "video", "diagram", "note", "practice", "quiz"
        resource_data: {"title": "...", "url": "...", "source": "..."}
    """
    s = StudentState(**state)
    
    for unit in s.learning_units:
        if unit["id"] == unit_id:
            if "resources" not in unit:
                unit["resources"] = {"videos": [], "diagrams": [], "notes": [], "practice": [], "quiz": []}
            
            if resource_type in unit["resources"]:
                unit["resources"][resource_type].append({
                    **resource_data,
                    "added_at": datetime.now().isoformat(),
                })
            
            break
    
    return s.model_dump()


def update_revision_history(state: dict, unit_id: int, rating: int, notes: str, time_spent: int) -> dict:
    """
    Record revision session.
    """
    s = StudentState(**state)
    
    for unit in s.learning_units:
        if unit["id"] == unit_id:
            if "revision_history" not in unit:
                unit["revision_history"] = []
            
            unit["revision_history"].append({
                "date": datetime.now().isoformat(),
                "rating": rating,
                "notes": notes,
                "time_spent": time_spent,
            })
            
            # Update mastery (weighted average of recent revisions)
            recent = unit["revision_history"][-3:]  # Last 3 revisions
            avg_rating = sum(h["rating"] for h in recent) / len(recent)
            unit["mastery"] = round(avg_rating)
            
            # Update last accessed
            unit["last_accessed"] = datetime.now().isoformat()
            
            # Schedule next revision
            from datetime import date, timedelta
            if rating <= 2:
                days = 1  # Review tomorrow if struggled
            elif rating == 3:
                days = 3
            elif rating == 4:
                days = 7
            else:
                days = 14  # Mastered, review in 2 weeks
            
            unit["next_revision"] = (date.today() + timedelta(days=days)).isoformat()
            
            break
    
    return s.model_dump()


def calculate_unit_mastery(unit: dict) -> float:
    """
    Calculate comprehensive mastery score from all available data.
    
    Considers:
    - Quiz scores
    - Practice history
    - Revision ratings
    - Time spent vs estimated
    """
    factors = []
    
    # Quiz performance (weight: 30%)
    if unit.get("quiz_score"):
        factors.append(("quiz", unit["quiz_score"] / 20, 0.3))  # Convert to 0-5
    
    # Practice performance (weight: 25%)
    if unit.get("practice_history"):
        avg_practice = sum(h["score"] for h in unit["practice_history"]) / len(unit["practice_history"])
        factors.append(("practice", avg_practice / 20, 0.25))
    
    # Revision ratings (weight: 35%)
    if unit.get("revision_history"):
        recent_revisions = unit["revision_history"][-3:]
        avg_revision = sum(h["rating"] for h in recent_revisions) / len(recent_revisions)
        factors.append(("revision", avg_revision, 0.35))
    
    # Efficiency (weight: 10%)
    if unit.get("actual_time_spent") and unit.get("estimated_minutes"):
        efficiency = min(unit["estimated_minutes"] / unit["actual_time_spent"], 1.0)
        factors.append(("efficiency", efficiency * 5, 0.1))
    
    if not factors:
        return unit.get("mastery", 0)
    
    # Weighted average
    total_weight = sum(w for _, _, w in factors)
    weighted_sum = sum(score * weight for _, score, weight in factors)
    
    return round(weighted_sum / total_weight, 1)


def generate_knowledge_report(state: dict) -> str:
    """
    Generate comprehensive knowledge report showing mastery across all units.
    """
    s = StudentState(**state)
    
    # Group by subject
    by_subject = {}
    for unit in s.learning_units:
        subj = unit.get("subject", "Unknown")
        if subj not in by_subject:
            by_subject[subj] = []
        by_subject[subj].append(unit)
    
    lines = [
        "📚 Knowledge Report",
        "=" * 60,
        "",
    ]
    
    for subject, units in sorted(by_subject.items()):
        completed = [u for u in units if u.get("status") in ("completed", "mastered")]
        pending = [u for u in units if u.get("status") == "pending"]
        
        if not completed:
            continue
        
        avg_mastery = sum(calculate_unit_mastery(u) for u in completed) / len(completed)
        stars = "★" * round(avg_mastery) + "☆" * (5 - round(avg_mastery))
        
        lines.append(f"📖 {subject}  {stars}  ({avg_mastery:.1f}/5)")
        lines.append("")
        
        # Top mastered units
        top_units = sorted(completed, key=lambda u: calculate_unit_mastery(u), reverse=True)[:3]
        if top_units:
            lines.append("  ✅ Mastered:")
            for u in top_units:
                mastery = calculate_unit_mastery(u)
                lines.append(f"     {u['unit_name'][:40]:40s}  {mastery:.1f}/5")
        
        # Weak units needing revision
        weak_units = [u for u in completed if calculate_unit_mastery(u) < 3]
        if weak_units:
            lines.append("")
            lines.append("  ⚠️  Needs Revision:")
            for u in weak_units[:3]:
                mastery = calculate_unit_mastery(u)
                lines.append(f"     {u['unit_name'][:40]:40s}  {mastery:.1f}/5")
        
        lines.append("")
        lines.append("-" * 60)
        lines.append("")
    
    # Overall stats
    all_completed = [u for u in s.learning_units if u.get("status") in ("completed", "mastered")]
    if all_completed:
        overall_mastery = sum(calculate_unit_mastery(u) for u in all_completed) / len(all_completed)
        lines.append(f"Overall Mastery: {overall_mastery:.1f}/5")
        
        # Distribution
        dist = [0] * 5
        for u in all_completed:
            mastery = round(calculate_unit_mastery(u))
            if 0 <= mastery <= 5:
                dist[mastery - 1] += 1
        
        lines.append("")
        lines.append("Mastery Distribution:")
        for i in range(5):
            bar = "█" * dist[i] + "░" * (max(dist) - dist[i]) if max(dist) > 0 else ""
            lines.append(f"  {i+1}★: {bar} ({dist[i]} units)")
    
    return "\n".join(lines)


def get_unit_profile(state: dict, unit_id: int) -> str:
    """
    Get detailed profile for a specific learning unit.
    """
    s = StudentState(**state)
    
    unit = next((u for u in s.learning_units if u["id"] == unit_id), None)
    if not unit:
        return "Unit not found."
    
    mastery = calculate_unit_mastery(unit)
    
    lines = [
        f"📋 Learning Unit Profile",
        "=" * 60,
        "",
        f"Subject: {unit.get('subject')}",
        f"Chapter: {unit.get('chapter')}",
        f"Unit: {unit['unit_name']}",
        f"Type: {unit.get('unit_type', 'concept')}",
        "",
        f"Status: {unit.get('status', 'pending')}",
        f"Mastery: {'★' * round(mastery) + '☆' * (5 - round(mastery))}  ({mastery:.1f}/5)",
        f"Difficulty: {unit.get('difficulty', 'medium')}",
        "",
        f"⏱️  Time:",
        f"   Estimated: {unit.get('estimated_minutes', 0)} min",
        f"   Actual: {unit.get('actual_time_spent', 0)} min",
        f"   Attempts: {unit.get('attempts', 0)}",
        "",
    ]
    
    # Quiz stats
    if unit.get("quiz_history"):
        lines.append(f"📝 Quiz Performance:")
        for q in unit["quiz_history"][-3:]:
            lines.append(f"   {q['date'][:10]}: {q['score']}% ({q['correct']}/{q['questions']})")
        lines.append("")
    
    # Practice stats
    if unit.get("practice_history"):
        lines.append(f"✏️  Practice Sessions:")
        for p in unit["practice_history"][-3:]:
            lines.append(f"   {p['date'][:10]}: {p['score']}% ({p['questions_attempted']} questions)")
        lines.append("")
    
    # Revision history
    if unit.get("revision_history"):
        lines.append(f"🔄 Revision History:")
        for r in unit["revision_history"][-3:]:
            lines.append(f"   {r['date'][:10]}: {r['rating']}/5  ({r['time_spent']} min)")
        if unit.get("next_revision"):
            lines.append(f"   Next: {unit['next_revision']}")
        lines.append("")
    
    # Resources
    if unit.get("resources"):
        res = unit["resources"]
        if any(res.values()):
            lines.append("📚 Resources:")
            for rtype, items in res.items():
                if items:
                    lines.append(f"   {rtype.title()}: {len(items)} saved")
    
    return "\n".join(lines)
