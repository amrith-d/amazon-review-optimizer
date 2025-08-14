"""
OpenRouter API Integration for Amazon Review Optimizer
Implements real API calls with cost optimization
"""

import os
import time
import asyncio
import yaml
from typing import Dict, List, Optional
from dataclasses import dataclass
from openai import OpenAI
import tiktoken


@dataclass
class OpenRouterConfig:
    """Configuration for OpenRouter integration"""
    api_key: str
    base_url: str = "https://openrouter.ai/api/v1"
    max_budget: float = 5.00  # Safety limit in USD
    current_spend: float = 0.00


class OpenRouterOptimizer:
    """Real LLM API integration with OpenRouter"""
    
    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config = self._load_config(config_path)
        self.openrouter_config = self._setup_openrouter()
        self.client = self._create_client()
        self.conversation_cache = {}  # For KV cache optimization
        self.token_encoder = tiktoken.get_encoding("cl100k_base")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_openrouter(self) -> OpenRouterConfig:
        """Setup OpenRouter configuration"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment")
        
        return OpenRouterConfig(
            api_key=api_key,
            max_budget=float(os.getenv('MAX_BUDGET', '5.00'))
        )
    
    def _create_client(self) -> OpenAI:
        """Create OpenRouter client using OpenAI SDK"""
        return OpenAI(
            base_url=self.openrouter_config.base_url,
            api_key=self.openrouter_config.api_key,
        )
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.token_encoder.encode(text))
    
    def _estimate_cost(self, model_config: Dict, prompt_tokens: int, completion_tokens: int = 50) -> float:
        """Estimate API call cost"""
        cost_per_million = model_config['cost_per_million_tokens']
        total_tokens = prompt_tokens + completion_tokens
        return (total_tokens / 1_000_000) * cost_per_million
    
    def _check_budget(self, estimated_cost: float):
        """Check if API call fits within budget"""
        if self.openrouter_config.current_spend + estimated_cost > self.openrouter_config.max_budget:
            raise Exception(
                f"Budget exceeded: ${self.openrouter_config.current_spend + estimated_cost:.4f} "
                f"vs limit ${self.openrouter_config.max_budget:.2f}"
            )
    
    def _get_model_config(self, model_tier: str) -> Dict:
        """Get model configuration by tier"""
        return self.config['models'][model_tier]
    
    def _create_optimized_prompt(self, review_text: str, category: str, use_conversation: bool = True) -> List[Dict]:
        """Create optimized prompt for API call"""
        base_prompt = f"""Analyze this {category.lower()} product review for:
1. Sentiment (Positive/Negative/Neutral)
2. Product Quality Assessment
3. Purchase Recommendation
4. Key Insights

Review: "{review_text}"

Respond in JSON format:
{{"sentiment": "", "quality": "", "recommendation": "", "insights": []}}"""

        if use_conversation and category in self.conversation_cache:
            # Reuse conversation context (KV cache optimization)
            messages = self.conversation_cache[category] + [
                {"role": "user", "content": f"Analyze: {review_text}"}
            ]
        else:
            # New conversation
            messages = [
                {"role": "system", "content": f"You are an expert at analyzing {category.lower()} product reviews."},
                {"role": "user", "content": base_prompt}
            ]
        
        return messages
    
    async def analyze_review_real(self, review_data: Dict, model_tier: str = "ultra_lightweight") -> Dict:
        """Make real API call to analyze review"""
        start_time = time.time()
        
        review_text = review_data['review_text']
        category = review_data['category']
        
        # Get model configuration
        model_config = self._get_model_config(model_tier)
        model_name = model_config['openrouter_name']
        
        # Create optimized prompt
        messages = self._create_optimized_prompt(review_text, category)
        
        # Calculate tokens and cost
        prompt_text = str(messages)
        prompt_tokens = self._count_tokens(prompt_text)
        estimated_cost = self._estimate_cost(model_config, prompt_tokens)
        
        # Budget check
        self._check_budget(estimated_cost)
        
        try:
            # Make real API call
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model=model_name,
                messages=messages,
                max_tokens=model_config['max_tokens'],
                temperature=0.1
            )
            
            # Track actual cost
            actual_tokens = response.usage.total_tokens if response.usage else prompt_tokens + 50
            actual_cost = self._estimate_cost(model_config, actual_tokens)
            self.openrouter_config.current_spend += actual_cost
            
            # Cache conversation for future KV optimization
            self.conversation_cache[category] = messages + [
                {"role": "assistant", "content": response.choices[0].message.content}
            ]
            
            # Parse response
            content = response.choices[0].message.content
            processing_time = time.time() - start_time
            
            return {
                'content': content,
                'model_used': model_name,
                'cost': actual_cost,
                'tokens_used': actual_tokens,
                'processing_time': processing_time,
                'cache_optimized': category in self.conversation_cache
            }
            
        except Exception as e:
            print(f"API call failed: {e}")
            raise
    
    def batch_analyze_reviews(self, reviews: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Analyze reviews in optimized batches"""
        results = []
        
        # Group by category for conversation reuse
        by_category = {}
        for review in reviews:
            category = review['category']
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(review)
        
        # Process each category
        for category, category_reviews in by_category.items():
            print(f"🔄 Processing {len(category_reviews)} {category} reviews with OpenRouter...")
            
            # Process in batches
            for i in range(0, len(category_reviews), batch_size):
                batch = category_reviews[i:i + batch_size]
                
                for review in batch:
                    try:
                        # Route to optimal model
                        model_tier = self._route_to_model(review['review_text'], category)
                        
                        # Make API call
                        result = asyncio.run(self.analyze_review_real(review, model_tier))
                        results.append({
                            'review_id': review.get('review_id', f'review_{len(results)}'),
                            'category': category,
                            'result': result,
                            'model_tier': model_tier
                        })
                        
                        # Small delay to avoid rate limits
                        time.sleep(0.1)
                        
                    except Exception as e:
                        print(f"⚠️ Skipping review due to error: {e}")
                        continue
        
        return results
    
    def _route_to_model(self, review_text: str, category: str) -> str:
        """Smart routing logic (same as original)"""
        text_length = len(review_text)
        
        if text_length < 100 and category in ["Books", "Home_and_Garden"]:
            return 'ultra_lightweight'  # gpt-4o-mini
        elif text_length < 200 and category == "Books":
            return 'lightweight'  # claude-haiku
        elif text_length > 500 or category == "Electronics":
            return 'advanced'  # gpt-4o
        elif category == "Electronics" and text_length > 300:
            return 'premium'  # claude-sonnet
        else:
            return 'medium'  # gpt-3.5-turbo
    
    def get_cost_report(self) -> Dict:
        """Get detailed cost and performance report"""
        return {
            'total_spent': round(self.openrouter_config.current_spend, 6),
            'remaining_budget': round(self.openrouter_config.max_budget - self.openrouter_config.current_spend, 6),
            'conversation_contexts': len(self.conversation_cache),
            'models_used': list(self.config['models'].keys())
        }


# Integration with existing main.py
class RealAPIMode:
    """Toggle between simulation and real API mode"""
    
    def __init__(self, use_real_apis: bool = False):
        self.use_real_apis = use_real_apis
        if use_real_apis:
            self.optimizer = OpenRouterOptimizer()
        else:
            self.optimizer = None
    
    async def analyze_review(self, review_data: Dict) -> Dict:
        """Analyze review with optional real API integration"""
        if self.use_real_apis and self.optimizer:
            # Use real OpenRouter API
            model_tier = self.optimizer._route_to_model(
                review_data['review_text'], 
                review_data['category']
            )
            result = await self.optimizer.analyze_review_real(review_data, model_tier)
            return result
        else:
            # Use existing simulation
            from main import AmazonReviewAnalyzer
            analyzer = AmazonReviewAnalyzer()
            return await analyzer.analyze_review(review_data)


if __name__ == "__main__":
    # Test OpenRouter integration
    print("🧪 Testing OpenRouter Integration...")
    
    # Sample review
    test_review = {
        'review_text': "This laptop is amazing! Great performance and battery life.",
        'category': 'Electronics',
        'rating': 5,
        'review_id': 'test_001'
    }
    
    # Create optimizer
    optimizer = OpenRouterOptimizer()
    
    # Test API call
    try:
        result = asyncio.run(optimizer.analyze_review_real(test_review))
        print("✅ OpenRouter API test successful!")
        print(f"Model: {result['model_used']}")
        print(f"Cost: ${result['cost']:.6f}")
        print(f"Response: {result['content'][:100]}...")
        
        # Cost report
        report = optimizer.get_cost_report()
        print(f"\n💰 Cost Report:")
        print(f"Spent: ${report['total_spent']:.6f}")
        print(f"Remaining: ${report['remaining_budget']:.6f}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Make sure OPENROUTER_API_KEY is set in your environment")