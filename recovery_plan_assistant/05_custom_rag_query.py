from __future__ import annotations

from shared import MODEL, search_recovery_projects, run_agent, write_output


def main() -> None:
    query = "evacuation access flood barriers transit"
    retrieved = search_recovery_projects(query=query, community="", sector="Transportation", top_n=3)

    role = (
        "You are a retrieval-augmented planning assistant. Use only the retrieved JSON provided by the user. "
        "Write a 180-220 word answer in markdown with a title, a short summary, and a bullet list of recommended project references."
    )
    task = (
        "Question: Which transportation-focused recovery projects would be most relevant for evacuation access and flood barriers?\n\n"
        f"Retrieved records:\n{retrieved}"
    )
    result = run_agent(role=role, task=task, model=MODEL, return_details=True)

    report = [
        "CUSTOM RAG QUERY",
        "",
        "Search query:",
        query,
        "",
        "Retrieved records:",
        retrieved,
        "",
        "Generated answer:",
        result["final_text"],
    ]

    output = "\n".join(report)
    print(output)
    write_output("05_custom_rag_query", output)


if __name__ == "__main__":
    main()
