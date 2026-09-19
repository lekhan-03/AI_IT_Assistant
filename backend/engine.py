"""
IT Support Triage Engine
=========================

Design philosophy
------------------
A support triage tool has to be *trustworthy*, not just clever. If an LLM
hallucinates a category or invents a "likely cause" from a two-line ticket,
it can send an engineer down the wrong path and waste more time than it
saves. So this engine is built as two cooperating layers:

1. A deterministic RULE ENGINE (this file's `RuleEngine` class). It looks at
   the literal text of the ticket -- keywords, phrasing, signals like
   "call in 20 minutes" -- and produces a category, a priority, a list of
   concretely missing facts, a next troubleshooting step and a plain-English
   reason. It is fully explainable: every decision can be traced back to a
   rule. It also decides when the ticket is too vague to safely proceed,
   in which case it asks ONE targeted follow-up question instead of
   guessing.

2. An optional LLM LAYER (`LLMEngine`, using the Anthropic API) that takes
   over when an API key is configured. It gets a structured system prompt,
   few-shot examples derived from the same rules, and is instructed to
   follow the *same* policy: only recommend a concrete next step when it
   is reasonably confident, otherwise ask a follow-up question rather than
   guess. Its output is validated against the same schema the rule engine
   produces, and if it ever returns something malformed, we silently fall
   back to the rule engine so the app never breaks.

This means the app works immediately with zero configuration (rule engine
only) and gets smarter/more nuanced the moment an ANTHROPIC_API_KEY is
supplied, without changing the contract the frontend depends on.
"""

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional
from rag import SimpleRAG

CATEGORIES = ["Network", "Account", "Application", "Device", "Other"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]


@dataclass
class TriageResult:
    category: str
    priority: str
    missing_info: List[str] = field(default_factory=list)
    next_step: str = ""
    reasoning: str = ""
    needs_followup: bool = False
    follow_up_question: Optional[str] = None
    kb_reference: Optional[str] = None
    confidence: str = "medium"          # low | medium | high
    engine: str = "rules"               # "rules" or "llm"

    def to_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# Signal dictionaries used by the rule engine. Kept simple and readable on
# purpose -- a real deployment would tune these against historical tickets.
# ---------------------------------------------------------------------------

CATEGORY_SIGNALS = {
    # Each signal is (keyword, weight). Weight lets a strong, specific
    # symptom (e.g. "slow", "crash") outweigh a merely-mentioned app name
    # that is just context (e.g. "Outlook" named as one of the open apps
    # on an otherwise-generic slow-laptop ticket).
    "Network": [
        ("wifi", 2), ("wi-fi", 2), ("internet", 2), ("vpn", 2), ("network", 2),
        ("connect", 1.5), ("connection", 1.5), ("offline", 2),
        ("can't access", 2), ("cannot access", 2), ("dns", 2), ("no signal", 2),
        ("ethernet", 2), ("router", 2), ("can't reach", 2), ("unreachable", 2),
    ],
    "Account": [
        ("password", 2), ("login", 1.5), ("log in", 1.5), ("locked out", 2),
        ("mfa", 2), ("2fa", 2), ("authenticat", 2), ("credential", 2),
        ("username", 1.5), ("account", 1), ("reset my", 2),
        ("access denied", 2), ("sign in", 1.5), ("signed out", 1.5),
    ],
    "Application": [
        # Bare app names are weak signals on their own (an app can just be
        # "open" without being the problem); explicit failure language is strong.
        ("outlook", 0.5), ("teams", 0.5), ("excel", 0.5), ("word", 0.5),
        ("application", 1.5), ("crash", 2), ("error message", 2),
        ("won't open", 2), ("not opening", 2), ("freezing", 2), ("freezes", 2),
        ("not responding", 2), ("update failed", 2),
    ],
    "Device": [
        ("laptop", 1), ("computer", 1), ("pc ", 1), ("slow", 2.5),
        ("battery", 2), ("screen", 1.5), ("keyboard", 1.5), ("hardware", 2),
        ("overheating", 2), ("won't turn on", 2.5), ("not booting", 2.5),
        ("shutting down", 2), ("fan noise", 2), ("blue screen", 2.5), ("bsod", 2.5),
    ],
}

URGENCY_SIGNALS_CRITICAL = [
    "client call", "meeting in", "call in", "presentation in", "demo in",
    "production is down", "entire team", "whole team", "everyone is affected",
    "cannot work at all", "completely down", "urgent", "asap", "right now",
]

URGENCY_SIGNALS_HIGH = [
    "can't work", "cannot work", "blocked", "deadline", "important",
    "multiple people", "several people", "today",
]

VAGUE_TICKET_MARKERS = [
    "internet is down", "it's not working", "nothing is working",
    "not working", "doesn't work", "broken", "down",
]

TIME_WINDOW_RE = re.compile(r"\b(\d{1,3})\s*(minute|min|hour|hr)s?\b", re.I)


class RuleEngine:
    """Deterministic, explainable triage logic."""

    def analyze(self, ticket_text: str, history: Optional[List[dict]] = None) -> TriageResult:
        history = history or []
        full_context = ticket_text + " " + " ".join(
            f"{h.get('question','')} {h.get('answer','')}" for h in history
        )
        text = full_context.lower()

        category, cat_hits = self._classify_category(text)
        priority, urgency_reason = self._classify_priority(text, ticket_text)
        missing = self._find_missing_info(text, category, history)

        # Decide if we have enough to give a confident recommendation.
        # Allow up to 3 follow-up questions to gather necessary information.
        too_many_turns = len(history) >= 3
        very_vague = len(ticket_text.strip()) < 60 and any(m in text for m in VAGUE_TICKET_MARKERS)
        should_ask = not too_many_turns and (very_vague or len(missing) >= 3)

        if should_ask:
            question = self._best_followup_question(category, missing, text)
            return TriageResult(
                category=category,
                priority=priority,
                missing_info=missing,
                next_step="Awaiting more information before recommending a troubleshooting step.",
                reasoning=(
                    f"The ticket text is too brief to safely diagnose (category signals point to "
                    f"'{category}', but {len(missing)} key detail(s) are missing: "
                    f"{', '.join(missing) if missing else 'scope and impact'}). "
                    "Rather than guess a fix, the assistant is asking a targeted clarifying "
                    "question first."
                ),
                needs_followup=True,
                follow_up_question=question,
                confidence="low",
                engine="rules",
            )

        next_step, reasoning = self._recommend_next_step(category, text, urgency_reason)
        confidence = "high" if not missing else ("medium" if len(missing) <= 2 else "low")

        return TriageResult(
            category=category,
            priority=priority,
            missing_info=missing,
            next_step=next_step,
            reasoning=reasoning,
            needs_followup=False,
            follow_up_question=None,
            confidence=confidence,
            engine="rules",
        )

    # -- classification helpers -------------------------------------------------

    def _classify_category(self, text: str):
        scores = {cat: 0.0 for cat in CATEGORY_SIGNALS}
        for cat, signals in CATEGORY_SIGNALS.items():
            for sig, weight in signals:
                if sig in text:
                    scores[cat] += weight
        best_cat = max(scores, key=scores.get)
        if scores[best_cat] == 0:
            return "Other", 0
        return best_cat, scores[best_cat]

    def _classify_priority(self, text: str, raw_text: str):
        # Explicit short time window ("20 minutes") strongly implies urgency.
        m = TIME_WINDOW_RE.search(raw_text)
        has_tight_deadline = False
        if m:
            qty, unit = int(m.group(1)), m.group(2).lower()
            minutes = qty if "min" in unit else qty * 60
            if minutes <= 60:
                has_tight_deadline = True

        if has_tight_deadline or any(s in text for s in URGENCY_SIGNALS_CRITICAL):
            return "Critical", "a near-term deadline or organisation-wide impact was mentioned"
        if any(s in text for s in URGENCY_SIGNALS_HIGH):
            return "High", "the user indicated they are blocked or under time pressure"
        # Multiple simultaneous symptoms (e.g. network + app both broken) raise priority.
        cat_count = sum(1 for cat, sigs in CATEGORY_SIGNALS.items() if any(s in text for s, _w in sigs))
        if cat_count >= 2:
            return "High", "multiple systems appear to be affected simultaneously"
        return "Medium", "no explicit urgency or deadline was mentioned"

    def _find_missing_info(self, text: str, category: str, history: List[dict]):
        answered = " ".join(f"{h.get('question','')} {h.get('answer','')}" for h in history).lower()
        missing = []

        def not_covered(*keywords):
            return not any(k in text for k in keywords)

        # Universal facts useful for almost any ticket
        if not_covered("since", "this morning", "started", "began", "after i", "yesterday", "today"):
            missing.append("When the issue started / what changed right before it began")

        if not_covered("only me", "everyone", "team", "just me", "other people", "colleagues"):
            missing.append("Whether this affects only this user or other people too")

        # Category-specific facts
        if category == "Network":
            if not_covered("wired", "wifi", "wi-fi", "ethernet", "vpn"):
                missing.append("Connection type (Wi-Fi, Ethernet, VPN) and whether other devices on the same network are affected")
            if not_covered("error", "message", "code"):
                missing.append("Any specific error message shown")
        elif category == "Account":
            if not_covered("outlook", "windows", "vpn", "which app", "laptop login", "portal"):
                missing.append("Which specific system(s) reject the credentials (Windows login, Outlook, VPN, a web portal, etc.)")
            if not_covered("error", "message", "locked", "denied"):
                missing.append("The exact error message or behavior when logging in")
        elif category == "Application":
            if not_covered("error", "message", "crash", "code"):
                missing.append("The exact error message, or what happens when the app is opened")
            if not_covered("version", "update", "reinstall"):
                missing.append("Whether the application was recently updated or reinstalled")
        elif category == "Device":
            if not_covered("model", "laptop model", "age", "battery", "plugged"):
                missing.append("Device model/age and whether it's plugged in or on battery")
            if not_covered("cpu", "task manager", "processes", "programs open"):
                missing.append("What programs are running / resource usage (e.g. Task Manager)")
        else:  # Other
            missing.append("More detail on what the user was doing when the issue occurred")

        # Remove anything the history has already answered (rough heuristic)
        missing = [m for m in missing if not self._roughly_answered(m, answered)]
        return missing[:4]

    def _roughly_answered(self, missing_item: str, answered_text: str) -> bool:
        if not answered_text:
            return False
        key_words = [w.lower() for w in re.findall(r"[a-zA-Z]{4,}", missing_item)][:3]
        return any(w in answered_text for w in key_words)

    def _best_followup_question(self, category: str, missing: List[str], text: str) -> str:
        if missing:
            item = missing[0]
            templates = {
                "Network": "Could you tell me: is this affecting just your device, or others nearby too, and is it Wi-Fi or a wired connection?",
                "Account": "Which system is rejecting your login exactly (Windows, Outlook, VPN, a web portal) and what message do you see?",
                "Application": "What error message (if any) appears, and did this start right after an update or reinstall?",
                "Device": "Since when has it been slow, and what programs do you currently have open?",
                "Other": "Could you describe a bit more about what you were doing when this happened, and any error messages you saw?",
            }
            return templates.get(category, f"Could you clarify: {item}?")
        return "Could you share a bit more detail about when this started and who else is affected?"

    def _recommend_next_step(self, category: str, text: str, urgency_reason: str):
        if category == "Network":
            if "vpn" in text:
                step = "Ask the user to disconnect and reconnect the VPN client; if that fails, verify VPN server status and check for a saved/expired VPN credential."
            else:
                step = ("Ask the user to run a basic connectivity check (ping 8.8.8.8, check if other devices on the "
                        "same network also can't reach the internet). If only this device is affected, restart the "
                        "network adapter / reboot the machine; if the whole floor/site is affected, escalate to "
                        "network infrastructure as a site-wide outage.")
            reasoning = (f"Signals in the ticket point to a network connectivity issue. Priority is set based on "
                         f"{urgency_reason}. The next step separates a single-device problem from a wider outage, "
                         f"which determines whether this stays with L1 support or escalates to network infrastructure.")
        elif category == "Account":
            if "changed" in text and "password" in text:
                step = ("Likely cause: apps with a cached/saved credential (commonly Outlook, VPN clients, mapped "
                        "drives) are still using the OLD password. Have the user update the stored credential in "
                        "Windows Credential Manager and re-enter the new password in Outlook when prompted, rather "
                        "than resetting the password again.")
            else:
                step = "Verify the account isn't locked in the identity provider/AD, then guide the user through a supervised password reset or MFA re-registration."
            reasoning = (f"The wording indicates a login/authentication problem rather than the underlying app being "
                         f"broken. Priority reflects that {urgency_reason}. Diagnosing 'stale saved credentials' vs. "
                         f"'account actually locked' first avoids an unnecessary full password reset.")
        elif category == "Application":
            step = ("Ask the user for the exact error text or a screenshot, then try: restart the application, "
                    "clear its cache/temp profile if applicable, and check whether the issue is limited to one "
                    "app or affects several (which would point back to a system-level cause instead).")
            reasoning = (f"The ticket centers on a specific application misbehaving. Priority reflects that "
                         f"{urgency_reason}. Capturing the exact error first prevents wasted troubleshooting on the "
                         f"wrong root cause.")
        elif category == "Device":
            step = ("Have the user open Task Manager to identify what's consuming CPU/RAM/disk, check for pending "
                    "OS/driver updates running in the background, and reboot the machine if it hasn't been restarted "
                    "recently. Escalate to hardware diagnostics if the slowness persists after a clean reboot.")
            reasoning = (f"Symptoms describe the device itself underperforming rather than a specific app or "
                         f"network resource. Priority reflects that {urgency_reason}. Starting with resource usage "
                         f"is the fastest way to distinguish a software/background-process cause from real hardware "
                         f"degradation.")
        else:
            step = "Gather more detail from the user (screenshots, exact wording, timeline) before assigning to a specialist queue."
            reasoning = f"The request doesn't clearly match Network, Account, Application or Device. Priority reflects that {urgency_reason}."
        return step, reasoning


# ---------------------------------------------------------------------------
# Optional LLM layer (Multi-Model Support)
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an IT triage assistant. Help humans triage tickets.
<company_knowledge> has fixes. If used, set kb_reference to ID.
- Vague tickets: needs_followup=true, ask ONE concise question, confidence="low". No fake root causes. Do NOT overwhelm with multiple questions.
- Clear tickets: needs_followup=false, provide actionable next_step.
- Priority: weigh technical severity & business impact.
- Keep reasoning brief & honest. If unsure, Category="Other"."""

class BaseLLMEngine:
    def __init__(self):
        self.available = False
        self.rag = SimpleRAG()

    def analyze(self, ticket_text: str, history: Optional[List[dict]] = None) -> Optional[TriageResult]:
        raise NotImplementedError

    def synthesize(self, ticket_text: str, history: Optional[List[dict]], results: List[dict]) -> Optional[TriageResult]:
        return None

    def _build_prompt(self, ticket_text: str, history: Optional[List[dict]]) -> str:
        history_block = ""
        if history:
            history = history[-2:]
            lines = [f"Q: {h.get('question','')}\nA: {h.get('answer','')}" for h in history]
            history_block = "\n\nFollow-up so far:\n" + "\n".join(lines)
        user_msg = f"Support ticket:\n\"\"\"{ticket_text}\"\"\"{history_block}"
        
        context_articles = self.rag.search(ticket_text + " " + history_block, top_k=1)
        if context_articles:
            kb_text = "\n\n".join(f"ID: {a.get('id', '')}\nTitle: {a.get('title', '')}\nContent: {a.get('content', '')}" for a in context_articles)
            user_msg += f"\n\n<company_knowledge>\n{kb_text}\n</company_knowledge>\n"
        return user_msg

    def _validate(self, data: dict, engine_name: str) -> Optional[TriageResult]:
        try:
            category = data.get("category") if data.get("category") in CATEGORIES else "Other"
            priority = data.get("priority") if data.get("priority") in PRIORITIES else "Medium"
            missing = data.get("missing_info") or []
            if not isinstance(missing, list):
                missing = [str(missing)]
            next_step = str(data.get("next_step") or "").strip()
            reasoning = str(data.get("reasoning") or "").strip()
            needs_followup = bool(data.get("needs_followup", False))
            followup_q = data.get("follow_up_question")
            kb_reference = data.get("kb_reference")
            confidence = data.get("confidence") if data.get("confidence") in ("low", "medium", "high") else "medium"
            if not next_step and not needs_followup:
                return None
            return TriageResult(
                category=category,
                priority=priority,
                missing_info=[str(m) for m in missing][:5],
                next_step=next_step or "Awaiting more information before recommending a troubleshooting step.",
                reasoning=reasoning,
                needs_followup=needs_followup,
                follow_up_question=str(followup_q) if followup_q else None,
                kb_reference=str(kb_reference) if kb_reference else None,
                confidence=confidence,
                engine=engine_name,
            )
        except Exception:
            return None



class GeminiEngine(BaseLLMEngine):
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self.available = bool(self.api_key)
        self._client = None
        if self.available:
            try:
                from google import genai
                from google.genai import types
                import pydantic
                from typing import Optional, List
                self._client = genai.Client(api_key=self.api_key)
                
                class TriageSchema(pydantic.BaseModel):
                    category: str
                    priority: str
                    missing_info: List[str]
                    next_step: str
                    reasoning: str
                    needs_followup: bool
                    follow_up_question: Optional[str]
                    kb_reference: Optional[str]
                    confidence: str
                
                self.config = types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    response_schema=TriageSchema,
                )
            except ImportError:
                self.available = False

    def analyze(self, ticket_text: str, history: Optional[List[dict]] = None) -> Optional[TriageResult]:
        if not self.available or not self._client: return None
        user_msg = self._build_prompt(ticket_text, history)
        try:
            resp = self._client.models.generate_content(
                model='gemini-3.6-flash',
                contents=user_msg,
                config=self.config
            )
            import json
            data = json.loads(resp.text)
            return self._validate(data, "llm (gemini)")
        except Exception:
            return None

    def synthesize(self, ticket_text: str, history: Optional[List[dict]], results: List[dict]) -> Optional[TriageResult]:
        if not self.available or not self._client: return None
        
        history_block = ""
        if history:
            history = history[-2:]
            lines = [f"Q: {h.get('question','')}\nA: {h.get('answer','')}" for h in history]
            history_block = "\n\nFollow-up so far:\n" + "\n".join(lines)
            
        import json
        minified_results = [{k: v for k, v in r.items() if k not in ['reasoning', 'engine']} for r in results]
        proposals_str = json.dumps(minified_results, separators=(',', ':'))
        
        user_msg = f"Original Ticket:\n\"\"\"{ticket_text}\"\"\"{history_block}\n\nHere are multiple AI triage proposals:\n{proposals_str}\n\nSynthesize these into a single, master triage result that picks the best insights, corrects any hallucinations, and combines missing info. If the ticket is vague, ensure the follow_up_question is exactly ONE concise, highly-targeted question that addresses the most critical missing information. Do NOT overwhelm the user with a list of questions."
        
        try:
            resp = self._client.models.generate_content(
                model='gemini-3.6-flash',
                contents=user_msg,
                config=self.config
            )
            data = json.loads(resp.text)
            return self._validate(data, "llm (consensus)")
        except Exception:
            return None


class GroqEngine(BaseLLMEngine):
    def __init__(self):
        super().__init__()
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.available = bool(self.api_key)
        self._client = None
        if self.available:
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
            except ImportError:
                self.available = False
                
        self.tool = {
            "type": "function",
            "function": {
                "name": "submit_triage_result",
                "description": "Submit the final triage result.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": CATEGORIES},
                        "priority": {"type": "string", "enum": PRIORITIES},
                        "missing_info": {"type": "array", "items": {"type": "string"}},
                        "next_step": {"type": "string"},
                        "reasoning": {"type": "string"},
                        "needs_followup": {"type": "boolean"},
                        "follow_up_question": {"type": ["string", "null"]},
                        "kb_reference": {"type": ["string", "null"]},
                        "confidence": {"type": "string", "enum": ["low", "medium", "high"]}
                    },
                    "required": ["category", "priority", "missing_info", "next_step", "reasoning", "needs_followup", "confidence"]
                }
            }
        }

    def analyze(self, ticket_text: str, history: Optional[List[dict]] = None) -> Optional[TriageResult]:
        if not self.available or not self._client: return None
        user_msg = self._build_prompt(ticket_text, history)
        try:
            resp = self._client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg}
                ],
                tools=[self.tool],
                tool_choice={"type": "function", "function": {"name": "submit_triage_result"}}
            )
            tool_call = resp.choices[0].message.tool_calls[0]
            import json
            data = json.loads(tool_call.function.arguments)
            return self._validate(data, "llm (groq)")
        except Exception:
            return None


import concurrent.futures

class TriageService:
    """Public entry point used by the Flask app. Dispatches requests to all available
    LLM engines simultaneously. Falls back to the deterministic rule engine on failure."""

    def __init__(self):
        self.rules = RuleEngine()
        self.engines = self._init_engines()

    def _init_engines(self) -> List[BaseLLMEngine]:
        available = []
        for eng_class in [GeminiEngine, GroqEngine]:
            eng = eng_class()
            if eng.available:
                available.append(eng)
        return available

    def triage(self, ticket_text: str, history: Optional[List[dict]] = None) -> dict:
        ticket_text = (ticket_text or "").strip()
        history = history or []
        
        if not ticket_text:
            res = TriageResult(
                category="Other", priority="Low", missing_info=["The ticket text itself"],
                next_step="Awaiting the user's description of the issue.",
                reasoning="No ticket text was provided.",
                needs_followup=True,
                follow_up_question="Could you describe the issue you're experiencing?",
                kb_reference=None, confidence="low", engine="rules",
            )
            return {"results": [res.to_dict()]}

        if not self.engines:
            return {"results": [self.rules.analyze(ticket_text, history).to_dict()]}

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(self.engines)) as executor:
            future_to_engine = {executor.submit(eng.analyze, ticket_text, history): eng for eng in self.engines}
            for future in concurrent.futures.as_completed(future_to_engine):
                res = future.result()
                if res:
                    results.append(res.to_dict())
                    
        if len(results) > 1:
            for eng in self.engines:
                syn = eng.synthesize(ticket_text, history, results)
                if syn:
                    return {"results": [syn.to_dict()]}
            conf_scores = {"high": 3, "medium": 2, "low": 1}
            results.sort(key=lambda x: conf_scores.get(x.get("confidence", "low"), 0), reverse=True)
            results = [results[0]]
                    
        # If all LLMs failed, fallback to rules
        if not results:
            results.append(self.rules.analyze(ticket_text, history).to_dict())
            
        return {"results": results}

    @property
    def mode(self) -> str:
        if self.engines:
            names = [e.__class__.__name__.replace('Engine', '').lower() for e in self.engines]
            return f"panel of experts ({', '.join(names)})"
        return "rules-only"
