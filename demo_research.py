"""
RESEARCH AGENT DEMO
  CuriosityEngine  - deeper questions, connections, open problems
  ResourceFinder   - papers, repos, real-world applications, courses
  ProjectIdeator   - buildable projects from mastered concepts
  Full explore()   - all three in one pipeline call
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.research import ResearchAgent, CuriosityEngine, ResourceFinder, ProjectIdeator


# ---------------------------------------------------------------------------
# Mock LLM
# ---------------------------------------------------------------------------

class MockLLM:
    def invoke(self, prompt):
        class R:
            def __init__(self, c): self.content = c

        p = prompt.lower()

        if "curiosity map" in p or "deeper_questions" in p:
            return R('''{
  "deeper_questions": [
    "Why does FCFS cause the convoy effect and how can it be avoided?",
    "How does FCFS perform on multi-core CPUs?",
    "What happens when all processes have the same arrival time?",
    "How do real OS schedulers handle FCFS in batch systems?"
  ],
  "connections": [
    {"topic": "Round Robin", "how": "RR is FCFS with time quanta — solves convoy effect"},
    {"topic": "Queue Data Structure", "how": "FCFS is a direct application of FIFO queue"}
  ],
  "open_problems": [
    "How can FCFS be made adaptive for heterogeneous workloads?",
    "Can ML predict optimal process ordering better than pure FCFS?"
  ],
  "next_rabbit_hole": "Explore how Linux CFS replaced FCFS/RR with a fair-share scheduler."
}''')

        if "concept_connections" in p or "direct conceptual" in p:
            return R('''[
  {"from": "Queue Data Structure", "to": "FCFS", "relationship": "FCFS is a FIFO queue applied to process scheduling"},
  {"from": "Round Robin", "to": "FCFS", "relationship": "Round Robin extends FCFS with time-slice preemption"}
]''')

        if "find learning resources" in p or "papers" in p:
            return R('''{
  "papers": [
    {"title": "Analysis of CPU Scheduling Algorithms", "authors": "Smith et al.", "year": 2021,
     "relevance": "Benchmarks FCFS against SJF and RR on real workloads"},
    {"title": "Convoy Effect Mitigation in Batch Schedulers", "authors": "Lee & Wang", "year": 2022,
     "relevance": "Directly addresses FCFS convoy problem with a hybrid approach"}
  ],
  "repos": [
    {"name": "cpu-scheduling-simulator", "url": "https://github.com/example/cpu-scheduling-simulator",
     "description": "Python CLI simulator for FCFS, SJF, RR with Gantt chart output"},
    {"name": "os-algorithms-viz", "url": "https://github.com/example/os-algorithms-viz",
     "description": "Web visualiser for CPU scheduling algorithms with step-by-step animation"}
  ],
  "applications": [
    {"domain": "Print Spoolers", "example": "FCFS used in printer queues — first job sent prints first",
     "why_relevant": "Shows FCFS in a familiar real-world context"},
    {"domain": "Batch Processing", "example": "Mainframe job queues use FCFS for overnight batch runs",
     "why_relevant": "Historical use case still active in HPC clusters"}
  ],
  "courses": [
    {"title": "Operating Systems: Three Easy Pieces", "platform": "ostep.org",
     "url": "https://ostep.org", "level": "intermediate"}
  ]
}''')

        if "project ideas" in p or "buildable" in p:
            return R('''[
  {
    "title": "CPU Scheduling Visualiser",
    "description": "Build a web app that animates FCFS, SJF, and Round Robin side by side. Input process burst times and watch the Gantt chart build in real time.",
    "tech_stack": ["Python", "Flask", "HTML/CSS/JS"],
    "concepts_used": ["FCFS Scheduling", "Round Robin", "Gantt Charts"],
    "estimated_hours": 8,
    "difficulty": "medium",
    "wow_factor": "Interactive comparison of all scheduling algorithms with live metrics."
  },
  {
    "title": "Mini Process Scheduler CLI",
    "description": "A command-line OS scheduler simulator. Feed it a process table and watch it execute FCFS with computed waiting and turnaround times printed step by step.",
    "tech_stack": ["Python"],
    "concepts_used": ["FCFS Scheduling", "Queue Data Structure"],
    "estimated_hours": 4,
    "difficulty": "easy",
    "wow_factor": "Printable Gantt chart and average waiting time comparison table."
  },
  {
    "title": "Adaptive Scheduler Research Prototype",
    "description": "Prototype an ML-assisted scheduler that predicts burst time from process history and reorders the FCFS queue to minimise average waiting time.",
    "tech_stack": ["Python", "scikit-learn"],
    "concepts_used": ["FCFS Scheduling", "Machine Learning basics"],
    "estimated_hours": 20,
    "difficulty": "hard",
    "wow_factor": "Combines OS scheduling theory with ML — strong hackathon or research project."
  }
]''')

        if "innovation" in p or "research/innovation prompt" in p:
            return R(
                "Can a lightweight ML model trained on process history predict burst times "
                "well enough to reorder an FCFS queue and reduce average waiting time below "
                "that of SJF — without the head-of-line blocking SJF introduces for long jobs? "
                "Implement this as a Python simulation and measure against standard FCFS and SJF."
            )

        return R("Research response.")


# ---------------------------------------------------------------------------
# Shared state with mastered topics
# ---------------------------------------------------------------------------

def _make_state():
    state = {
        "goal": "Semester Exam",
        "learning_units": [
            {"id": 1, "unit_name": "FCFS Scheduling", "subject": "Operating Systems",
             "status": "pending"}
        ],
        "learning_passports": {
            "student:FCFS Scheduling": {
                "topic": "FCFS Scheduling", "learning_unit": "FCFS Scheduling",
                "status": "completed", "mastery": 4.2
            },
            "student:Queue Data Structure": {
                "topic": "Queue Data Structure", "learning_unit": "Queue Data Structure",
                "status": "completed", "mastery": 3.8
            },
            "student:Round Robin": {
                "topic": "Round Robin", "learning_unit": "Round Robin",
                "status": "completed", "mastery": 3.5
            },
        }
    }
    return state


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_curiosity_engine():
    print("\n[Module 1] CuriosityEngine")
    print("-" * 70)

    engine  = CuriosityEngine(MockLLM())
    mastered = ["FCFS Scheduling", "Queue Data Structure", "Round Robin"]

    cmap = engine.generate_curiosity_map("FCFS Scheduling", mastered, "Operating Systems")

    print(f"  Deeper questions : {len(cmap['deeper_questions'])}")
    for q in cmap["deeper_questions"][:2]:
        print(f"    - {q}")

    print(f"  Connections      : {len(cmap['connections'])}")
    for c in cmap["connections"]:
        print(f"    - {c['topic']}: {c['how']}")

    print(f"  Open problems    : {len(cmap['open_problems'])}")
    print(f"  Next rabbit hole : {cmap['next_rabbit_hole']}")

    assert len(cmap["deeper_questions"]) >= 2
    assert len(cmap["connections"])      >= 1
    assert len(cmap["open_problems"])    >= 1
    assert cmap["next_rabbit_hole"]

    conns = engine.generate_concept_connections("FCFS Scheduling", mastered)
    print(f"  Concept links    : {len(conns)}")
    for cn in conns:
        print(f"    {cn['from']} -> {cn['to']}: {cn['relationship']}")

    print("  CuriosityEngine PASS")


def test_resource_finder():
    print("\n[Module 2] ResourceFinder")
    print("-" * 70)

    finder  = ResourceFinder(MockLLM())
    result  = finder.find_resources("FCFS Scheduling", "Operating Systems")

    papers  = result.get("papers", [])
    repos   = result.get("repos", [])
    apps    = result.get("applications", [])
    courses = result.get("courses", [])

    print(f"  Papers      : {len(papers)}")
    for p in papers:
        print(f"    [{p.get('year','')}] {p['title']} — {p['relevance']}")

    print(f"  Repos       : {len(repos)}")
    for r in repos:
        print(f"    {r['name']} — {r['description']}")

    print(f"  Applications: {len(apps)}")
    for a in apps:
        print(f"    {a['domain']}: {a['example']}")

    print(f"  Courses     : {len(courses)}")

    assert len(papers) >= 1
    assert len(repos)  >= 1
    assert len(apps)   >= 1
    print("  ResourceFinder PASS")


def test_project_ideator():
    print("\n[Module 3] ProjectIdeator")
    print("-" * 70)

    ideator  = ProjectIdeator(MockLLM())
    mastered = ["FCFS Scheduling", "Queue Data Structure", "Round Robin"]
    ideas    = ideator.generate_project_ideas(mastered, goal="Semester Exam")

    print(f"  Projects generated: {len(ideas)}")
    for i, p in enumerate(ideas, 1):
        print(f"\n  {i}. {p['title']}  [{p.get('difficulty','?')}]  ~{p.get('estimated_hours','?')}h")
        print(f"     {p['description'][:90]}...")
        print(f"     Stack : {', '.join(p.get('tech_stack', []))}")
        print(f"     Concepts: {', '.join(p.get('concepts_used', []))}")
        print(f"     Wow: {p.get('wow_factor', '')}")

    assert len(ideas) >= 1
    assert ideas[0]["title"]
    assert ideas[0]["tech_stack"]

    open_problems = ["How can FCFS be adaptive?", "Can ML beat pure FCFS ordering?"]
    prompt = ideator.generate_innovation_prompt("FCFS Scheduling", open_problems)
    print(f"\n  Innovation prompt ({len(prompt)} chars):")
    print(f"  {prompt[:150]}...")
    assert len(prompt) > 20

    print("  ProjectIdeator PASS")


def test_full_explore():
    print("\n[Full Pipeline] ResearchAgent.explore()")
    print("-" * 70)

    state  = _make_state()
    agent  = ResearchAgent(MockLLM(), state)
    result = agent.explore("FCFS Scheduling", user_id="student")

    print(f"  Topic         : {result['topic']}")
    print(f"  Subject       : {result['subject']}")
    print(f"  Deeper Qs     : {len(result['curiosity_map']['deeper_questions'])}")
    print(f"  Connections   : {len(result['connections'])}")
    print(f"  Papers        : {len(result['resources'].get('papers', []))}")
    print(f"  Repos         : {len(result['resources'].get('repos', []))}")
    print(f"  Projects      : {len(result['projects'])}")
    print(f"  Innovation    : {result['innovation_prompt'][:80]}...")
    print(f"  Persisted     : {'FCFS Scheduling' in state.get('research_output', {})}")

    assert result["curiosity_map"]["deeper_questions"]
    assert result["resources"]["papers"]
    assert result["projects"]
    assert result["innovation_prompt"]
    assert "FCFS Scheduling" in state["research_output"]

    print("  Full explore() PASS")


def test_orchestrator_routing():
    print("\n[Routing] Orchestrator -> Research")
    print("-" * 70)

    from app.agents.orchestrator import classify_intent
    cases = [
        ("suggest a project idea for OS",    "research"),
        ("find papers on FCFS scheduling",   "research"),
        ("explore curiosity about Round Robin", "research"),
        ("what can I build with what I know", "research"),
        ("I want to innovate something",     "research"),
    ]
    for msg, expected in cases:
        got = classify_intent(msg)
        mark = "OK" if got == expected else "FAIL"
        print(f"  [{mark}] '{msg}' -> {got}")
        assert got == expected, f"Expected {expected}, got {got}"

    print("  Routing PASS")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n" + "="*70)
    print("  RESEARCH AGENT DEMO")
    print("  CuriosityEngine + ResourceFinder + ProjectIdeator")
    print("="*70)

    test_curiosity_engine()
    test_resource_finder()
    test_project_ideator()
    test_full_explore()
    test_orchestrator_routing()

    print("\n" + "="*70)
    print("  ALL RESEARCH AGENT TESTS PASS")
    print("="*70)
    print(
        "\n  Architecture:"
        "\n"
        "\n            ORCHESTRATOR"
        "\n                 |"
        "\n    +------------+------------+"
        "\n    |            |            |"
        "\n  Planner     Learner     Research"
        "\n  (frozen)    (frozen)    (active)"
        "\n                              |"
        "\n             +----------------+----------------+"
        "\n             |                |                |"
        "\n       CuriosityEngine  ResourceFinder  ProjectIdeator"
        "\n"
        "\n  Research Agent: ready for integration."
        "\n"
    )
