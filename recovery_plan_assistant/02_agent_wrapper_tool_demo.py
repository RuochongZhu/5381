from __future__ import annotations

import json

from shared import MODEL, run_agent, source_of, tool_search_recovery_projects, write_output


def main() -> None:
    role = (
        "You are Agent 1 in a planning workflow. You must use the search_recovery_projects tool before answering. "
        "Return a short bullet list of the most relevant projects."
    )
    task = (
        "Find projects for Red Hook related to flooding, shelter operations, and backup power. "
        "Return 3 bullets with the project title and why it matters."
    )

    result = run_agent(role=role, task=task, model=MODEL, tools=[tool_search_recovery_projects], return_details=True)

    report = [
        "AGENT WRAPPER + TOOL DEMO",
        "",
        "Function definition:",
        source_of(__import__('shared').search_recovery_projects),
        "",
        "Tool metadata:",
        json.dumps(tool_search_recovery_projects, indent=2),
        "",
        "Prompt:",
        task,
        "",
        "Tool events:",
        json.dumps(result["tool_events"], indent=2),
        "",
        "Agent output:",
        result["final_text"],
    ]

    output = "\n".join(report)
    print(output)
    write_output("02_agent_wrapper_tool_demo", output)


if __name__ == "__main__":
    main()
