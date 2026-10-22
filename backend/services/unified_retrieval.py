"""
Unified Retrieval Service with Fallback Routing

This module implements a two-tier retrieval strategy:
1. Primary search in the classified source (FAQ FAISS or KB FAISS)
2. If results don't meet confidence threshold, secondary search in alternative source
3. Combines and re-ranks context from both sources for LLM consumption
"""

import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger("unified_retrieval")

# Confidence thresholds for triggering fallback
PRIMARY_CONFIDENCE_THRESHOLD = 0.30  # Minimum CE score to consider primary sufficient
MIN_RESULTS_REQUIRED = 2  # Minimum number of results needed from primary
MAX_COMBINED_CONTEXT_CHUNKS = 8  # Max chunks to pass to LLM


@dataclass
class RetrievalResult:
    """Result from a retrieval source"""
    source: str  # "faq" or "kb"
    chunks: List[Dict]  # Each: {"text": str, "metadata": dict, "score": float}
    best_score: float


async def search_faq_index(query: str, k: int = 20, tenant_id: Optional[str] = None) -> RetrievalResult:
    """Search FAQ hybrid index (FAISS + BM25 + rerank), scoped to one tenant"""
    from backend.faq.service import faq_index, _clean_faq_chunk

    if not faq_index.is_built:
        logger.warning("FAQ index not built, attempting build")
        try:
            faq_index.build()
        except Exception as e:
            logger.error(f"FAQ index build failed: {e}")
            return RetrievalResult(source="faq", chunks=[], best_score=0.0)

    if not faq_index.is_built:
        return RetrievalResult(source="faq", chunks=[], best_score=0.0)

    try:
        results = faq_index.search(query, k=k, tenant_id=tenant_id)
        chunks = []
        best_score = 0.0
        for chunk_text, metadata, score in results:
            cleaned = _clean_faq_chunk(chunk_text)
            chunks.append({
                "text": cleaned,
                "metadata": metadata,
                "score": float(score)
            })
            if score > best_score:
                best_score = float(score)
        
        logger.info(f"FAQ search: {len(chunks)} results, best_score={best_score:.3f}")
        return RetrievalResult(source="faq", chunks=chunks, best_score=best_score)
    except Exception as e:
        logger.error(f"FAQ search failed: {e}")
        return RetrievalResult(source="faq", chunks=[], best_score=0.0)


async def search_kb_index(query: str, k: int = 20, tenant_id: Optional[str] = None) -> RetrievalResult:
    """Search KB FAISS index, scoped to one tenant"""
    try:
        from kb.services.rag import search_kb_faiss
        from database import get_db_context

        hits = search_kb_faiss(query, limit=k, tenant_id=tenant_id)
        if not hits:
            return RetrievalResult(source="kb", chunks=[], best_score=0.0)
        
        chunks = []
        best_score = 0.0
        
        for hit in hits:
            score = float(hit.get("score", 0.0))
            doc_id = hit.get("doc_id")
            chunk_index = hit.get("chunk_index")
            
            # Fetch full chunk text from database
            with get_db_context() as conn:
                row = conn.execute(
                    "SELECT chunks_json FROM knowledge_base WHERE id=?", (doc_id,)
                ).fetchone()
            
            if row and row[0]:
                import json as _json
                chunks_data = _json.loads(row[0])
                if isinstance(chunk_index, int) and 0 <= chunk_index < len(chunks_data):
                    chunk_text = chunks_data[chunk_index]
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {"doc_id": doc_id, "chunk_index": chunk_index},
                        "score": score
                    })
                    if score > best_score:
                        best_score = score
        
        logger.info(f"KB search: {len(chunks)} results, best_score={best_score:.3f}")
        return RetrievalResult(source="kb", chunks=chunks, best_score=best_score)
    except Exception as e:
        logger.error(f"KB search failed: {e}")
        return RetrievalResult(source="kb", chunks=[], best_score=0.0)


def _should_fallback(primary_result: RetrievalResult) -> bool:
    """Determine if we should trigger fallback to secondary source"""
    if not primary_result.chunks:
        logger.info("Fallback triggered: no primary results")
        return True
    
    if primary_result.best_score < PRIMARY_CONFIDENCE_THRESHOLD:
        logger.info(f"Fallback triggered: best_score {primary_result.best_score:.3f} < threshold {PRIMARY_CONFIDENCE_THRESHOLD}")
        return True
    
    if len(primary_result.chunks) < MIN_RESULTS_REQUIRED:
        logger.info(f"Fallback triggered: only {len(primary_result.chunks)} results < {MIN_RESULTS_REQUIRED}")
        return True
    
    return False


def _merge_and_rerank(primary: RetrievalResult, secondary: RetrievalResult, query: str) -> List[Dict]:
    """Merge chunks from both sources, deduplicate, and sort by score"""
    all_chunks = []
    
    # Add primary chunks with source tag
    for chunk in primary.chunks:
        chunk_copy = chunk.copy()
        chunk_copy["retrieval_source"] = "primary"
        all_chunks.append(chunk_copy)
    
    # Add secondary chunks with source tag
    for chunk in secondary.chunks:
        chunk_copy = chunk.copy()
        chunk_copy["retrieval_source"] = "secondary"
        all_chunks.append(chunk_copy)
    
    # Deduplicate by text similarity (simple approach: exact text match)
    seen_texts = set()
    unique_chunks = []
    for chunk in all_chunks:
        text_hash = hash(chunk["text"][:200])  # Use first 200 chars for dedup
        if text_hash not in seen_texts:
            seen_texts.add(text_hash)
            unique_chunks.append(chunk)
    
    # Sort by score descending
    unique_chunks.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Limit total chunks
    return unique_chunks[:MAX_COMBINED_CONTEXT_CHUNKS]


def _format_combined_context(chunks: List[Dict]) -> str:
    """Format merged chunks into context string for LLM"""
    if not chunks:
        return "No relevant information found in knowledge bases."
    
    context_parts = []
    for chunk in chunks:
        source = chunk.get("retrieval_source", "unknown")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")
        metadata = chunk.get("metadata", {})
        source_file = metadata.get("source_file") or metadata.get("doc_id", "unknown")
        
        context_parts.append(
            f"[source={source} | score={score:.3f} | file={source_file}]\n{text}"
        )
    
    return "\n\n---\n\n".join(context_parts)


async def unified_retrieve(
    query: str,
    primary_source: str,  # "faq" or "kb"
    k: int = 20,
    tenant_id: Optional[str] = None,
) -> Tuple[str, Dict]:
    """
    Unified retrieval with fallback routing.
    
    Args:
        query: User's question
        primary_source: Which source to search first ("faq" or "kb")
        k: Number of candidates to retrieve from each source
        tenant_id: Tenant whose content may be retrieved (None → default tenant)
    
    Returns:
        Tuple of (combined_context_string, metadata_dict)
        metadata contains: primary_source, fallback_triggered, primary_score, secondary_score, total_chunks
    """
    logger.info(f"Unified retrieval: query='{query[:100]}', primary={primary_source}")
    
    # Determine primary and secondary search functions
    if primary_source == "faq":
        primary_search = search_faq_index
        secondary_search = search_kb_index
    else:
        primary_search = search_kb_index
        secondary_search = search_faq_index
    
    # Step 1: Primary search
    primary_result = await primary_search(query, k=k, tenant_id=tenant_id)
    
    # Step 2: Check if fallback needed
    fallback_triggered = _should_fallback(primary_result)
    
    secondary_result = RetrievalResult(source="secondary", chunks=[], best_score=0.0)
    
    if fallback_triggered:
        # Step 3: Secondary search
        logger.info(f"Triggering fallback search in {'kb' if primary_source == 'faq' else 'faq'}")
        secondary_result = await secondary_search(query, k=k, tenant_id=tenant_id)
    
    # Step 4: Merge and re-rank
    combined_chunks = _merge_and_rerank(primary_result, secondary_result, query)
    
    # Step 5: Format context
    combined_context = _format_combined_context(combined_chunks)
    
    metadata = {
        "primary_source": primary_source,
        "fallback_triggered": fallback_triggered,
        "primary_best_score": primary_result.best_score,
        "secondary_best_score": secondary_result.best_score,
        "total_chunks": len(combined_chunks),
        "primary_chunks_count": len(primary_result.chunks),
        "secondary_chunks_count": len(secondary_result.chunks),
    }
    
    logger.info(
        f"Unified retrieval complete: fallback={fallback_triggered}, "
        f"primary_score={primary_result.best_score:.3f}, "
        f"secondary_score={secondary_result.best_score:.3f}, "
        f"total_chunks={len(combined_chunks)}"
    )
    
    return combined_context, metadata