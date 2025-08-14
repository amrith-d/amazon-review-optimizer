"""
Small demo with 50 reviews to test full optimization pipeline
"""

import asyncio
import time
from main_with_openrouter import IntegratedOptimizer

async def run_small_demo():
    """Run small demo with 50 reviews"""
    print("🚀 Small Demo: 50 Reviews with Full Optimization")
    print("=" * 60)
    
    # Initialize with small budget for safety
    optimizer = IntegratedOptimizer(use_real_apis=True, max_budget=1.00)
    
    # Load small sample
    print("📦 Loading 50 reviews for demo...")
    categories = ["Electronics", "Books", "Home_and_Garden"]
    all_reviews = []
    
    for category in categories:
        reviews = optimizer.data_loader.load_sample_data(category, sample_size=17)
        all_reviews.extend(reviews)
        print(f"✅ Loaded {len(reviews)} {category} reviews")
    
    # Limit to exactly 50
    demo_reviews = all_reviews[:50]
    print(f"📊 Processing {len(demo_reviews)} reviews...")
    
    # Process with full optimization
    start_time = time.time()
    results = await optimizer.process_batch(demo_reviews, batch_size=5)
    total_time = time.time() - start_time
    
    print(f"✅ Processing completed in {total_time:.2f} seconds")
    
    # Performance metrics
    metrics = optimizer.get_performance_metrics(results)
    print(f"\n📈 Demo Results:")
    print(f"  Reviews Processed: {metrics['total_reviews']}")
    print(f"  Cache Hit Rate: {metrics['cache_hit_rate']}%")
    print(f"  Total Cost: ${metrics['total_cost']:.6f}")
    print(f"  Cost per Review: ${metrics['avg_cost_per_review']:.8f}")
    
    # Show model distribution
    print(f"\n🤖 Model Distribution:")
    for model, count in metrics['model_distribution'].items():
        percentage = (count / metrics['total_reviews']) * 100
        print(f"  {model}: {count} reviews ({percentage:.1f}%)")
    
    # KV Cache stats if available
    if optimizer.use_real_apis and optimizer.kv_optimizer:
        kv_stats = optimizer.kv_optimizer.get_optimization_stats()
        print(f"\n🚀 KV Cache Optimization:")
        print(f"  Total API Calls: {kv_stats['total_calls']}")
        print(f"  Context Cache Hits: {kv_stats['cache_hits']}")
        print(f"  KV Hit Rate: {kv_stats['cache_hit_rate']}%")
        print(f"  Token Savings: {kv_stats['total_token_savings']} tokens")
    
    # Cost projection for Week 1
    cost_per_review = metrics['avg_cost_per_review']
    week1_cost = cost_per_review * 1000
    print(f"\n💰 Week 1 Cost Projection:")
    print(f"  Estimated cost for 1,000 reviews: ${week1_cost:.6f}")
    print(f"  Well within budget: {'✅' if week1_cost < 0.10 else '⚠️'}")
    
    return results, metrics

if __name__ == "__main__":
    results, metrics = asyncio.run(run_small_demo())
    print(f"\n🎉 Small Demo Complete!")
    print(f"Ready to run full Week 1 demo with 1,000 reviews!")
    print(f"Expected cost: ~${metrics['avg_cost_per_review'] * 1000:.6f}")