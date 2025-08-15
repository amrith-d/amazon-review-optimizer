#!/usr/bin/env python3
"""
Scalable Architecture for 1000+ Concurrent Users
Enterprise-grade review processing with Redis caching and async processing
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

# For production deployment (install separately)
try:
    import redis
    import aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("📦 For production: pip install redis aioredis")

@dataclass
class UserSession:
    """User session management"""
    user_id: str
    session_start: datetime
    requests_count: int = 0
    total_cost: float = 0.0
    cache_hits: int = 0
    last_request: datetime = None

@dataclass
class ProcessingResult:
    """Standardized processing result"""
    user_id: str
    request_id: str
    review_text: str
    category: str
    sentiment: str
    model_used: str
    cost: float
    processing_time: float
    cache_hit: bool
    complexity_score: float
    timestamp: datetime

class ScalableReviewProcessor:
    """Enterprise-grade scalable review processor"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.user_sessions = {}  # In-memory for demo, Redis for production
        self.global_cache = {}   # Semantic cache
        self.request_queue = asyncio.Queue(maxsize=10000)
        self.processing_workers = []
        
        # Configuration
        self.config = {
            'max_concurrent_users': 1000,
            'max_requests_per_user_per_minute': 100,
            'cache_ttl_seconds': 3600,  # 1 hour
            'worker_count': 50,
            'batch_size': 20,
            'rate_limit_window': 60  # seconds
        }
        
        # Initialize components
        self._setup_redis()
        self._setup_logging()
        
        print(f"✅ Scalable processor initialized for {self.config['max_concurrent_users']} users")
    
    def _setup_redis(self):
        """Setup Redis connection for production caching"""
        if REDIS_AVAILABLE:
            try:
                self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                self.redis_client.ping()
                print("✅ Redis connected for production caching")
            except Exception as e:
                print(f"⚠️ Redis unavailable, using in-memory cache: {e}")
                self.redis_client = None
        else:
            self.redis_client = None
    
    def _setup_logging(self):
        """Setup structured logging for monitoring"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('ScalableReviewProcessor')
    
    async def start_workers(self):
        """Start async processing workers"""
        self.processing_workers = [
            asyncio.create_task(self._processing_worker(f"worker-{i}"))
            for i in range(self.config['worker_count'])
        ]
        self.logger.info(f"Started {len(self.processing_workers)} processing workers")
    
    async def stop_workers(self):
        """Stop all processing workers"""
        for worker in self.processing_workers:
            worker.cancel()
        await asyncio.gather(*self.processing_workers, return_exceptions=True)
        self.logger.info("All workers stopped")
    
    async def _processing_worker(self, worker_id: str):
        """Async worker for processing review requests"""
        while True:
            try:
                # Get batch of requests from queue
                batch = []
                for _ in range(self.config['batch_size']):
                    try:
                        request = await asyncio.wait_for(
                            self.request_queue.get(), 
                            timeout=1.0
                        )
                        batch.append(request)
                    except asyncio.TimeoutError:
                        break
                
                if batch:
                    await self._process_batch(batch, worker_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1)
    
    async def _process_batch(self, batch: List[Dict], worker_id: str):
        """Process a batch of review requests"""
        from smart_router_v2 import SmartRouterV2
        router = SmartRouterV2()
        
        start_time = time.time()
        results = []
        
        for request_data in batch:
            try:
                result = await self._process_single_request(request_data, router)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Request processing error: {e}")
        
        batch_time = time.time() - start_time
        self.logger.info(f"Worker {worker_id}: processed {len(results)} requests in {batch_time:.2f}s")
        
        return results
    
    async def _process_single_request(self, request_data: Dict, router: SmartRouterV2) -> ProcessingResult:
        """Process single review request with caching"""
        start_time = time.time()
        
        user_id = request_data['user_id']
        request_id = request_data['request_id']
        review_text = request_data['review_text']
        category = request_data['category']
        
        # Check cache first
        cache_key = self._generate_cache_key(review_text, category)
        cached_result = await self._get_from_cache(cache_key)
        
        if cached_result:
            # Cache hit
            self._update_user_session(user_id, cost=0.0, cache_hit=True)
            
            return ProcessingResult(
                user_id=user_id,
                request_id=request_id,
                review_text=review_text,
                category=category,
                sentiment=cached_result['sentiment'],
                model_used='cache',
                cost=0.0,
                processing_time=time.time() - start_time,
                cache_hit=True,
                complexity_score=cached_result.get('complexity_score', 0.0),
                timestamp=datetime.now()
            )
        
        # Process with smart routing
        routing_result = router.route_review(review_text, category)
        
        # Simulate API call (replace with real implementation)
        await asyncio.sleep(0.1)  # API latency simulation
        
        # Calculate cost
        estimated_tokens = len(review_text.split()) * 1.3  # Token estimation
        cost = (estimated_tokens / 1_000_000) * routing_result['cost_per_million']
        
        # Simulate sentiment analysis result
        sentiment = 'Positive'  # Simplified for demo
        
        # Cache result
        cache_data = {
            'sentiment': sentiment,
            'complexity_score': routing_result['complexity_analysis']['final'],
            'model_used': routing_result['recommended_tier'],
            'timestamp': datetime.now().isoformat()
        }
        await self._set_cache(cache_key, cache_data)
        
        # Update user session
        self._update_user_session(user_id, cost=cost, cache_hit=False)
        
        return ProcessingResult(
            user_id=user_id,
            request_id=request_id,
            review_text=review_text,
            category=category,
            sentiment=sentiment,
            model_used=routing_result['recommended_tier'],
            cost=cost,
            processing_time=time.time() - start_time,
            cache_hit=False,
            complexity_score=routing_result['complexity_analysis']['final'],
            timestamp=datetime.now()
        )
    
    def _generate_cache_key(self, review_text: str, category: str) -> str:
        """Generate cache key for review"""
        content = f"{category}_{review_text.lower().strip()[:200]}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get result from cache (Redis or in-memory)"""
        if self.redis_client:
            try:
                cached = self.redis_client.get(f"review:{cache_key}")
                return json.loads(cached) if cached else None
            except Exception:
                pass
        
        return self.global_cache.get(cache_key)
    
    async def _set_cache(self, cache_key: str, data: Dict):
        """Set result in cache with TTL"""
        if self.redis_client:
            try:
                self.redis_client.setex(
                    f"review:{cache_key}",
                    self.config['cache_ttl_seconds'],
                    json.dumps(data)
                )
            except Exception:
                pass
        
        self.global_cache[cache_key] = data
    
    def _update_user_session(self, user_id: str, cost: float, cache_hit: bool):
        """Update user session tracking"""
        now = datetime.now()
        
        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = UserSession(
                user_id=user_id,
                session_start=now,
                last_request=now
            )
        
        session = self.user_sessions[user_id]
        session.requests_count += 1
        session.total_cost += cost
        session.last_request = now
        
        if cache_hit:
            session.cache_hits += 1
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limits"""
        if user_id not in self.user_sessions:
            return True
        
        session = self.user_sessions[user_id]
        window_start = datetime.now() - timedelta(seconds=self.config['rate_limit_window'])
        
        # Simple rate limiting (production would use sliding window)
        if session.last_request and session.last_request < window_start:
            session.requests_count = 0  # Reset counter
        
        return session.requests_count < self.config['max_requests_per_user_per_minute']
    
    async def submit_request(self, user_id: str, review_text: str, category: str) -> str:
        """Submit review processing request"""
        
        # Rate limiting check
        if not self._check_rate_limit(user_id):
            raise Exception(f"Rate limit exceeded for user {user_id}")
        
        # Queue size check
        if self.request_queue.qsize() >= self.request_queue.maxsize:
            raise Exception("Processing queue full, try again later")
        
        request_id = f"{user_id}_{int(time.time() * 1000)}"
        request_data = {
            'user_id': user_id,
            'request_id': request_id,
            'review_text': review_text,
            'category': category,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.request_queue.put(request_data)
        self.logger.info(f"Queued request {request_id} for user {user_id}")
        
        return request_id
    
    def get_system_stats(self) -> Dict:
        """Get system performance statistics"""
        total_users = len(self.user_sessions)
        total_requests = sum(s.requests_count for s in self.user_sessions.values())
        total_cost = sum(s.total_cost for s in self.user_sessions.values())
        total_cache_hits = sum(s.cache_hits for s in self.user_sessions.values())
        
        cache_hit_rate = (total_cache_hits / total_requests * 100) if total_requests > 0 else 0
        avg_cost_per_request = total_cost / total_requests if total_requests > 0 else 0
        
        return {
            'active_users': total_users,
            'total_requests': total_requests,
            'queue_size': self.request_queue.qsize(),
            'cache_hit_rate': round(cache_hit_rate, 2),
            'total_cost': round(total_cost, 6),
            'avg_cost_per_request': round(avg_cost_per_request, 6),
            'worker_count': len(self.processing_workers),
            'cache_size': len(self.global_cache)
        }

# Demo usage
async def demo_scalable_processing():
    """Demonstrate scalable processing with multiple users"""
    print("🚀 SCALABLE ARCHITECTURE DEMO")
    print("=" * 40)
    
    processor = ScalableReviewProcessor()
    await processor.start_workers()
    
    try:
        # Simulate multiple users submitting requests
        sample_reviews = [
            ("Great product, love it!", "Electronics"),
            ("This book changed my life", "Books"), 
            ("Garden hose works perfectly", "Home_and_Garden"),
            ("Complex technical analysis needed here with CPU benchmarks", "Electronics"),
            ("Mixed feelings about this book", "Books")
        ]
        
        # Submit requests from multiple users
        request_ids = []
        for user_id in range(10):  # 10 users
            for review_text, category in sample_reviews:
                request_id = await processor.submit_request(
                    f"user_{user_id:03d}",
                    review_text,
                    category
                )
                request_ids.append(request_id)
        
        print(f"✅ Submitted {len(request_ids)} requests from 10 users")
        
        # Wait for processing
        await asyncio.sleep(5)
        
        # Show statistics
        stats = processor.get_system_stats()
        print(f"\n📊 SYSTEM STATISTICS:")
        print(f"Active Users: {stats['active_users']}")
        print(f"Total Requests: {stats['total_requests']}") 
        print(f"Cache Hit Rate: {stats['cache_hit_rate']}%")
        print(f"Total Cost: ${stats['total_cost']:.6f}")
        print(f"Avg Cost/Request: ${stats['avg_cost_per_request']:.6f}")
        print(f"Queue Size: {stats['queue_size']}")
        print(f"Cache Size: {stats['cache_size']}")
        
    finally:
        await processor.stop_workers()

if __name__ == "__main__":
    asyncio.run(demo_scalable_processing())