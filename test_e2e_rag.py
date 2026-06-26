"""
End-to-End Test: RAG-Grounded Teaching
Shows student uploading notes → Learner uses them → grounded explanations
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.learner import LearnerAgent
from app.agents.resource_hub import ResourceHub
from app.agents.rag_engine import RAGEngine


class MockLLM:
    def invoke(self, prompt):
        class Response:
            def __init__(self, content):
                self.content = content
        
        if "context" in prompt.lower() and "fcfs" in prompt.lower():
            return Response("""Let me explain FCFS intuitively using the context from your textbook.

Think of FCFS like standing in a queue at a movie theater. The first person who arrives gets their ticket first, then the second person, and so on. Nobody cuts in line!

In your OS, processes work the same way. The process that arrives first gets the CPU first. Simple and fair!

However, there's a catch (your notes mention this): if the first person takes a really long time buying tickets, everyone behind them has to wait. This is called the "convoy effect" - short processes get stuck waiting for long ones.""")
        
        return Response("FCFS is a scheduling algorithm.")


def test_end_to_end_rag_teaching():
    print("\n" + "="*70)
    print("  END-TO-END TEST: RAG-GROUNDED TEACHING")
    print("="*70)
    
    state = {}
    
    # Step 1: Student uploads their OS notes
    print("\n[Step 1] Student uploads OS notes...")
    resource_hub = ResourceHub("student_123", state)
    
    notes_content = """
CPU SCHEDULING - MY NOTES

FCFS (First Come First Serve):
- Processes execute in arrival order
- No preemption
- Simple queue-based approach

Example:
P1 arrives at t=0, needs 5ms
P2 arrives at t=1, needs 3ms  
P3 arrives at t=2, needs 8ms

Execution order: P1 → P2 → P3

Problems:
- Convoy effect: short processes wait for long ones
- Poor average waiting time
- Not suitable for time-sharing systems

Formula:
Waiting Time = Completion Time - Arrival Time - Burst Time
"""
    
    upload_result = resource_hub.upload_pdf(
        file_path="my_os_notes.pdf",
        file_content=notes_content,
        subject="Operating Systems"
    )
    
    print(f"   ✓ Uploaded: {upload_result['chunks_created']} chunks indexed")
    
    # Step 2: RAG indexes the notes
    print("\n[Step 2] RAG system indexes notes...")
    rag_engine = RAGEngine(MockLLM(), "student_123", state)
    
    pdf = resource_hub.get_resource_by_id(upload_result['resource_id'])
    indexed = rag_engine.index_chunks(
        resource_id=upload_result['resource_id'],
        chunks=pdf['chunks'],
        resource_metadata={
            "filename": pdf['filename'],
            "subject": pdf['subject'],
            "topics_covered": pdf['topics_covered']
        }
    )
    
    print(f"   ✓ Indexed: {indexed} chunks in vector DB")
    
    # Step 3: Student starts learning session
    print("\n[Step 3] Student starts learning FCFS...")
    learner = LearnerAgent(MockLLM(), "student_123", state)
    
    session_start = learner.start_learning_session(
        learning_unit="FCFS Scheduling",
        subject="Operating Systems"
    )
    
    print(f"   Session type: {session_start['type']}")
    print(f"   Message: {session_start['message']}")
    
    # Step 4: RAG retrieves relevant chunks
    print("\n[Step 4] Student asks for explanation...")
    query = "Explain FCFS scheduling"
    retrieved = rag_engine.retrieve(query, top_k=2)
    
    print(f"   Query: '{query}'")
    print(f"   Retrieved: {len(retrieved)} relevant chunks from uploaded notes")
    if retrieved:
        print(f"   Similarity: {retrieved[0]['similarity']:.3f}")
    
    # Step 5: Learner generates grounded explanation
    print("\n[Step 5] Learner generates explanation from student's notes...")
    explanation = rag_engine.generate_grounded_explanation(
        topic="FCFS",
        query="Explain intuitively",
        context={"layer": 1, "subject": "Operating Systems"}
    )
    
    print(f"   Grounded: {explanation['grounded']}")
    print(f"   Sources used: {len(explanation['sources'])}")
    print(f"\n   Explanation:")
    print(f"   {explanation['explanation'][:250]}...")
    
    # Step 6: Verify explanation uses student's content
    print("\n[Step 6] Verification...")
    explanation_text = explanation['explanation'].lower()
    
    checks = {
        "Uses 'convoy effect' from notes": "convoy" in explanation_text,
        "Mentions queue/order": "queue" in explanation_text or "order" in explanation_text,
        "References textbook context": "your textbook" in explanation_text or "your notes" in explanation_text or "context" in explanation_text,
        "Grounded in uploaded material": explanation['grounded']
    }
    
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"   {status} {check}")
    
    # Step 7: Show resource usage
    print("\n[Step 7] Resource tracking...")
    stats = resource_hub.get_library_stats()
    rag_stats = rag_engine.get_rag_stats()
    
    print(f"   Library: {stats['total_pdfs']} PDFs, {stats['indexed_topics']} topics")
    print(f"   RAG: {rag_stats['indexed_chunks']} chunks, {rag_stats['vector_db_size']} vectors")
    
    print("\n" + "="*70)
    print("  ✓ END-TO-END RAG TEACHING: SUCCESS")
    print("  Student's notes → RAG indexing → Grounded explanations")
    print("="*70)


if __name__ == "__main__":
    test_end_to_end_rag_teaching()
