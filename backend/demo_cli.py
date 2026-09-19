"""
Quick command-line demo: runs the five sample tickets from the brief
through the triage engine and prints the structured result for each.
Useful for verifying the logic without spinning up the web server.

Usage:
    python demo_cli.py
"""
import json
from engine import TriageService
from rag import SimpleRAG

SAMPLE_TICKETS = [
    "My laptop is connected to Wi-Fi but I can't access any websites. "
    "Teams isn't working either. I have a client call in 20 minutes.",

    "I changed my password this morning. I can log into my laptop but "
    "Outlook keeps asking me for my password.",

    "My laptop has become extremely slow since this morning. I only "
    "have Chrome, Outlook and Teams open.",

    "Nothing is connecting since I changed my password.",

    "The internet is down.",
    
    "I'm getting a 403 Forbidden error when trying to log into Salesforce with SSO.",
]


def main():
    svc = TriageService()
    rag = SimpleRAG()
    
    print(f"Engine mode: {svc.mode}\n{'=' * 60}\n")
    for i, ticket in enumerate(SAMPLE_TICKETS, 1):
        print(f"Ticket {i:02d}: {ticket}")
        
        # Showcase RAG Retrieval
        kb_matches = rag.search(ticket)
        if kb_matches:
            print("\n  [RAG Knowledge Base Hits]:")
            for match in kb_matches:
                print(f"  - {match['title']}")
        
        result = svc.triage(ticket, [])
        print(json.dumps(result, indent=2))
        
        # If any of the results needed follow up, mock asking it
        first_followup = next((r for r in result["results"] if r.get("needs_followup")), None)
        if first_followup:
            print(f"\n  -> Assistant would ask: \"{first_followup['follow_up_question']}\"")
            print("     (rather than guessing a fix from insufficient information)")
            
        print("\n" + "-"*60 + "\n")


if __name__ == "__main__":
    main()
