"""
Amazon Product Review Analysis Optimizer - OpenRouter Integration
Real API implementation with cost tracking and LinkedIn reporting
"""

import os
import time
import asyncio
from typing import List, Dict
from dotenv import load_dotenv

from openrouter_integration import OpenRouterOptimizer, RealAPIMode
from cost_reporter import CostTracker
from kv_cache_optimizer import KVCacheOptimizer, EnhancedOpenRouterOptimizer
from main import AmazonDataLoader  # Use existing data loader

# Load environment variables
load_dotenv()

class IntegratedOptimizer:
    """Integrated system with real APIs and cost tracking"""
    
    def __init__(self, use_real_apis: bool = True, max_budget: float = 5.00):
        self.use_real_apis = use_real_apis
        self.data_loader = AmazonDataLoader()
        self.cost_tracker = CostTracker()
        
        if use_real_apis:
            # Set budget limit
            os.environ['MAX_BUDGET'] = str(max_budget)
            base_optimizer = OpenRouterOptimizer()
            self.api_optimizer = EnhancedOpenRouterOptimizer(base_optimizer)
            self.kv_optimizer = self.api_optimizer.kv_optimizer
            print(f"✅ OpenRouter + KV Cache optimization enabled (Budget: ${max_budget})")
        else:
            self.api_optimizer = None
            self.kv_optimizer = None
            print("🎭 Simulation mode enabled")
    
    async def analyze_single_review(self, review_data: Dict) -> Dict:
        """Analyze single review with cost tracking"""
        start_time = time.time()
        
        if self.use_real_apis and self.api_optimizer:
            # Real API call
            model_tier = self.api_optimizer.base_optimizer._route_to_model(
                review_data['review_text'], 
                review_data['category']
            )
            
            try:
                result = await self.api_optimizer.base_optimizer.analyze_review_real(review_data, model_tier)
                
                # Log cost tracking
                self.cost_tracker.log_api_call(
                    model=result['model_used'],
                    tokens_input=result.get('tokens_used', 100) // 2,  # Estimate input tokens
                    tokens_output=result.get('tokens_used', 100) // 2,  # Estimate output tokens
                    cost_usd=result['cost'],
                    category=review_data['category'],
                    cache_hit=result.get('cache_optimized', False),
                    processing_time=result['processing_time']
                )
                
                return {
                    'review_id': review_data.get('review_id', 'unknown'),
                    'category': review_data['category'],
                    'sentiment': self._extract_sentiment_from_api_response(result['content']),
                    'model_used': result['model_used'],
                    'cost': result['cost'],
                    'processing_time': result['processing_time'],
                    'cache_hit': result.get('cache_optimized', False),
                    'real_api': True
                }
                
            except Exception as e:
                print(f"⚠️ API call failed: {e}")
                return None
        else:
            # Fallback to simulation
            from main import AmazonReviewAnalyzer
            analyzer = AmazonReviewAnalyzer()
            result = await analyzer.analyze_review(review_data)
            
            return {
                'review_id': review_data.get('review_id', 'unknown'),
                'category': result.product_category,
                'sentiment': result.sentiment,
                'model_used': result.model_used,
                'cost': result.cost,
                'processing_time': result.processing_time,
                'cache_hit': result.cache_hit,
                'real_api': False
            }
    
    def _extract_sentiment_from_api_response(self, content: str) -> str:
        """Extract sentiment from API response"""
        # Simple extraction logic - could be improved with JSON parsing
        content_lower = content.lower()
        if 'positive' in content_lower:
            return 'Positive'
        elif 'negative' in content_lower:
            return 'Negative'
        else:
            return 'Neutral'
    
    async def process_batch(self, reviews: List[Dict], batch_size: int = 10) -> List[Dict]:
        """Process reviews in batches with progress tracking"""
        results = []
        total_batches = len(reviews) // batch_size + (1 if len(reviews) % batch_size else 0)
        
        print(f"🔄 Processing {len(reviews)} reviews in {total_batches} batches...")
        
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            print(f"📦 Batch {batch_num}/{total_batches}: Processing {len(batch)} reviews...")
            
            # Process batch
            batch_results = []
            for review in batch:
                result = await self.analyze_single_review(review)
                if result:
                    batch_results.append(result)
                
                # Small delay to avoid rate limits
                if self.use_real_apis:
                    await asyncio.sleep(0.1)
            
            results.extend(batch_results)
            
            # Progress update
            total_processed = len(results)
            if self.use_real_apis and self.api_optimizer:
                cost_report = self.api_optimizer.base_optimizer.get_cost_report()
                print(f"✅ Batch {batch_num} complete: {len(batch_results)} processed (Total: {total_processed}, Spent: ${cost_report['total_spent']:.6f})")
            else:
                print(f"✅ Batch {batch_num} complete: {len(batch_results)} processed (Total: {total_processed})")
        
        return results
    
    def generate_week_summary(self, week_number: int = 1) -> str:
        """Generate weekly summary for LinkedIn"""
        if self.use_real_apis:
            return self.cost_tracker.generate_linkedin_cost_summary(week_number)
        else:
            return "🎭 Simulation mode - no real costs incurred"
    
    def get_performance_metrics(self, results: List[Dict]) -> Dict:
        """Calculate performance metrics"""
        if not results:
            return {}
        
        total_reviews = len(results)
        api_calls = len([r for r in results if not r['cache_hit']])
        cache_hits = len([r for r in results if r['cache_hit']])
        cache_hit_rate = (cache_hits / total_reviews * 100) if total_reviews > 0 else 0
        
        total_cost = sum(r['cost'] for r in results)
        avg_cost_per_review = total_cost / total_reviews if total_reviews > 0 else 0
        
        # Model distribution
        model_counts = {}
        for result in results:
            model = result['model_used']
            model_counts[model] = model_counts.get(model, 0) + 1
        
        return {
            'total_reviews': total_reviews,
            'api_calls': api_calls,
            'cache_hit_rate': round(cache_hit_rate, 1),
            'total_cost': round(total_cost, 6),
            'avg_cost_per_review': round(avg_cost_per_review, 8),
            'model_distribution': model_counts,
            'using_real_apis': self.use_real_apis
        }


async def run_week1_demo(use_real_apis: bool = True, budget: float = 5.00):
    """Run Week 1 demonstration"""
    print("🚀 Amazon Review Optimizer - Week 1 Demo")
    print(f"Mode: {'Real OpenRouter APIs' if use_real_apis else 'Simulation'}")
    print("=" * 60)
    
    # Initialize system
    optimizer = IntegratedOptimizer(use_real_apis=use_real_apis, max_budget=budget)
    
    # Load sample data
    print("📦 Loading Amazon review data...")
    categories = ["Electronics", "Books", "Home_and_Garden"]
    all_reviews = []
    
    for category in categories:
        reviews = optimizer.data_loader.load_sample_data(category, sample_size=334)
        all_reviews.extend(reviews)
        print(f"✅ Loaded {len(reviews)} {category} reviews")
    
    # Limit to exactly 1000 for consistency
    sample_reviews = all_reviews[:1000]
    print(f"📊 Processing {len(sample_reviews)} reviews for Week 1...")
    
    # Process reviews
    start_time = time.time()
    results = await optimizer.process_batch(sample_reviews, batch_size=20)
    total_time = time.time() - start_time
    
    print(f"✅ Processing completed in {total_time:.2f} seconds")
    
    # Performance metrics
    metrics = optimizer.get_performance_metrics(results)
    print(f"\n📈 Week 1 Results:")
    print(f"  Reviews Processed: {metrics['total_reviews']}")
    print(f"  Cache Hit Rate: {metrics['cache_hit_rate']}%")
    print(f"  Total Cost: ${metrics['total_cost']:.6f}")
    print(f"  Cost per Review: ${metrics['avg_cost_per_review']:.8f}")
    print(f"  Real APIs Used: {metrics['using_real_apis']}")
    
    # LinkedIn summary
    linkedin_summary = optimizer.generate_week_summary(1)
    print(f"\n📝 LinkedIn Cost Summary:")
    print(linkedin_summary)
    
    # Export detailed report
    if use_real_apis:
        report_file = optimizer.cost_tracker.export_detailed_report("week1_cost_report.json")
        print(f"\n📄 Detailed cost report saved: {report_file}")
    
    return results, metrics


if __name__ == "__main__":
    # Configuration
    USE_REAL_APIS = os.getenv('USE_REAL_APIS', 'true').lower() == 'true'
    BUDGET_LIMIT = float(os.getenv('BUDGET_LIMIT', '5.00'))
    
    print("🎯 Configuration:")
    print(f"USE_REAL_APIS: {USE_REAL_APIS}")
    print(f"BUDGET_LIMIT: ${BUDGET_LIMIT}")
    print(f"OPENROUTER_API_KEY: {'✅ Set' if os.getenv('OPENROUTER_API_KEY') else '❌ Missing'}")
    print()
    
    # Run demo
    if USE_REAL_APIS and not os.getenv('OPENROUTER_API_KEY'):
        print("❌ Error: OPENROUTER_API_KEY not found in environment")
        print("Set your API key: export OPENROUTER_API_KEY=your_key_here")
    else:
        results, metrics = asyncio.run(run_week1_demo(USE_REAL_APIS, BUDGET_LIMIT))
        print(f"\n🎉 Week 1 Demo Complete!")
        print(f"Ready for LinkedIn series launch with {'authentic' if USE_REAL_APIS else 'simulated'} results!")