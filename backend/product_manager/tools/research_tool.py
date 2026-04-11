"""
Research Tool — Market research, competitor analysis, and user insights.
"""

import os
import json
import httpx
from typing import Any, Optional, List
from datetime import datetime
from backend.workflows.tools.base import BaseTool, ToolResult, CredentialRequirement


class ResearchTool(BaseTool):
    """
    Research capabilities for product managers.
    
    Supports:
    - Web search for market research
    - Perplexity API for AI-powered research
    - Competitor website analysis
    - Trend analysis
    - News monitoring
    """
    
    name = "research"
    description = "Conduct market research, competitive analysis, and gather industry insights"
    category = "research"
    
    def get_required_credentials(self) -> list[CredentialRequirement]:
        return [
            CredentialRequirement(
                key="PERPLEXITY_API_KEY",
                description="Perplexity API key for AI-powered research (optional)",
                env_var="PERPLEXITY_API_KEY",
                required=False,
                example="pplx-xxxxxxxxxxxxxxxx",
                auth_type="api_key",
                docs_url="https://www.perplexity.ai/settings/api",
            ),
            CredentialRequirement(
                key="SERPAPI_KEY",
                description="SerpAPI key for web search (optional)",
                env_var="SERPAPI_KEY",
                required=False,
                example="xxxxxxxxxxxxxxxx",
            ),
        ]
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Research action",
                    "enum": [
                        "market_research",
                        "competitor_analysis",
                        "trend_analysis",
                        "customer_research",
                        "industry_news",
                        "pricing_research",
                    ],
                },
                # Research params
                "topic": {
                    "type": "string",
                    "description": "Research topic or query",
                },
                "competitors": {
                    "type": "array",
                    "description": "List of competitors to analyze",
                    "items": {"type": "string"},
                },
                "industry": {
                    "type": "string",
                    "description": "Industry/category",
                },
                "geography": {
                    "type": "string",
                    "description": "Geographic focus",
                    "default": "global",
                },
                "time_period": {
                    "type": "string",
                    "description": "Time period for research",
                    "enum": ["last_week", "last_month", "last_quarter", "last_year", "all_time"],
                    "default": "last_year",
                },
            },
            "required": ["action"],
        }
    
    async def execute(
        self,
        parameters: dict,
        context: dict = None,
    ) -> ToolResult:
        action = parameters.get("action")
        
        try:
            if action == "market_research":
                return await self._market_research(parameters)
            elif action == "competitor_analysis":
                return await self._competitor_analysis(parameters)
            elif action == "trend_analysis":
                return await self._trend_analysis(parameters)
            elif action == "customer_research":
                return await self._customer_research(parameters)
            elif action == "industry_news":
                return await self._industry_news(parameters)
            elif action == "pricing_research":
                return await self._pricing_research(parameters)
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Unknown action: {action}",
                )
        
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Research error: {str(e)}",
            )
    
    async def _market_research(self, params: dict) -> ToolResult:
        """Conduct market research on a topic."""
        topic = params.get("topic", "")
        industry = params.get("industry", "")
        geography = params.get("geography", "global")
        
        # Try Perplexity if available
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        if perplexity_key:
            return await self._perplexity_research(topic, industry, geography)
        
        # Fallback to structured template
        research = f"""# Market Research: {topic or industry}

## Market Overview

### Market Size & Growth
- **TAM (Total Addressable Market)**: [To be researched]
- **SAM (Serviceable Addressable Market)**: [To be researched]
- **SOM (Serviceable Obtainable Market)**: [To be researched]
- **Growth Rate**: [CAGR %]
- **Geography**: {geography.title()}

### Industry Trends
1. **[Trend 1]**: [Description and impact]
2. **[Trend 2]**: [Description and impact]
3. **[Trend 3]**: [Description and impact]

### Key Players
| Company | Market Share | Strengths | Weaknesses |
|---------|--------------|-----------|------------|
| [Leader 1] | XX% | [Strengths] | [Weaknesses] |
| [Leader 2] | XX% | [Strengths] | [Weaknesses] |
| [Leader 3] | XX% | [Strengths] | [Weaknesses] |

### Customer Segments
1. **Segment A**: [Description, size, needs]
2. **Segment B**: [Description, size, needs]
3. **Segment C**: [Description, size, needs]

### Market Dynamics
- **Barriers to Entry**: [Description]
- **Competitive Intensity**: [High/Medium/Low]
- **Customer Bargaining Power**: [High/Medium/Low]
- **Supplier Power**: [High/Medium/Low]
- **Threat of Substitutes**: [Description]

### Opportunities
1. [Market opportunity 1]
2. [Market opportunity 2]
3. [Market opportunity 3]

### Threats
1. [Market threat 1]
2. [Market threat 2]

## Recommendations

### Immediate Actions
- [Action item with timeline]

### Strategic Considerations
- [Strategic recommendation]

---
*Research framework generated by Katy*
*For deeper research, configure PERPLEXITY_API_KEY for AI-powered analysis*
"""
        
        return ToolResult(
            success=True,
            output=research[:800] + "...\n\n(Full research template available)",
            data={"research": research, "topic": topic or industry},
        )
    
    async def _perplexity_research(
        self, topic: str, industry: str, geography: str
    ) -> ToolResult:
        """Use Perplexity API for AI-powered research."""
        api_key = os.getenv("PERPLEXITY_API_KEY")
        
        query = f"Market research on {topic or industry}"
        if geography != "global":
            query += f" in {geography}"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "llama-3.1-sonar-small-128k-online",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a market research analyst. Provide comprehensive, factual market analysis with sources."
                        },
                        {
                            "role": "user",
                            "content": query
                        }
                    ],
                    "max_tokens": 2000,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                citations = data.get("citations", [])
                
                output = f"# Market Research: {topic or industry}\n\n{content}\n\n"
                if citations:
                    output += "## Sources\n"
                    for i, citation in enumerate(citations[:5], 1):
                        output += f"{i}. {citation}\n"
                
                return ToolResult(
                    success=True,
                    output=output[:1000] + "...\n\n(Full research available)",
                    data={"research": output, "sources": citations},
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Perplexity API error: {response.text}",
                )
    
    async def _competitor_analysis(self, params: dict) -> ToolResult:
        """Analyze specific competitors."""
        competitors = params.get("competitors", [])
        industry = params.get("industry", "")
        
        if not competitors:
            return ToolResult(
                success=False,
                output="",
                error="Please provide competitors to analyze",
            )
        
        analysis = f"""# Competitive Analysis

## Competitors Analyzed
{', '.join(competitors)}

## Detailed Analysis

"""
        
        for competitor in competitors:
            analysis += f"""### {competitor}

**Overview**
- Founded: [Year]
- Headquarters: [Location]
- Employees: [Number]
- Funding: [Amount]

**Product/Service**
- Core offering: [Description]
- Key features: [List]
- Differentiation: [Unique value prop]

**Pricing**
- Model: [Subscription/Transaction/Freemium]
- Price range: [$X - $Y]
- Free tier: [Yes/No]

**Strengths**
- [Strength 1]
- [Strength 2]
- [Strength 3]

**Weaknesses**
- [Weakness 1]
- [Weakness 2]
- [Weakness 3]

**Market Position**
- Target segment: [Description]
- Market share: [Estimated %]
- Growth rate: [Trend]

**Recent Developments**
- [News/Update 1]
- [News/Update 2]

---

"""
        
        analysis += f"""## Competitive Landscape Summary

### Positioning Map
```
High Price
   |
   |    [Comp A]
   |
   |         [Comp B]
   |
   |    [You]    [Comp C]
   |
Low ------------------------ High
   |         Features
   |
Low Price
```

### Strategic Implications
1. **Differentiation Opportunity**: [Analysis]
2. **Market Gap**: [Description]
3. **Competitive Threat**: [Assessment]

### Recommended Actions
- [ ] Action 1
- [ ] Action 2
- [ ] Action 3

---
*Analysis generated by Katy*
*For live data, consider configuring API access to Crunchbase, G2, or similar sources*
"""
        
        return ToolResult(
            success=True,
            output=analysis[:1000] + "...\n\n(Full analysis available)",
            data={"analysis": analysis, "competitors": competitors},
        )
    
    async def _trend_analysis(self, params: dict) -> ToolResult:
        """Analyze industry trends."""
        industry = params.get("industry", "")
        time_period = params.get("time_period", "last_year")
        
        trends = f"""# Trend Analysis: {industry}

## Key Trends in {industry}

### Technology Trends
1. **AI/ML Integration**
   - Impact: [Description]
   - Adoption: [Current state]
   - Timeline: [Short/Medium/Long term]

2. **Automation**
   - Impact: [Description]
   - Adoption: [Current state]
   - Timeline: [Short/Medium/Long term]

### Market Trends
1. **Customer Behavior Shift**
   - Trend: [Description]
   - Evidence: [Data points]
   - Implications: [For your product]

2. **Competitive Landscape**
   - Trend: [Consolidation/New entrants/etc]
   - Drivers: [Why this is happening]
   - Implications: [Strategic impact]

### Regulatory Trends
1. **[Regulation Name]**
   - Status: [Proposed/Enacted]
   - Impact: [Description]
   - Timeline: [Effective date]

### Emerging Opportunities
1. **[Opportunity]**
   - Description: [Details]
   - Market size: [Estimate]
   - Action: [Recommendation]

### Threats to Watch
1. **[Threat]**
   - Description: [Details]
   - Likelihood: [High/Medium/Low]
   - Mitigation: [Strategy]

## Trend Radar

```
                    2-3 Years
                        |
    AI Integration      |      Market Expansion
          o             |            o
                        |
1 Year -----------------+----------------- 5+ Years
                        |
    Automation          |      New Category
          o             |            o
                        |
                   Now (6-12 mo)
```

## Recommendations

### Immediate (0-6 months)
- [ ] Monitor trend X for opportunity
- [ ] Assess competitive response to trend Y

### Short-term (6-12 months)
- [ ] Pilot project for emerging trend
- [ ] Update roadmap to address trend Z

### Long-term (1-3 years)
- [ ] Strategic initiative for major shift
- [ ] Build capabilities for future state

---
*Trend analysis by Katy*
*For real-time trend monitoring, consider setting up Google Alerts or news feeds*
"""
        
        return ToolResult(
            success=True,
            output=trends[:800] + "...\n\n(Full trend analysis available)",
            data={"trends": trends},
        )
    
    async def _customer_research(self, params: dict) -> ToolResult:
        """Research customer needs and pain points."""
        industry = params.get("industry", "")
        topic = params.get("topic", "")
        
        research = f"""# Customer Research: {topic or industry}

## Customer Personas

### Primary Persona: [Name]
**Demographics**
- Role: [Job title]
- Industry: [Industry]
- Company size: [Size range]
- Location: [Geography]

**Goals**
- [Goal 1]
- [Goal 2]
- [Goal 3]

**Pain Points**
- [Pain point 1]
- [Pain point 2]
- [Pain point 3]

**Current Solutions**
- [How they solve it today]
- [Workarounds they use]
- [Why these fall short]

**Decision Criteria**
1. [Criterion 1] - Weight: High/Medium/Low
2. [Criterion 2] - Weight: High/Medium/Low
3. [Criterion 3] - Weight: High/Medium/Low

### Secondary Persona: [Name]
[Same structure]

## Jobs-to-be-Done

### Job 1: [Core job]
**When I** [situation]
**I want to** [motivation]
**So I can** [outcome]

**Current approach**: [How they do it]
**Pain**: [What frustrates them]
**Gain**: [What success looks like]

### Job 2: [Related job]
[Same structure]

## Customer Journey

### Awareness
- Touchpoints: [Where they learn about solutions]
- Triggers: [What prompts the search]
- Questions: [What they're asking]

### Consideration
- Evaluation criteria: [What matters]
- Comparison points: [What they compare]
- Barriers: [What's stopping them]

### Decision
- Decision makers: [Who's involved]
- Approval process: [Steps required]
- Final criteria: [Deal breakers]

### Adoption
- Onboarding: [Experience expectations]
- First value: [Time to first win]
- Success metrics: [How they measure]

## Voice of Customer

### Quotes from Research
> "[Customer quote about pain point]"
— [Persona type]

> "[Customer quote about ideal solution]"
— [Persona type]

### Feature Requests (Aggregated)
1. [Request] - Frequency: [High/Medium/Low]
2. [Request] - Frequency: [High/Medium/Low]
3. [Request] - Frequency: [High/Medium/Low]

## Insights & Opportunities

### Unmet Needs
1. [Need] - Evidence: [Research finding]
2. [Need] - Evidence: [Research finding]

### Surprising Findings
1. [Finding] - Implication: [What this means]
2. [Finding] - Implication: [What this means]

## Recommended Actions

### Product
- [ ] Address top pain point with feature X
- [ ] Improve onboarding for persona Y

### Marketing
- [ ] Messaging around key benefit Z
- [ ] Target persona A on channel B

### Sales
- [ ] Enablement for objection handling
- [ ] Case study featuring persona C

---
*Customer research framework by Katy*
*Populate with data from user interviews, surveys, and support tickets*
"""
        
        return ToolResult(
            success=True,
            output=research[:800] + "...\n\n(Full customer research available)",
            data={"research": research},
        )
    
    async def _industry_news(self, params: dict) -> ToolResult:
        """Get recent industry news."""
        industry = params.get("industry", "")
        time_period = params.get("time_period", "last_month")
        
        # This would integrate with news APIs
        news = f"""# Industry News: {industry}
*Period: {time_period.replace('_', ' ').title()}*

## Headlines

### Funding & M&A
- [Company] raises $XXM Series [X] for [purpose]
- [Company] acquires [Target] for $XXM
- [Trend] in venture funding for [sector]

### Product Launches
- [Company] launches [Product/Feature]
- [Company] announces [Major update]
- New category: [Emerging trend]

### Market Moves
- [Company] enters [New market]
- [Company] partners with [Partner]
- [Regulatory change] impacts [sector]

### Executive Changes
- [Name] joins [Company] as [Role]
- [Name] departs [Company]
- [Company] announces leadership restructure

## Analysis

### What This Means
[Strategic interpretation of news]

### Competitive Implications
- [Competitor move] suggests [strategy]
- [Market trend] indicates [shift]
- [Technology] becoming [mainstream/emerging]

### Opportunities
1. [Opportunity from news item]
2. [Opportunity from trend]

### Threats
1. [Threat from competitor move]
2. [Threat from market shift]

## Recommended Follow-up
- [ ] Deep dive on [topic]
- [ ] Competitive response to [move]
- [ ] Partnership opportunity with [company]

---
*News summary by Katy*
*For live news, configure news API integration (NewsAPI, Google News, etc.)*
"""
        
        return ToolResult(
            success=True,
            output=news[:800] + "...\n\n(Full news summary available)",
            data={"news": news},
        )
    
    async def _pricing_research(self, params: dict) -> ToolResult:
        """Research pricing in the market."""
        competitors = params.get("competitors", [])
        industry = params.get("industry", "")
        
        research = f"""# Pricing Research: {industry}

## Market Pricing Overview

### Pricing Models in Market
1. **Subscription (SaaS)**
   - Prevalence: XX%
   - Typical range: $X - $Y/month
   - Best for: [Use cases]

2. **Usage-based**
   - Prevalence: XX%
   - Typical unit: [Metric]
   - Best for: [Use cases]

3. **Freemium**
   - Prevalence: XX%
   - Free tier limits: [Typical constraints]
   - Conversion rate: XX%

4. **Enterprise/Custom**
   - Prevalence: XX%
   - Deal size: $X - $Y
   - Best for: [Use cases]

## Competitive Pricing

"""
        
        for comp in competitors:
            research += f"""### {comp}
- **Model**: [Subscription/Usage/etc]
- **Tiers**:
  - Free: [What's included]
  - Starter: $X/month - [Features]
  - Professional: $Y/month - [Features]
  - Enterprise: Custom - [Features]
- **Notes**: [Unique aspects]

"""
        
        research += f"""
## Pricing Analysis

### Price Positioning Map
```
High Value
    |
    |    [Premium Player]
    |
    |         [Mid-market Leader]
    |
    |    [Your Position]
    |              [Value Leader]
    |
Low ------------------------ High
    |         Price
    |
Low Value
```

### Key Insights
1. **Price Range**: Market ranges from $X to $Y
2. **Sweet Spot**: Most successful at $Z price point
3. **Differentiation**: [How players differentiate at same price]

### Pricing Psychology
- **Anchoring**: [How market leaders use anchoring]
- **Decoy Effect**: [Examples in market]
- **Bundle Strategy**: [Common bundles]

## Recommendations

### Pricing Strategy Options

#### Option A: Market Parity
- Price: $X/month
- Rationale: Match market leader
- Risk: Commoditization

#### Option B: Premium Positioning
- Price: $Y/month (20% above market)
- Rationale: Superior features/service
- Risk: Adoption friction

#### Option C: Disruptive Pricing
- Price: $Z/month (below market)
- Rationale: Land-and-expand strategy
- Risk: Unit economics pressure

### Implementation Plan
1. **Phase 1**: [Initial pricing launch]
2. **Phase 2**: [Add tier/change price]
3. **Phase 3**: [Enterprise tier]

### Metrics to Track
- Conversion rate by tier
- Average revenue per user (ARPU)
- Churn by price point
- Upgrade/downgrade rates

---
*Pricing research by Katy*
*Validate with actual competitor research and customer willingness-to-pay studies*
"""
        
        return ToolResult(
            success=True,
            output=research[:1000] + "...\n\n(Full pricing research available)",
            data={"research": research},
        )
