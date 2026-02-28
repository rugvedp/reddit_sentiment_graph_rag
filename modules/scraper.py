import requests
import time
import logging
import random
from urllib.parse import quote

logger = logging.getLogger(__name__)

class RedditScraper:
    BASE_URL = "https://www.reddit.com"
    
    # Using a modern, varied User-Agent is critical to avoid 429/403/503 errors
    USER_AGENTS = [
        # macOS / Chrome
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        # macOS / Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
        # iPhone
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        # Windows / Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]

    DEFAULT_HEADERS = {
        "Accept": "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

    def __init__(self):
        self.session = requests.Session()
        # Start with a random UA per session to reduce detection
        headers = dict(self.DEFAULT_HEADERS)
        headers["User-Agent"] = random.choice(self.USER_AGENTS)
        self.session.headers.update(headers)

    def _get_with_retry(self, url, retries=6):
        """Robust GET with handling for transient errors (502/503/429) and jittered backoff.

        Returns parsed JSON on success, otherwise None.
        """
        for i in range(retries):
            try:
                # rotate User-Agent occasionally to avoid easy fingerprinting
                if i > 0 and (i % 2) == 0:
                    self.session.headers["User-Agent"] = random.choice(self.USER_AGENTS)

                response = self.session.get(url, timeout=15)

                status = response.status_code
                if status == 200:
                    try:
                        return response.json()
                    except ValueError:
                        logger.debug("Received non-JSON response from Reddit")
                        return None

                # Handle rate limiting and temporary server errors with backoff
                if status in (429, 502, 503, 504):
                    base = 2 ** i
                    jitter = random.uniform(0.5, 1.5)
                    wait = min(60, base + jitter)
                    logger.warning(f"Transient error {status}. Backing off {wait:.1f}s (attempt {i+1}/{retries})...")
                    time.sleep(wait)
                    continue

                if status == 403:
                    logger.error("Access Forbidden (403). Reddit may have blocked this IP/User-Agent.")
                    break

                # For other statuses, log and don't retry aggressively
                logger.error(f"Unexpected status {status} from {url}")
                break

            except requests.RequestException as e:
                # Network or TLS issue; backoff and retry
                jitter = random.uniform(0.5, 2.0)
                wait = min(30, (i + 1) * 2 + jitter)
                logger.warning(f"Request exception: {e}. Retrying in {wait:.1f}s (attempt {i+1}/{retries})")
                time.sleep(wait)

        return None

    def fetch(self, query, pages=3, include_comments=True, comment_limit=15):
        posts = []
        after = None
        
        # URL encode the query properly
        encoded_query = quote(query)

        for page in range(pages):
            search_url = (
                f"{self.BASE_URL}/search.json"
                f"?q={encoded_query}"
                f"&sort=new&limit=100&raw_json=1"
            )
            if after:
                search_url += f"&after={after}"

            logger.info(f"Fetching page {page+1} for query: {query}")
            data = self._get_with_retry(search_url)
            
            if not data or "data" not in data:
                logger.error("Failed to retrieve search results.")
                break

            children = data.get("data", {}).get("children", [])
            for child in children:
                item = child.get("data", {})
                if not item: continue

                post_id = item.get("id")
                permalink = item.get("permalink")

                post_data = {
                    "id": post_id,
                    "name": item.get("name"),
                    "title": item.get("title"),
                    "selftext": item.get("selftext", ""),
                    "full_text": f"{item.get('title', '')}\n\n{item.get('selftext', '')}",
                    "score": item.get("score", 0),
                    "upvote_ratio": item.get("upvote_ratio", 0),
                    "num_comments": item.get("num_comments", 0),
                    "author": item.get("author"),
                    "subreddit": item.get("subreddit"),
                    "created_utc": item.get("created_utc"),
                    "permalink": f"{self.BASE_URL}{permalink}",
                    "top_comments": []
                }

                if include_comments and permalink:
                    # Small random jitter to prevent bot detection
                    time.sleep(random.uniform(0.5, 1.2)) 
                    post_data["top_comments"] = self.fetch_comments(permalink, limit=comment_limit)

                posts.append(post_data)

            after = data.get("data", {}).get("after")
            if not after:
                break
            
            # Delay between pages
            time.sleep(1.5)

        return posts

    def fetch_comments(self, permalink, limit=15):
        """Fetches and cleans top-level comments for a given post."""
        comments_list = []
        # Construct the .json URL
        url = f"{self.BASE_URL}{permalink}.json?limit={limit}&sort=top&raw_json=1"
        
        data = self._get_with_retry(url)
        
        # Reddit post JSON is a list: [PostData, CommentData]
        if not data or not isinstance(data, list) or len(data) < 2:
            return []

        raw_comments = data[1].get("data", {}).get("children", [])

        for c in raw_comments:
            # kind 't1' is a Comment. kind 'more' is a "load more" button.
            if c.get("kind") != "t1":
                continue

            c_data = c.get("data", {})
            
            # Skip deleted comments or empty ones
            body = c_data.get("body")
            if not body or body in ["[deleted]", "[removed]"]:
                continue

            comments_list.append({
                "id": c_data.get("id"),
                "author": c_data.get("author"),
                "body": body,
                "score": c_data.get("score", 0),
                "created_utc": c_data.get("created_utc"),
                "is_submitter": c_data.get("is_submitter", False),
                "controversiality": c_data.get("controversiality", 0),
            })

            if len(comments_list) >= limit:
                break

        return comments_list

    @staticmethod
    def fetch_static(query, pages=3, include_comments=True):
        """Standard entry point to keep compatibility with your runner."""
        scraper = RedditScraper()
        return scraper.fetch(query, pages, include_comments)