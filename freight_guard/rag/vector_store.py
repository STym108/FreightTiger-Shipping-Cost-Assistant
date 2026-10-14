"""
ChromaDB Vector Store & Retrieval Engine for Context Notes.

Indexes context notes with semantic embeddings and structured metadata
(route, date, date_range, impact_class) to enable hybrid semantic + metadata filtering.
"""

import os
from typing import List, Dict, Any, Optional
import pandas as pd
import chromadb
from chromadb.utils import embedding_functions


class ContextNoteStore:
    """
    Vector database wrapper for shipping context notes using ChromaDB.
    """

    def __init__(self, notes_csv_path: str, persist_dir: Optional[str] = None):
        self.notes_csv_path = notes_csv_path
        self.persist_dir = persist_dir

        if persist_dir:
            self.client = chromadb.PersistentClient(path=persist_dir)
        else:
            self.client = chromadb.Client()

        # Local default embedding function (ONNX all-MiniLM-L6-v2, 100% local, no API keys needed)
        self.embedding_fn = embedding_functions.DefaultEmbeddingFunction()
        
        # Reset or get collection
        collection_name = "shipping_context_notes"
        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            pass

        self.collection = self.client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )

        self._load_and_index_notes()

    def _load_and_index_notes(self):
        """Loads context_notes.csv and populates the ChromaDB collection."""
        df = pd.read_csv(self.notes_csv_path)

        documents = []
        metadatas = []
        ids = []

        for _, row in df.iterrows():
            note_id = str(row['note_id']).strip()
            date = str(row['date']).strip()
            applies_to = str(row['applies_to']).strip()
            note_text = str(row['note']).strip()

            # Classify known note attributes for precise guardrail filtering
            is_all_routes = (applies_to.lower() == "all routes")

            # Document representation enriched for retrieval
            doc_text = f"Date: {date} | Route: {applies_to} | Note: {note_text}"
            
            documents.append(doc_text)
            ids.append(note_id)
            metadatas.append({
                "note_id": note_id,
                "date": date,
                "applies_to": applies_to,
                "is_all_routes": is_all_routes,
                "raw_note": note_text
            })

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def retrieve_candidates(
        self,
        query: str,
        route: str,
        week_of: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Retrieves top-k candidate notes for a given route and week query.
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )

        candidates = []
        if results and results['ids'] and len(results['ids'][0]) > 0:
            for i in range(len(results['ids'][0])):
                candidates.append({
                    "note_id": results['ids'][0][i],
                    "metadata": results['metadatas'][0][i],
                    "document": results['documents'][0][i],
                    "distance": results['distances'][0][i] if 'distances' in results and results['distances'] else 0.0
                })

        return candidates

    def get_all_notes(self) -> List[Dict[str, Any]]:
        """Returns all indexed notes."""
        data = self.collection.get()
        notes = []
        for i in range(len(data['ids'])):
            notes.append({
                "note_id": data['ids'][i],
                "metadata": data['metadatas'][i],
                "document": data['documents'][i]
            })
        return notes
