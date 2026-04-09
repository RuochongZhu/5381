from __future__ import annotations

import json

from shared import MODEL, run_agent, tool_search_recovery_projects, tool_summarize_sector_counts, write_output


def main() -> None:
    agent1_role = (
        "You are a retrieval agent for a local recovery planning team. "
        "You must use the available tools before answering. "
        "Return an evidence brief with a heading and 3-4 bullets."
    )
    agent1_task = (
        "The team wants ideas for Red Hook that improve flood response, shelter reliability, and backup power. "
        "Use the tools to gather evidence, then summarize the best options."
    )
    agent1 = run_agent(
        role=agent1_role,
        task=agent1_task,
        model=MODEL,
        tools=[tool_search_recovery_projects, tool_summarize_sector_counts],
        return_details=True,
    )

    agent2_role = (
        "You are a planning memo writer. Read the evidence brief from Agent 1 and write a compact 1-paragraph memo "
        "with 2 recommended next steps."
    )
    agent2_task = (
        "Agent 1 evidence brief:\n\n"
        f"{agent1['final_text']}\n\n"
        "Write the memo in plain language for a city planning manager."
    )
    agent2 = run_agent(role=agent2_role, task=agent2_task, model=MODEL, return_details=True)

    report = [
        "MULTI-AGENT SYSTEM WITH TOOLS",
        "",
        "Agent 1 prompt:",
        agent1_task,
        "",
        "Agent 1 tool events:",
        json.dumps(agent1["tool_events"], indent=2),
        "",
        "Agent 1 output:",
        agent1["final_text"],
        "",
        "Agent 2 prompt:",
        agent2_task,
        "",
        "Agent 2 output:",
        agent2["final_text"],
    ]

    output = "\n".join(report)
    print(output)
    write_output("03_multi_agent_with_tools", output)


if __name__ == "__main__":
    main()
