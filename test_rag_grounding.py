"""
RAG Grounding Test — verifies Grounded: True when a PDF is uploaded before querying.
Run: python -X utf8 test_rag_grounding.py
"""

from app.agents.rag_engine import RAGEngine
from app.agents.resource_hub import KnowledgeHub
from app.llm import ask_gemini

SEP = "-" * 60

# Minimal stub so RAGEngine.generate_grounded_explanation can call llm.invoke()
class _LLMStub:
    def invoke(self, prompt):
        class _R:
            content = ask_gemini(prompt)
        return _R()


FCFS_NOTES = """
CPU SCHEDULING

1. Introduction
CPU scheduling decides which process runs on the CPU and when.
The goal is to maximise CPU utilisation and minimise waiting time.

2. FCFS – First Come First Served
FCFS is the simplest scheduling algorithm.
Processes are executed in the order they arrive in the ready queue.
It is non-preemptive: once a process starts, it runs to completion.

Example:
  Process | Arrival | Burst
  P1      |   0     |  24
  P2      |   1     |   3
  P3      |   2     |   3

Gantt chart: P1(0-24) P2(24-27) P3(27-30)
Average waiting time = (0 + 23 + 25) / 3 = 16 ms

Disadvantage: Convoy Effect
Short processes wait behind a long process, causing poor turnaround time.

3. SJF – Shortest Job First
Selects the process with the smallest burst time next.
Can be preemptive (SRTF) or non-preemptive.
Optimal for minimising average waiting time.
"""


def run():
    state = {}
    user_id = "test_user"
    llm = _LLMStub()

    hub  = KnowledgeHub(user_id, state)
    rag  = RAGEngine(llm, user_id, state)

    # ── Step 1: Upload notes ──────────────────────────────────────────────────
    print(SEP)
    print("STEP 1: Upload FCFS notes to Knowledge Hub")
    print(SEP)
    result = hub.upload_pdf("cpu_scheduling_notes.txt", FCFS_NOTES, subject="OS")
    print(f"  Chunks created : {result['chunks_created']}")
    print(f"  Topics found   : {result['topics_found']}")
    print(f"  Resource ID    : {result['resource_id']}")

    # ── Step 2: Index chunks into RAG ─────────────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 2: Index chunks into RAG engine")
    print(SEP)
    pdf = hub.get_resource_by_id(result["resource_id"])
    indexed = rag.index_chunks(
        resource_id=result["resource_id"],
        chunks=pdf["chunks"],
        resource_metadata={"filename": "cpu_scheduling_notes.txt", "subject": "OS",
                           "topics_covered": pdf["topics_covered"]}
    )
    stats = rag.get_rag_stats()
    print(f"  Indexed chunks : {indexed}")
    print(f"  Vector DB size : {stats['vector_db_size']}")

    # ── Step 3: Query — Layer 1 (intuitive) ───────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 3: Layer 1 query — explain FCFS intuitively")
    print(SEP)
    r1 = rag.generate_grounded_explanation(
        topic="FCFS",
        query="explain FCFS intuitively with real-life analogies",
        context={"layer": 1, "subject": "OS"}
    )
    _print_result(r1, "Layer 1")

    # ── Step 4: Query — Layer 2 (structured) ──────────────────────────────────
    print(f"\n{SEP}")
    print("STEP 4: Layer 2 query — structured explanation")
    print(SEP)
    r2 = rag.generate_grounded_explanation(
        topic="FCFS",
        query="structured explanation with definition, components, step-by-step",
        context={"layer": 2, "subject": "OS"}
    )
    _print_result(r2, "Layer 2")

    # ── Step 5: Query — convoy effect (specific detail) ───────────────────────
    print(f"\n{SEP}")
    print("STEP 5: Specific detail query — convoy effect")
    print(SEP)
    r3 = rag.generate_grounded_explanation(
        topic="convoy effect",
        query="what is convoy effect in FCFS scheduling",
        context={"layer": 1, "subject": "OS"}
    )
    _print_result(r3, "Convoy Effect")

    # ── Step 6: Query — unrelated topic (should be Grounded: False) ───────────
    print(f"\n{SEP}")
    print("STEP 6: Unrelated topic — should NOT be grounded")
    print(SEP)
    r4 = rag.generate_grounded_explanation(
        topic="Quantum Mechanics",
        query="explain double-slit experiment",
        context={"layer": 1, "subject": "Physics"}
    )
    _print_result(r4, "Unrelated (Physics)")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("RESULTS SUMMARY")
    print(SEP)
    checks = [
        ("Layer 1 grounded",          r1["grounded"] is True),
        ("Layer 2 grounded",          r2["grounded"] is True),
        ("Convoy effect grounded",     r3["grounded"] is True),
        ("Unrelated NOT grounded",     r4["grounded"] is False),
        ("Layer 1 has sources",        len(r1.get("sources", [])) > 0),
        ("Layer 2 has sources",        len(r2.get("sources", [])) > 0),
    ]
    all_pass = True
    for label, passed in checks:
        icon = "✓" if passed else "✗"
        print(f"  {icon} {label}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("✅ All grounding checks passed — Grounded: True is now reliable.")
    else:
        print("❌ Some checks failed. Review similarity scores above.")


def _print_result(r: dict, label: str):
    grounded   = r.get("grounded", False)
    sources    = r.get("sources", [])
    chunks     = r.get("chunks_used", 0)
    explanation = r.get("explanation", "")
    icon = "✓" if grounded else "✗"
    print(f"  {icon} Grounded  : {grounded}")
    print(f"    Sources   : {len(sources)}")
    print(f"    Chunks    : {chunks}")
    if sources:
        for s in sources:
            print(f"    └─ {s['filename']}  ({s['chunks_used']} chunks)")
    print(f"    Explanation preview:")
    for line in explanation[:300].split("\n"):
        print(f"      {line}")
    if len(explanation) > 300:
        print(f"      ... ({len(explanation) - 300} more chars)")


if __name__ == "__main__":
    run()
