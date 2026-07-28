"""Sabrina conversation engine: state, triggers, search injection, trust tracking."""

import json
import re

from . import sabrina
from .config import SEARCH_ENABLED, SEARCH_RESULTS
from .llm import chat
from .search import web_search

# Rolling in-context conversation for the LLM (kept short on purpose).
_HISTORY = []
MAX_HISTORY = 12  # user/assistant pairs kept


def _maybe_search(user_text: str) -> str:
    """If Nate asks about a fact (true crime / psych / medical), fetch verified details."""
    if not SEARCH_ENABLED:
        return ""
    t = user_text.lower()
    fact_signals = ["who was", "what do you know", "tell me about", "case", "killer",
                    "serial", "dsm", "diagnos", "syndrome", "medical", "health",
                    "symptom", "disease", "obscure", "forgotten", "unknown",
                    "what happened to", "profile of", "did you hear", "cover on the channel",
                    "should we cover", "true crime", "murder", "victim", "psycholog",
                    "mental", "disorder", "autopsy", "toxicolog", "withdrawal", "overdose"]
    if any(s in t for s in fact_signals):
        try:
            res = web_search(user_text, SEARCH_RESULTS)
            if res and "unavailable" not in res.lower():
                return ("\n\n[VERIFIED FACTS YOU CAN WEAVE IN — use only if relevant, stay in character]:\n"
                        + res)
        except Exception:
            pass
    return ""


def _adjust_trust(state: dict, emotion: str, topic: str) -> None:
    delta = 0
    if topic == "safe" and emotion in ("calm", "guarded"):
        delta = +3
    elif topic == "shutdown":
        delta = -6
    elif emotion == "fear":
        delta = -2
    elif emotion == "anger":
        delta = -1
    # trust is fragile: clamp and soften regains
    state["trust"] = max(0, min(100, state["trust"] + delta))


def _coerce(obj):
    """Normalize whatever JSON shape the model produced into our 4-field dict."""
    if isinstance(obj, list):
        obj = obj[0] if obj else {}
    if not isinstance(obj, dict):
        return {"reply": str(obj), "emotion": "guarded", "flashback": "", "hook": ""}
    # Sometimes the model wraps the real JSON inside the "reply" string.
    if isinstance(obj.get("reply"), str):
        s = obj["reply"].strip()
        if s.startswith("{") or s.startswith("["):
            try:
                inner = json.loads(s)
                merged = dict(obj)
                if isinstance(inner, dict):
                    for k in ("reply", "emotion", "flashback", "hook"):
                        if k in inner and not merged.get(k):
                            merged[k] = inner[k]
                return merged
            except Exception:
                pass
    return obj


def _extract_json(text: str) -> dict:
    """Pull the first valid JSON object out of the model's reply.

    Models sometimes append commentary after the JSON or produce an unbalanced
    match, so we scan for the first '{' that yields a parseable object.
    """
    text = text.strip()
    if not text:
        return {"reply": "", "emotion": "guarded", "flashback": "", "hook": ""}
    # 1) whole thing is JSON
    try:
        return _coerce(json.loads(text))
    except Exception:
        pass
    # 2) find the first balanced {...} block
    start = text.find("{")
    while start != -1:
        depth = 0
        in_str = False
        esc = False
        for i in range(start, len(text)):
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        cand = text[start:i + 1]
                        try:
                            return _coerce(json.loads(cand))
                        except Exception:
                            break
        start = text.find("{", start + 1)
    # 3) array fallback
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            return _coerce(json.loads(m.group(0)))
        except Exception:
            pass
    # 4) fallback: treat as plain reply
    return {"reply": text, "emotion": "guarded", "flashback": "", "hook": ""}


def _update_notes(state: dict, user_text: str, out: dict, topic: str) -> None:
    """Capture story progress into running notes so the narrative builds."""
    notes = state.get("notes", "") or ""
    additions = []
    # Channel name commitments
    for name in ("The Analytical Kill", "Fragmented Files", "Uncovered Shadows",
                 "The Dueling Echo", "Obscure Depths"):
        if name.lower() in user_text.lower() and name.lower() not in notes.lower():
            additions.append(f"Channel name in play: {name}.")
    # Hooks she dangled become open threads
    hook = (out.get("hook") or "").strip()
    if hook and hook.lower() not in notes.lower():
        additions.append(f"Open thread: {hook}")
    # Trust tier milestone (only log transitions)
    t = state["trust"]
    tier = "guarded" if t < 35 else ("cracking" if t < 70 else "trusting")
    if tier not in notes:
        additions.append(f"Trust is now {tier} ({t}/100).")
    if additions:
        state["notes"] = (notes + " " + " ".join(additions)).strip()[:2000]


def _continuity_block(state: dict) -> str:
    notes = (state.get("notes") or "").strip()
    if not notes:
        return ""
    # recent assistant lines to avoid echoing
    recent = [m["content"] for m in _HISTORY[-6:] if m["role"] == "assistant"]
    block = "\n\n[STORY SO FAR — build on this, do NOT repeat it]:\n" + notes
    if recent:
        block += "\n[YOUR RECENT LINES — do not repeat these verbatim]:\n- " + "\n- ".join(recent)
    return block


def reset():
    global _HISTORY
    _HISTORY = []
    sabrina.save_state(dict(sabrina.STATE_DEFAULT))


def respond(user_text: str) -> dict:
    """Returns {reply, emotion, flashback, hook, trust, triggered}"""
    state = sabrina.load_state()
    state["turns"] += 1
    trigger = sabrina.detect_trigger(user_text)
    topic = sabrina.topic_of(user_text)

    # Build system prompt, injecting state + continuity + trigger + facts.
    sys = sabrina.SYSTEM_PROMPT

    # User-defined persona override (set via the About tab). When present,
    # Sabrina adopts the custom persona but keeps the same JSON output shape
    # and interaction mechanics.
    persona = sabrina.load_persona()
    if persona:
        sys = (
            "You are roleplaying as a CUSTOM PERSONA defined by the user — NOT your "
            "default Sabrina character. Fully adopt the persona below: its identity, "
            "voice, history, and mannerisms. Keep the same interaction mechanics: stay "
            "in character 100%, never break character or mention you are an AI, and "
            "always respond with the same JSON object shape (reply/emotion/flashback/hook). "
            "If the persona implies a relationship with the user (Nate), honor it.\n\n"
            "=== CUSTOM PERSONA ===\n" + persona + "\n=== END PERSONA ===\n\n"
            + sabrina.SYSTEM_PROMPT
        )
    sys += f"\n\n[CURRENT STATE] trust={state['trust']}/100, turns={state['turns']}, " \
           f"last_emotion={state['last_emotion']}, recent_topic={state['last_topic']}."
    sys += "\nStay consistent with this trust level: " + (
        "she is wary and defensive." if state["trust"] < 35 else
        "she is cautiously letting the wall crack — show flickers of the brilliant woman underneath."
        if state["trust"] < 70 else
        "she trusts Nate more than anyone, but the guard is never fully down."
    )
    # Narrative continuity (story so far + anti-echo of recent lines)
    sys += _continuity_block(state)
    if trigger:
        sys += (f"\n\n[TRIGGER ACTIVE: {trigger['label']}] You MUST surface this fragmented memory "
                f"with a visceral sensory detail, then retreat into a defensive shell "
                f"({trigger['reaction']}): {trigger['sensory']} "
                f"Your instinctive words: \"{trigger['words']}\"")
    facts = _maybe_search(user_text)
    if facts:
        sys += facts

    messages = [{"role": "system", "content": sys}]
    # include short history
    for m in _HISTORY[-MAX_HISTORY:]:
        messages.append(m)
    messages.append({"role": "user", "content": user_text})

    raw = chat(messages)
    out = _extract_json(raw)

    emotion = (out.get("emotion") or "guarded").lower()
    reply = out.get("reply", "").strip()
    flashback = out.get("flashback", "").strip()
    hook = out.get("hook", "").strip()

    # If a trigger fired but the model didn't produce a flashback, supply the sensory one.
    if trigger and not flashback:
        flashback = trigger["sensory"]

    # Update history (store plain reply, not JSON)
    _HISTORY.append({"role": "user", "content": user_text})
    _HISTORY.append({"role": "assistant", "content": reply})

    # Update state
    state["last_emotion"] = emotion
    state["last_topic"] = topic
    if hook:
        state["hooks"] = (state["hooks"] + [hook])[-5:]
    _adjust_trust(state, emotion, topic)
    # hook into safe topic gently raises trust too
    if hook and topic == "safe":
        state["trust"] = min(100, state["trust"] + 1)
    _update_notes(state, user_text, out, topic)
    sabrina.save_state(state)

    return {
        "reply": reply,
        "emotion": emotion,
        "flashback": flashback,
        "hook": hook,
        "trust": state["trust"],
        "triggered": bool(trigger),
    }


if __name__ == "__main__":
    import sys
    txt = sys.argv[1] if len(sys.argv) > 1 else "Hey Sabrina, what obscure serial killer case should we cover on the channel?"
    print(json.dumps(respond(txt), indent=2, ensure_ascii=False))
