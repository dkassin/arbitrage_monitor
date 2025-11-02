import asyncio
import logging

logger = logging.getLogger(__name__)

async def retry_with_backoff(func, max_retries=3):
    delay = 2
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            
            if attempt < max_retries - 1:
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
                delay = min(delay * 2, 30)
            else:
                logger.error(f"All {max_retries} attempts failed")
    
    raise last_exception