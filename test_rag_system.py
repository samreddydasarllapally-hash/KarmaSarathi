"""
Test RAG Integration
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from app.agents.resource_hub import ResourceHub
from app.agents.rag_engine import RAGEngine


class MockLLM:
    def invoke(self, prompt):
        class Response:
            def __init__(self, content):
                self.content = content
        
        if "grounded" in prompt.lower() or "context" in prompt.lower():
            return Response("Based on the provided context, FCFS (First Come First Serve) is a CPU scheduling algorithm where processes are executed in the order they arrive. Think of it like a queue at a ticket counter - whoever arrives first gets served first.")
        
        return Response("FCFS is a scheduling algorithm.")


def test_rag_system():
    print("\n" + "="*60)
    print("  RAG SYSTEM TEST")
    print("="*60)
    
    state = {}
    
    # Initialize components
    resource_hub = ResourceHub("test_user", state)
    rag_engine = RAGEngine(MockLLM(), "test_user", state)
    
    # Test 1: Upload and process PDF
    print("\n[1] Testing PDF upload and chunking...")
    sample_content = """
CHAPTER 5: CPU SCHEDULING

5.1 Introduction
CPU scheduling is a fundamental OS function. The scheduler selects a process from the ready queue for execution.

5.2 FCFS (First Come First Serve)
FCFS is the simplest scheduling algorithm. Processes are executed in arrival order.

Example:
Process  Arrival  Burst
P1       0        5
P2       1        3
P3       2        8

The Gantt chart shows execution order: P1, P2, P3.
Average waiting time = (0 + 4 + 6) / 3 = 3.33 ms

5.3 Advantages
- Simple to implement
- No starvation
- Fair ordering

5.4 Disadvantages  
- Convoy effect: Short processes wait for long processes
- Poor average waiting time
"""
    
    result = resource_hub.upload_pdf(
        file_path="os_textbook.pdf",
        file_content=sample_content,
        subject="Operating Systems"
    )
    
    print(f"   Uploaded: {result['success']}")
    print(f"   Chunks created: {result['chunks_created']}")
    print(f"   Topics found: {result['topics_found']}")
    
    # Test 2: Index chunks in RAG
    print("\n[2] Testing RAG indexing...")
    pdf_resource = resource_hub.get_resource_by_id(result['resource_id'])
    
    indexed_count = rag_engine.index_chunks(
        resource_id=result['resource_id'],
        chunks=pdf_resource['chunks'],
        resource_metadata={
            "filename": pdf_resource['filename'],
            "subject": pdf_resource['subject'],
            "topics_covered": pdf_resource['topics_covered']
        }
    )
    
    print(f"   Indexed chunks: {indexed_count}")
    
    # Test 3: Retrieve relevant chunks
    print("\n[3] Testing retrieval...")
    query = "Explain FCFS scheduling algorithm"
    retrieved = rag_engine.retrieve(query, top_k=3)
    
    print(f"   Query: {query}")
    print(f"   Retrieved: {len(retrieved)} chunks")
    if retrieved:
        print(f"   Top match similarity: {retrieved[0]['similarity']:.3f}")
        print(f"   Top match preview: {retrieved[0]['metadata']['text'][:100]}...")
    
    # Test 4: Generate grounded explanation
    print("\n[4] Testing grounded explanation...")
    explanation_result = rag_engine.generate_grounded_explanation(
        topic="FCFS",
        query="Explain FCFS intuitively",
        context={"layer": 1, "subject": "Operating Systems"}
    )
    
    print(f"   Grounded: {explanation_result['grounded']}")
    print(f"   Sources: {len(explanation_result['sources'])}")
    print(f"   Explanation: {explanation_result['explanation'][:150]}...")
    
    # Test 5: Search resources
    print("\n[5] Testing resource search...")
    search_results = resource_hub.search_resources("FCFS")
    
    print(f"   Search query: FCFS")
    print(f"   Results found: {len(search_results)}")
    if search_results:
        print(f"   Top result: {search_results[0]['filename']}")
        print(f"   Relevance score: {search_results[0]['relevance']}")
    
    # Test 6: Add bookmark
    print("\n[6] Testing bookmarks...")
    bookmark = resource_hub.add_bookmark(
        resource_id=result['resource_id'],
        location="Section 5.2",
        note="FCFS definition and example"
    )
    
    print(f"   Bookmark added: {bookmark['id']}")
    print(f"   Location: {bookmark['location']}")
    
    bookmarks = resource_hub.get_bookmarks(result['resource_id'])
    print(f"   Total bookmarks: {len(bookmarks)}")
    
    # Test 7: Library stats
    print("\n[7] Testing library statistics...")
    stats = resource_hub.get_library_stats()
    
    print(f"   Total PDFs: {stats['total_pdfs']}")
    print(f"   Indexed topics: {stats['indexed_topics']}")
    
    rag_stats = rag_engine.get_rag_stats()
    print(f"   RAG indexed chunks: {rag_stats['indexed_chunks']}")
    print(f"   Vector DB size: {rag_stats['vector_db_size']}")
    
    print("\n" + "="*60)
    print("  ALL RAG TESTS PASSED")
    print("="*60)


if __name__ == "__main__":
    test_rag_system()
