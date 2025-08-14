"""
Quick progress check - test with 100 reviews to estimate timing
"""

import asyncio
import time
from week1_full_demo import Week1FullOptimizer

async def quick_progress_test():
    """Test with 100 reviews to estimate full demo timing"""
    print("🧪 Progress Test: 100 Reviews")
    print("=" * 40)
    
    optimizer = Week1FullOptimizer(max_budget=1.00)
    
    # Load 100 reviews
    categories = ["Electronics", "Books", "Home_and_Garden"]
    all_reviews = []
    
    for category in categories:
        reviews = optimizer.data_loader.load_sample_data(category, sample_size=34)
        all_reviews.extend(reviews)
    
    test_reviews = all_reviews[:100]
    print(f"📦 Loaded {len(test_reviews)} reviews for timing test")
    
    # Process with timing
    start_time = time.time()
    results = await optimizer.process_week1_batch(test_reviews, batch_size=10)
    test_time = time.time() - start_time
    
    # Calculate projections
    avg_time_per_review = test_time / len(results) if results else 0
    projected_time_1000 = avg_time_per_review * 1000
    
    total_cost = sum(r['cost'] for r in results) if results else 0
    projected_cost_1000 = (total_cost / len(results)) * 1000 if results else 0
    
    print(f"\n📊 Test Results:")
    print(f"  Reviews Processed: {len(results)}")
    print(f"  Test Time: {test_time:.1f} seconds")
    print(f"  Avg Time/Review: {avg_time_per_review:.2f}s")
    print(f"  Test Cost: ${total_cost:.6f}")
    
    print(f"\n🎯 1,000 Review Projections:")
    print(f"  Estimated Time: {projected_time_1000/60:.1f} minutes")
    print(f"  Estimated Cost: ${projected_cost_1000:.6f}")
    print(f"  Budget Safety: {5.00/projected_cost_1000:.0f}x" if projected_cost_1000 > 0 else "N/A")
    
    return results

if __name__ == "__main__":
    asyncio.run(quick_progress_test())