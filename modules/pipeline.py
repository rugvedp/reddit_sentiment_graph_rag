import json
import time
import torch
import numpy as np
from sklearn.cluster import KMeans
from sentence_transformers import SentenceTransformer
from core.config import Config
from core.schemas import BatchDiscussionResponse, DynamicDiscussion
from utils.logger import step_logger, log_memory_status

class BrandPipeline:
    def __init__(self, driver, groq_client):
        self.driver = driver
        self.groq = groq_client
        # Load model on M4 Pro (MPS)
        self.model = SentenceTransformer(Config.EMBED_MODEL, device=Config.DEVICE)
        self.colors = ["#FF5733", "#33FF57", "#3357FF", "#F333FF", "#FFF333", "#33FFF3", "#FF8333"]

    def init_db(self):
        """Initializes database constraints and vector indexes."""
        queries = [
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Post) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Cluster) REQUIRE c.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            """
            CREATE VECTOR INDEX post_embeddings IF NOT EXISTS FOR (p:Post) ON (p.embedding) 
            OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}}
            """
        ]
        with self.driver.session() as s:
            for q in queries:
                try:
                    s.run(q)
                except Exception:
                    pass 

    def get_all_brands(self):
        with self.driver.session() as s:
            result = s.run("MATCH (b:Brand) RETURN b.name as name ORDER BY b.name ASC")
            return [record["name"] for record in result]
        
    def check_brand_exists(self, brand_name):
        with self.driver.session() as s:
            res = s.run("MATCH (b:Brand {name: $name}) RETURN b LIMIT 1", name=brand_name)
            return res.single() is not None

    def analyze_posts(self, brand, posts):
        start_time = time.time()
        step_logger.info(f"Analyzing {len(posts)} posts via Groq...")
        meta_map = {}
        for i in range(0, len(posts), 12):
            batch = posts[i : i+12]
            payload = [{"id": p["id"], "txt": p["title"]} for p in batch]
            prompt = f"Analyze these '{brand}' discussions. Return JSON results list: id, topic, nature, score, reason, people_mentioned. Data: {json.dumps(payload)}"
            try:
                resp = self.groq.chat.completions.create(
                    model=Config.EXTRACT_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                items = json.loads(resp.choices[0].message.content).get("results", [])
                for item in items:
                    valid_item = DynamicDiscussion(**item)
                    meta_map[valid_item.id] = valid_item.model_dump()
                time.sleep(1.0)
            except Exception as e:
                step_logger.error(f"Extraction error in batch {i}: {e}")
        
        log_memory_status("LLM Analysis", start_time)
        return meta_map

    def name_clusters(self, cluster_samples):
        named_clusters = {}
        step_logger.info(f"Naming {len(cluster_samples)} clusters...")
        
        for cid, titles in cluster_samples.items():
            sample_text = "\n- ".join(titles[:8])
            prompt = f"Summarize these Reddit post titles into a concise 3-word theme name:\n{sample_text}"
            
            try:
                resp = self.groq.chat.completions.create(
                    model=Config.EXTRACT_MODEL,
                    messages=[{"role": "system", "content": "You are a branding expert. Return only the name."},
                            {"role": "user", "content": prompt}]
                )
                clean_name = resp.choices[0].message.content.strip().replace('"', '')
                named_clusters[cid] = clean_name
                
                # ADD THIS: Wait 0.5 seconds between naming requests to prevent 429
                time.sleep(0.5) 
                
            except Exception as e:
                step_logger.error(f"Error naming cluster {cid}: {e}")
                named_clusters[cid] = f"Discussion Group {cid}"
        
        return named_clusters
    
    def build_graph(self, brand, posts, meta_map):
        if not posts:
            step_logger.warning("No posts to build graph.")
            return

        start_time = time.time()
        step_logger.info(f"Generating embeddings for {len(posts)} posts...")

        # 1️⃣ Use FULL TEXT for embeddings
        texts = [p.get("full_text") or f"{p['title']} {p.get('selftext','')}" for p in posts]
        embeddings = self.model.encode(texts, batch_size=32, convert_to_numpy=True)

        if Config.DEVICE == "mps":
            torch.mps.empty_cache()

        # 2️⃣ Cluster
        num_cl = min(12, max(2, len(posts)//8))
        kmeans = KMeans(n_clusters=num_cl, n_init=10, random_state=42).fit(embeddings)
        labels = kmeans.labels_

        cluster_samples = {}
        for idx, label in enumerate(labels):
            cluster_samples.setdefault(label, []).append(posts[idx]['title'])

        cluster_names = self.name_clusters(cluster_samples)

        # 3️⃣ Upload Graph
        with self.driver.session() as s:

            s.run("MERGE (b:Brand {name:$name})", name=brand)

            for idx, p in enumerate(posts):
                meta = meta_map.get(p["id"], {})
                cid = int(labels[idx])
                cluster_name = cluster_names.get(cid, f"Group {cid}")

                s.run("""
                MATCH (b:Brand {name:$brand})

                MERGE (cl:Cluster {id:$cid})
                SET cl.name=$cluster_name

                MERGE (sub:Subreddit {name:$subreddit})

                MERGE (author:Person {name:$author})

                MERGE (post:Post {id:$id})
                SET post.title=$title,
                    post.body=$body,
                    post.score=$score,
                    post.upvote_ratio=$ratio,
                    post.num_comments=$comments,
                    post.created_utc=$created,
                    post.url=$url,
                    post.embedding=$embedding,
                    post.sentiment_score=$sentiment,
                    post.nature=$nature,
                    post.reason=$reason,
                    post.cluster_name=$cluster_name

                MERGE (post)-[:BELONGS_TO]->(cl)
                MERGE (post)-[:SUBJECT_OF]->(b)
                MERGE (post)-[:POSTED_IN]->(sub)
                MERGE (post)-[:AUTHORED_BY]->(author)
                MERGE (author)-[:ACTIVE_IN]->(sub)

                MERGE (t:Topic {name:$topic})
                MERGE (post)-[:DISCUSSES]->(t)
                MERGE (t)-[:RELATED_TO]->(b)
                """,
                brand=brand,
                cid=cid,
                cluster_name=cluster_name,
                id=p["id"],
                title=p["title"],
                body=p.get("selftext"),
                score=p.get("score"),
                ratio=p.get("upvote_ratio"),
                comments=p.get("num_comments"),
                created=p.get("created_utc"),
                url=p.get("permalink"),
                embedding=embeddings[idx].tolist(),
                sentiment=meta.get("score", 0),
                nature=meta.get("nature", "Unknown"),
                reason=meta.get("reason", ""),
                topic=meta.get("topic", "General"),
                subreddit=p.get("subreddit"),
                author=p.get("author")
                )

                # 4️⃣ Insert Comments
                for c in p.get("top_comments", []):
                    s.run("""
                    MATCH (post:Post {id:$post_id})  // 1. Find the post first
                    MERGE (person:Person {name:$author}) // 2. Ensure author exists
                    MERGE (comment:Comment {id:$cid}) // 3. Ensure comment exists
                    SET comment.body=$body,
                        comment.score=$score,
                        comment.created_utc=$created,
                        comment.controversiality=$controversy

                    // 4. Create relationships
                    MERGE (comment)-[:ON_POST]->(post)
                    MERGE (comment)-[:AUTHORED_BY]->(person)
                    """,
                    cid=c.get("id"),
                    body=c.get("body"),
                    score=c.get("score"),
                    created=c.get("created_utc"),
                    controversy=c.get("controversiality"),
                    author=c.get("author"),
                    post_id=p["id"]
                    )

        log_memory_status("Robust Graph Building", start_time)
