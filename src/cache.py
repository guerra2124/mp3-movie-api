import json
import logging

import fakeredis

logger = logging.getLogger(__name__)


class MovieCache:
    def __init__(self):
        self.client = fakeredis.FakeRedis(decode_responses=True)

    def make_key(self, limit):
        return f"movies:limit:{limit}"

    def get(self, limit):
        """Return the cached response dictionary, or None."""
        key = self.make_key(limit)
        cached = self.client.get(key)
        if cached is None:
            logger.debug(f"Cache MISS: {key}")
            return None
        logger.debug(f"Cache HIT: {key}")
        return json.loads(cached)

    def set(self, limit, response):
        """Cache the response dictionary for 90 seconds."""
        self.client.set(self.make_key(limit), json.dumps(response), ex=90)

    def invalidate(self):
        """Remove all cached movie retrievals."""
        self.client.flushdb()
        logger.debug("Invalidated movie cache")


        