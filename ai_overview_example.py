"""Read the AI Overview and People Also Ask blocks from one Google query."""

from cse_to_serp import fetch_serp

page = fetch_serp({
    "q": "what is retrieval augmented generation",
    "gl": "us",
    "hl": "en",
    "brd_json": 1,
    "brd_ai_overview": 2,  # asks for the AI Overview block
})

overview = page.get("ai_overview") or {}
print("AI Overview text blocks:", len(overview.get("texts", [])))
print("AI Overview sources:", len(overview.get("references", [])))
questions = dict.fromkeys(
    item["question"] for item in page.get("people_also_ask", [])
    if item.get("question")
)
for question in list(questions)[:2]:
    print("People also ask:", question)
