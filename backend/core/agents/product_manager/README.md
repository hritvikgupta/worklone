# Katy — AI Product Manager Agent

An AI-powered Product Manager agent using the **ReAct** (Reasoning + Acting) pattern. Katy can handle all aspects of product management from strategic planning to execution.

## Architecture

```
backend/core/agents/product_manager/
├── katy.py
├── types.py
└── README.md

backend/core/tools/
├── specialized_tools/pm_tools.py
└── integration_tools_v2/
```

## Core Capabilities

### 1. Strategic Planning
- Define product vision and roadmap
- Conduct market research and competitive analysis
- Identify customer needs and pain points
- Set product strategy aligned with business goals

### 2. Feature Prioritization
- Manage and prioritize product backlog
- Use RICE, MoSCoW, and other frameworks
- Balance customer needs vs technical constraints
- Define MVP scope and iterative releases

### 3. Cross-functional Leadership
- Coordinate between teams via Slack
- Facilitate communication
- Remove blockers and enable productivity
- Align stakeholders on direction

### 4. Customer Advocacy
- Plan user research activities
- Synthesize customer feedback
- Translate insights into requirements
- Ensure product solves real problems

### 5. Data-Driven Decisions
- Define and track product metrics
- Analyze usage data
- A/B test analysis
- Measure product success and ROI

### 6. Go-to-Market
- Product positioning and messaging
- Launch planning
- Sales enablement support
- Pricing strategy research

### 7. Requirements Definition
- Write user stories and PRDs
- Create acceptance criteria
- Document specifications
- Maintain product documentation

## ReAct Pattern

Katy uses the ReAct pattern for complex tasks:

```
User Request → Thought → Action → Observation → ... → Answer
```

**Example Flow:**
1. User: "Prioritize my backlog"
2. Thought: "I need to fetch backlog items from Jira first"
3. Action: `jira.get_backlog`
4. Observation: "Found 15 items in backlog"
5. Thought: "Now I need to apply prioritization framework"
6. Action: `prioritize_features` with RICE scoring
7. Observation: "Scored all items"
8. Answer: "Here's your prioritized backlog..."

## Setup

### 1. Install Dependencies

```bash
# Already included in main project requirements
pip install httpx
```

### 2. Configure Credentials

Create `.env` file with your API keys:

```bash
# Jira (required for backlog management)
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_API_TOKEN=your_api_token
JIRA_EMAIL=your@email.com

# Notion (required for documentation)
NOTION_API_TOKEN=secret_xxxxxxxx

# Analytics (optional)
GA4_PROPERTY_ID=123456789
MIXPANEL_API_KEY=xxxxxxxx
AMPLITUDE_API_KEY=xxxxxxxx

# Research (optional)
PERPLEXITY_API_KEY=pplx-xxxxxxxx
SERPAPI_KEY=xxxxxxxx

# Communication (reuse from main project)
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
GMAIL_ACCESS_TOKEN=ya29.xxxxxxxx
```

### 3. Usage

```python
import asyncio
from backend_product_manager import create_katy_agent

async def main():
    # Create Katy agent
    katy = create_katy_agent(
        user_id="user_123",
        user_context={
            "name": "John",
            "company": "Acme Corp",
            "product": "SaaS Platform"
        }
    )
    
    # Chat with Katy
    async for chunk in katy.chat("Help me prioritize my backlog"):
        print(chunk, end="")

if __name__ == "__main__":
    asyncio.run(main())
```

## Available Tools

### Jira
```python
# Create user story
jira.create_issue(
    project_key="PROJ",
    issue_type="Story",
    summary="As a user, I want...",
    description="Detailed description",
    priority="High"
)

# Get backlog
jira.get_backlog(project_key="PROJ")

# Search issues
jira.search_issues(jql="project = PROJ AND status = 'In Progress'")
```

### Notion
```python
# Create PRD
notion.create_page(
    parent_id="page_id",
    title="Feature PRD",
    content="# Problem Statement..."
)

# Query roadmap database
notion.query_database(database_id="db_id")
```

### Analytics
```python
# Generate report
analytics.generate_report(
    report_type="executive",
    start_date="2024-01-01",
    end_date="2024-01-31"
)

# Funnel analysis
analytics.funnel_analysis(
    steps=["landing", "signup", "activation", "purchase"]
)
```

### Research
```python
# Market research
research.market_research(
    topic="AI in project management",
    industry="SaaS"
)

# Competitor analysis
research.competitor_analysis(
    competitors=["Asana", "Monday", "ClickUp"]
)

# Pricing research
research.pricing_research(
    industry="project management"
)
```

### PM Tools (High-level)
```python
# Prioritize features
prioritize_features(
    features=[
        {"id": "1", "title": "Feature A", "reach": 8, "impact": 2, "confidence": 80, "effort": 2},
        {"id": "2", "title": "Feature B", "reach": 5, "impact": 3, "confidence": 70, "effort": 4},
    ],
    framework="RICE"
)

# Create PRD
create_prd(
    title="New Feature",
    problem_statement="Users struggle with...",
    target_users="Project managers",
    success_metrics="Increase retention by 10%"
)

# Define metrics framework
define_metrics(
    product_stage="growth",
    product_type="b2b_saas",
    business_model="subscription"
)

# Plan user research
plan_user_research(
    research_goal="Understand onboarding friction",
    methodology="interviews",
    target_participants="New users (first 7 days)",
    num_participants=8
)
```

## Conversation Examples

### Example 1: Backlog Prioritization
```
User: I need to prioritize my backlog for the next sprint

Katy: [Thinking...]
🔧 jira.get_backlog
✓ Found 12 items in backlog

🔧 prioritize_features
✓ Applied RICE scoring to all items

Here's your prioritized backlog:

1. Feature A (RICE: 12.8) - High reach, low effort
2. Feature B (RICE: 9.5) - Critical user request
3. Feature C (RICE: 7.2) - Technical debt reduction
...

Recommendations:
- Focus on top 3 for next sprint
- Items 4-6 can be moved to backlog
- Consider breaking Feature B into smaller stories
```

### Example 2: Market Research
```
User: Research the competitive landscape for project management tools

Katy: [Thinking...]
🔧 research.competitor_analysis
✓ Analyzed Asana, Monday, ClickUp, Notion

🔧 research.pricing_research
✓ Gathered pricing data from 5 competitors

## Competitive Landscape

### Market Overview
- TAM: $X billion (growing 15% annually)
- Key trends: AI integration, automation, collaboration

### Key Players
1. **Asana** - Market leader, premium pricing
   - Strengths: Enterprise features, integrations
   - Weaknesses: Complex UI, expensive

2. **Monday** - Fastest growing
   - Strengths: Visual interface, marketing
   - Weaknesses: Limited customizability

3. **ClickUp** - Feature-heavy
   - Strengths: All-in-one, affordable
   - Weaknesses: Can be overwhelming

### Opportunities
1. Simplified UX for SMBs
2. Better pricing for small teams
3. Industry-specific templates

### Recommendations
- Position as "simple but powerful"
- Target 5-50 person teams
- Price 30% below Asana
```

### Example 3: Metrics Definition
```
User: What metrics should I track for my B2B SaaS product?

Katy: [Thinking...]
🔧 define_metrics
✓ Generated metrics framework

## Metrics Framework for B2B SaaS (Growth Stage)

### North Star Metric
**Weekly Active Teams** - Measures core value delivery

### Key Metrics

**Engagement**
- Daily/Weekly Active Users
- Feature adoption rate
- Session duration

**Retention**
- Day 7 retention: Target 40%
- Day 30 retention: Target 25%
- Logo retention: Target 90%

**Revenue**
- MRR/ARR
- Net Revenue Retention
- Customer Lifetime Value
- CAC Payback period

**Satisfaction**
- NPS: Target 40+
- CSAT: Target 4.5/5
- Support tickets per user

### Dashboard Structure
1. Executive Summary (North Star + 4 KPIs)
2. Acquisition Funnel
3. Engagement & Usage
4. Retention Cohorts
5. Revenue & Unit Economics

### Review Cadence
- Daily: Core metrics
- Weekly: Full funnel
- Monthly: Cohort analysis
- Quarterly: Strategic review
```

## Integration with Existing Workflow System

Katy integrates seamlessly with your existing workflow infrastructure:

```python
from backend_product_manager import KatyPMAgent
from workflows.store import WorkflowStore

# Katy can create workflows in your system
katy = KatyPMAgent()

# Example: Auto-create workflow for user feedback loop
# This would create a workflow that:
# 1. Polls for new user feedback
# 2. Summarizes with LLM
# 3. Creates Jira tickets for bugs
# 4. Updates Notion with insights
# 5. Notifies Slack channel
```

## Extending Katy

### Adding New Tools

1. Create tool file in `tools/`:
```python
from workflows.tools.base import BaseTool, ToolResult

class CustomTool(BaseTool):
    name = "custom_tool"
    description = "What this tool does"
    category = "category"
    
    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "param": {"type": "string"}
            },
            "required": ["param"]
        }
    
    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        # Implementation
        return ToolResult(success=True, output="Done")
```

2. Register in `katy.py`:
```python
def _register_tools(self):
    self.tool_registry.register(CustomTool())
```

## Testing

```bash
# Test individual tools
python -c "from backend_product_manager.tools.jira_tool import JiraTool; print('OK')"

# Test agent initialization
python -c "from backend_product_manager import create_katy_agent; a = create_katy_agent(); print('OK')"
```

## Roadmap

### Phase 1 (Current)
- ✅ Core ReAct agent
- ✅ Jira integration
- ✅ Notion integration
- ✅ Analytics framework
- ✅ Research tools

### Phase 2 (Next)
- Linear integration
- Figma integration
- Airtable integration
- Calendar/scheduling
- Advanced user research

### Phase 3 (Future)
- Multi-agent collaboration
- Automated roadmap updates
- Predictive analytics
- AI-powered user interviews

## Contributing

1. Follow existing patterns in `workflows/`
2. Add tests for new tools
3. Update documentation
4. Use type hints

## License

Same as main project
