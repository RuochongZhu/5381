from __future__ import annotations

import json

from shared import (
    MODEL,
    run_agent,
    tool_calculate_priority_score,
    tool_search_recovery_projects,
    tool_summarize_sector_counts,
    write_output,
)


def main() -> None:
    user_question = (
        "What should Red Hook prioritize if it wants to improve flood response and backup power for residents?"
    )

    agent1_role = (
        "You are the retrieval agent in a 3-agent workflow. "
        "You must call the available tools before answering. "
        "Return a markdown section called Evidence Brief with 3 project candidates. "
        "For each candidate, include project title, a one-sentence reason, and 1-5 ratings for impact, feasibility, and urgency."
    )
    agent1_task = (
        f"User question: {user_question}\n"
        "Focus on Red Hook and use the tools to gather evidence before writing."
    )
    agent1 = run_agent(
        role=agent1_role,
        task=agent1_task,
        model=MODEL,
        tools=[tool_search_recovery_projects, tool_summarize_sector_counts],
        return_details=True,
    )

    agent2_role = (
        "You are the scoring agent. For every candidate in the user's brief, call calculate_priority_score using the provided "
        "impact, feasibility, and urgency values. Then return a markdown table with columns Project, Score, and Priority Label."
    )
    agent2_task = f"Candidate brief from Agent 1:\n\n{agent1['final_text']}"
    agent2 = run_agent(
        role=agent2_role,
        task=agent2_task,
        model=MODEL,
        tools=[tool_calculate_priority_score],
        return_details=True,
    )

    agent3_role = (
        "You are the final briefing agent. Combine the evidence brief and scoring table into a concise executive summary "
        "with a title, a 3-sentence summary, and 3 action bullets."
    )
    agent3_task = (
        f"Original question: {user_question}\n\n"
        f"Agent 1 evidence:\n{agent1['final_text']}\n\n"
        f"Agent 2 scoring table:\n{agent2['final_text']}"
    )
    agent3 = run_agent(role=agent3_role, task=agent3_task, model=MODEL, return_details=True)

    report = [
        "FINAL AI AGENT SYSTEM WITH RAG AND TOOLS",
        "",
        f"User question: {user_question}",
        "",
        "Agent 1 tool events:",
        json.dumps(agent1["tool_events"], indent=2),
        "",
        "Agent 1 output:",
        agent1["final_text"],
        "",
        "Agent 2 tool events:",
        json.dumps(agent2["tool_events"], indent=2),
        "",
        "Agent 2 output:",
        agent2["final_text"],
        "",
        "Agent 3 output:",
        agent3["final_text"],
    ]

    output = "\n".join(report)
    print(output)
    write_output("06_final_ai_agent_system", output)


if __name__ == "__main__":
    main()
