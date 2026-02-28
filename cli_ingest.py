import sys
import logging
import time
from core.config import Config
from core.database import Neo4jManager
from modules.scraper import RedditScraper
from modules.pipeline import BrandPipeline
from groq import Groq

# -------------------------------
# Logging - Unbuffered for real-time output
# -------------------------------
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)8s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)
# Force unbuffered output
sys.stdout.flush()
sys.stderr.flush()

# -------------------------------
# Main
# -------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python cli_ingest.py 'Brand Name'")
        return

    brand_name = sys.argv[1]
    logger.info("=" * 60)
    logger.info(f"STARTING DATA INGESTION FOR: {brand_name}")
    logger.info("=" * 60)

    # Step 1: Initialize Config
    logger.info("📋 Step 1/5: Initializing configuration...")
    try:
        Config.init_environment()
        logger.info(f"   ✓ Device: {Config.DEVICE}")
        logger.info(f"   ✓ Cores: {Config.CORES}")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"   ✗ Failed to initialize config: {e}")
        return

    # Step 2: Connect to Neo4j
    logger.info("📋 Step 2/5: Connecting to Neo4j database...")
    try:
        db = Neo4jManager()
        logger.info("   ✓ Connected to Neo4j")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"   ✗ Failed to connect to Neo4j: {e}")
        logger.error("   Make sure Neo4j is running: docker-compose up -d neo4j")
        return

    # Step 3: Initialize Groq client
    logger.info("📋 Step 3/5: Initializing Groq LLM client...")
    try:
        groq = Groq(api_key=Config.GROQ_API_KEY)
        logger.info("   ✓ Groq API initialized")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"   ✗ Failed to initialize Groq: {e}")
        logger.error("   Check your GROQ_API_KEY in .env")
        return

    # Step 4: Initialize pipeline and scraper
    logger.info("📋 Step 4/5: Setting up pipeline and scraper...")
    try:
        pipeline = BrandPipeline(db.driver, groq)
        scraper = RedditScraper()
        logger.info("   ✓ Pipeline and scraper ready")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"   ✗ Failed to setup pipeline: {e}")
        return

    # Initialize database
    logger.info("   → Initializing database constraints...")
    try:
        pipeline.init_db()
        logger.info("   ✓ Database initialized")
        sys.stdout.flush()
    except Exception as e:
        logger.warning(f"   ⚠ Database init warning: {e}")
        sys.stdout.flush()

    # Step 5: Data Ingestion
    logger.info("📋 Step 5/5: Data Ingestion Pipeline")
    logger.info("-" * 60)
    
    # 5a: Scrape Reddit
    logger.info(f"   [5a] Scraping Reddit for '{brand_name}'...")
    logger.info("       This may take 30-60 seconds (includes rate-limit handling)...")
    sys.stdout.flush()
    
    try:
        start_scrape = time.time()
        posts = scraper.fetch(brand_name, pages=3)
        scrape_time = time.time() - start_scrape
        
        if not posts:
            logger.error(f"   ✗ No posts found for '{brand_name}'. Exiting.")
            logger.info("   Tip: Check if the brand name is popular on Reddit")
            return
        
        logger.info(f"   ✓ Scraped {len(posts)} posts in {scrape_time:.1f}s")
        if posts:
            logger.info(f"      Sample post: {posts[0].get('title', 'N/A')[:60]}...")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"   ✗ Scraping failed: {e}")
        return

    # 5b: Analyze posts with LLM
    logger.info(f"   [5b] Analyzing {len(posts)} posts via Groq LLM...")
    logger.info("       (This takes ~2-5 minutes depending on batch size)...")
    sys.stdout.flush()
    
    try:
        start_analyze = time.time()
        meta_map = pipeline.analyze_posts(brand_name, posts)
        analyze_time = time.time() - start_analyze
        
        logger.info(f"   ✓ Analysis complete in {analyze_time:.1f}s")
        logger.info(f"      Processed metadata for posts")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"   ✗ Analysis failed: {e}")
        logger.error("      Check Neo4j connection and GROQ_API_KEY")
        return

    # 5c: Build graph
    logger.info(f"   [5c] Building sentiment graph in Neo4j...")
    sys.stdout.flush()
    
    try:
        start_graph = time.time()
        pipeline.build_graph(brand_name, posts, meta_map)
        graph_time = time.time() - start_graph
        
        logger.info(f"   ✓ Graph built in {graph_time:.1f}s")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"   ✗ Graph building failed: {e}")
        return

    # Success!
    total_time = time.time() - start_scrape
    logger.info("=" * 60)
    logger.info(f"✅ SUCCESS: Ingestion complete for '{brand_name}'")
    logger.info(f"   Total time: {total_time:.1f}s")
    logger.info(f"   Posts: {len(posts)}")
    logger.info("=" * 60)
    sys.stdout.flush()
# -------------------------------
# Entry Point
# -------------------------------
if __name__ == "__main__":
    main()