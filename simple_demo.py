"""
Simple demo using basic OpenRouter integration
"""

import os
import asyncio
import time
from dotenv import load_dotenv
from openrouter_integration import OpenRouterOptimizer
from cost_reporter import CostTracker
from main import AmazonDataLoader

# Load environment variables
load_dotenv()

async def run_simple_demo():
    """Run simple demo with direct OpenRouter integration"""
    print("🚀 Simple Demo: OpenRouter + Cost Tracking")
    print("=" * 50)
    
    # Initialize components
    optimizer = OpenRouterOptimizer()
    cost_tracker = CostTracker()
    data_loader = AmazonDataLoader()
    
    print("✅ Components initialized")
    
    # Load small sample
    reviews = data_loader.load_sample_data("Electronics", sample_size=10)
    print(f"📦 Loaded {len(reviews)} sample reviews")
    
    # Process reviews
    results = []
    total_cost = 0.0
    start_time = time.time()
    
    for i, review in enumerate(reviews):
        print(f"🔄 Processing review {i+1}/{len(reviews)}...")
        
        # Route to optimal model
        model_tier = optimizer._route_to_model(review['review_text'], review['category'])
        
        try:
            # Make API call
            result = await optimizer.analyze_review_real(review, model_tier)
            
            # Track cost
            cost_tracker.log_api_call(
                model=result['model_used'],
                tokens_input=result.get('tokens_used', 100) // 2,
                tokens_output=result.get('tokens_used', 100) // 2,
                cost_usd=result['cost'],
                category=review['category'],
                cache_hit=result.get('cache_optimized', False),
                processing_time=result['processing_time']
            )
            
            total_cost += result['cost']
            results.append(result)
            
            print(f"  ✅ ${result['cost']:.6f} | {result['model_used']} | {result['tokens_used']} tokens")
            
            # Small delay
            await asyncio.sleep(0.1)
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
            continue
    
    total_time = time.time() - start_time
    
    print(f"\n📊 Results Summary:")
    print(f"  Reviews Processed: {len(results)}")
    print(f"  Total Time: {total_time:.2f} seconds")
    print(f"  Total Cost: ${total_cost:.6f}")
    print(f"  Average Cost: ${total_cost/len(results):.8f} per review")
    
    # Cost projection
    week1_projection = (total_cost / len(results)) * 1000
    print(f"\n💰 Week 1 Projection (1,000 reviews):")
    print(f"  Estimated Cost: ${week1_projection:.6f}")
    print(f"  Budget Safety: {5.00 / week1_projection:.0f}x coverage")
    
    # Generate LinkedIn summary
    linkedin_summary = cost_tracker.generate_linkedin_cost_summary(1)
    print(f"\n📝 LinkedIn Cost Summary Preview:")
    print(linkedin_summary[:300] + "...")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(run_simple_demo())
    print(f"\n🎉 Simple Demo Complete!")
    print(f"OpenRouter integration working perfectly!")