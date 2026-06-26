"""
Full Integration Test: Learner Agent
Tests engagement monitor, layer progression, planner event handoff,
RAG grounding, and emotional adaptation.
Run: python -X utf8 test_learner_integration.py
"""

from app.agents.learner import LearnerAgent
from app.agents.resource_hub import KnowledgeHub
from app.agents.rag_engine import RAGEngine
from app.agents.engagement_monitor import EngagementMonitor
from app.llm import ask_gemini

SEP = "-" * 60

FCFS_NOTES = """
CPU SCHEDULING

1. Introduction
CPU scheduling decides which process runs on the CPU and when.
The goal is to maximise CPU utilisation and minimise waiting time.

2. FCFS - First Come First Served
FCFS is the simplest non-preemptive scheduling algorithm.
Processes are executed in the order they arrive in the ready queue.

Example:
  P1 arrival=0 burst=24, P2 arrival=1 burst=3, P3 arrival=2 burst=3
  Gantt: P1(0-24) P2(24-27) P3(27-30)
  Average waiting time = (0+23+25)/3 = 16 ms

Disadvantage: Convoy Effect
Short processes wait behind a long process, increasing turnaround time.

3. SJF - Shortest Job First
Selects the process with the smallest burst time.
Optimal for minimising average waiting time.
"""


class _LLMWrapper:
    """Thin wrapper so LearnerAgent can call llm.invoke()."""
    def invoke(self, prompt):
        class _R:
            content = ask_gemini(prompt)
        return _R()


def run():
    llm     = _LLMWrapper()
    state   = {}
    user_id = "student_1"

    # Shared planner state (simulates what planner would provide)
    planner_state = {
        "learning_units": [
            {"id": 1, "unit_name": "FCFS Algorithm", "chapter": "CPU Scheduling",
             "subject": "OS", "status": "pending", "estimated_minutes": 20},
            {"id": 2, "unit_name": "SJF Algorithm", "chapter": "CPU Scheduling",
             "subject": "OS", "status": "pending", "estimated_minutes": 20},
        ]
    }

    agent = LearnerAgent(llm, user_id, state)
    agent.wire_planner(planner_state)   # connect event bus

    # ── Step 1: Upload notes ──────────────────────────────────────────────────
    print(SEP)
    print("STEP 1: Upload notes → index into RAG")
    print(SEP)
    hub = KnowledgeHub(user_id, state)
    hub.upload_pdf("cpu_notes.txt", FCFS_NOTES, subject="OS")
    pdf = hub.get_resource_by_id("pdf_0")
    agent.rag_engine.index_chunks(
        "pdf_0", pdf["chunks"],
        {"filename": "cpu_notes.txt", "subject": "OS",
         "topics_covered": pdf["topics_covered"]}
    )
    stats = agent.rag_engine.get_rag_stats()
    print(f"  Indexed chunks : {stats['vector_db_size']}")

    # ── Step 2: Start session ────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 2: Start learning session for 'FCFS Algorithm'")
    print(SEP)
    result = agent.start_learning_session("FCFS Algorithm", "OS")
    print(f"  Type    : {result['type']}")
    print(f"  Message : {result['message']}")

    # ── Step 3: Layer 1 (intuitive) ──────────────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 3: Layer 1 — intuitive teaching")
    print(SEP)
    r1 = agent.process_learning_interaction(
        "teach me", {"current_layer": 1, "action": "teach", "subject": "OS"}
    )
    print(f"  Grounded  : {r1.get('grounded')}")
    print(f"  Sources   : {len(r1.get('sources', []))}")
    print(f"  Engagement: {r1.get('engagement')}")
    print(f"  Explanation preview: {r1.get('explanation','')[:200]}")

    # ── Step 4: Simulate confusion ───────────────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 4: Student says 'I don't understand this at all'")
    print(SEP)
    r2 = agent.process_learning_interaction(
        "I don't understand this at all", {"current_layer": 1, "subject": "OS"}
    )
    snap_after = r2.get("engagement", {})
    print(f"  Type       : {r2['type']}")
    print(f"  Confusion  : {snap_after.get('confusion')}%")
    print(f"  Style      : {snap_after.get('style')}")
    print(f"  Response preview: {r2.get('message','')[:200]}")

    # ── Step 5: Layer 2 (structured + SVG) ───────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 5: Layer 2 — structured teaching with SVG")
    print(SEP)
    r3 = agent.process_learning_interaction(
        "teach me", {"current_layer": 2, "action": "teach", "subject": "OS"}
    )
    svg = r3.get("svg", "")
    print(f"  Grounded  : {r3.get('grounded')}")
    print(f"  SVG size  : {len(svg)} chars")
    print(f"  SVG valid : {svg.strip().startswith('<svg') or svg.strip().startswith('<?xml')}")
    print(f"  Engagement: {r3.get('engagement')}")

    # ── Step 6: Frustration path ─────────────────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 6: Simulate frustration → empathy-first response")
    print(SEP)
    for msg in ["I don't understand", "I've asked this same question again"]:
        agent.process_learning_interaction(msg, {"current_layer": 1, "subject": "OS"})
    r4 = agent.process_learning_interaction(
        "still not getting it", {"current_layer": 1, "subject": "OS"}
    )
    snap4 = r4.get("engagement", {})
    print(f"  Frustration  : {snap4.get('frustration')}%")
    print(f"  Intervention : {snap4.get('intervention')}")
    print(f"  Response preview: {r4.get('message','')[:200]}")

    # ── Step 7: Planner event handoff ─────────────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 7: Complete unit → planner event fired → planner state updated")
    print(SEP)
    print(f"  Before: planner unit status = {planner_state['learning_units'][0]['status']}")
    # Manually emit completion to test the wiring
    from app.event_bus import Event, EventType
    evt = Event(
        event_type=EventType.UNIT_COMPLETED,
        source="learner", target="planner",
        data={"learning_unit": "FCFS Algorithm", "mastery_score": 0.85},
        priority=8
    )
    agent.event_bus.emit(evt)
    print(f"  After : planner unit status = {planner_state['learning_units'][0]['status']}")
    print(f"  Mastery stored (0-5): {planner_state['learning_units'][0].get('mastery')}")
    print(f"  Next unit ready     : {planner_state.get('next_unit_ready')}")

    # ── Step 8: Engagement monitor in isolation ───────────────────────────────
    print(f"\n{SEP}")
    print("STEP 8: Engagement Monitor — rule-based signal accumulation")
    print(SEP)
    monitor = EngagementMonitor()
    interactions = [
        ("I got it!", None, 8.0, 0),
        ("makes sense now", None, 5.0, 0),
        ("I don't understand this at all", None, None, 0),
        ("still confused even after explaining", None, None, 1),
        ("I've asked this same question three times", None, None, 0),
    ]
    for text, qs, rt, wrong in interactions:
        monitor.record_interaction(text, qs, rt, wrong)
    snap = monitor.snapshot()
    print(f"  Engagement   : {snap.engagement_pct}%")
    print(f"  Confusion    : {snap.confusion_pct}%")
    print(f"  Frustration  : {snap.frustration_pct}%")
    print(f"  Confidence   : {snap.confidence_pct}%")
    print(f"  Sentiment    : {snap.sentiment}")
    print(f"  Style        : {snap.recommended_style}")
    print(f"  Intervention : {snap.intervention_needed}")

    # ── Step 9: Prompt enrichment ────────────────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 9: Prompt enrichment — engagement context injected")
    print(SEP)
    base   = "Explain FCFS scheduling algorithm."
    enriched = monitor.enrich_prompt(base, snap, "FCFS", used_analogies=["coffee shop"])
    print(f"  Base prompt length    : {len(base)}")
    print(f"  Enriched prompt length: {len(enriched)}")
    print(f"  Contains confusion    : {'Confusion' in enriched}")
    print(f"  Contains frustration  : {'Frustration' in enriched}")
    print(f"  Skips 'coffee shop'   : {'coffee shop' in enriched}")
    print(f"\n  Enriched prompt:\n")
    for line in enriched.split("\n")[:12]:
        print(f"    {line}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("RESULTS SUMMARY")
    print(SEP)
    checks = [
        ("Layer 1 grounded",                 r1.get("grounded") is True),
        ("Layer 1 has engagement snapshot",  "engagement" in r1),
        ("Confusion detected after 'don't understand'",
                                             snap_after.get("confusion", 0) > 0),
        ("Layer 2 SVG generated",            len(svg) > 100),
        ("Frustration triggers intervention",snap4.get("intervention") is True or snap4.get("frustration", 0) >= 25),
        ("Planner unit marked completed",    planner_state["learning_units"][0]["status"] == "completed"),
        ("Next unit unlocked",               planner_state.get("next_unit_ready") is not None),
        ("Prompt enrichment works",          len(enriched) > len(base)),
        ("Enriched prompt blocks used analogy", "coffee shop" in enriched),
    ]

    all_pass = True
    for label, passed in checks:
        icon = "✓" if passed else "✗"
        print(f"  {icon} {label}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("✅ All integration checks passed.")
    else:
        print("❌ Some checks failed — review output above.")


if __name__ == "__main__":
    run()
