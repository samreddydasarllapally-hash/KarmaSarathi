"""
Research Agent — 7-Stage Research Mentor

Two Entry Modes:
  Mode 1 — Learning-Driven Research
    Planner → Learner → Research
    After mastering a topic, explores applications, papers, projects

  Mode 2 — Idea-First Research
    Student has an idea (e.g. "I want to build an AI drone")
    Research breaks it down, finds skill gaps, hands off to Planner

Five Research Modes (within a session):
  explore         — Stage 1-3: applications → curiosity → questions
  problem_finder  — Stage 2 variant: what problems still exist?
  idea_generator  — Stage 5: innovation suggestions
  build_mentor    — Stage 6: multi-turn project supervisor
  reflection      — Stage 7: post-project reflection loop
  paper           — Stage 4: paper simplification

7-Stage Pipeline:
  Stage 1 — Real World Applications
  Stage 2 — Curiosity Builder (scenario question)
  Stage 3 — Research Questions (level-based Socratic)
  Stage 4 — Paper Simplification (RAG-style summary)
  Stage 5 — Innovation Suggestions
  Stage 6 — Project Builder (Build Mentor)
  Stage 7 — Planner Update (session report)

Inter-Agent Handoffs:
  research → learner   (teach a missing skill before continuing)
  research → planner   (build a full roadmap for a project idea)
  learner  → research  (return after learning completes)
  research ← progress  (post-mastery offer triggers research)
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from app.state import StudentState
from app.llm import ask_gemini


# ─────────────────────────────────────────────────────────────────────────────
# LLM wrapper + JSON parser
# ─────────────────────────────────────────────────────────────────────────────

def _llm(prompt: str) -> str:
    return ask_gemini(prompt)


def _parse_json(raw: str, fallback):
    try:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        s = clean.find("{") if isinstance(fallback, dict) else clean.find("[")
        e = clean.rfind("}") + 1 if isinstance(fallback, dict) else clean.rfind("]") + 1
        if s != -1 and e > s:
            return json.loads(clean[s:e])
    except Exception:
        pass
    return fallback


# ─────────────────────────────────────────────────────────────────────────────
# Research Profile helpers
# ─────────────────────────────────────────────────────────────────────────────

def _init_profile(profile: dict) -> dict:
    defaults = {
        "applications_viewed": 0,
        "problems_explored": 0,
        "ideas_generated": 0,
        "projects_started": 0,
        "projects_completed": 0,
        "papers_read": 0,
        "innovation_score": 0,
        "research_level": "beginner",
        "prototype_built": False,
        "research_sessions": [],
    }
    for k, v in defaults.items():
        profile.setdefault(k, v)
    return profile


def _update_research_level(profile: dict) -> dict:
    score = profile.get("innovation_score", 0)
    papers = profile.get("papers_read", 0)
    ideas = profile.get("ideas_generated", 0)
    projects = profile.get("projects_started", 0)
    total = score + papers * 5 + ideas * 3 + projects * 10
    if total >= 100:
        profile["research_level"] = "advanced"
    elif total >= 40:
        profile["research_level"] = "intermediate"
    else:
        profile["research_level"] = "beginner"
    return profile


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — Real World Applications
# ─────────────────────────────────────────────────────────────────────────────

def _stage1_applications(topic: str, subject: str) -> dict:
    prompt = f"""A student just mastered: {topic} (subject: {subject})

Generate real-world applications across 6+ different domains. Return ONLY JSON:
{{
  "domains": [
    {{
      "name": "Healthcare",
      "example": "Cancer detection using CNN in radiology",
      "impact": "Reduces diagnosis time by 60%",
      "companies": ["Google Health", "Zebra Medical"]
    }}
  ],
  "wow_fact": "One surprising fact about {topic} in the real world",
  "biggest_impact": "The single most impactful application of {topic}"
}}
Include 6 domains. Be specific and inspiring."""
    return _parse_json(_llm(prompt), {
        "domains": [
            {"name": "Healthcare", "example": f"{topic} in medical imaging", "impact": "Improves diagnosis accuracy", "companies": []},
            {"name": "Industry", "example": f"{topic} in production systems", "impact": "Increases efficiency", "companies": []},
        ],
        "wow_fact": f"{topic} powers systems processing millions of requests daily.",
        "biggest_impact": f"{topic} is transforming how we build intelligent systems."
    })


def _format_stage1(topic: str, data: dict) -> str:
    lines = [
        f"🌍 **Where is {topic} used in the real world?**\n",
        f"💡 *{data.get('wow_fact', '')}*\n",
        "Here are the domains where this is making a real difference:\n"
    ]
    for d in data.get("domains", []):
        companies = f"  _(e.g. {', '.join(d.get('companies', [])[:2])})_" if d.get("companies") else ""
        lines.append(f"**{d['name']}**{companies}")
        lines.append(f"  → {d.get('example', '')}")
        lines.append(f"  ✓ {d.get('impact', '')}\n")

    lines.append(f"\n🏆 **Biggest impact:** {data.get('biggest_impact', '')}\n")
    lines.append("---")
    lines.append("Want to go deeper? I can:")
    lines.append("  • `problems` — Show open research problems in these domains")
    lines.append("  • `innovate` — Generate an innovation idea for you")
    lines.append("  • `project` — Design a project you can build")
    lines.append("  • `paper` — Find and simplify a research paper")
    lines.append("  • `questions` — Challenge you with research-level questions")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — Curiosity Builder (scenario-based)
# ─────────────────────────────────────────────────────────────────────────────

def _stage2_curiosity(topic: str, subject: str) -> dict:
    prompt = f"""Create an immersive scenario for a student who just learned {topic}.

The scenario should:
1. Place them in a real organization (ISRO, hospital, Tesla, etc.)
2. Describe a real problem they need to solve using {topic}
3. Ask ONE open-ended question that makes them think like an engineer

Return ONLY JSON:
{{
  "organization": "Name of the org",
  "role": "Their role (e.g. Junior ML Engineer at ISRO)",
  "scenario": "2-3 sentence vivid description of the situation",
  "challenge": "The specific technical problem to solve",
  "question": "One open-ended question that sparks curiosity",
  "hint": "A gentle hint to guide their thinking"
}}"""
    return _parse_json(_llm(prompt), {
        "organization": "Tech Startup",
        "role": f"ML Engineer using {topic}",
        "scenario": f"Your team needs to deploy {topic} in a real system with constraints.",
        "challenge": f"How do you optimize {topic} for production?",
        "question": f"What would you change about {topic} to make it work better here?",
        "hint": "Think about data, compute, and accuracy trade-offs."
    })


def _format_stage2(data: dict) -> str:
    lines = [
        f"🎭 **Imagine you are a {data.get('role', 'researcher')}**\n",
        f"📍 *{data.get('scenario', '')}*\n",
        f"⚠️ **The Challenge:**",
        f"  {data.get('challenge', '')}\n",
        f"🤔 **Here's what I want you to think about:**",
        f"  _{data.get('question', '')}_\n",
        f"💡 *Hint: {data.get('hint', '')}*\n",
        "---",
        "Take your time — type your thoughts and I'll respond like a research mentor.",
        "Or type `skip` to jump to research questions."
    ]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2b — Problem Finder Mode
# ─────────────────────────────────────────────────────────────────────────────

def _problem_finder(topic: str, subject: str) -> dict:
    prompt = f"""What are the REAL unsolved problems in {topic} (subject: {subject})?

Think like a researcher reviewing the current state of the art. Return ONLY JSON:
{{
  "open_problems": [
    {{
      "problem": "Clear description of the unsolved problem",
      "why_hard": "Why this is technically challenging",
      "current_approaches": ["Approach 1", "Approach 2"],
      "limitation": "What current approaches fail at",
      "research_opportunity": "What a student could explore"
    }}
  ],
  "biggest_gap": "The single most important unsolved problem",
  "entry_point": "Where a beginner researcher could contribute"
}}
Include 3-4 problems at different difficulty levels."""
    return _parse_json(_llm(prompt), {
        "open_problems": [
            {
                "problem": f"Scalability of {topic} in real-time systems",
                "why_hard": "Requires low latency and high accuracy simultaneously",
                "current_approaches": ["Quantization", "Pruning"],
                "limitation": "Accuracy drops significantly at high compression",
                "research_opportunity": "Design adaptive compression that preserves accuracy"
            }
        ],
        "biggest_gap": f"Making {topic} reliable in low-resource environments",
        "entry_point": f"Start with benchmarking existing {topic} methods on a new dataset"
    })


def _format_problem_finder(topic: str, data: dict) -> str:
    lines = [
        f"🔬 **Open Research Problems in {topic}**\n",
        f"🎯 **Biggest Gap:** {data.get('biggest_gap', '')}\n",
        f"🚪 **Entry Point for You:** {data.get('entry_point', '')}\n",
        "---"
    ]
    for i, p in enumerate(data.get("open_problems", []), 1):
        lines.append(f"\n**Problem {i}: {p.get('problem', '')}**")
        lines.append(f"  ❓ Why it's hard: {p.get('why_hard', '')}")
        current = p.get("current_approaches", [])
        if current:
            lines.append(f"  🔧 Current approaches: {', '.join(current)}")
        lines.append(f"  ⚠️ Limitation: {p.get('limitation', '')}")
        lines.append(f"  💡 Your opportunity: _{p.get('research_opportunity', '')}_")
    lines.append("\n---")
    lines.append("Type `innovate` to generate an idea tackling one of these problems.")
    lines.append("Type `project` to design a research project around one.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — Research Questions (Socratic, level-based)
# ─────────────────────────────────────────────────────────────────────────────

def _stage3_questions(topic: str, subject: str, level: str = "beginner") -> dict:
    prompt = f"""Generate research-level Socratic questions for {topic} (subject: {subject}).
Student research level: {level}

Return ONLY JSON:
{{
  "beginner": [
    {{"question": "...", "why_asked": "What thinking this develops", "hint": "..."}}
  ],
  "intermediate": [
    {{"question": "...", "why_asked": "...", "hint": "..."}}
  ],
  "advanced": [
    {{"question": "...", "why_asked": "...", "hint": "..."}}
  ],
  "challenge": "One interview-level question that even experts find tricky"
}}
Each level should have 2-3 questions that progressively deepen thinking."""
    return _parse_json(_llm(prompt), {
        "beginner": [{"question": f"Why was {topic} created?", "why_asked": "Builds historical context", "hint": "Think about what problem it solved"}],
        "intermediate": [{"question": f"What are the trade-offs in {topic}?", "why_asked": "Builds systems thinking", "hint": "Consider speed vs accuracy"}],
        "advanced": [{"question": f"How would you improve {topic} for edge cases?", "why_asked": "Builds research thinking", "hint": "Think about distribution shift"}],
        "challenge": f"Design a variant of {topic} that works with 10x less data. What would you change and why?"
    })


def _format_stage3(topic: str, data: dict, level: str) -> str:
    level_icon = {"beginner": "🟢", "intermediate": "🟡", "advanced": "🔴"}.get(level, "🟢")
    lines = [
        f"🧠 **Research Questions on {topic}** {level_icon} {level.capitalize()} Level\n",
        "These aren't trivia questions. Take time to think deeply.\n"
    ]

    questions = data.get(level, data.get("beginner", []))
    for i, q in enumerate(questions, 1):
        lines.append(f"**Q{i}. {q.get('question', '')}**")
        lines.append(f"  🎯 _{q.get('why_asked', '')}_")
        lines.append(f"  💡 Hint: {q.get('hint', '')}\n")

    challenge = data.get("challenge", "")
    if challenge:
        lines.append(f"---\n⚡ **Challenge Question:**")
        lines.append(f"  _{challenge}_\n")

    lines.append("---")
    lines.append("Answer any question — I'll respond as your research mentor.")
    lines.append("Type `beginner` / `intermediate` / `advanced` to switch levels.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — Paper Simplification (RAG-style)
# ─────────────────────────────────────────────────────────────────────────────

def _stage4_paper(topic: str, paper_title: str = "") -> dict:
    if not paper_title:
        paper_title = f"Recent advances in {topic}"
    prompt = f"""Simplify this research paper for an undergraduate student:
Paper: "{paper_title}" (related to {topic})

Return ONLY JSON:
{{
  "title": "Paper title",
  "year": 2023,
  "venue": "Conference/journal name",
  "one_line": "What this paper does in one sentence",
  "idea": "The core innovation — what new idea did they propose?",
  "method": "How they implemented it — key technical approach",
  "dataset": "What data they used and why",
  "results": "Main results — what numbers or improvements did they achieve?",
  "limitations": ["Limitation 1", "Limitation 2"],
  "future_work": ["What the authors suggest next", "A gap you could explore"],
  "your_takeaway": "What you as a student should remember from this paper",
  "related_papers": ["Paper title 1", "Paper title 2"]
}}"""
    return _parse_json(_llm(prompt), {
        "title": paper_title,
        "year": 2023,
        "venue": "arXiv",
        "one_line": f"A new approach to {topic} that improves performance.",
        "idea": f"The authors propose a novel method for {topic}.",
        "method": "They use a combination of existing techniques with a key modification.",
        "dataset": "Evaluated on standard benchmarks.",
        "results": "Outperforms baselines by a significant margin.",
        "limitations": ["Requires large compute", "Not tested in real-time"],
        "future_work": ["Extend to low-resource settings", "Apply to other domains"],
        "your_takeaway": f"Understand the core contribution and how it improves {topic}.",
        "related_papers": []
    })


def _format_stage4(data: dict) -> str:
    lines = [
        f"📄 **Paper:** {data.get('title', 'Unknown')} ({data.get('year', '')}) — _{data.get('venue', '')}_\n",
        f"**In one sentence:** {data.get('one_line', '')}\n",
        f"---",
        f"**💡 The Idea:**",
        f"  {data.get('idea', '')}\n",
        f"**⚙️ The Method:**",
        f"  {data.get('method', '')}\n",
        f"**📊 Dataset:**",
        f"  {data.get('dataset', '')}\n",
        f"**📈 Results:**",
        f"  {data.get('results', '')}\n",
    ]
    limits = data.get("limitations", [])
    if limits:
        lines.append("**⚠️ Limitations:**")
        for l in limits:
            lines.append(f"  • {l}")
        lines.append("")

    future = data.get("future_work", [])
    if future:
        lines.append("**🔭 Future Work / Your Opportunity:**")
        for f_item in future:
            lines.append(f"  → {f_item}")
        lines.append("")

    lines.append(f"**🎓 Your Takeaway:**")
    lines.append(f"  _{data.get('your_takeaway', '')}_\n")

    related = data.get("related_papers", [])
    if related:
        lines.append("**📚 Related Papers:**")
        for r in related:
            lines.append(f"  • {r}")
        lines.append("")

    lines.append("---")
    lines.append("Type `another paper` or `innovate` to build on this research.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 5 — Innovation Suggestions (Practical Solution Engine)
# ─────────────────────────────────────────────────────────────────────────────

def _stage5_innovate(topic: str, subject: str, student_level: str = "beginner") -> dict:
    prompt = f"""Generate a concrete research innovation idea for a {student_level} student who knows {topic}.

Think like a research supervisor guiding a first project. Return ONLY JSON:
{{
  "idea_title": "Short punchy title",
  "current_problem": "What specific problem exists today in the real world",
  "your_solution": "The student's proposed approach using {topic}",
  "how_it_works": "Step-by-step: how this solution would work technically",
  "novelty": "What makes this different from existing solutions",
  "difficulty": "⭐⭐☆☆",
  "estimated_weeks": 3,
  "datasets": ["Dataset name and where to find it"],
  "tools": ["Python", "TensorFlow", "etc"],
  "expected_result": "Concrete measurable outcome",
  "research_potential": "Could this become a paper? Why?",
  "compare_with": ["Alternative approach 1", "Alternative approach 2"],
  "socratic_challenge": "One question that makes the student think deeper about their idea"
}}"""
    return _parse_json(_llm(prompt), {
        "idea_title": f"Improved {topic} System",
        "current_problem": f"Current {topic} systems struggle with edge cases.",
        "your_solution": f"Use {topic} with an adaptive component to handle edge cases.",
        "how_it_works": "Step 1: Collect data. Step 2: Train model. Step 3: Evaluate.",
        "novelty": "Combines two existing ideas in a new way.",
        "difficulty": "⭐⭐☆☆",
        "estimated_weeks": 3,
        "datasets": ["Standard benchmark dataset"],
        "tools": ["Python", "TensorFlow"],
        "expected_result": "10% improvement over baseline.",
        "research_potential": "Yes — novel combination of techniques.",
        "compare_with": ["Baseline approach", "State-of-the-art"],
        "socratic_challenge": f"What happens to your approach when the input data distribution shifts?"
    })


def _format_stage5(data: dict) -> str:
    lines = [
        f"💡 **Innovation Idea: {data.get('idea_title', '')}**\n",
        f"**🔍 The Problem:**",
        f"  {data.get('current_problem', '')}\n",
        f"**✨ Your Solution:**",
        f"  {data.get('your_solution', '')}\n",
        f"**⚙️ How It Works:**",
        f"  {data.get('how_it_works', '')}\n",
        f"**🆕 What Makes It Novel:**",
        f"  {data.get('novelty', '')}\n",
        f"Difficulty: {data.get('difficulty', '⭐⭐☆☆')}  |  Est. Time: {data.get('estimated_weeks', '?')} weeks\n",
    ]

    datasets = data.get("datasets", [])
    if datasets:
        lines.append("**📊 Datasets:**")
        for d in datasets:
            lines.append(f"  • {d}")
        lines.append("")

    tools = data.get("tools", [])
    if tools:
        lines.append(f"**🛠 Tools:** {', '.join(tools)}\n")

    lines.append(f"**📈 Expected Result:**")
    lines.append(f"  {data.get('expected_result', '')}\n")

    compare = data.get("compare_with", [])
    if compare:
        lines.append("**🔄 Compare Against:**")
        for c in compare:
            lines.append(f"  • {c}")
        lines.append("")

    pub = data.get("research_potential", "")
    if pub:
        lines.append(f"**📝 Publication Potential:** {pub}\n")

    challenge = data.get("socratic_challenge", "")
    if challenge:
        lines.append(f"---\n🤔 **Think about this:**")
        lines.append(f"  _{challenge}_\n")

    lines.append("---")
    lines.append("Type `build` to get a full project roadmap for this idea.")
    lines.append("Type `more ideas` for alternative innovations.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 6 — Project Builder / Build Mentor
# ─────────────────────────────────────────────────────────────────────────────

def _stage6_project(topic: str, idea_title: str, subject: str) -> dict:
    prompt = f"""Design a complete project roadmap for a student.
Topic: {topic}
Project Idea: {idea_title}
Subject: {subject}

Act as a project supervisor. Return ONLY JSON:
{{
  "title": "{idea_title}",
  "difficulty": "⭐⭐☆",
  "estimated_weeks": 4,
  "prerequisites": ["skill1", "skill2"],
  "tools": ["Python", "etc"],
  "datasets": ["{{"name": "...", "url": "...", "size": "..."}}"],
  "evaluation_metric": "How success is measured (e.g., accuracy, F1, BLEU)",
  "expected_outcome": "What the student will have at the end",
  "weekly_roadmap": [
    {{
      "week": 1,
      "title": "Week theme",
      "tasks": ["Task 1", "Task 2"],
      "milestone": "What you'll have by end of week",
      "hours": 8
    }}
  ],
  "checkpoints": ["Checkpoint at week 2", "Checkpoint at week 4"],
  "deployment": "How to showcase this project",
  "resume_value": "How to describe this on a resume/CV",
  "next_steps": ["What to do after this project to grow further"]
}}
Make it realistic and buildable by an undergraduate."""
    return _parse_json(_llm(prompt), {
        "title": idea_title,
        "difficulty": "⭐⭐☆",
        "estimated_weeks": 4,
        "prerequisites": [topic],
        "tools": ["Python"],
        "datasets": [],
        "evaluation_metric": "Accuracy on test set",
        "expected_outcome": "A working prototype you can demo",
        "weekly_roadmap": [
            {"week": 1, "title": "Setup & Data", "tasks": ["Setup environment", "Collect dataset"], "milestone": "Data ready", "hours": 6},
            {"week": 2, "title": "Model Training", "tasks": ["Implement model", "Train baseline"], "milestone": "Baseline results", "hours": 10},
            {"week": 3, "title": "Optimization", "tasks": ["Tune hyperparameters", "Compare models"], "milestone": "Best model found", "hours": 8},
            {"week": 4, "title": "Deployment", "tasks": ["Build demo", "Write report"], "milestone": "Deployable app", "hours": 6},
        ],
        "checkpoints": ["Working baseline at week 2", "Final results at week 4"],
        "deployment": "Host on Hugging Face Spaces or as a web demo",
        "resume_value": f"Built end-to-end {topic} system achieving X% accuracy",
        "next_steps": ["Write a paper", "Open source it", "Enter a competition"]
    })


def _format_stage6(data: dict) -> str:
    lines = [
        f"🛠 **Project Roadmap: {data.get('title', '')}**\n",
        f"Difficulty: {data.get('difficulty', '⭐⭐☆')}  |  Time: {data.get('estimated_weeks', '?')} weeks\n",
    ]

    prereqs = data.get("prerequisites", [])
    if prereqs:
        lines.append(f"**Prerequisites:** {', '.join(prereqs)}")

    tools = data.get("tools", [])
    if tools:
        lines.append(f"**Tools:** {', '.join(tools)}\n")

    datasets = data.get("datasets", [])
    if datasets:
        lines.append("**📊 Datasets:**")
        for d in datasets:
            if isinstance(d, dict):
                lines.append(f"  • {d.get('name', str(d))} — {d.get('url', '')}")
            else:
                lines.append(f"  • {d}")
        lines.append("")

    lines.append(f"**📏 Evaluation Metric:** {data.get('evaluation_metric', '')}")
    lines.append(f"**🏆 Expected Outcome:** {data.get('expected_outcome', '')}\n")
    lines.append("---")
    lines.append("**📅 Weekly Roadmap:**\n")

    for week in data.get("weekly_roadmap", []):
        lines.append(f"**Week {week.get('week', '?')}: {week.get('title', '')}** (~{week.get('hours', '?')}h)")
        for task in week.get("tasks", []):
            lines.append(f"  □ {task}")
        lines.append(f"  ✅ Milestone: _{week.get('milestone', '')}_\n")

    checkpoints = data.get("checkpoints", [])
    if checkpoints:
        lines.append("**🔖 Checkpoints:**")
        for c in checkpoints:
            lines.append(f"  → {c}")
        lines.append("")

    lines.append(f"**🚀 Deployment:** {data.get('deployment', '')}")
    lines.append(f"**💼 Resume Value:** _{data.get('resume_value', '')}_\n")

    next_steps = data.get("next_steps", [])
    if next_steps:
        lines.append("**⏭ After This Project:**")
        for n in next_steps:
            lines.append(f"  • {n}")
        lines.append("")

    lines.append("---")
    lines.append("Type `reflect` after completing the project for a reflection session.")
    lines.append("Type `missing skills` if you need to learn something before starting.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Stage 7 — Reflection Mode + Planner Update
# ─────────────────────────────────────────────────────────────────────────────

def _stage7_reflection(topic: str, project_title: str = "") -> str:
    project_str = f"on '{project_title}'" if project_title else ""
    return "\n".join([
        f"🪞 **Reflection Session {project_str}**\n",
        "Reflection is how researchers grow. Answer these honestly:\n",
        "**1.** What worked well in your approach?",
        "**2.** What failed or surprised you?",
        "**3.** If you started over, what would you do differently?",
        "**4.** Would another model or approach work better? Why?",
        "**5.** What did you learn that no textbook taught you?",
        "**6.** Would you publish this? What would you add to make it publishable?\n",
        "---",
        "Answer as many as you like — I'll respond as your research mentor.",
        "Your reflections are saved to your Research Notebook automatically."
    ])


def _session_report(topic: str, profile: dict, session_data: dict) -> str:
    return "\n".join([
        f"📊 **Research Session Report**\n",
        f"**Topic:** {topic}",
        f"**Duration:** {session_data.get('duration_min', 0)} min",
        f"**Mode:** {session_data.get('mode', 'explore').replace('_', ' ').title()}\n",
        "---",
        f"**Your Research Profile:**",
        f"  📱 Applications Explored: {profile.get('applications_viewed', 0)}",
        f"  🔬 Problems Explored: {profile.get('problems_explored', 0)}",
        f"  💡 Ideas Generated: {profile.get('ideas_generated', 0)}",
        f"  🛠 Projects Started: {profile.get('projects_started', 0)}",
        f"  📄 Papers Read: {profile.get('papers_read', 0)}",
        f"  ⭐ Innovation Score: {profile.get('innovation_score', 0)}",
        f"  🎓 Research Level: **{profile.get('research_level', 'beginner').capitalize()}**\n",
        "---",
        "Your research history is saved to your Research Notebook."
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Skill Gap Analyser (for Idea-First mode)
# ─────────────────────────────────────────────────────────────────────────────

def _analyse_skill_gap(idea: str, known_topics: list) -> dict:
    known_str = ", ".join(known_topics[:15]) if known_topics else "none"
    prompt = f"""A student wants to build: "{idea}"
They already know: {known_str}

Analyse the skill gap. Return ONLY JSON:
{{
  "required_skills": ["skill1", "skill2"],
  "known": ["skills they already have"],
  "missing": ["skills they need but don't have"],
  "suggested_order": ["learn this first", "then this"],
  "estimated_weeks": 4
}}"""
    return _parse_json(_llm(prompt), {
        "required_skills": [],
        "known": [],
        "missing": [],
        "suggested_order": [],
        "estimated_weeks": 4
    })


# ─────────────────────────────────────────────────────────────────────────────
# Research Workspace helpers
# ─────────────────────────────────────────────────────────────────────────────

def _create_workspace_entry(idea: str, gap: dict) -> dict:
    return {
        "id": str(uuid.uuid4())[:8],
        "title": idea,
        "problem_statement": f"Build: {idea}",
        "required_skills": gap.get("required_skills", []),
        "known_skills": gap.get("known", []),
        "missing_skills": gap.get("missing", []),
        "suggested_order": gap.get("suggested_order", []),
        "notes": [],
        "papers": [],
        "ideas": [],
        "experiments": [],
        "reflections": [],
        "progress": "skill_gap_identified",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }


def _render_workspace(entry: dict) -> str:
    lines = [
        f"📁 **Research Workspace: {entry['title']}**",
        f"   Status: {entry['status']}  |  Progress: {entry.get('progress', 'active')}\n",
        "🔧 Required Skills:",
    ]
    for skill in entry.get("required_skills", []):
        icon = "✓" if skill in entry.get("known_skills", []) else "✗"
        lines.append(f"   {icon} {skill}")
    missing = entry.get("missing_skills", [])
    if missing:
        lines.append(f"\n❌ Missing ({len(missing)}):")
        for s in missing:
            lines.append(f"   • {s}")
    order = entry.get("suggested_order", [])
    if order:
        lines.append(f"\n📋 Learning Order:")
        for i, s in enumerate(order, 1):
            lines.append(f"   {i}. {s}")
    return "\n".join(lines)


def _format_idea_analysis(idea: str, gap: dict, workspace: dict) -> str:
    missing = gap.get("missing", [])
    known = gap.get("known", [])
    order = gap.get("suggested_order", [])
    weeks = gap.get("estimated_weeks", 4)
    lines = [
        f"🚀 **{idea}**\n",
        f"I've analysed what this project requires.\n",
        f"✅ You already know ({len(known)}): {', '.join(known) if known else 'none yet'}",
        f"❌ Missing ({len(missing)}): {', '.join(missing) if missing else 'nothing! you can start now.'}",
    ]
    if order:
        lines.append(f"\n📋 Recommended learning order:")
        for i, s in enumerate(order, 1):
            lines.append(f"  {i}. {s}")
        lines.append(f"\n⏱  Estimated time to be project-ready: ~{weeks} weeks")
    if missing:
        lines.append("\n\nWould you like me to:")
        lines.append("  `1` — Build a full learning roadmap (sends to Planner)")
        lines.append("  `2` — Teach the first missing skill right now (Learner)")
        lines.append("  `3` — Save this to Research Workspace and explore the idea anyway")
    else:
        lines.append("\n✨ You have all the skills! Ready to start building.")
        lines.append("Type `project` for a full project roadmap, or `innovate` for innovation ideas.")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Research Notebook helpers
# ─────────────────────────────────────────────────────────────────────────────

def _ensure_notebook_entry(s: StudentState, topic: str) -> dict:
    """Get or create a notebook entry for this topic."""
    entry = next((nb for nb in s.research_notebook if nb.get("topic") == topic), None)
    if not entry:
        entry = {
            "id": str(uuid.uuid4())[:8],
            "topic": topic,
            "problem_statement": "",
            "hypotheses": [],
            "papers": [],
            "paper_summaries": [],
            "ideas": [],
            "experiments": [],
            "results": [],
            "reflections": [],
            "design_decisions": [],
            "future_work": [],
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
        s.research_notebook.append(entry)
    return entry


def _save_to_notebook(s: StudentState, topic: str, category: str, content: str):
    """Append content to the appropriate notebook section."""
    entry = _ensure_notebook_entry(s, topic)
    entry.setdefault(category, []).append({
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    entry["last_updated"] = datetime.now().isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Curiosity Map + Resource Finder (legacy helpers, kept for compatibility)
# ─────────────────────────────────────────────────────────────────────────────

def _curiosity_map(topic: str, subject: str, known: list) -> dict:
    known_str = ", ".join(known[:10]) if known else "none"
    prompt = f"""Student just mastered: {topic} (subject: {subject})
Other topics they know: {known_str}
Generate a curiosity map. Return ONLY JSON:
{{
  "deeper_questions": ["3 questions that go one level deeper"],
  "connections": [{{"topic": "known topic", "how": "brief connection"}}],
  "open_problems": ["1-2 real-world unsolved problems"],
  "next_rabbit_hole": "one sentence on the most exciting direction"
}}"""
    return _parse_json(_llm(prompt), {
        "deeper_questions": [
            f"What are the limitations of {topic}?",
            f"How does {topic} work at scale?",
            f"What replaces {topic} in modern systems?"
        ],
        "connections": [],
        "open_problems": [f"How can {topic} be optimised for real-time use?"],
        "next_rabbit_hole": f"Explore trade-offs and alternatives to {topic}."
    })


def _find_resources(topic: str, subject: str) -> dict:
    prompt = f"""Find learning resources for: {topic} (subject: {subject})
Return ONLY JSON:
{{
  "papers": [{{"title": "...", "authors": "...", "year": 2023, "relevance": "one line"}}],
  "repos":  [{{"name": "...", "url": "https://github.com/...", "description": "one line"}}],
  "applications": [{{"domain": "...", "example": "...", "why_relevant": "one line"}}],
  "courses": [{{"title": "...", "platform": "...", "level": "beginner|intermediate|advanced"}}]
}}
Limit: 2-3 items per category."""
    return _parse_json(_llm(prompt), {
        "papers": [{"title": f"Survey of {topic}", "authors": "Various", "year": 2023, "relevance": f"Overview of {topic}"}],
        "repos": [{"name": f"{topic.replace(' ','-').lower()}-demo",
                   "url": f"https://github.com/search?q={topic.replace(' ','+')}",
                   "description": f"Open source {topic} implementation"}],
        "applications": [{"domain": "Industry", "example": f"{topic} in production", "why_relevant": "Shows real-world constraints"}],
        "courses": []
    })


def _generate_projects(mastered: list, goal: str) -> list:
    topics_str = ", ".join(mastered[:8]) if mastered else "general CS"
    prompt = f"""Student goal: {goal}
Has mastered: {topics_str}
Generate 3 concrete buildable project ideas. Return ONLY JSON array:
[{{
  "title": "...",
  "description": "2-3 sentences on what it does and why interesting",
  "tech_stack": ["tool1", "tool2"],
  "concepts_used": ["concept"],
  "estimated_hours": 8,
  "difficulty": "easy|medium|hard",
  "wow_factor": "one sentence on what makes this impressive"
}}]"""
    result = _parse_json(_llm(prompt), [])
    if isinstance(result, list) and result:
        return result
    return [{
        "title": f"Mini {mastered[0] if mastered else 'CS'} Simulator",
        "description": f"Command-line simulator for {mastered[0] if mastered else 'algorithms'}.",
        "tech_stack": ["Python"],
        "concepts_used": mastered[:2],
        "estimated_hours": 6,
        "difficulty": "medium",
        "wow_factor": "Interactive step-by-step visualisation."
    }]


# ─────────────────────────────────────────────────────────────────────────────
# LangGraph node  — main entry point
# ─────────────────────────────────────────────────────────────────────────────

def research_node(state: dict) -> dict:
    s = StudentState(**state)
    msg = s.user_message.strip()
    lower = msg.lower()

    # ── Initialise research profile ──────────────────────────────────────────
    s.student_research_profile = _init_profile(s.student_research_profile)
    profile = s.student_research_profile

    # ── Determine active topic ───────────────────────────────────────────────
    topic = s.post_mastery_topic or (
        s.subjects[0]["name"] if s.subjects else "your topic"
    )
    subject = s.subjects[0]["name"] if s.subjects else "Computer Science"

    # ── Handle return from Learner / Planner handoff ─────────────────────────
    if s.return_to_agent == "research":
        active = next(
            (w for w in s.research_workspace if w.get("id") == s.active_research_id),
            None
        )
        s.return_to_agent = None
        s.return_context = {}
        s.agent_handoff = None

        if active:
            known_now = [t.get("topic", t.get("title", ""))
                         for t in s.tasks if t.get("status") == "completed"]
            still_missing = [sk for sk in active.get("missing_skills", [])
                             if not any(sk.lower() in k.lower() for k in known_now)]
            active["missing_skills"] = still_missing
            active["updated_at"] = datetime.now().isoformat()

            if still_missing:
                s.agent_response = (
                    f"Welcome back! You've made progress on **{active['title']}**.\n\n"
                    f"Still missing: {', '.join(still_missing)}\n\n"
                    f"Continue learning? Type the skill name or `roadmap` for a full plan."
                )
            else:
                s.agent_response = (
                    f"🎉 You now have all the skills for **{active['title']}**!\n\n"
                    + _render_workspace(active) +
                    "\n\nReady to start building. Type `project` for the full roadmap."
                )
        else:
            s.agent_response = "Welcome back to Research! Type a topic to explore, or your project idea."

        s.history.append({"role": "user", "content": s.user_message})
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    # ── Idea-First response handlers (1/2/3) ─────────────────────────────────
    active_ws = next(
        (w for w in s.research_workspace
         if w.get("id") == s.active_research_id and w.get("status") == "active"),
        None
    )

    if active_ws and lower in ("1", "roadmap", "plan", "build a roadmap"):
        missing = active_ws.get("missing_skills", [])
        s.agent_handoff = {
            "to": "planner",
            "reason": f"Build learning roadmap for: {active_ws['title']}",
            "context": {
                "project": active_ws["title"],
                "skills_needed": missing,
                "suggested_order": active_ws.get("suggested_order", [])
            }
        }
        s.return_to_agent = "research"
        s.return_context = {"research_id": active_ws["id"]}
        s.goal = f"Build project: {active_ws['title']}"
        s.goal_category = "project"
        s.goal_category_locked = True
        s.agent_response = (
            f"📋 Opening Planner to build your roadmap for **{active_ws['title']}**.\n"
            f"Skills to learn: {', '.join(missing)}\n\n"
            "The Planner will create a week-by-week study plan."
        )
        s.intent = "planner"
        s.planner_stage = "collect_deadline"
        s.history.append({"role": "user", "content": s.user_message})
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    if active_ws and lower in ("2", "teach", "learn now", "teach now"):
        missing = active_ws.get("missing_skills", [])
        if missing:
            first_skill = missing[0]
            s.agent_handoff = {
                "to": "learner",
                "reason": f"Teach {first_skill} for project: {active_ws['title']}",
                "context": {"topic": first_skill, "return_after": True}
            }
            s.return_to_agent = "research"
            s.return_context = {"research_id": active_ws["id"]}
            s.user_message = f"teach me {first_skill}"
            s.agent_response = (
                f"🎓 Opening Learner Agent to teach you **{first_skill}**.\n"
                f"After completing it, we'll return to your project: {active_ws['title']}"
            )
            s.intent = "learner"
            s.history.append({"role": "user", "content": msg})
            s.history.append({"role": "assistant", "content": s.agent_response})
            return s.model_dump()

    if active_ws and lower in ("3", "save", "save to workspace"):
        active_ws["status"] = "saved"
        s.agent_response = (
            f"💾 Saved to Research Workspace.\n\n"
            + _render_workspace(active_ws) +
            "\n\nCome back anytime with `workspace` to continue. Or explore the idea now with `innovate`."
        )
        s.history.append({"role": "user", "content": s.user_message})
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    # ── Missing skills detected mid-build ────────────────────────────────────
    if lower in ("missing skills", "missing skill", "i don't know this", "i need to learn"):
        if active_ws and active_ws.get("missing_skills"):
            first_skill = active_ws["missing_skills"][0]
            s.agent_handoff = {
                "to": "learner",
                "reason": f"Teach {first_skill} before project continues",
                "context": {"topic": first_skill, "return_after": True}
            }
            s.return_to_agent = "research"
            s.return_context = {"research_id": active_ws["id"]}
            s.user_message = f"teach me {first_skill}"
            s.agent_response = (
                f"🎓 No problem! Let me send you to the Learner Agent to master **{first_skill}** first.\n"
                f"We'll return to your project after."
            )
            s.intent = "learner"
            s.history.append({"role": "user", "content": msg})
            s.history.append({"role": "assistant", "content": s.agent_response})
            return s.model_dump()

    # ── View workspace ────────────────────────────────────────────────────────
    if lower in ("workspace", "my workspace", "research workspace"):
        if not s.research_workspace:
            s.agent_response = (
                "📁 Your Research Workspace is empty.\n"
                "Start with a project idea like: `I want to build a crop monitoring drone`\n"
                "Or explore a topic like: `explore CNN`"
            )
        else:
            lines = ["📁 **Research Workspace**\n"]
            for w in s.research_workspace:
                lines.append(f"  [{w['id']}] **{w['title']}** — {w['status']}")
                missing = w.get("missing_skills", [])
                if missing:
                    lines.append(f"         Missing: {', '.join(missing[:3])}")
                notes_count = len(w.get("notes", []))
                if notes_count:
                    lines.append(f"         Notes: {notes_count}")
            s.agent_response = "\n".join(lines)
        s.history.append({"role": "user", "content": s.user_message})
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    # ── View research notebook ────────────────────────────────────────────────
    if lower in ("notebook", "my notebook", "research notebook"):
        if not s.research_notebook:
            s.agent_response = (
                "📓 Your Research Notebook is empty.\n"
                "It fills up automatically as you explore topics, read papers, and reflect on projects."
            )
        else:
            lines = ["📓 **Research Notebook**\n"]
            for nb in s.research_notebook:
                ideas_count = len(nb.get("ideas", []))
                papers_count = len(nb.get("papers", []))
                reflections_count = len(nb.get("reflections", []))
                lines.append(f"  **{nb['topic']}** (last updated: {nb.get('last_updated', '')[:10]})")
                lines.append(f"    💡 Ideas: {ideas_count}  |  📄 Papers: {papers_count}  |  🪞 Reflections: {reflections_count}")
            s.agent_response = "\n".join(lines)
        s.history.append({"role": "user", "content": s.user_message})
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    # ── Research profile ──────────────────────────────────────────────────────
    if lower in ("profile", "research profile", "my research profile", "innovation score"):
        _update_research_level(profile)
        s.agent_response = "\n".join([
            "🎓 **Your Research Profile**\n",
            f"  Research Level: **{profile.get('research_level', 'beginner').capitalize()}**",
            f"  ⭐ Innovation Score: {profile.get('innovation_score', 0)}",
            f"  📱 Applications Explored: {profile.get('applications_viewed', 0)}",
            f"  🔬 Problems Explored: {profile.get('problems_explored', 0)}",
            f"  💡 Ideas Generated: {profile.get('ideas_generated', 0)}",
            f"  🛠 Projects Started: {profile.get('projects_started', 0)}",
            f"  ✅ Projects Completed: {profile.get('projects_completed', 0)}",
            f"  📄 Papers Read: {profile.get('papers_read', 0)}",
            f"  🏗 Prototype Built: {'Yes' if profile.get('prototype_built') else 'No'}",
            f"\n  Research Sessions: {len(profile.get('research_sessions', []))}",
        ])
        s.history.append({"role": "user", "content": s.user_message})
        s.history.append({"role": "assistant", "content": s.agent_response})
        return s.model_dump()

    # ── Post-mastery Learner → Planner option handling ────────────────────────
    if s.daily_loop_stage == "ask_post_mastery":
        post_topic = s.post_mastery_topic or topic
        if lower in ("1", "continue", "next topic"):
            s.daily_loop_stage = "idle"
            s.agent_response = f"✅ Continuing to the next topic. Great work on **{post_topic}**!"
            s.intent = "progress"
        elif lower in ("2", "explore", "applications", "explore applications"):
            s.daily_loop_stage = "idle"
            s.research_mode = "explore"
            # Fall through to explore logic below
            topic = post_topic
        elif lower in ("3", "build", "build a project", "project"):
            s.daily_loop_stage = "idle"
            s.research_mode = "build_mentor"
            topic = post_topic
        elif lower in ("4", "paper", "papers", "read papers"):
            s.daily_loop_stage = "idle"
            s.research_mode = "paper"
            topic = post_topic
        elif lower in ("5", "skip"):
            s.daily_loop_stage = "idle"
            s.agent_response = f"No problem! Continuing your study plan."
            s.intent = "progress"
            s.history.append({"role": "user", "content": s.user_message})
            s.history.append({"role": "assistant", "content": s.agent_response})
            return s.model_dump()
        else:
            s.agent_response = (
                f"What would you like to do with **{post_topic}**?\n\n"
                "  `1` Continue next topic\n"
                "  `2` Explore real-world applications\n"
                "  `3` Build a project using it\n"
                "  `4` Read research papers\n"
                "  `5` Skip"
            )
            s.history.append({"role": "user", "content": s.user_message})
            s.history.append({"role": "assistant", "content": s.agent_response})
            return s.model_dump()

    # ─────────────────────────────────────────────────────────────────────────
    # MODE DISPATCHER — detect intent and dispatch to correct stage
    # ─────────────────────────────────────────────────────────────────────────

    # ── Mode detection keywords ───────────────────────────────────────────────
    idea_keywords = [
        "i want to build", "i want to make", "i want to create",
        "build a", "make a", "create a", "develop a", "i want to develop"
    ]

    explore_keywords = [
        "explore", "applications", "where is", "real world", "where can",
        "use cases", "how is", "what domains", "industry"
    ]

    problem_keywords = [
        "problems", "open problems", "unsolved", "what problems",
        "research problems", "limitations", "challenges", "gaps"
    ]

    paper_keywords = [
        "paper", "papers", "research paper", "arxiv", "study",
        "simplify", "explain paper", "read paper", "summary"
    ]

    innovate_keywords = [
        "innovate", "innovation", "idea", "generate idea", "suggest idea",
        "novel", "new idea", "research idea", "creative"
    ]

    project_keywords = [
        "project", "build this", "how to build", "roadmap",
        "week by week", "timeline", "supervisor", "guide me"
    ]

    reflect_keywords = [
        "reflect", "reflection", "what worked", "review project",
        "lessons", "what i learned", "after project"
    ]

    question_keywords = [
        "questions", "challenge me", "socratic", "quiz", "research questions",
        "think deeper", "test me"
    ]

    resource_keywords = [
        "resources", "find", "course", "courses", "github", "dataset", "repo"
    ]

    # ── Branch: Idea-First Mode ───────────────────────────────────────────────
    if any(kw in lower for kw in idea_keywords):
        idea = msg.strip()
        for kw in idea_keywords:
            if kw in lower:
                idx = lower.find(kw)
                idea = msg[idx:].strip()
                break

        known_topics = list({
            t.get("topic") or t.get("title", "")
            for t in s.tasks if t.get("status") == "completed"
        } | {
            v.get("topic", "")
            for v in s.knowledge_vault
        })

        gap = _analyse_skill_gap(idea, known_topics)
        workspace_entry = _create_workspace_entry(idea, gap)
        s.research_workspace.append(workspace_entry)
        s.active_research_id = workspace_entry["id"]
        profile["projects_started"] = profile.get("projects_started", 0) + 1
        profile["innovation_score"] = profile.get("innovation_score", 0) + 5

        # Save to notebook
        _save_to_notebook(s, idea, "ideas", f"Project idea: {idea}")

        s.agent_response = _format_idea_analysis(idea, gap, workspace_entry)
        s.research_mode = "idea_first"

    # ── Branch: Reflect ───────────────────────────────────────────────────────
    elif any(kw in lower for kw in reflect_keywords):
        project_title = ""
        if active_ws:
            project_title = active_ws.get("title", "")
        s.research_mode = "reflection"
        s.agent_response = _stage7_reflection(topic, project_title)
        # Save reflection trigger to notebook
        _save_to_notebook(s, topic, "reflections", f"Reflection session started: {msg}")
        if active_ws:
            active_ws.get("reflections", []).append({"content": msg, "timestamp": datetime.now().isoformat()})

    # ── Branch: Problem Finder ────────────────────────────────────────────────
    elif any(kw in lower for kw in problem_keywords):
        # Extract topic from message if provided
        extracted = msg
        for prefix in ("problems in ", "open problems in ", "what problems in ",
                        "challenges in ", "limitations of ", "gaps in "):
            if prefix in lower:
                extracted = msg[lower.find(prefix) + len(prefix):].strip()
                break
        if len(extracted.split()) > 6:
            extracted = topic

        s.research_mode = "problem_finder"
        data = _problem_finder(extracted, subject)
        s.agent_response = _format_problem_finder(extracted, data)
        profile["problems_explored"] = profile.get("problems_explored", 0) + 1
        profile["innovation_score"] = profile.get("innovation_score", 0) + 3

    # ── Branch: Paper ─────────────────────────────────────────────────────────
    elif any(kw in lower for kw in paper_keywords):
        paper_title = ""
        for prefix in ("paper on ", "papers on ", "simplify ", "explain paper ",
                        "read paper ", "summary of ", "research paper on "):
            if prefix in lower:
                paper_title = msg[lower.find(prefix) + len(prefix):].strip()
                break
        if not paper_title:
            paper_title = f"Recent advances in {topic}"

        s.research_mode = "paper"
        data = _stage4_paper(topic, paper_title)
        s.agent_response = _format_stage4(data)
        profile["papers_read"] = profile.get("papers_read", 0) + 1
        profile["innovation_score"] = profile.get("innovation_score", 0) + 5
        _save_to_notebook(s, topic, "papers", paper_title)

    # ── Branch: Innovation Idea ───────────────────────────────────────────────
    elif any(kw in lower for kw in innovate_keywords) or lower in ("more ideas", "another idea"):
        extracted = topic
        for prefix in ("innovate ", "innovation in ", "idea for ", "ideas on "):
            if prefix in lower:
                extracted = msg[lower.find(prefix) + len(prefix):].strip()
                break

        s.research_mode = "idea_generator"
        data = _stage5_innovate(extracted, subject, profile.get("research_level", "beginner"))
        s.agent_response = _format_stage5(data)
        profile["ideas_generated"] = profile.get("ideas_generated", 0) + 1
        profile["innovation_score"] = profile.get("innovation_score", 0) + 8
        _save_to_notebook(s, extracted, "ideas", data.get("idea_title", "Innovation idea"))

    # ── Branch: Project Builder ───────────────────────────────────────────────
    elif any(kw in lower for kw in project_keywords) and lower not in ("i want to build", "build a"):
        # Get idea title from active workspace or message
        idea_title = ""
        if active_ws:
            idea_title = active_ws.get("title", f"{topic} Project")
        elif s.research_output.get(topic, {}).get("projects"):
            p = s.research_output[topic]["projects"]
            idea_title = p[0].get("title", f"{topic} Project") if p else f"{topic} Project"
        else:
            idea_title = f"{topic} Project"

        s.research_mode = "build_mentor"
        data = _stage6_project(topic, idea_title, subject)
        s.agent_response = _format_stage6(data)
        profile["projects_started"] = profile.get("projects_started", 0) + 1
        profile["innovation_score"] = profile.get("innovation_score", 0) + 10
        _save_to_notebook(s, topic, "ideas", f"Project: {idea_title}")
        if active_ws:
            active_ws["progress"] = "project_roadmap_created"
            active_ws["updated_at"] = datetime.now().isoformat()

    # ── Branch: Research Questions (Socratic) ─────────────────────────────────
    elif any(kw in lower for kw in question_keywords):
        extracted = topic
        for prefix in ("questions on ", "quiz on ", "challenge me on ", "test me on "):
            if prefix in lower:
                extracted = msg[lower.find(prefix) + len(prefix):].strip()
                break

        level = "beginner"
        if "intermediate" in lower:
            level = "intermediate"
        elif "advanced" in lower:
            level = "advanced"
        elif profile.get("research_level") in ("intermediate", "advanced"):
            level = profile["research_level"]

        s.research_mode = "explore"
        data = _stage3_questions(extracted, subject, level)
        s.agent_response = _format_stage3(extracted, data, level)

    # ── Branch: Resources ─────────────────────────────────────────────────────
    elif any(kw in lower for kw in resource_keywords):
        extracted = topic
        for prefix in ("find resources on ", "resources for ", "find papers on ",
                        "courses on ", "datasets for "):
            if prefix in lower:
                extracted = msg[lower.find(prefix) + len(prefix):].strip()
                break

        resources = _find_resources(extracted, subject)
        lines = [f"📚 **Resources for: {extracted}**\n"]
        for p in resources.get("papers", []):
            lines.append(f"  📄 {p['title']} ({p.get('year','')}) — {p.get('relevance','')}")
        for r in resources.get("repos", []):
            lines.append(f"  💻 {r['name']} — {r.get('description','')}")
        for a in resources.get("applications", []):
            lines.append(f"  🌍 {a['domain']}: {a.get('example','')}")
        for c in resources.get("courses", []):
            lines.append(f"  🎓 {c['title']} ({c.get('platform','')}) — {c.get('level','')}")
        s.agent_response = "\n".join(lines)

    # ── Branch: Explore (default — full pipeline Stage 1 + 2) ────────────────
    elif any(kw in lower for kw in explore_keywords) or s.research_mode == "explore":
        extracted = msg
        for prefix in ("explore ", "applications of ", "where is ", "how is ", "real world uses of "):
            if prefix in lower:
                extracted = msg[lower.find(prefix) + len(prefix):].strip()
                break
        if len(extracted.split()) > 5:
            extracted = topic

        s.research_mode = "explore"
        # Stage 1: Applications
        apps_data = _stage1_applications(extracted, subject)
        s.agent_response = _format_stage1(extracted, apps_data)
        profile["applications_viewed"] = profile.get("applications_viewed", 0) + len(apps_data.get("domains", []))
        profile["innovation_score"] = profile.get("innovation_score", 0) + 2

        # Store in research output for subsequent commands
        s.research_output[extracted] = {
            "applications": apps_data,
            "generated_at": datetime.now().isoformat()
        }
        _save_to_notebook(s, extracted, "ideas", f"Explored applications of {extracted}")

    # ── Default: Full exploration using topic from message ────────────────────
    else:
        extracted = msg if len(msg.split()) <= 6 else " ".join(msg.split()[-3:])
        known = [t.get("topic") or t.get("title", "")
                 for t in s.tasks if t.get("status") == "completed"]

        cmap = _curiosity_map(extracted, subject, known)
        resources = _find_resources(extracted, subject)
        projects = _generate_projects(known or [extracted], s.goal or "learning")

        # Format as a quick curiosity overview
        lines = [f"🔭 **Exploring: {extracted}**\n"]
        lines.append("💡 **Deeper Questions:**")
        for q in cmap.get("deeper_questions", [])[:3]:
            lines.append(f"  • {q}")
        if cmap.get("next_rabbit_hole"):
            lines.append(f"\n🐇 **Next rabbit hole:** {cmap['next_rabbit_hole']}")
        papers = resources.get("papers", [])
        if papers:
            lines.append("\n📄 **Research Papers:**")
            for p in papers[:2]:
                lines.append(f"  • {p['title']} ({p.get('year','')}) — {p.get('relevance','')}")
        apps = resources.get("applications", [])
        if apps:
            lines.append("\n🌍 **Real-world Applications:**")
            for a in apps[:2]:
                lines.append(f"  • {a['domain']}: {a.get('example','')}")
        if projects:
            lines.append(f"\n🛠 **Project Idea: {projects[0]['title']}**")
            lines.append(f"  {projects[0]['description']}")
            lines.append(f"  Stack: {', '.join(projects[0].get('tech_stack', []))}")
        lines.append("\n---")
        lines.append("Type `applications` for Stage 1, `problems` for open research, `innovate` for innovation, `project` for a roadmap.")
        s.agent_response = "\n".join(lines)
        s.research_output[extracted] = {
            "curiosity_map": cmap, "resources": resources,
            "projects": projects, "generated_at": datetime.now().isoformat()
        }

    # ── Update research level ────────────────────────────────────────────────
    _update_research_level(profile)
    s.student_research_profile = profile

    # ── Record session ───────────────────────────────────────────────────────
    profile.setdefault("research_sessions", []).append({
        "topic": topic,
        "duration_min": 0,  # Updated by progress agent on session end
        "mode": s.research_mode,
        "timestamp": datetime.now().isoformat()
    })

    s.history.append({"role": "user", "content": s.user_message})
    s.history.append({"role": "assistant", "content": s.agent_response})
    print(f"[Research] mode={s.research_mode} | '{s.user_message[:60]}' → {len(s.agent_response)} chars")
    return s.model_dump()
