"""
Resource Hub - Student's Personal Knowledge Base

Handles:
- PDF upload and OCR
- Semantic chunking
- Library management
- Bookmarks and annotations
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
import re


class ResourceHub:
    """Manages student's uploaded and downloaded resources"""
    
    def __init__(self, user_id: str, state: dict):
        self.user_id = user_id
        self.state = state
        self._ensure_library_structure()
    
    def _ensure_library_structure(self):
        """Initialize library structure in state"""
        if "resource_library" not in self.state:
            self.state["resource_library"] = {}
        
        if self.user_id not in self.state["resource_library"]:
            self.state["resource_library"][self.user_id] = {
                "pdfs": [],
                "videos": [],
                "notes": [],
                "bookmarks": [],
                "highlights": [],     # {id, resource_id, text, color, location, created_at}
                "annotations": [],    # {id, resource_id, note, location, created_at}
                "folders": {},        # {folder_name: [resource_id, ...]}
                "downloads": [],      # {resource_id, filename, downloaded_at}
                "generated_materials": {
                    "summaries": [],
                    "flashcards": [],
                    "svgs": [],
                    "practice_problems": []
                },
                "metadata": {
                    "total_resources": 0,
                    "indexed_topics": [],
                    "last_updated": None
                }
            }
    
    def upload_pdf(self, file_path: str, file_content: str, subject: str) -> Dict[str, Any]:
        """
        Upload and process PDF
        
        Args:
            file_path: Original filename
            file_content: Extracted text content (OCR already done)
            subject: Subject category
        
        Returns:
            Processing results with chunk count
        """
        
        # Parse structure (detect chapters, sections, headings)
        structure = self._parse_document_structure(file_content)
        
        # Semantic chunking
        chunks = self._semantic_chunk(file_content, structure)
        
        # Extract topics covered
        topics = self._extract_topics(file_content, subject)
        
        # Store in library
        pdf_entry = {
            "id": f"pdf_{len(self.state['resource_library'][self.user_id]['pdfs'])}",
            "filename": file_path,
            "subject": subject,
            "pages": len(file_content.split('\n\n\n')),  # Rough page estimate
            "chunks": chunks,
            "structure": structure,
            "topics_covered": topics,
            "uploaded_at": datetime.now().isoformat(),
            "indexed": True,
            "usage_count": 0
        }
        
        self.state["resource_library"][self.user_id]["pdfs"].append(pdf_entry)
        
        # Update metadata
        self.state["resource_library"][self.user_id]["metadata"]["total_resources"] += 1
        self.state["resource_library"][self.user_id]["metadata"]["indexed_topics"].extend(topics)
        self.state["resource_library"][self.user_id]["metadata"]["last_updated"] = datetime.now().isoformat()
        
        return {
            "success": True,
            "resource_id": pdf_entry["id"],
            "chunks_created": len(chunks),
            "topics_found": len(topics),
            "message": f"Processed {file_path}: {len(chunks)} chunks, {len(topics)} topics"
        }
    
    def _parse_document_structure(self, text: str) -> Dict[str, Any]:
        """Parse document to detect headings, chapters, sections"""
        
        lines = text.split('\n')
        structure = {
            "chapters": [],
            "sections": [],
            "subsections": []
        }
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Detect chapters (all caps, or "Chapter X", or numbered headings)
            if line_stripped.isupper() and len(line_stripped) > 5:
                structure["chapters"].append({"title": line_stripped, "line": i})
            elif re.match(r'^Chapter\s+\d+', line_stripped, re.IGNORECASE):
                structure["chapters"].append({"title": line_stripped, "line": i})
            elif re.match(r'^\d+\.\s+[A-Z]', line_stripped):
                structure["sections"].append({"title": line_stripped, "line": i})
            elif re.match(r'^\d+\.\d+\s+[A-Z]', line_stripped):
                structure["subsections"].append({"title": line_stripped, "line": i})
        
        return structure
    
    def _semantic_chunk(self, text: str, structure: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Chunk text semantically based on structure
        Target: ~500 tokens per chunk with natural boundaries
        """
        
        chunks = []
        lines = text.split('\n')
        
        # If structure detected, chunk by sections
        if structure["sections"]:
            section_boundaries = [s["line"] for s in structure["sections"]]
            section_boundaries.append(len(lines))
            
            for i in range(len(section_boundaries) - 1):
                start = section_boundaries[i]
                end = section_boundaries[i + 1]
                section_text = '\n'.join(lines[start:end])
                
                # Split large sections into smaller chunks
                if len(section_text.split()) > 600:
                    sub_chunks = self._split_large_chunk(section_text)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append({
                        "text": section_text,
                        "type": "section",
                        "start_line": start,
                        "end_line": end,
                        "tokens": len(section_text.split())
                    })
        else:
            # No clear structure, use paragraph-based chunking
            paragraphs = text.split('\n\n')
            current_chunk = []
            current_tokens = 0
            
            for para in paragraphs:
                para_tokens = len(para.split())
                
                if current_tokens + para_tokens > 600:
                    # Save current chunk
                    chunks.append({
                        "text": '\n\n'.join(current_chunk),
                        "type": "paragraph_group",
                        "tokens": current_tokens
                    })
                    current_chunk = [para]
                    current_tokens = para_tokens
                else:
                    current_chunk.append(para)
                    current_tokens += para_tokens
            
            # Save last chunk
            if current_chunk:
                chunks.append({
                    "text": '\n\n'.join(current_chunk),
                    "type": "paragraph_group",
                    "tokens": current_tokens
                })
        
        return chunks
    
    def _split_large_chunk(self, text: str) -> List[Dict[str, Any]]:
        """Split large chunks into smaller ones at paragraph boundaries"""
        
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for para in paragraphs:
            para_tokens = len(para.split())
            
            if current_tokens + para_tokens > 500:
                chunks.append({
                    "text": '\n\n'.join(current_chunk),
                    "type": "sub_chunk",
                    "tokens": current_tokens
                })
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens
        
        if current_chunk:
            chunks.append({
                "text": '\n\n'.join(current_chunk),
                "type": "sub_chunk",
                "tokens": current_tokens
            })
        
        return chunks
    
    def _extract_topics(self, text: str, subject: str) -> List[str]:
        """Extract main topics from text"""
        
        # Look for common topic indicators
        topics = []
        lines = text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            
            # Headings (all caps or title case)
            if line_stripped.isupper() and 5 < len(line_stripped) < 50:
                topics.append(line_stripped.lower().title())
            
            # Numbered sections
            match = re.match(r'^\d+\.?\s+([A-Z][^.]+)', line_stripped)
            if match:
                topics.append(match.group(1).strip())
        
        # Remove duplicates while preserving order
        seen = set()
        unique_topics = []
        for topic in topics:
            if topic not in seen:
                seen.add(topic)
                unique_topics.append(topic)
        
        return unique_topics[:20]  # Return top 20 topics
    
    def search_resources(self, query: str, resource_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        Search across all resources for query
        
        Args:
            query: Search query
            resource_types: Filter by types (e.g., ['pdfs', 'videos'])
        
        Returns:
            List of matching resources with relevance scores
        """
        
        library = self.state["resource_library"][self.user_id]
        results = []
        query_lower = query.lower()
        
        # Search PDFs
        if not resource_types or 'pdfs' in resource_types:
            for pdf in library["pdfs"]:
                # Check if query matches topics
                topic_matches = [t for t in pdf["topics_covered"] if query_lower in t.lower()]
                
                # Check chunks for content matches
                chunk_matches = []
                for i, chunk in enumerate(pdf["chunks"]):
                    if query_lower in chunk["text"].lower():
                        chunk_matches.append({
                            "chunk_index": i,
                            "preview": chunk["text"][:200] + "..."
                        })
                
                if topic_matches or chunk_matches:
                    results.append({
                        "type": "pdf",
                        "resource_id": pdf["id"],
                        "filename": pdf["filename"],
                        "subject": pdf["subject"],
                        "topic_matches": topic_matches,
                        "chunk_matches": chunk_matches[:3],  # Top 3 chunks
                        "relevance": len(topic_matches) * 10 + len(chunk_matches)
                    })
        
        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)
        
        return results
    
    def get_resource_by_id(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource details by ID"""
        
        library = self.state["resource_library"][self.user_id]
        
        # Search in PDFs
        for pdf in library["pdfs"]:
            if pdf["id"] == resource_id:
                return pdf
        
        # Search in videos
        for video in library["videos"]:
            if video["id"] == resource_id:
                return video
        
        return None
    
    def add_bookmark(self, resource_id: str, location: str, note: str = "") -> Dict[str, Any]:
        """Add bookmark to a resource"""
        
        bookmark = {
            "id": f"bookmark_{len(self.state['resource_library'][self.user_id]['bookmarks'])}",
            "resource_id": resource_id,
            "location": location,  # page number, timestamp, chunk index
            "note": note,
            "created_at": datetime.now().isoformat()
        }
        
        self.state["resource_library"][self.user_id]["bookmarks"].append(bookmark)
        
        return bookmark
    
    def get_bookmarks(self, resource_id: str = None) -> List[Dict[str, Any]]:
        """Get all bookmarks, optionally filtered by resource"""
        
        bookmarks = self.state["resource_library"][self.user_id]["bookmarks"]
        
        if resource_id:
            return [b for b in bookmarks if b["resource_id"] == resource_id]
        
        return bookmarks
    
    def add_generated_material(self, material_type: str, content: Any, learning_unit: str) -> str:
        """
        Store generated materials (summaries, flashcards, SVGs, etc.)
        
        Args:
            material_type: 'summary', 'flashcard', 'svg', 'practice_problem'
            content: The generated content
            learning_unit: Which learning unit this is for
        
        Returns:
            material_id
        """
        
        material = {
            "id": f"{material_type}_{len(self.state['resource_library'][self.user_id]['generated_materials'][material_type + 's'])}",
            "type": material_type,
            "content": content,
            "learning_unit": learning_unit,
            "created_at": datetime.now().isoformat(),
            "usage_count": 0
        }
        
        self.state["resource_library"][self.user_id]["generated_materials"][material_type + "s"].append(material)
        
        return material["id"]
    
    def get_resources_for_topic(self, topic: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get all resources related to a topic"""
        
        library = self.state["resource_library"][self.user_id]
        topic_lower = topic.lower()
        
        results = {
            "pdfs": [],
            "videos": [],
            "notes": [],
            "generated_materials": []
        }
        
        # Search PDFs
        for pdf in library["pdfs"]:
            if any(topic_lower in t.lower() for t in pdf["topics_covered"]):
                results["pdfs"].append(pdf)
        
        # Search generated materials
        for mat_type, materials in library["generated_materials"].items():
            for material in materials:
                if topic_lower in material["learning_unit"].lower():
                    results["generated_materials"].append(material)
        
        return results
    
    def increment_usage(self, resource_id: str):
        """Track resource usage"""
        
        resource = self.get_resource_by_id(resource_id)
        if resource:
            resource["usage_count"] = resource.get("usage_count", 0) + 1
            resource["last_used"] = datetime.now().isoformat()
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get library statistics"""
        
        library = self.state["resource_library"][self.user_id]
        
        return {
            "total_pdfs": len(library["pdfs"]),
            "total_videos": len(library["videos"]),
            "total_bookmarks": len(library["bookmarks"]),
            "total_highlights": len(library.get("highlights", [])),
            "total_annotations": len(library.get("annotations", [])),
            "total_folders": len(library.get("folders", {})),
            "total_summaries": len(library["generated_materials"]["summaries"]),
            "total_flashcards": len(library["generated_materials"]["flashcards"]),
            "total_svgs": len(library["generated_materials"]["svgs"]),
            "indexed_topics": len(set(library["metadata"]["indexed_topics"])),
            "last_updated": library["metadata"]["last_updated"]
        }
    
    # ── Folder management ────────────────────────────────────────────────────
    
    def create_folder(self, folder_name: str) -> Dict[str, Any]:
        """Create a named folder for organising resources."""
        library = self.state["resource_library"][self.user_id]
        library.setdefault("folders", {})
        if folder_name not in library["folders"]:
            library["folders"][folder_name] = []
        return {"folder": folder_name, "resource_ids": library["folders"][folder_name]}
    
    def add_to_folder(self, folder_name: str, resource_id: str) -> bool:
        """Add a resource to a folder. Creates folder if it does not exist."""
        library = self.state["resource_library"][self.user_id]
        library.setdefault("folders", {})
        library["folders"].setdefault(folder_name, [])
        if resource_id not in library["folders"][folder_name]:
            library["folders"][folder_name].append(resource_id)
            return True
        return False
    
    def remove_from_folder(self, folder_name: str, resource_id: str) -> bool:
        """Remove a resource from a folder."""
        library = self.state["resource_library"][self.user_id]
        folder = library.get("folders", {}).get(folder_name, [])
        if resource_id in folder:
            folder.remove(resource_id)
            return True
        return False
    
    def get_folder_contents(self, folder_name: str) -> List[Dict[str, Any]]:
        """Get all resources in a folder with their details."""
        library = self.state["resource_library"][self.user_id]
        resource_ids = library.get("folders", {}).get(folder_name, [])
        return [r for r in (self.get_resource_by_id(rid) for rid in resource_ids) if r]
    
    def list_folders(self) -> Dict[str, int]:
        """Return folder names with their resource counts."""
        folders = self.state["resource_library"][self.user_id].get("folders", {})
        return {name: len(ids) for name, ids in folders.items()}
    
    # ── Highlights ────────────────────────────────────────────────────────────
    
    def add_highlight(
        self,
        resource_id: str,
        text: str,
        location: str,
        color: str = "yellow",
    ) -> Dict[str, Any]:
        """Highlight a passage in a resource."""
        library = self.state["resource_library"][self.user_id]
        library.setdefault("highlights", [])
        highlight = {
            "id": f"hl_{len(library['highlights'])}",
            "resource_id": resource_id,
            "text": text,
            "color": color,
            "location": location,
            "created_at": datetime.now().isoformat(),
        }
        library["highlights"].append(highlight)
        return highlight
    
    def get_highlights(self, resource_id: str = None) -> List[Dict[str, Any]]:
        """Get highlights, optionally filtered by resource."""
        highlights = self.state["resource_library"][self.user_id].get("highlights", [])
        if resource_id:
            return [h for h in highlights if h["resource_id"] == resource_id]
        return highlights
    
    def delete_highlight(self, highlight_id: str) -> bool:
        library = self.state["resource_library"][self.user_id]
        before = len(library.get("highlights", []))
        library["highlights"] = [h for h in library.get("highlights", []) if h["id"] != highlight_id]
        return len(library["highlights"]) < before
    
    # ── Annotations ──────────────────────────────────────────────────────────
    
    def add_annotation(
        self,
        resource_id: str,
        note: str,
        location: str,
    ) -> Dict[str, Any]:
        """Add a text annotation to a specific location in a resource."""
        library = self.state["resource_library"][self.user_id]
        library.setdefault("annotations", [])
        annotation = {
            "id": f"ann_{len(library['annotations'])}",
            "resource_id": resource_id,
            "note": note,
            "location": location,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        library["annotations"].append(annotation)
        return annotation
    
    def get_annotations(self, resource_id: str = None) -> List[Dict[str, Any]]:
        """Get annotations, optionally filtered by resource."""
        annotations = self.state["resource_library"][self.user_id].get("annotations", [])
        if resource_id:
            return [a for a in annotations if a["resource_id"] == resource_id]
        return annotations
    
    def update_annotation(self, annotation_id: str, note: str) -> bool:
        """Update the text of an existing annotation."""
        for ann in self.state["resource_library"][self.user_id].get("annotations", []):
            if ann["id"] == annotation_id:
                ann["note"] = note
                ann["updated_at"] = datetime.now().isoformat()
                return True
        return False
    
    def delete_annotation(self, annotation_id: str) -> bool:
        library = self.state["resource_library"][self.user_id]
        before = len(library.get("annotations", []))
        library["annotations"] = [a for a in library.get("annotations", []) if a["id"] != annotation_id]
        return len(library["annotations"]) < before
    
    # ── Downloads ────────────────────────────────────────────────────────────
    
    def mark_downloaded(self, resource_id: str) -> Dict[str, Any]:
        """Record that a resource was downloaded locally."""
        resource = self.get_resource_by_id(resource_id)
        library = self.state["resource_library"][self.user_id]
        library.setdefault("downloads", [])
        entry = {
            "resource_id": resource_id,
            "filename": resource.get("filename", resource_id) if resource else resource_id,
            "downloaded_at": datetime.now().isoformat(),
        }
        # avoid duplicates
        existing = [d for d in library["downloads"] if d["resource_id"] == resource_id]
        if not existing:
            library["downloads"].append(entry)
        return entry
    
    def get_downloads(self) -> List[Dict[str, Any]]:
        return self.state["resource_library"][self.user_id].get("downloads", [])
    
    # ── Delete resource ───────────────────────────────────────────────────────
    
    def delete_resource(self, resource_id: str) -> bool:
        """Remove a resource from the library (but keep highlights/annotations intact)."""
        library = self.state["resource_library"][self.user_id]
        before = len(library["pdfs"]) + len(library["videos"])
        library["pdfs"] = [p for p in library["pdfs"] if p["id"] != resource_id]
        library["videos"] = [v for v in library["videos"] if v["id"] != resource_id]
        after = len(library["pdfs"]) + len(library["videos"])
        # Also remove from folders
        for folder in library.get("folders", {}).values():
            if resource_id in folder:
                folder.remove(resource_id)
        return after < before


# Alias so both names work — the Knowledge Hub is the same as the Resource Hub
KnowledgeHub = ResourceHub
