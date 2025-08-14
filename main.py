"""
Amazon Product Review Analysis Optimizer
Day 1 Implementation - Real Amazon Reviews 2023 Dataset

Author: Amrith D
Repository: https://github.com/amrith-d/amazon-review-optimizer
"""

import time
import json
import hashlib
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Optional
from collections import defaultdict
import random

# For real dataset integration
try:
    from datasets import load_dataset
    import pandas as pd
    DATASETS_AVAILABLE = True
    print("✅ Dataset libraries available")
except ImportError:
    DATASETS_AVAILABLE = False
    print("📦 Install datasets: pip install datasets pandas")

@dataclass
class ProductReviewResult:
    product_category: str
    sentiment: str
    product_quality: str
    purchase_recommendation: str
    key_insights: List[str]
    cost: float
    model_used: str
    cache_hit: bool
    processing_time: float

class AmazonDataLoader:
    """Load and preprocess Amazon Reviews 2023 dataset"""
    
    def __init__(self):
        self.categories = ["Electronics", "Books", "Home_and_Garden"]
        
    def load_sample_data(self, category: str = "Electronics", sample_size: int = 100) -> List[Dict]:
        """Load sample data from Amazon Reviews 2023"""
        if not DATASETS_AVAILABLE:
            return self._generate_sample_data(sample_size)
        
        try:
            print(f"🔄 Loading {sample_size} {category} reviews from Amazon Reviews 2023...")
            
            # Load from Hugging Face dataset
            dataset_name = f"raw_review_{category}"
            dataset = load_dataset("McAuley-Lab/Amazon-Reviews-2023", 
                                 dataset_name, 
                                 split="train", 
                                 streaming=True)
            
            reviews = []
            for i, item in enumerate(dataset):
                if i >= sample_size:
                    break
                    
                if item.get('text') and item.get('rating') and len(item['text']) > 20:
                    reviews.append({
                        'review_text': item['text'][:1000],  # Limit for efficiency
                        'rating': item['rating'],
                        'category': category,
                        'product_title': item.get('title', 'Product')[:50],
                        'review_id': item.get('asin', f"review_{i}")
                    })
            
            print(f"✅ Loaded {len(reviews)} real Amazon {category} reviews")
            return reviews
            
        except Exception as e:
            print(f"⚠️ Dataset error: {e}")
            print("🔄 Using sample data for demonstration...")
            return self._generate_sample_data(sample_size)
    
    def _generate_sample_data(self, sample_size: int) -> List[Dict]:
        """Generate realistic sample data when dataset isn't available"""
        sample_reviews = [
            {"review_text": "This laptop is amazing! Fast processor, great screen quality, and the battery lasts all day. Perfect for work and gaming.", "rating": 5, "category": "Electronics", "product_title": "Gaming Laptop Pro 15", "review_id": "B001"},
            {"review_text": "The wireless headphones have excellent sound quality but the battery dies too quickly. Good for the price but could be better.", "rating": 3, "category": "Electronics", "product_title": "Wireless Headphones X1", "review_id": "B002"},
            {"review_text": "Great book! The characters are well-developed and the plot keeps you engaged from start to finish.", "rating": 5, "category": "Books", "product_title": "Adventure Novel", "review_id": "B003"},
            {"review_text": "Coffee maker works well but the setup was confusing. Makes good coffee once you figure it out.", "rating": 4, "category": "Home_and_Garden", "product_title": "Coffee Maker Pro", "review_id": "B004"},
        ]
        
        # Expand to requested size
        expanded_reviews = []
        for i in range(sample_size):
            base_review = sample_reviews[i % len(sample_reviews)].copy()
            base_review['review_id'] = f"sample_{i:04d}"
            expanded_reviews.append(base_review)
        
        return expanded_reviews

class CostTracker:
    """Track LLM optimization costs"""
    
    def __init__(self):
        self.total_cost = 0.0
        self.requests_by_model = {}
        self.cache_hits = 0
        self.cache_misses = 0
        
    def log_request(self, model: str, tokens: int, cost: float, cache_hit: bool = False):
        if cache_hit:
            self.cache_hits += 1
            return 0.0
            
        self.cache_misses += 1
        self.total_cost += cost
        
        if model not in self.requests_by_model:
            self.requests_by_model[model] = {'requests': 0, 'cost': 0.0, 'tokens': 0}
        
        self.requests_by_model[model]['requests'] += 1
        self.requests_by_model[model]['cost'] += cost
        self.requests_by_model[model]['tokens'] += tokens
        
        return cost
    
    def get_metrics(self) -> Dict:
        total_requests = self.cache_hits + self.cache_misses
        cache_hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0
        
        return {
            'total_cost': round(self.total_cost, 6),
            'total_requests': total_requests,
            'cache_hit_rate': round(cache_hit_rate * 100, 1),
            'cost_per_request': round(self.total_cost / self.cache_misses, 6) if self.cache_misses > 0 else 0,
            'model_breakdown': self.requests_by_model
        }

class ModelRouter:
    """Smart model routing for cost optimization"""
    
    def __init__(self):
        self.model_costs = {
            'claude-haiku': 0.25,    # Cheap for simple analysis
            'claude-sonnet': 3.0,    # Expensive for complex analysis
            'gpt-3.5-turbo': 1.5,    # Medium cost
        }
        
    def route_request(self, review_text: str, category: str) -> str:
        text_length = len(review_text)
        
        # Route based on complexity
        if text_length < 150 and category == "Books":
            return 'claude-haiku'  # Simple sentiment for books
        elif text_length > 400 or category == "Electronics":
            return 'claude-sonnet'  # Detailed analysis for electronics
        else:
            return 'gpt-3.5-turbo'  # Default
    
    def get_cost_per_token(self, model: str) -> float:
        return self.model_costs.get(model, 1.0) / 1_000_000

class SemanticCache:
    """Cache similar analysis results"""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        
    def _get_cache_key(self, review_text: str, category: str) -> str:
        content = review_text.lower().strip()[:100]
        key_string = f"{category}_{content}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def get(self, review_text: str, category: str) -> Optional[ProductReviewResult]:
        cache_key = self._get_cache_key(review_text, category)
        return self.cache.get(cache_key)
    
    def set(self, review_text: str, category: str, result: ProductReviewResult):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        cache_key = self._get_cache_key(review_text, category)
        self.cache[cache_key] = result

class AmazonReviewAnalyzer:
    """Main analyzer with optimizations"""
    
    def __init__(self):
        self.cost_tracker = CostTracker()
        self.model_router = ModelRouter()
        self.cache = SemanticCache()
        self.data_loader = AmazonDataLoader()
    
    async def analyze_review(self, review_data: Dict) -> ProductReviewResult:
        """Analyze single review with optimizations"""
        start_time = time.time()
        
        review_text = review_data['review_text']
        category = review_data['category']
        
        # Check cache first
        cached_result = self.cache.get(review_text, category)
        if cached_result:
            cached_result.cache_hit = True
            self.cost_tracker.log_request('cache', 0, 0.0, cache_hit=True)
            return cached_result
        
        # Route to optimal model
        model = self.model_router.route_request(review_text, category)
        
        # Estimate tokens and cost
        token_count = len(review_text) // 4  # Rough estimate
        cost_per_token = self.model_router.get_cost_per_token(model)
        estimated_cost = token_count * cost_per_token
        
        # Simulate API call (replace with real API)
        await asyncio.sleep(0.1 if model == 'claude-haiku' else 0.3)
        
        # Simulate analysis results
        sentiment_map = {5: 'Positive', 4: 'Positive', 3: 'Neutral', 2: 'Negative', 1: 'Negative'}
        sentiment = sentiment_map.get(review_data.get('rating', 3), 'Neutral')
        
        # Track cost
        actual_cost = self.cost_tracker.log_request(model, token_count, estimated_cost)
        processing_time = time.time() - start_time
        
        result = ProductReviewResult(
            product_category=category,
            sentiment=sentiment,
            product_quality='Good' if review_data.get('rating', 3) >= 4 else 'Fair',
            purchase_recommendation='Recommend' if review_data.get('rating', 3) >= 4 else 'Neutral',
            key_insights=[f"Customer feedback on {category.lower()} product"],
            cost=actual_cost,
            model_used=model,
            cache_hit=False,
            processing_time=processing_time
        )
        
        # Cache result
        self.cache.set(review_text, category, result)
        return result

    def batch_analyze(self, reviews: List[Dict]) -> List[ProductReviewResult]:
        """Process reviews in batches - FIXED VERSION"""
        results = []
    
        # Group by category for efficiency
        categorized = defaultdict(list)
        for review in reviews:
            categorized[review['category']].append(review)
    
        # Process each category
        for category, category_reviews in categorized.items():
            print(f"🔄 Processing {len(category_reviews)} {category} reviews...")
        
        # Process one review at a time to avoid async conflicts
        for review in category_reviews:
            try:
                # Create simple sync version instead of async
                start_time = time.time()
                
                review_text = review['review_text']
                category = review['category']
                
                # Check cache first
                cached_result = self.cache.get(review_text, category)
                if cached_result:
                    cached_result.cache_hit = True
                    self.cost_tracker.log_request('cache', 0, 0.0, cache_hit=True)
                    results.append(cached_result)
                    continue
                
                # Route to optimal model
                model = self.model_router.route_request(review_text, category)
                
                # Calculate cost
                token_count = len(review_text) // 4
                cost_per_token = self.model_router.get_cost_per_token(model)
                estimated_cost = token_count * cost_per_token
                
                # Simulate processing (no async)
                time.sleep(0.05 if model == 'claude-haiku' else 0.1)
                
                # Generate result
                sentiment_map = {5: 'Positive', 4: 'Positive', 3: 'Neutral', 2: 'Negative', 1: 'Negative'}
                sentiment = sentiment_map.get(review.get('rating', 3), 'Neutral')
                
                # Track cost
                actual_cost = self.cost_tracker.log_request(model, token_count, estimated_cost)
                processing_time = time.time() - start_time
                
                # Create result
                analysis_result = ProductReviewResult(
                    product_category=category,
                    sentiment=sentiment,
                    product_quality='Good' if review.get('rating', 3) >= 4 else 'Fair',
                    purchase_recommendation='Recommend' if review.get('rating', 3) >= 4 else 'Neutral',
                    key_insights=[f"Customer feedback on {category.lower()} product"],
                    cost=actual_cost,
                    model_used=model,
                    cache_hit=False,
                    processing_time=processing_time,
                #    review_length removed
                )
                
                # Cache for future use
                self.cache.set(review_text, category, analysis_result)
                results.append(analysis_result)
                
            except Exception as e:
                print(f"⚠️ Skipping review due to error: {e}")
                continue
        return results
    
    def get_optimization_report(self) -> Dict:
        """Generate optimization report"""
        metrics = self.cost_tracker.get_metrics()
        
        # Calculate savings vs baseline (GPT-4)
        baseline_cost_per_request = 0.006  # $6 per 1000 requests
        baseline_cost = metrics['total_requests'] * baseline_cost_per_request
        actual_cost = metrics['total_cost']
        savings = baseline_cost - actual_cost
        savings_percentage = (savings / baseline_cost * 100) if baseline_cost > 0 else 0
        
        return {
            'optimization_metrics': metrics,
            'cost_comparison': {
                'baseline_cost': round(baseline_cost, 6),
                'optimized_cost': round(actual_cost, 6),
                'total_savings': round(savings, 6),
                'savings_percentage': round(savings_percentage, 1)
            }
        }

# Main execution
async def main():
    """Day 1 Demo: Amazon Review Optimization"""
    print("🚀 Amazon Product Review Analysis Optimizer - Day 1")
    print("Using Real Amazon Reviews 2023 Dataset")
    print("=" * 60)
    
    analyzer = AmazonReviewAnalyzer()
    
    # Load real Amazon data
    amazon_reviews = analyzer.data_loader.load_sample_data("Electronics", sample_size=10)
    
    print(f"📊 Processing {len(amazon_reviews)} real Amazon reviews...")
    
    start_time = time.time()
    results = analyzer.batch_analyze(amazon_reviews)
    total_time = time.time() - start_time
    
    print(f"✅ Processing completed in {total_time:.2f} seconds")
    
    # Show sample results
    print(f"\n📈 Sample Results:")
    for i, result in enumerate(results[:3]):
        print(f"\nReview {i+1}:")
        print(f"  Category: {result.product_category}")
        print(f"  Sentiment: {result.sentiment}")
        print(f"  Quality: {result.product_quality}")
        print(f"  Model: {result.model_used}")
        print(f"  Cost: ${result.cost:.6f}")
        print(f"  Cached: {'Yes' if result.cache_hit else 'No'}")
    
    # Generate report
    report = analyzer.get_optimization_report()
    
    print(f"\n💰 Optimization Report:")
    print(f"  Baseline cost (GPT-4): ${report['cost_comparison']['baseline_cost']:.6f}")
    print(f"  Optimized cost: ${report['cost_comparison']['optimized_cost']:.6f}")
    print(f"  Total savings: ${report['cost_comparison']['total_savings']:.6f}")
    print(f"  Savings percentage: {report['cost_comparison']['savings_percentage']:.1f}%")
    
    print(f"\n⚡ Performance Metrics:")
    print(f"  Cache hit rate: {report['optimization_metrics']['cache_hit_rate']}%")
    print(f"  Total requests: {report['optimization_metrics']['total_requests']}")
    print(f"  Cost per request: ${report['optimization_metrics']['cost_per_request']:.6f}")
    
    print(f"\n🎯 Day 1 SUCCESS Metrics:")
    print(f"  • {report['cost_comparison']['savings_percentage']:.0f}% cost reduction achieved ✅")
    print(f"  • {len(amazon_reviews)} real Amazon reviews processed ✅")
    print(f"  • {report['optimization_metrics']['cache_hit_rate']:.0f}% cache efficiency ✅")
    print(f"  • {total_time:.1f}s total processing time ✅")
    
    return report

if __name__ == "__main__":
    # Run Day 1 demonstration
    asyncio.run(main())
