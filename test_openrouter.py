"""
Quick test of OpenRouter integration with small sample
"""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_openrouter_basic():
    """Test basic OpenRouter functionality with minimal cost"""
    try:
        from openrouter_integration import OpenRouterOptimizer
        
        print("🧪 Testing OpenRouter Integration...")
        print(f"API Key: {'✅ Set' if os.getenv('OPENROUTER_API_KEY') else '❌ Missing'}")
        print(f"Budget: ${os.getenv('MAX_BUDGET', '5.00')}")
        
        # Create optimizer
        optimizer = OpenRouterOptimizer()
        print("✅ OpenRouter optimizer created successfully")
        
        # Test single review
        test_review = {
            'review_text': "Great product! Works perfectly and fast delivery.",
            'category': 'Electronics',
            'rating': 5,
            'review_id': 'test_001'
        }
        
        print("\n🔄 Testing single review analysis...")
        result = await optimizer.analyze_review_real(test_review, 'ultra_lightweight')
        
        print("✅ API call successful!")
        print(f"Model: {result['model_used']}")
        print(f"Cost: ${result['cost']:.6f}")
        print(f"Tokens: {result['tokens_used']}")
        print(f"Response preview: {result['content'][:100]}...")
        
        # Get cost report
        cost_report = optimizer.get_cost_report()
        print(f"\n💰 Cost Report:")
        print(f"Total spent: ${cost_report['total_spent']:.6f}")
        print(f"Remaining budget: ${cost_report['remaining_budget']:.6f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

async def test_kv_cache_optimization():
    """Test KV cache optimization with small batch"""
    try:
        from kv_cache_optimizer import KVCacheOptimizer
        from openrouter_integration import OpenRouterOptimizer
        
        print("\n🚀 Testing KV Cache Optimization...")
        
        # Create optimizers
        base_optimizer = OpenRouterOptimizer()
        kv_optimizer = KVCacheOptimizer(base_optimizer.client)
        
        # Test reviews (same category for context reuse)
        test_reviews = [
            {'review_text': 'Good book, enjoyed reading it', 'category': 'Books', 'review_id': '1'},
            {'review_text': 'Another excellent book in the series', 'category': 'Books', 'review_id': '2'},
            {'review_text': 'Great story and characters', 'category': 'Books', 'review_id': '3'},
        ]
        
        print(f"Processing {len(test_reviews)} reviews for KV cache testing...")
        
        # Process with KV optimization
        results = await kv_optimizer.batch_analyze_with_kv_optimization(
            test_reviews, 
            'openai/gpt-4o-mini'
        )
        
        print("✅ KV Cache optimization test successful!")
        
        # Show results
        for result in results:
            print(f"Review {result['review_id']}: Context reused = {result['context_reused']}")
        
        # Get optimization stats
        stats = kv_optimizer.get_optimization_stats()
        print(f"\n📊 KV Cache Stats:")
        print(f"Total calls: {stats['total_calls']}")
        print(f"Cache hits: {stats['cache_hits']}")
        print(f"Hit rate: {stats['cache_hit_rate']}%")
        print(f"Token savings: {stats['total_token_savings']}")
        
        return True
        
    except Exception as e:
        print(f"❌ KV Cache test failed: {e}")
        return False

async def main():
    """Run all tests"""
    print("🎯 OpenRouter Integration Test Suite")
    print("=" * 50)
    
    # Test 1: Basic OpenRouter
    test1_success = await test_openrouter_basic()
    
    if test1_success:
        # Test 2: KV Cache Optimization
        test2_success = await test_kv_cache_optimization()
        
        if test1_success and test2_success:
            print("\n🎉 All tests passed! Ready for Week 1 demo.")
            print("\nNext step: Run full Week 1 demo with:")
            print("python3 main_with_openrouter.py")
        else:
            print("\n⚠️ Some tests failed. Check configuration.")
    else:
        print("\n❌ Basic test failed. Check API key and configuration.")

if __name__ == "__main__":
    asyncio.run(main())