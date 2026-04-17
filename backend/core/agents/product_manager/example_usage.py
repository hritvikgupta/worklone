"""
Example usage of Katy - AI Product Manager Agent

This file demonstrates how to use Katy for various product management tasks.
"""

import asyncio
import os
from backend_product_manager import create_katy_agent


async def example_1_simple_chat():
    """Example 1: Simple conversation without tools."""
    print("=" * 60)
    print("Example 1: Simple Chat")
    print("=" * 60)
    
    katy = create_katy_agent(
        user_id="demo_user",
        user_context={
            "name": "Alice",
            "role": "Product Lead",
            "company": "TechCorp"
        }
    )
    
    message = "What are the key responsibilities of a product manager?"
    print(f"\nUser: {message}\n")
    print("Katy: ", end="")
    
    async for chunk in katy.chat(message):
        print(chunk, end="")
    print("\n")


async def example_2_backlog_prioritization():
    """Example 2: Backlog prioritization with RICE framework."""
    print("=" * 60)
    print("Example 2: Feature Prioritization")
    print("=" * 60)
    
    katy = create_katy_agent(user_id="demo_user")
    
    message = """Help me prioritize these features using RICE scoring:
    
1. Feature A: Affects 1000 users, high impact (3), 80% confident, 2 person-months
2. Feature B: Affects 500 users, medium impact (1), 70% confident, 4 person-months  
3. Feature C: Affects 2000 users, low impact (0.5), 90% confident, 1 person-month
4. Feature D: Affects 300 users, massive impact (3), 60% confident, 6 person-months
"""
    
    print(f"\nUser: {message}\n")
    print("Katy: ", end="")
    
    async for chunk in katy.chat(message):
        print(chunk, end="")
    print("\n")


async def example_3_prd_creation():
    """Example 3: Creating a Product Requirements Document."""
    print("=" * 60)
    print("Example 3: PRD Creation")
    print("=" * 60)
    
    katy = create_katy_agent(user_id="demo_user")
    
    message = """Create a PRD for a new "Smart Notifications" feature.

Problem: Users are overwhelmed by notification noise and miss important updates.
Target users: Project managers and team leads
Success metrics: 20% increase in engagement, 15% reduction in notification fatigue
"""
    
    print(f"\nUser: {message}\n")
    print("Katy: ", end="")
    
    async for chunk in katy.chat(message):
        print(chunk, end="")
    print("\n")


async def example_4_metrics_framework():
    """Example 4: Defining metrics framework."""
    print("=" * 60)
    print("Example 4: Metrics Framework")
    print("=" * 60)
    
    katy = create_katy_agent(user_id="demo_user")
    
    message = "I'm building a B2B SaaS collaboration tool in the growth stage. What metrics should I track?"
    
    print(f"\nUser: {message}\n")
    print("Katy: ", end="")
    
    async for chunk in katy.chat(message):
        print(chunk, end="")
    print("\n")


async def example_5_competitive_analysis():
    """Example 5: Competitive analysis."""
    print("=" * 60)
    print("Example 5: Competitive Analysis")
    print("=" * 60)
    
    katy = create_katy_agent(user_id="demo_user")
    
    message = "Analyze the competitive landscape for team collaboration tools. Include Notion, Slack, and Microsoft Teams."
    
    print(f"\nUser: {message}\n")
    print("Katy: ", end="")
    
    async for chunk in katy.chat(message):
        print(chunk, end="")
    print("\n")


async def example_6_user_research_plan():
    """Example 6: Planning user research."""
    print("=" * 60)
    print("Example 6: User Research Plan")
    print("=" * 60)
    
    katy = create_katy_agent(user_id="demo_user")
    
    message = """Help me plan user interviews to understand why new users churn in their first week.

Target: Users who signed up but didn't return after day 1
I want to interview 8 people
"""
    
    print(f"\nUser: {message}\n")
    print("Katy: ", end="")
    
    async for chunk in katy.chat(message):
        print(chunk, end="")
    print("\n")


async def example_7_tool_usage():
    """Example 7: Direct tool usage (when credentials are configured)."""
    print("=" * 60)
    print("Example 7: Direct Tool Usage (requires credentials)")
    print("=" * 60)
    
    katy = create_katy_agent(user_id="demo_user")
    
    # Example: Using tools directly
    # This would require JIRA_BASE_URL, JIRA_API_TOKEN, etc. to be set
    
    message = "Show me my Jira projects"
    
    print(f"\nUser: {message}\n")
    print("Katy: ", end="")
    
    async for chunk in katy.chat(message):
        print(chunk, end="")
    print("\n")
    
    print("\nNote: This requires Jira credentials to be configured in environment variables.")


async def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("KATY - AI Product Manager Agent Demo")
    print("=" * 60 + "\n")
    
    # Run examples that don't require credentials
    await example_1_simple_chat()
    await example_2_backlog_prioritization()
    await example_3_prd_creation()
    await example_4_metrics_framework()
    await example_5_competitive_analysis()
    await example_6_user_research_plan()
    
    # Example requiring credentials
    # await example_7_tool_usage()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
