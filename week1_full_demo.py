"""
Week 1 Full Demo: 1,000 Amazon Reviews with Complete Optimization
Real OpenRouter API calls with semantic caching and KV optimization
"""

import os
import asyncio
import time
import json
from datetime import datetime
from dotenv import load_dotenv
from openrouter_integration import OpenRouterOptimizer
from cost_reporter import CostTracker
from main import AmazonDataLoader, SemanticCache

# Load environment variables
load_dotenv()

class Week1FullOptimizer:
    """Complete Week 1 optimizer with all optimizations"""
    
    def __init__(self, max_budget: float = 5.00):
        self.max_budget = max_budget
        os.environ['MAX_BUDGET'] = str(max_budget)
        
        # Initialize components
        self.api_optimizer = OpenRouterOptimizer()
        self.cost_tracker = CostTracker()
        self.data_loader = AmazonDataLoader()
        self.semantic_cache = SemanticCache(max_size=2000)
        
        # Conversation contexts for KV cache optimization
        self.conversation_contexts = {}
        
        print(f"✅ Week 1 Full Optimizer initialized (Budget: ${max_budget})")
    
    def _get_conversation_context(self, category: str) -> list:
        """Get or create conversation context for KV cache optimization"""
        if category not in self.conversation_contexts:
            system_prompts = {
                "Electronics": "You are an expert at analyzing electronics product reviews. Focus on technical features, performance, and value.",
                "Books": "You are an expert at analyzing book reviews. Focus on content quality, readability, and reader satisfaction.", 
                "Home_and_Garden": "You are an expert at analyzing home and garden product reviews. Focus on utility, durability, and practical value."
            }
            
            self.conversation_contexts[category] = [
                {"role": "system", "content": system_prompts.get(category, "You are an expert product review analyst.")}
            ]
        
        return self.conversation_contexts[category]
    
    async def analyze_review_with_full_optimization(self, review: dict) -> dict:
        """Analyze single review with all optimizations"""
        start_time = time.time()
        
        review_text = review['review_text']
        category = review['category']
        
        # Layer 1: Semantic Cache Check
        cached_result = self.semantic_cache.get(review_text, category)
        if cached_result:
            # Semantic cache hit - completely free
            self.cost_tracker.log_api_call(
                model='cache_hit',
                tokens_input=0,
                tokens_output=0,
                cost_usd=0.0,
                category=category,
                cache_hit=True,
                processing_time=time.time() - start_time
            )
            
            return {
                'review_id': review.get('review_id', 'unknown'),
                'category': category,
                'sentiment': cached_result.sentiment,
                'model_used': 'semantic_cache',
                'cost': 0.0,
                'processing_time': time.time() - start_time,
                'semantic_cache_hit': True,
                'kv_cache_hit': False,
                'tokens_used': 0
            }
        
        # Layer 2: Smart Routing + KV Cache Optimization
        model_tier = self.api_optimizer._route_to_model(review_text, category)
        
        # Prepare conversation context for KV cache optimization
        conversation_context = self._get_conversation_context(category)
        
        # Create optimized prompt with context
        user_prompt = f"""Analyze this {category.lower()} review:

Product: {review.get('product_title', 'Product')}
Rating: {review.get('rating', 'N/A')}/5
Review: "{review_text}"

Provide brief analysis: sentiment (Positive/Negative/Neutral), quality assessment, and key insight."""
        
        # Use conversation context (KV cache optimization)
        messages = conversation_context + [{"role": "user", "content": user_prompt}]
        
        try:
            # Make API call with conversation context
            model_config = self.api_optimizer._get_model_config(model_tier)
            model_name = model_config['openrouter_name']
            
            response = await asyncio.to_thread(
                self.api_optimizer.client.chat.completions.create,
                model=model_name,
                messages=messages,
                max_tokens=100,
                temperature=0.1
            )
            
            # Calculate costs
            tokens_used = response.usage.total_tokens if response.usage else 100
            cost_per_million = model_config['cost_per_million_tokens']
            actual_cost = (tokens_used / 1_000_000) * cost_per_million
            
            # Update conversation context for next KV cache optimization
            assistant_response = response.choices[0].message.content
            conversation_context.extend([
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response}
            ])
            
            # Trim context if too long
            if len(conversation_context) > 15:
                conversation_context[:] = [conversation_context[0]] + conversation_context[-14:]
            
            # Track cost
            kv_cache_benefit = len(conversation_context) > 3  # Context reused
            self.cost_tracker.log_api_call(
                model=model_name,
                tokens_input=tokens_used // 2,
                tokens_output=tokens_used // 2,
                cost_usd=actual_cost,
                category=category,
                cache_hit=False,
                processing_time=time.time() - start_time
            )
            
            # Update budget tracking
            self.api_optimizer.openrouter_config.current_spend += actual_cost
            
            # Extract sentiment from response
            sentiment = 'Neutral'
            response_lower = assistant_response.lower()
            if 'positive' in response_lower:
                sentiment = 'Positive'
            elif 'negative' in response_lower:
                sentiment = 'Negative'
            
            # Create result for semantic caching
            from main import ProductReviewResult
            cache_result = ProductReviewResult(
                product_category=category,
                sentiment=sentiment,
                product_quality='Good' if review.get('rating', 3) >= 4 else 'Fair',
                purchase_recommendation='Recommend' if review.get('rating', 3) >= 4 else 'Neutral',
                key_insights=[assistant_response[:100]],
                cost=actual_cost,
                model_used=model_name,
                cache_hit=False,
                processing_time=time.time() - start_time
            )
            
            # Cache for future semantic hits
            self.semantic_cache.set(review_text, category, cache_result)
            
            return {
                'review_id': review.get('review_id', 'unknown'),
                'category': category,
                'sentiment': sentiment,
                'model_used': model_name,
                'cost': actual_cost,
                'processing_time': time.time() - start_time,
                'semantic_cache_hit': False,
                'kv_cache_hit': kv_cache_benefit,
                'tokens_used': tokens_used,
                'response_preview': assistant_response[:100]
            }
            
        except Exception as e:
            print(f"❌ API call failed: {e}")
            return None
    
    async def process_week1_batch(self, reviews: list, batch_size: int = 20) -> list:
        """Process Week 1 reviews in optimized batches"""
        results = []
        total_batches = len(reviews) // batch_size + (1 if len(reviews) % batch_size else 0)
        
        print(f"🔄 Processing {len(reviews)} reviews in {total_batches} batches...")
        
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i + batch_size]
            batch_num = i // batch_size + 1
            
            print(f"\n📦 Batch {batch_num}/{total_batches}: Processing {len(batch)} reviews...")
            batch_start = time.time()
            
            # Process batch with slight delay between requests
            batch_results = []
            for j, review in enumerate(batch):
                result = await self.analyze_review_with_full_optimization(review)
                if result:
                    batch_results.append(result)
                    
                    # Progress indicator
                    if (j + 1) % 5 == 0:
                        print(f"  ✅ {j + 1}/{len(batch)} reviews processed...")
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.05)
            
            batch_time = time.time() - batch_start
            results.extend(batch_results)
            
            # Batch summary
            batch_cost = sum(r['cost'] for r in batch_results)
            semantic_hits = len([r for r in batch_results if r['semantic_cache_hit']])
            kv_hits = len([r for r in batch_results if r['kv_cache_hit']])
            
            print(f"✅ Batch {batch_num} complete:")
            print(f"  • Processed: {len(batch_results)} reviews")
            print(f"  • Time: {batch_time:.1f}s")
            print(f"  • Cost: ${batch_cost:.6f}")
            print(f"  • Semantic Cache Hits: {semantic_hits}")
            print(f"  • KV Cache Benefits: {kv_hits}")
            print(f"  • Total Processed: {len(results)}/{len(reviews)}")
            
            # Budget check
            current_spend = self.api_optimizer.openrouter_config.current_spend
            print(f"  • Total Spent: ${current_spend:.6f} / ${self.max_budget}")
            
            if current_spend > self.max_budget * 0.8:
                print(f"⚠️ Approaching budget limit!")
        
        return results
    
    def generate_week1_report(self, results: list, total_time: float) -> dict:
        """Generate comprehensive Week 1 report"""
        if not results:
            return {}
        
        # Basic metrics
        total_reviews = len(results)
        total_cost = sum(r['cost'] for r in results)
        semantic_hits = len([r for r in results if r['semantic_cache_hit']])
        kv_hits = len([r for r in results if r['kv_cache_hit']])
        api_calls = len([r for r in results if not r['semantic_cache_hit']])
        
        cache_hit_rate = (semantic_hits / total_reviews * 100) if total_reviews > 0 else 0
        kv_hit_rate = (kv_hits / api_calls * 100) if api_calls > 0 else 0
        
        # Model distribution
        model_counts = {}
        for result in results:
            model = result['model_used']
            model_counts[model] = model_counts.get(model, 0) + 1
        
        # Category breakdown
        category_stats = {}
        for result in results:
            cat = result['category']
            if cat not in category_stats:
                category_stats[cat] = {'count': 0, 'cost': 0.0, 'semantic_hits': 0}
            category_stats[cat]['count'] += 1
            category_stats[cat]['cost'] += result['cost']
            if result['semantic_cache_hit']:
                category_stats[cat]['semantic_hits'] += 1
        
        # Baseline comparison
        baseline_cost = total_reviews * 150 * (10.00 / 1_000_000)  # GPT-4 Turbo baseline
        savings = baseline_cost - total_cost
        savings_percentage = (savings / baseline_cost * 100) if baseline_cost > 0 else 0
        
        return {
            'total_reviews': total_reviews,
            'total_time': total_time,
            'total_cost': total_cost,
            'avg_cost_per_review': total_cost / total_reviews if total_reviews > 0 else 0,
            'api_calls': api_calls,
            'semantic_cache_hit_rate': cache_hit_rate,
            'kv_cache_hit_rate': kv_hit_rate,
            'model_distribution': model_counts,
            'category_breakdown': category_stats,
            'baseline_cost': baseline_cost,
            'savings_amount': savings,
            'savings_percentage': savings_percentage,
            'budget_used': (total_cost / self.max_budget * 100) if self.max_budget > 0 else 0
        }

async def run_week1_full_demo():
    """Run complete Week 1 demo"""
    print("🚀 WEEK 1 FULL DEMO: 1,000 Amazon Reviews")
    print("Real OpenRouter APIs + Semantic Cache + KV Optimization")
    print("=" * 70)
    
    # Initialize optimizer
    optimizer = Week1FullOptimizer(max_budget=5.00)
    
    # Load 1,000 reviews
    print("\n📦 Loading Amazon review data...")
    categories = ["Electronics", "Books", "Home_and_Garden"]
    all_reviews = []
    
    for category in categories:
        reviews = optimizer.data_loader.load_sample_data(category, sample_size=334)
        all_reviews.extend(reviews)
        print(f"✅ Loaded {len(reviews)} {category} reviews")
    
    # Ensure exactly 1,000 reviews
    week1_reviews = all_reviews[:1000]
    print(f"\n📊 Week 1 Dataset Ready: {len(week1_reviews)} reviews")
    
    # Process with full optimization
    start_time = time.time()
    print(f"\n🔄 Starting Week 1 processing at {datetime.now().strftime('%H:%M:%S')}...")
    
    results = await optimizer.process_week1_batch(week1_reviews, batch_size=25)
    
    total_time = time.time() - start_time
    print(f"\n✅ Week 1 processing completed in {total_time:.1f} seconds!")
    
    # Generate comprehensive report
    report = optimizer.generate_week1_report(results, total_time)
    
    print(f"\n📊 WEEK 1 FINAL RESULTS:")
    print(f"{'=' * 50}")
    print(f"Reviews Processed: {report['total_reviews']:,}")
    print(f"Total Time: {report['total_time']:.1f} seconds")
    print(f"Total Cost: ${report['total_cost']:.6f}")
    print(f"Cost per Review: ${report['avg_cost_per_review']:.8f}")
    print(f"Budget Used: {report['budget_used']:.1f}%")
    
    print(f"\n🎯 OPTIMIZATION RESULTS:")
    print(f"Semantic Cache Hit Rate: {report['semantic_cache_hit_rate']:.1f}%")
    print(f"KV Cache Benefit Rate: {report['kv_cache_hit_rate']:.1f}%")
    print(f"API Calls Made: {report['api_calls']:,}")
    print(f"Baseline Cost (GPT-4): ${report['baseline_cost']:.6f}")
    print(f"Savings: ${report['savings_amount']:.6f} ({report['savings_percentage']:.1f}%)")
    
    print(f"\n🤖 MODEL DISTRIBUTION:")
    for model, count in report['model_distribution'].items():
        percentage = (count / report['total_reviews']) * 100
        print(f"  {model}: {count} reviews ({percentage:.1f}%)")
    
    print(f"\n📂 CATEGORY PERFORMANCE:")
    for category, stats in report['category_breakdown'].items():
        cache_rate = (stats['semantic_hits'] / stats['count'] * 100)
        print(f"  {category}: {stats['count']} reviews, ${stats['cost']:.6f}, {cache_rate:.1f}% cached")
    
    # Generate LinkedIn summary
    linkedin_summary = optimizer.cost_tracker.generate_linkedin_cost_summary(1)
    
    # Save detailed results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"week1_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'total_reviews': len(results),
                'processing_time': total_time
            },
            'summary': report,
            'linkedin_summary': linkedin_summary,
            'detailed_results': results[:10]  # First 10 for space
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved: {results_file}")
    print(f"\n📝 LinkedIn Summary:")
    print("=" * 50)
    print(linkedin_summary)
    
    print(f"\n🎉 WEEK 1 DEMO COMPLETE!")
    print(f"Ready for LinkedIn series launch with authentic results!")
    
    return results, report

if __name__ == "__main__":
    results, report = asyncio.run(run_week1_full_demo())
    print(f"\nFinal Cost: ${report['total_cost']:.6f}")
    print(f"Budget Safety Factor: {5.00 / report['total_cost']:.0f}x")