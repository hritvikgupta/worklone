"""
High-level Product Manager tools for Katy.

These tools wrap the lower-level integrations (Jira, Notion, etc.)
and provide PM-specific functionality.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.core.tools.system_tools.base import BaseTool, ToolResult
from backend.core.agents.product_manager.types import (
    Priority, Status, UserInsight, Feature, RoadmapItem,
    Competitor, ProductDecision, Metric
)


class PrioritizeFeaturesTool(BaseTool):
    """Prioritize features using a framework (RICE, MoSCoW, etc.)."""
    
    name = "prioritize_features"
    description = "Prioritize a list of features using RICE scoring (Reach, Impact, Confidence, Effort)"
    category = "product_management"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "features": {
                    "type": "array",
                    "description": "List of features to prioritize",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "reach": {"type": "number", "description": "How many users will this affect (1-10)"},
                            "impact": {"type": "number", "description": "Impact on each user (0.25=minimal, 1=high, 3=massive)"},
                            "confidence": {"type": "number", "description": "Confidence in estimates (%)"},
                            "effort": {"type": "number", "description": "Person-months required"},
                        },
                    },
                },
                "framework": {
                    "type": "string",
                    "enum": ["RICE", "MoSCoW", "Kano", "ValueEffort"],
                    "default": "RICE",
                },
            },
            "required": ["features"],
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        features = parameters.get("features", [])
        framework = parameters.get("framework", "RICE")
        
        if not features:
            return ToolResult(success=False, output="", error="No features provided")
        
        try:
            if framework == "RICE":
                prioritized = self._rice_score(features)
            elif framework == "MoSCoW":
                prioritized = self._moscow_prioritize(features)
            elif framework == "ValueEffort":
                prioritized = self._value_effort_matrix(features)
            else:
                prioritized = self._rice_score(features)
            
            output = f"Prioritized using {framework} framework:\n\n"
            for i, feature in enumerate(prioritized, 1):
                output += f"{i}. {feature['title']}"
                if "rice_score" in feature:
                    output += f" (RICE: {feature['rice_score']:.1f})"
                elif "category" in feature:
                    output += f" ({feature['category']})"
                output += "\n"
            
            return ToolResult(success=True, output=output, data={"prioritized": prioritized})
        
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))
    
    def _rice_score(self, features: List[Dict]) -> List[Dict]:
        """Calculate RICE score for each feature."""
        scored = []
        for feature in features:
            reach = feature.get("reach", 0)
            impact = feature.get("impact", 0)
            confidence = feature.get("confidence", 100) / 100
            effort = feature.get("effort", 1)
            
            rice = (reach * impact * confidence) / effort if effort > 0 else 0
            feature["rice_score"] = rice
            scored.append(feature)
        
        return sorted(scored, key=lambda x: x["rice_score"], reverse=True)
    
    def _moscow_prioritize(self, features: List[Dict]) -> List[Dict]:
        """Categorize features by MoSCoW."""
        categorized = []
        for feature in features:
            rice = feature.get("reach", 5) * feature.get("impact", 1)
            if rice >= 20:
                feature["category"] = "Must have"
            elif rice >= 10:
                feature["category"] = "Should have"
            elif rice >= 5:
                feature["category"] = "Could have"
            else:
                feature["category"] = "Won't have"
            categorized.append(feature)
        
        order = {"Must have": 0, "Should have": 1, "Could have": 2, "Won't have": 3}
        return sorted(categorized, key=lambda x: order.get(x["category"], 4))
    
    def _value_effort_matrix(self, features: List[Dict]) -> List[Dict]:
        """Categorize by value vs effort."""
        categorized = []
        for feature in features:
            value = feature.get("impact", 1) * feature.get("reach", 5)
            effort = feature.get("effort", 1)
            
            if value >= 15 and effort <= 3:
                feature["category"] = "Quick wins - Do first"
            elif value >= 15 and effort > 3:
                feature["category"] = "Major projects - Schedule carefully"
            elif value < 15 and effort <= 3:
                feature["category"] = "Fill-ins - Do when time permits"
            else:
                feature["category"] = "Avoid - Low value, high effort"
            
            categorized.append(feature)
        
        return categorized


class CreatePRDTool(BaseTool):
    """Create a Product Requirements Document."""
    
    name = "create_prd"
    description = "Generate a Product Requirements Document (PRD) with user stories, acceptance criteria, and technical considerations"
    category = "product_management"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Feature or product name",
                },
                "problem_statement": {
                    "type": "string",
                    "description": "What problem are we solving?",
                },
                "target_users": {
                    "type": "string",
                    "description": "Who is this for?",
                },
                "success_metrics": {
                    "type": "string",
                    "description": "How will we measure success?",
                },
                "key_features": {
                    "type": "array",
                    "description": "List of key features/capabilities",
                    "items": {"type": "string"},
                },
                "out_of_scope": {
                    "type": "array",
                    "description": "What is explicitly NOT included",
                    "items": {"type": "string"},
                },
            },
            "required": ["title", "problem_statement"],
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        try:
            title = parameters.get("title")
            problem = parameters.get("problem_statement")
            target_users = parameters.get("target_users", "TBD")
            success_metrics = parameters.get("success_metrics", "TBD")
            key_features = parameters.get("key_features", [])
            out_of_scope = parameters.get("out_of_scope", [])
            
            prd = f"""# {title} - Product Requirements Document

## 1. Overview

### Problem Statement
{problem}

### Target Users
{target_users}

### Success Metrics
{success_metrics}

## 2. Goals
- Primary: [Define main objective]
- Secondary: [Define secondary objectives]

## 3. User Stories
"""
            
            for i, feature in enumerate(key_features, 1):
                prd += f"\n### {i}. {feature}\n"
                prd += f"**As a** [user type]\n"
                prd += f"**I want** {feature.lower()}\n"
                prd += f"**So that** [benefit/value]\n\n"
                prd += f"**Acceptance Criteria:**\n"
                prd += f"- [ ] Criterion 1\n"
                prd += f"- [ ] Criterion 2\n"
                prd += f"- [ ] Criterion 3\n"
            
            prd += f"""
## 4. Out of Scope
"""
            if out_of_scope:
                for item in out_of_scope:
                    prd += f"- {item}\n"
            else:
                prd += "- [List items explicitly not included]\n"
            
            prd += f"""
## 5. Technical Considerations
- Performance requirements
- Security considerations
- Integration points
- Data requirements

## 6. Design Considerations
- UX patterns to follow
- Mobile vs desktop
- Accessibility requirements

## 7. Analytics & Tracking
- Events to track
- Funnel steps
- Dashboard requirements

## 8. Launch Plan
- [ ] Pre-launch checklist
- [ ] Go-live date
- [ ] Marketing coordination
- [ ] Support team training

---
**Document created:** {datetime.now().strftime("%Y-%m-%d")}
**Author:** Katy (AI Product Manager)
"""
            
            return ToolResult(
                success=True,
                output=f"PRD created for '{title}':\n\n{prd[:500]}...\n\n(Full document available)",
                data={"prd": prd, "title": title}
            )
        
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))


class AnalyzeCompetitorsTool(BaseTool):
    """Analyze competitors and provide insights."""
    
    name = "analyze_competitors"
    description = "Analyze competitors and generate competitive landscape insights"
    category = "product_management"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "product_category": {
                    "type": "string",
                    "description": "What category are we analyzing?",
                },
                "competitors": {
                    "type": "array",
                    "description": "Known competitors to analyze",
                    "items": {"type": "string"},
                },
                "focus_areas": {
                    "type": "array",
                    "description": "What to focus on",
                    "items": {
                        "type": "string",
                        "enum": ["pricing", "features", "market_share", "strengths_weaknesses", "positioning"],
                    },
                },
            },
            "required": ["product_category"],
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        category = parameters.get("product_category")
        competitors = parameters.get("competitors", [])
        focus = parameters.get("focus_areas", ["features", "pricing", "strengths_weaknesses"])
        
        analysis = f"""# Competitive Analysis: {category}

## Market Overview
{category} is a [describe market size, growth, trends].

## Key Players
"""
        
        if competitors:
            for comp in competitors:
                analysis += f"\n### {comp}\n"
                analysis += "- **Strengths:** [Key advantages]\n"
                analysis += "- **Weaknesses:** [Areas of vulnerability]\n"
                analysis += "- **Pricing:** [Pricing model/range]\n"
                analysis += "- **Target:** [Target market segment]\n"
        else:
            analysis += "\n**Direct competitors identified:**\n"
            analysis += "1. [Competitor 1]\n"
            analysis += "2. [Competitor 2]\n"
            analysis += "3. [Competitor 3]\n\n"
        
        analysis += f"""
## Feature Comparison

| Feature | Us | Comp 1 | Comp 2 | Comp 3 |
|---------|---|--------|--------|--------|
| Core A | ✓ | ✓ | ✓ | ✗ |
| Feature B | ✓ | ✓ | ✗ | ✓ |
| Feature C | ✗ | ✓ | ✓ | ✓ |

## Pricing Comparison

| Competitor | Model | Price Range | Notes |
|------------|-------|-------------|-------|
| Comp 1 | [SaaS/Perpetual/etc] | $X-Y/mo | [Notes] |
| Comp 2 | [Model] | $X-Y/mo | [Notes] |

## Strategic Opportunities

1. **Differentiation:** [How we can stand out]
2. **Market Gap:** [Underserved segment]
3. **Feature Gap:** [What competitors lack]
4. **Pricing:** [Opportunity for competitive advantage]

## Recommendations

### Short-term (0-3 months)
- [Action item 1]
- [Action item 2]

### Medium-term (3-6 months)
- [Action item 3]
- [Action item 4]

### Long-term (6-12 months)
- [Strategic initiative]

---
*Analysis generated by Katy on {datetime.now().strftime("%Y-%m-%d")}*
"""
        
        return ToolResult(
            success=True,
            output=analysis[:500] + "...\n\n(Full analysis available)",
            data={"analysis": analysis, "category": category}
        )


class DefineMetricsTool(BaseTool):
    """Define product metrics and KPIs framework."""
    
    name = "define_metrics"
    description = "Define a framework of metrics for measuring product success (North Star, KPIs, etc.)"
    category = "product_management"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "product_stage": {
                    "type": "string",
                    "enum": ["pre_product", "mvp", "product_market_fit", "growth", "mature"],
                    "description": "Current stage of the product",
                },
                "product_type": {
                    "type": "string",
                    "enum": ["b2b_saas", "b2c_app", "marketplace", "platform", "api"],
                    "description": "Type of product",
                },
                "business_model": {
                    "type": "string",
                    "enum": ["subscription", "transactional", "freemium", "ad_supported"],
                    "description": "How you make money",
                },
            },
            "required": ["product_stage", "product_type"],
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        stage = parameters.get("product_stage")
        product_type = parameters.get("product_type")
        business_model = parameters.get("business_model", "subscription")
        
        framework = self._generate_metrics_framework(stage, product_type, business_model)
        
        return ToolResult(
            success=True,
            output=framework[:800] + "...\n\n(Full framework available)",
            data={"framework": framework}
        )
    
    def _generate_metrics_framework(
        self, stage: str, product_type: str, business_model: str
    ) -> str:
        """Generate appropriate metrics based on product characteristics."""
        
        frameworks = {
            "pre_product": {
                "north_star": "Validation signals (waitlist signups, pilot interest)",
                "focus": "Problem validation and solution fit",
                "metrics": ["Landing page CTR", "Waitlist signups", "Interview completion rate"],
            },
            "mvp": {
                "north_star": "Activation rate or early engagement",
                "focus": "Finding early adopters and usage patterns",
                "metrics": ["Activation rate", "DAU/MAU", "Feature adoption", "NPS"],
            },
            "product_market_fit": {
                "north_star": "Retention or engagement",
                "focus": "Understanding value and improving stickiness",
                "metrics": ["Retention (D1, D7, D30)", "Power user curve", "PMF survey score"],
            },
            "growth": {
                "north_star": "Revenue or user growth",
                "focus": "Scaling acquisition and optimizing conversion",
                "metrics": ["CAC", "LTV", "Viral coefficient", "Conversion funnel"],
            },
            "mature": {
                "north_star": "Revenue or profitability",
                "focus": "Efficiency, expansion, and churn reduction",
                "metrics": ["Net Revenue Retention", "Gross Margin", "Churn rate", "Expansion MRR"],
            },
        }
        
        framework = frameworks.get(stage, frameworks["mvp"])
        
        output = f"""# Metrics Framework for {product_type.replace('_', ' ').title()} ({stage.replace('_', ' ').title()} Stage)

## North Star Metric
**{framework['north_star']}**

## Focus Area
{framework['focus']}

## Key Metrics

### Engagement
- Daily Active Users (DAU)
- Weekly Active Users (WAU)  
- Monthly Active Users (MAU)
- DAU/MAU ratio (stickiness)

### Retention
- Day 1 retention
- Day 7 retention
- Day 30 retention
- Cohort analysis

### Acquisition
- New signups (daily/weekly)
- Traffic sources
- Activation rate
- Time to value

### Revenue (for {business_model} model)
"""
        
        if business_model == "subscription":
            output += """- Monthly Recurring Revenue (MRR)
- Annual Recurring Revenue (ARR)
- Average Revenue Per User (ARPU)
- Customer Lifetime Value (LTV)
- Customer Acquisition Cost (CAC)
- LTV:CAC ratio
"""
        elif business_model == "transactional":
            output += """- Transaction volume
- Average transaction value
- Take rate / commission
- Gross merchandise value (GMV)
"""
        elif business_model == "freemium":
            output += """- Free to paid conversion rate
- Upgrade rate
- Paying user count
- Revenue per paying user
"""
        
        output += f"""
### Satisfaction
- Net Promoter Score (NPS)
- Customer Satisfaction Score (CSAT)
- Support ticket volume
- Feature request volume

### Product Quality
- Error rate
- Uptime/availability
- Page load time
- Support response time

## Dashboard Structure
1. **Executive Summary** - North Star + 3-4 key metrics
2. **Acquisition** - Funnel from visitor to activated user
3. **Engagement** - Usage patterns and feature adoption
4. **Retention** - Cohort analysis and churn metrics
5. **Revenue** - Monetization metrics (if applicable)

## Review Cadence
- **Daily:** Core engagement metrics
- **Weekly:** Full funnel review
- **Monthly:** Cohort and retention analysis
- **Quarterly:** Strategic metrics review

---
*Framework customized for your product by Katy*
"""
        
        return output


class PlanUserResearchTool(BaseTool):
    """Plan user research activities."""
    
    name = "plan_user_research"
    description = "Create a user research plan with methodology, questions, and participant criteria"
    category = "product_management"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "research_goal": {
                    "type": "string",
                    "description": "What do you want to learn?",
                },
                "methodology": {
                    "type": "string",
                    "enum": ["interviews", "survey", "usability_test", "focus_group", "diary_study"],
                    "description": "Research method",
                },
                "target_participants": {
                    "type": "string",
                    "description": "Who should participate?",
                },
                "num_participants": {
                    "type": "integer",
                    "description": "How many participants needed",
                    "default": 5,
                },
            },
            "required": ["research_goal", "methodology"],
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        goal = parameters.get("research_goal")
        method = parameters.get("methodology")
        target = parameters.get("target_participants", "Current users")
        num = parameters.get("num_participants", 5)
        
        plan = f"""# User Research Plan: {method.replace('_', ' ').title()}

## Research Goal
{goal}

## Methodology
**{method.replace('_', ' ').title()}**

### Why this method?
{self._get_method_rationale(method)}

## Participants
- **Target:** {target}
- **Number:** {num} participants
- **Recruitment:** [How you'll find participants]
- **Incentive:** [What you'll offer]

## Timeline
- **Week 1:** Recruit participants
- **Week 2-3:** Conduct sessions
- **Week 4:** Synthesize and report

## Discussion Guide / Questions
"""
        
        questions = self._get_questions_for_method(method, goal)
        for i, q in enumerate(questions, 1):
            plan += f"{i}. {q}\n"
        
        plan += f"""
## Success Criteria
- [ ] All sessions completed
- [ ] Notes documented for each session
- [ ] Insights synthesized
- [ ] Recommendations documented
- [ ] Share-out with stakeholders

## Output Deliverables
1. Raw notes/transcripts
2. Insight summary document
3. User quotes repository
4. Recommended next steps

---
*Plan created by Katy*
"""
        
        return ToolResult(
            success=True,
            output=plan[:500] + "...\n\n(Full plan available)",
            data={"plan": plan}
        )
    
    def _get_method_rationale(self, method: str) -> str:
        rationales = {
            "interviews": "Best for understanding user needs, motivations, and context in depth.",
            "survey": "Good for quantitative validation and reaching many users quickly.",
            "usability_test": "Essential for evaluating interface effectiveness and finding UX issues.",
            "focus_group": "Useful for exploring group dynamics and consensus on concepts.",
            "diary_study": "Captures real-world usage patterns over time.",
        }
        return rationales.get(method, "Appropriate for this research goal.")
    
    def _get_questions_for_method(self, method: str, goal: str) -> List[str]:
        if method == "interviews":
            return [
                "Can you tell me about your current workflow for [relevant activity]?",
                "What's the hardest part about [problem area]?",
                "How do you currently solve this problem?",
                "What would an ideal solution look like?",
                "Can you walk me through a recent time you experienced this?",
            ]
        elif method == "survey":
            return [
                "How frequently do you [relevant activity]? (Daily/Weekly/Monthly/Rarely)",
                "Rate your satisfaction with current solutions (1-10)",
                "What's your biggest frustration with [problem area]? (Open ended)",
                "How likely are you to try a new solution? (Very/Somewhat/Not likely)",
            ]
        elif method == "usability_test":
            return [
                "Please try to [specific task]",
                "What would you expect to happen next?",
                "Was there anything confusing?",
                "How would you rate the ease of this task? (1-5)",
            ]
        else:
            return [
                "[Customize questions based on research goal]",
                f"Related to: {goal}",
            ]


def create_pm_tools() -> List[BaseTool]:
    """Create and return all high-level PM tools."""
    return [
        PrioritizeFeaturesTool(),
        CreatePRDTool(),
        AnalyzeCompetitorsTool(),
        DefineMetricsTool(),
        PlanUserResearchTool(),
    ]
