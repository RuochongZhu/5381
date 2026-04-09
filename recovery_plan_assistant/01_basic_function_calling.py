from __future__ import annotations

import json

from shared import MODEL, run_agent, source_of, tool_calculate_priority_score, write_output


def main() -> None:
    role = (
        "You are a planning assistant. Use the available tool for all numeric scoring tasks. "
        "After the tool call, explain the result in 2 short sentences."
    )
    task = (
        "Evaluate a flood barrier project with impact 5, feasibility 4, and urgency 5. "
        "Use the tool first, then explain whether it should be funded soon."
    )

    result = run_agent(role=role, task=task, model=MODEL, tools=[tool_calculate_priority_score], return_details=True)

    report = [
        "BASIC FUNCTION CALLING DEMO",
        "",
        "Function definition:",
        source_of(__import__('shared').calculate_priority_score),
        "",
        "Tool metadata:",
        json.dumps(tool_calculate_priority_score, indent=2),
        "",
        "Prompt:",
        task,
        "",
        "Tool events:",
        json.dumps(result["tool_events"], indent=2),
        "",
        "Final response:",
        result["final_text"],
    ]

    output = "\n".join(report)
    print(output)
    write_output("01_basic_function_calling", output)


if __name__ == "__main__":
    main()
