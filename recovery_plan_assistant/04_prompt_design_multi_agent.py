from __future__ import annotations

from shared import MODEL, load_projects, run_agent, write_output


def main() -> None:
    df = load_projects()
    long_beach = df[df["community"].isin(["Long Beach", "Lower Manhattan", "Broad Channel"])].head(4)
    project_table = long_beach.to_markdown(index=False)

    agent1_role = (
        "You are a risk analyst. Return exactly 3 bullets that identify the most important planning problems in the table."
    )
    agent1_task = f"Analyze these recovery projects:\n\n{project_table}"
    agent1 = run_agent(role=agent1_role, task=agent1_task, model=MODEL, return_details=True)

    agent2_role = (
        "You are a strategy agent. Convert the analyst's bullets into a ranked action list with Rank 1-3 and one sentence each."
    )
    agent2_task = f"Analyst notes:\n\n{agent1['final_text']}"
    agent2 = run_agent(role=agent2_role, task=agent2_task, model=MODEL, return_details=True)

    agent3_role = (
        "You are a communications agent. Turn the ranked actions into a short public update with a title and 2 short paragraphs."
    )
    agent3_task = f"Strategy notes:\n\n{agent2['final_text']}"
    agent3 = run_agent(role=agent3_role, task=agent3_task, model=MODEL, return_details=True)

    report = [
        "PROMPT DESIGN MULTI-AGENT WORKFLOW",
        "",
        "Input table:",
        project_table,
        "",
        "Agent 1 output:",
        agent1["final_text"],
        "",
        "Agent 2 output:",
        agent2["final_text"],
        "",
        "Agent 3 output:",
        agent3["final_text"],
    ]

    output = "\n".join(report)
    print(output)
    write_output("04_prompt_design_multi_agent", output)


if __name__ == "__main__":
    main()
