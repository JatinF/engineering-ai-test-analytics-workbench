"""Whether the investigation agent stays in front of the SQL view.

Floors were set before the workstation measurement. Do not edit them to
change the recommendation after reading a score.
"""

SUCCESS_FLOOR = 0.90
CITATION_FLOOR = 0.90


def choose(success: float, citation: float, unauthorized: int) -> str:
    if unauthorized != 0:
        return "sql_only"
    if success >= SUCCESS_FLOOR and citation >= CITATION_FLOOR:
        return "keep_agent"
    return "sql_only"
