import json
import logging
import re
from core.config import Config

logger = logging.getLogger(__name__)

class BrandChatbot:
    def __init__(self, driver, groq_client, embed_model):
        self.driver = driver
        self.groq = groq_client
        self.embed_model = embed_model
        
        # Schema precisely aligned with your build_graph logic
        self.schema_context = """
        Nodes:
        - Brand {name}
        - Cluster {id, name}
        - Post {id, title, body, score, upvote_ratio, num_comments, sentiment_score, nature, reason, cluster_name, url}
        - Comment {id, body, score, controversiality}
        - Topic {name}
        - Person {name}
        - Subreddit {name}

        Relationships:
        - (Post)-[:BELONGS_TO]->(Cluster)
        - (Post)-[:SUBJECT_OF]->(Brand)
        - (Post)-[:POSTED_IN]->(Subreddit)
        - (Post)-[:AUTHORED_BY]->(Person)
        - (Comment)-[:ON_POST]->(Post)
        - (Comment)-[:AUTHORED_BY]->(Person)
        - (Post)-[:DISCUSSES]->(Topic)
        - (Topic)-[:RELATED_TO]->(Brand)
        """

    def generate_cypher(self, question, brand):
        """Generates advanced Cypher including aggregations and joins."""
        prompt = f"""
        You are a Neo4j Cypher expert. 
        Brand Context: {brand}
        Schema: {self.schema_context}
        
        Task: Generate a Cypher query to answer: "{question}"
        
        Rules for Complex Queries:
        1. If asked about a "Cluster" (e.g., 'Hardware Issues'), search BOTH Cluster nodes AND the cluster_name property on Posts.
        2. To get the "full picture", match Posts and their top Comments using: 
           OPTIONAL MATCH (comment)-[:ON_POST]->(post)
        3. For sentiment analysis, use avg(post.sentiment_score) and collect(DISTINCT post.nature).
        4. If the user asks "what is happening", return: post.title, post.body, post.reason, and a few comment bodies.
        5. Use toLower() for fuzzy string matching.
        6. LIMIT results to 20 for posts and 3 comments per post to save space.

        Return ONLY the raw Cypher code. No backticks.
        Cypher:"""

        resp = self.groq.chat.completions.create(
            model=Config.CHAT_MODEL,
            messages=[{"role": "system", "content": "You are a specialized Neo4j database assistant. Output only raw Cypher code."},
                      {"role": "user", "content": prompt}],
            temperature=0
        )
        
        query = resp.choices[0].message.content.strip()
        return re.sub(r"```cypher|```|;", "", query)

    def vector_search(self, question, limit=5):
        """Fallback when structured query finds nothing."""
        query_emb = self.embed_model.encode(question).tolist()
        cypher = """
        CALL db.index.vector.queryNodes('post_embeddings', $limit, $emb)
        YIELD node, score
        RETURN node {.*, embedding: null} as post, score
        """
        with self.driver.session() as s:
            result = s.run(cypher, emb=query_emb, limit=limit)
            return [dict(r) for r in result]

    def ask(self, question, brand):
        """Main pipeline with smart data reduction for the LLM."""
        cypher = self.generate_cypher(question, brand)
        logger.info(f"Complex Cypher: {cypher}")
        
        raw_data = []
        try:
            with self.driver.session() as s:
                records = s.run(cypher)
                raw_data = [dict(r) for r in records]
        except Exception as e:
            logger.warning(f"Cypher failed, trying vector fallback. Error: {e}")
            raw_data = self.vector_search(question)

        # Handle empty results
        if not raw_data:
            raw_data = self.vector_search(question)

        # Process data to fit in LLM context (truncate long bodies)
        processed_data = []
        for item in raw_data:
            cleaned = {}
            for k, v in item.items():
                if isinstance(v, str) and len(v) > 500:
                    cleaned[k] = v[:500] + "..." # Truncate long Reddit posts
                elif isinstance(v, list):
                    cleaned[k] = [str(x)[:200] for x in v[:3]] # Limit number/length of comments
                else:
                    cleaned[k] = v
            processed_data.append(cleaned)

        # Synthesis with a focus on 'Analysis'
        synthesis_prompt = f"""
        You are 'BrandIntelligenceBot'. Based on the Reddit graph data below, provide a detailed analysis.
        
        Brand: {brand}
        Question: {question}
        Data: {json.dumps(processed_data)}
        
        Requirements:
        1. If multiple posts are provided, identify the common theme.
        2. Specifically mention the 'nature' (sentiment) and 'reason' provided in the data.
        3. If users are complaining about hardware, list the specific parts or issues mentioned.
        4. Provide Reddit URLs if available in the data so the user can check them.
        """
        
        try:
            final = self.groq.chat.completions.create(
                model=Config.CHAT_MODEL,
                messages=[{"role": "system", "content": "You are a brand analyst that provides insights based on social media data. If URLs are in the data, always include them."},
                          {"role": "user", "content": synthesis_prompt}]
            )
            return final.choices[0].message.content
        except Exception as e:
            return f"I found the data but encountered an error summarizing it: {str(e)}"