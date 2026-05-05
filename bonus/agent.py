import uuid
from pathlib import Path
from datetime import datetime

from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from feast import FeatureStore

REPO_ROOT = Path(__file__).resolve().parent.parent
FEAST_DIR = REPO_ROOT / "app" / "feast_repo"

class HybridMemoryAgent:
    def __init__(self):
        # 1. Initialize Qdrant for Episodic Memory
        # Using bge-small as it is the default in the lab. In production for VN, bge-m3 is better.
        self.embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        self.qdrant = QdrantClient(":memory:")
        self.collection_name = "episodic_memory"
        self.qdrant.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )
        
        # 2. Initialize Feast for Stable Profile & Recent Activity
        try:
            self.fs = FeatureStore(repo_path=str(FEAST_DIR))
        except Exception as e:
            print(f"Warning: Could not initialize Feast. Make sure 'feast apply' and 'feast materialize-incremental' were run in {FEAST_DIR}.")
            print(f"Error: {e}")
            self.fs = None

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Add a new piece of episodic memory for this user."""
        # Simple per-message chunking for POC
        vector = list(self.embedder.embed([text]))[0].tolist()
        
        point_id = str(uuid.uuid4())
        point = PointStruct(
            id=point_id, 
            vector=vector,
            payload={
                "user_id": user_id, 
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
        )
        self.qdrant.upsert(collection_name=self.collection_name, points=[point])

    def recall(self, query: str, user_id: str = "u_001", top_k: int = 3) -> str:
        """Retrieve top-K memories + user profile features -> return assembled context."""
        
        # 1. Get user profile + recent activity from Feast online store
        profile_context = ""
        if self.fs:
            try:
                features = self.fs.get_online_features(
                    features=[
                        "user_profile_features:reading_speed_wpm",
                        "user_profile_features:preferred_language",
                        "user_profile_features:topic_affinity",
                        "query_velocity_features:queries_last_hour",
                    ],
                    entity_rows=[{"user_id": user_id}],
                ).to_dict()
                
                lang = features.get('preferred_language', ['en'])[0]
                topic = features.get('topic_affinity', ['general'])[0]
                speed = features.get('reading_speed_wpm', [200])[0]
                recent_queries = features.get('queries_last_hour', [0])[0]
                
                profile_context = (
                    f"User Profile: preferred language is '{lang}', "
                    f"topic affinity is '{topic}', reading speed {speed} wpm.\n"
                    f"Recent Activity: {recent_queries} queries in the last hour."
                )
            except Exception as e:
                profile_context = f"[Feast Error: {e}]"
        else:
            profile_context = "[Feast not initialized]"
            
        # 2. Vector search Qdrant filtered by user_id
        q_vec = list(self.embedder.embed([query]))[0].tolist()
        
        search_res = self.qdrant.query_points(
            collection_name=self.collection_name,
            query=q_vec,
            query_filter=Filter(
                must=[
                    FieldCondition(key="user_id", match=MatchValue(value=user_id))
                ]
            ),
            limit=top_k
        )
        
        # Lowered threshold to ensure we get matches for the demo, or just use top k
        memories = [p.payload['text'] for p in search_res.points if p.score > 0.1]
        
        if memories:
            memory_str = "\n".join([f"- {m}" for m in memories])
        else:
            memory_str = "No relevant episodic memories found."
            
        # 3. Assemble context string
        assembled_context = f"""
==================================================
[SYSTEM ASSEMBLED CONTEXT FOR LLM]
Query: "{query}"

{profile_context}

Top Relevant Memories:
{memory_str}
==================================================
"""
        return assembled_context.strip()
