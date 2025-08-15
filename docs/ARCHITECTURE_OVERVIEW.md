# Architecture Overview - Amazon Review AI Optimizer

## Quick Reference Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   INPUT LAYER                           │
│  Amazon Reviews (Electronics, Books, Home & Garden)    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                COMPLEXITY ANALYSIS                      │
│  SmartRouterV2: Technical(35%) + Sentiment(25%) +      │
│  Length(20%) + Domain(20%) → Final Complexity Score    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                  MODEL ROUTING                          │
│  Score < 0.3 → GPT-4o-mini     ($0.15/M tokens)       │
│  0.3-0.5     → Claude Haiku    ($0.25/M tokens)       │
│  0.5-0.7     → GPT-3.5-turbo   ($0.50/M tokens)       │
│  0.7-0.9     → GPT-4o          ($2.50/M tokens)       │
│  > 0.9       → Claude Sonnet   ($3.00/M tokens)       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│               CONCURRENT PROCESSING                     │
│  5 Workers • 30s Timeout • Rate Limiting • Retries    │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                     OUTPUT                              │
│  Sentiment • Quality • Recommendation • Metrics        │
│  63.3% Cost Reduction • 2.70 reviews/second           │
└─────────────────────────────────────────────────────────┘
```

## Component Interaction Flow

```
AmazonDataLoader ──→ SmartRouterV2 ──→ OpenRouterOptimizer
       │                  │                    │
   Load Reviews      Analyze Complexity    Process with
   from Dataset      Score 4 Dimensions    Selected Model
       │                  │                    │
   Stream 1000+ ──→  Route to Tier  ──→   Return Results
   in Batches        (6 model tiers)       + Performance
```

## Core Files Structure

```
src/
├── main.py                 # Entry point & ReviewOptimizer
├── smart_router_v2.py      # Complexity analysis & routing
├── openrouter_integration.py # API client & cost tracking
├── cost_reporter.py        # Performance metrics
└── week1_full_demo.py      # Validation testing

config/
└── settings.yaml           # Model configs & parameters

docs/
├── results/                # Performance validation data
└── TECHNICAL_SPECIFICATION.md # Complete system documentation
```

## Key Performance Metrics (Week 1 Validated)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Cost Reduction | 50%+ | **63.3%** | ✅ Exceeded |
| Processing Speed | 1.0+ rev/s | **2.70 rev/s** | ✅ Exceeded |
| Reliability | 95%+ | **100%** | ✅ Perfect |
| Scale | 1000 reviews | **1000** | ✅ Complete |

## Model Distribution (Actual Usage)
- **52.3%** Claude Haiku (lightweight)
- **27.7%** GPT-4o-mini (ultra-lightweight)  
- **20.0%** GPT-3.5-turbo (medium)
- **0%** Premium models (efficient routing)

**Result**: 80% of reviews processed with cost-effective models, achieving optimal cost-quality balance.