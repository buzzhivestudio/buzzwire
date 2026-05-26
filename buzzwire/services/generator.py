from __future__ import annotations

import re
from typing import Any

from buzzwire.services.text_utils import clean_text, first_sentence, title_case_soft


COMMON_TITLE_WORDS = {
    "The",
    "A",
    "An",
    "To",
    "For",
    "And",
    "Or",
    "In",
    "On",
    "Of",
    "With",
    "As",
    "At",
    "By",
    "From",
    "New",
    "News",
    "Why",
    "How",
    "This",
    "That",
    "These",
    "Those",
}

WEAK_ACTORS = {"new", "news", "story", "this", "that", "us", "uk"}


def _actor_from_title(title: str) -> str:
    title_lower = title.lower()
    actor_checks = [
        ("spacex", "SpaceX"),
        ("elon musk", "Elon Musk"),
        ("uk agrees", "The UK-Gulf Trade Deal"),
        ("gulf states", "The UK-Gulf Trade Deal"),
        ("fuel duty freeze", "The Fuel Duty Freeze"),
        ("google rejects", "Google's Union Fight"),
        ("union recognition", "Google's Union Fight"),
        ("smart glasses", "Google's Smart Glasses Comeback"),
        ("ai industry", "The AI Industry"),
        ("musk-altman", "The Musk-Altman Trial"),
        ("startup grant", "Karnataka's Startup Grant"),
        ("karnataka invites", "Karnataka's Startup Grant"),
        ("bihar cabinet", "Bihar's Air Route Push"),
        ("direct flight", "Bihar's Air Route Push"),
        ("roblox", "Roblox"),
        ("ubisoft", "Ubisoft"),
    ]
    for needle, actor in actor_checks:
        if needle in title_lower:
            return actor
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9&.-]*(?:\s+[A-Z][A-Za-z0-9&.-]*){0,2}", title)
    for candidate in candidates:
        words = candidate.split()
        cleaned = candidate.strip(" .,:;-")
        if words[0] not in COMMON_TITLE_WORDS and cleaned.lower() not in WEAK_ACTORS:
            return cleaned
    if "startup" in title_lower:
        return "Startups"
    if "ipo" in title_lower:
        return "The IPO"
    if "restructuring" in title_lower:
        return "The Restructuring"
    if "price" in title_lower:
        return "Pricing"
    for candidate in candidates:
        cleaned = candidate.strip(" .,:;-")
        if cleaned:
            return candidate.strip(" .,:;-")
    words = clean_text(title).split()
    return "This Move" if not words else " ".join(words[:2]).strip(" .,:;-")


def _topic_label(classification: dict[str, Any]) -> str:
    categories = classification.get("categories", [])
    if "domestic_politics" in categories:
        return "political debate"
    if "AI" in categories:
        return "AI"
    if "jobs" in categories:
        return "jobs"
    if "business" in categories:
        return "business"
    if "infrastructure" in categories:
        return "infrastructure"
    if "culture" in categories:
        return "culture"
    if "India" in categories:
        return "India"
    if "relationships" in categories:
        return "relationship"
    if "women" in categories:
        return "women"
    if categories:
        first = categories[0]
        if first != "general":
            return first
    return "trend"


def _is_domestic_politics(classification: dict[str, Any]) -> bool:
    return "domestic_politics" in classification.get("categories", [])


def _risk_notes(risk_level: str, classification: dict[str, Any] | None = None) -> str:
    if classification and _is_domestic_politics(classification):
        return (
            "High risk politics. Verify the source, attribute claims clearly, avoid taking sides, "
            "and remove inflammatory wording before approval."
        )
    if risk_level == "high":
        return "High risk. Verify source details, avoid accusations, and keep the copy factual before approval."
    if risk_level == "medium":
        return "Medium risk. Keep claims tied to the source and avoid overstating future outcomes."
    return "Low risk. Still verify names, numbers, and source context before publishing."


def _rotate(options: list[str], variant_hint: int) -> str:
    return options[variant_hint % len(options)]


def _headline_topic(topic: str, *, india_default: str = "Growth") -> str:
    if topic in {"India", "trend", "general"}:
        return india_default
    if topic == "political debate":
        return "Political"
    return title_case_soft(topic)


def _possessive(actor: str) -> str:
    if actor.endswith("'"):
        return actor
    if actor.upper() == actor and len(actor) <= 4:
        return f"{actor}'s"
    if actor.endswith("s"):
        return f"{actor}'"
    return f"{actor}'s"


def _be_verb(actor: str) -> str:
    if actor.upper() == actor and len(actor) <= 4:
        return "Is"
    if actor.endswith("s") and not actor.endswith("ss"):
        return "Are"
    return "Is"


def _actor_topic_shift(actor: str, headline_topic: str) -> str:
    if actor.lower() == headline_topic.lower():
        return f"The {headline_topic} Shift"
    return f"{_possessive(actor)} {headline_topic} Shift"


def _topic_signal(raw_title: str, classification: dict[str, Any]) -> str:
    text = raw_title.lower()
    checks = [
        ("ipo", "IPO"),
        ("entry-level jobs", "Entry-Level Jobs"),
        ("entry level jobs", "Entry-Level Jobs"),
        ("graduate jobs", "Graduate Jobs"),
        ("hiring", "Hiring"),
        ("job", "Workforce"),
        ("smart glasses", "Hardware"),
        ("ai industry", "AI Industry"),
        ("artificial intelligence", "AI"),
        ("machine learning", "AI"),
        ("restructuring", "Restructuring"),
        ("record annual loss", "Turnaround"),
        ("loss", "Turnaround"),
        ("union recognition", "Labor"),
        ("union", "Labor"),
        ("startup grant", "Startup Funding"),
        ("grant", "Funding"),
        ("trade deal", "Trade Deal"),
        ("price", "Pricing"),
        ("fuel duty", "Pricing"),
        ("child safety", "Platform Risk"),
        ("spending", "Platform Risk"),
        ("engineering hubs", "Talent"),
        ("generate ip", "Innovation"),
    ]
    for needle, signal in checks:
        if needle in text:
            return signal
    categories = {str(category).lower() for category in classification.get("categories", [])}
    if "ai" in categories:
        return "AI"
    if "business" in categories:
        return "Business"
    if "jobs" in categories:
        return "Workforce"
    if "geopolitics" in categories:
        return "Global Risk"
    return "Business Signal"


def _business_subject(actor: str, raw_title: str, signal: str) -> str:
    text = raw_title.lower()
    clean_actor = actor.strip()
    actor_valid = (
        bool(clean_actor)
        and clean_actor.lower() not in WEAK_ACTORS
        and clean_actor.lower() != signal.lower()
        and clean_actor.lower() != "ai"
    )
    checks = [
        ("entry-level jobs", "Entry-Level Jobs"),
        ("entry level jobs", "Entry-Level Jobs"),
        ("graduate jobs", "Graduate Jobs"),
        ("generate ip", "AI-Generated IP"),
        ("engineering hubs", "Engineering Hubs"),
        ("api tools", "API Tools"),
        ("ai agents", "AI Agents"),
        ("ai hiring", "AI Hiring"),
        ("artificial intelligence engineers", "AI Engineers"),
        ("smart glasses", "Smart Glasses"),
        ("union recognition", "Union Recognition"),
        ("trade deal", "Trade Deal"),
        ("startup grant", "Startup Grant"),
        ("record annual loss", "Record Loss"),
        ("restructuring", "Restructuring"),
    ]
    for needle, subject in checks:
        if needle in text:
            if actor_valid and subject not in {"Entry-Level Jobs", "Graduate Jobs"} and clean_actor.lower() not in subject.lower():
                return f"{_possessive(clean_actor)} {subject}"
            return subject

    if actor_valid:
        return clean_actor

    title_words = [
        word
        for word in title_case_soft(raw_title).split()
        if word.strip(".,:;!?").lower() not in {"says", "said", "warns", "warned", "new"}
    ]
    return " ".join(title_words[:4]).strip(" .,:;-") or signal


def _specific_ceo_title(
    actor: str,
    raw_title: str,
    classification: dict[str, Any],
    variant_hint: int,
) -> tuple[str, str] | None:
    text = raw_title.lower()
    if ("entry-level" in text or "entry level" in text or "graduate job" in text) and "job" in text:
        subject = _business_subject(actor, raw_title, "Workforce")
        actor_label = actor if actor.lower() not in WEAK_ACTORS else "This Boss"
        return (
            _rotate(
                [
                    f"{_possessive(actor_label)} Warning Turns {subject} Into A CEO Signal",
                    f"{subject} Are Becoming A Leadership Problem",
                    f"The First Career Step Is Turning Into A CEO Test",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    f"Why Leaders Should Watch The {subject} Squeeze",
                    "The Hiring Lesson Behind This Entry-Level Jobs Warning",
                    "What CEOs Should Learn From The Shrinking Job Ladder",
                ],
                variant_hint,
            ),
        )
    if "spacex" in text and "ipo" in text:
        return (
            _rotate(
                [
                    "SpaceX's IPO Could Create A New Wealth Playbook",
                    "SpaceX Is Turning Founder Equity Into A Power Move",
                    "Elon Musk's SpaceX IPO Could Rewrite CEO Wealth",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why The SpaceX IPO Could Change Founder Wealth",
                    "The CEO Lesson Hidden Inside SpaceX's IPO",
                    "What Operators Should Learn From SpaceX's IPO",
                ],
                variant_hint,
            ),
        )
    if "ai helping india" in text or ("india" in text and "engineering hubs" in text):
        return (
            _rotate(
                [
                    "India's AI Talent Is Becoming A Boardroom Advantage",
                    "India's Engineering Hubs Are Moving Up The AI Value Chain",
                    "The AI Talent Race CEOs Should Be Watching",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why India's AI Talent Could Become A Global Advantage",
                    "The CEO Lesson Inside India's AI Engineering Shift",
                    "What Founders Should Learn From India's AI Talent Push",
                ],
                variant_hint,
            ),
        )
    if "smart glasses" in text and "google" in text:
        return (
            _rotate(
                [
                    "Google's Smart Glasses Comeback Is A Boardroom Signal",
                    "Google Is Testing The Next Interface War",
                    "Google's Hardware Comeback Could Matter More Than It Looks",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Google's Smart Glasses Bet Matters For CEOs",
                    "The Platform Lesson Behind Google's Hardware Comeback",
                    "What Leaders Should Notice About Google's Smart Glasses",
                ],
                variant_hint,
            ),
        )
    if "musk-altman" in text or "ai industry" in text:
        return (
            _rotate(
                [
                    "The AI Industry Is Quietly Winning The Power Game",
                    "The Musk-Altman Trial Shows Who Really Benefits From AI",
                    "AI Companies Are Learning How To Turn Chaos Into Leverage",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why The AI Industry Keeps Winning The Narrative",
                    "The CEO Lesson Inside The Musk-Altman Trial",
                    "What Operators Should Learn From The AI Power Game",
                ],
                variant_hint,
            ),
        )
    if "ubisoft" in text and ("loss" in text or "restructuring" in text):
        return (
            _rotate(
                [
                    "Ubisoft Shows The Cost Of Missing The Execution Window",
                    "Ubisoft Is A Turnaround Lesson In Real Time",
                    "Ubisoft's Loss Is A Warning About Slow Strategy",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Ubisoft Became A Leadership Warning",
                    "The Execution Mistake Behind Ubisoft's Restructuring",
                    "What Founders Should Learn From Ubisoft's Loss",
                ],
                variant_hint,
            ),
        )
    if "roblox" in text:
        return (
            _rotate(
                [
                    "Roblox Reveals The Hidden Cost Of Platform Scale",
                    "Roblox Is Facing The Problem Every Platform CEO Fears",
                    "Roblox Shows Why Trust Is Now A Business Risk",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Platform Risk Can Break Growth Stories",
                    "The CEO Lesson Behind Roblox's Safety Pressure",
                    "What Operators Should Learn From Roblox's Risk Problem",
                ],
                variant_hint,
            ),
        )
    if "union recognition" in text or "google rejects" in text:
        return (
            _rotate(
                [
                    "Google's Union Fight Reveals A Bigger CEO Problem",
                    "Google Is Facing A Leadership Test Inside Its Workforce",
                    "Google's Labor Fight Shows Where Power Is Shifting",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Google's Union Fight Matters For Leaders",
                    "The CEO Lesson Behind Google's Workforce Pressure",
                    "What Operators Should Learn From Google's Labor Fight",
                ],
                variant_hint,
            ),
        )
    if "trade deal" in text and "gulf" in text:
        return (
            _rotate(
                [
                    "The UK-Gulf Trade Deal Shows How Power Moves Are Made",
                    "The UK-Gulf Deal Is A Quiet Signal For Global Operators",
                    "The UK-Gulf Trade Deal Reveals A Bigger Market Shift",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why CEOs Should Watch The UK-Gulf Trade Deal",
                    "The Market Lesson Inside The UK-Gulf Deal",
                    "What Operators Should Learn From This Trade Deal",
                ],
                variant_hint,
            ),
        )
    if "startup grant" in text or "karnataka invites" in text:
        return (
            _rotate(
                [
                    "Karnataka's Startup Grant Is A Signal For Founders",
                    "Karnataka Is Turning Startup Policy Into Leverage",
                    "This Startup Grant Shows How Ecosystems Compete",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Founders Should Watch Karnataka's Startup Grant",
                    "The Ecosystem Lesson Behind Karnataka's Startup Push",
                    "What Operators Should Learn From This Startup Grant",
                ],
                variant_hint,
            ),
        )
    if "fuel duty" in text:
        return (
            _rotate(
                [
                    "The Fuel Duty Freeze Shows How Policy Hits Business",
                    "Fuel Duty Is A Margin Story Leaders Cannot Ignore",
                    "The Fuel Duty Freeze Is A Quiet Business Signal",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Fuel Duty Matters More Than It Sounds",
                    "The CEO Lesson Inside A Fuel Duty Freeze",
                    "What Operators Should Learn From This Policy Move",
                ],
                variant_hint,
            ),
        )
    if "supermarkets" in text and "price" in text:
        return (
            _rotate(
                [
                    "Supermarket Pricing Pressure Is Becoming A Leadership Test",
                    "Supermarkets Are Fighting A Bigger Margin Battle",
                    "The Grocery Price Fight Shows How Thin Trust Has Become",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Supermarket Pricing Pressure Matters For CEOs",
                    "The Margin Lesson Behind The Grocery Price Fight",
                    "What Operators Should Learn From Supermarket Pressure",
                ],
                variant_hint,
            ),
        )
    return None


def _tone_line(tone_override: str | None, default: str) -> str:
    if not tone_override:
        return default
    tone = tone_override.strip().lower()
    if "calm" in tone or "balanced" in tone:
        return "Keep the framing balanced, clear, and source-led."
    if "urgent" in tone:
        return "Make the framing feel immediate without turning it into panic."
    if "relatable" in tone:
        return "Make the framing feel conversational and human."
    if "dramatic" in tone:
        return "Lean into the hidden implication and make the stakes feel bigger."
    return f"Use a {tone_override.strip()} tone while staying source-led."


def _specific_success_title(
    actor: str,
    raw_title: str,
    classification: dict[str, Any],
    variant_hint: int,
) -> tuple[str, str] | None:
    text = raw_title.lower()
    if "spacex" in text and "ipo" in text:
        return (
            _rotate(
                [
                    "SpaceX Is Quietly Building A Trillionaire Playbook",
                    "SpaceX's IPO Could Change The Wealth Game",
                    "The SpaceX IPO Is Bigger Than A Market Story",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "What SpaceX's IPO Means For Ambitious Operators",
                    "Why The SpaceX IPO Could Rewrite Founder Wealth",
                    "The Wealth Lesson Hidden Inside SpaceX's IPO",
                ],
                variant_hint,
            ),
        )
    if "smart glasses" in text and "google" in text:
        return (
            _rotate(
                [
                    "Google Is Quietly Reopening The Smart Glasses War",
                    "Google's Smart Glasses Comeback Says A Lot",
                    "Google May Be Early To The Next Interface Shift",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Google's Smart Glasses Bet Matters Again",
                    "What Google's Hardware Comeback Means For Work",
                    "The Platform Shift Behind Google's Smart Glasses",
                ],
                variant_hint,
            ),
        )
    if "ai helping india" in text or ("india" in text and "engineering hubs" in text):
        return (
            _rotate(
                [
                    "India's AI Talent Could Become A Global Power Move",
                    "AI Is Quietly Moving Up India's Engineering Stack",
                    "India's Engineering Hubs Are Becoming An AI Advantage",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why India's AI Talent Shift Matters For Your Career",
                    "The AI Skills Race India Could Win Next",
                    "What India's AI Engineering Push Means For Work",
                ],
                variant_hint,
            ),
        )
    if "musk-altman" in text or "ai industry" in text:
        return (
            _rotate(
                [
                    "The AI Industry Is Quietly Winning The Narrative War",
                    "The Real Winner Of The Musk-Altman Fight Is AI",
                    "AI Companies Are Turning Chaos Into Leverage",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why The AI Industry Keeps Winning",
                    "The Business Lesson Hidden In The Musk-Altman Trial",
                    "What The AI Power Game Means For Your Career",
                ],
                variant_hint,
            ),
        )
    if "ubisoft" in text and ("loss" in text or "restructuring" in text):
        return (
            _rotate(
                [
                    "Ubisoft Shows What Happens When Growth Breaks",
                    "Ubisoft's Restructuring Is A Warning For Every Company",
                    "Ubisoft Is Paying The Price For A Hard Reset",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "What Ubisoft's Loss Means For Ambitious Operators",
                    "Why Execution Matters More Than Brand Power",
                    "The Business Lesson Behind Ubisoft's Restructuring",
                ],
                variant_hint,
            ),
        )
    if "roblox" in text:
        return (
            _rotate(
                [
                    "Roblox Is Facing The Hidden Cost Of Scale",
                    "Roblox Shows Why Trust Is Now A Business Risk",
                    "Roblox Is Learning The Hard Side Of Platform Growth",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Platform Risk Can Break A Growth Story",
                    "What Roblox Shows About Trust And Scale",
                    "The Business Lesson Behind Roblox's Safety Pressure",
                ],
                variant_hint,
            ),
        )
    if "union recognition" in text or "google rejects" in text:
        return (
            _rotate(
                [
                    "Google's Union Fight Shows Where Workplace Power Is Moving",
                    "Google Is Facing A Quiet Workforce Power Shift",
                    "Google's Labor Fight Says A Lot About The Future Of Work",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "What Google's Union Fight Means For Your Career",
                    "Why Workplace Power Is Shifting Inside Big Tech",
                    "The Career Signal Hidden In Google's Labor Fight",
                ],
                variant_hint,
            ),
        )
    if "trade deal" in text and "gulf" in text:
        return (
            _rotate(
                [
                    "The UK-Gulf Deal Is A Quiet Power Move",
                    "The UK-Gulf Trade Deal Says A Lot About Global Leverage",
                    "A $3.7bn Trade Deal Is Reshaping The Opportunity Map",
                ],
                variant_hint,
            ),
            _rotate(
                [
                    "Why Operators Should Watch The UK-Gulf Trade Deal",
                    "What This Trade Deal Means For Global Business",
                    "The Business Signal Inside The UK-Gulf Deal",
                ],
                variant_hint,
            ),
        )
    return None


def _success_titles(actor: str, topic: str, raw_title: str, classification: dict[str, Any], variant_hint: int) -> tuple[str, str]:
    specific = _specific_success_title(actor, raw_title, classification, variant_hint)
    if specific:
        return specific

    success_topic = _headline_topic("business" if topic == "India" else topic, india_default="Business")
    if actor.lower() == success_topic.lower():
        subject = _business_subject(actor, raw_title, success_topic)
        viral = _rotate(
            [
                f"{subject} Is Moving Faster Than Workers Think",
                f"The {success_topic} Shift Around {subject} Is Getting Real",
                f"{subject} Could Change How People Build Careers",
            ],
            variant_hint,
        )
        aggressive = _rotate(
            [
                f"Why Workers Should Watch {subject}",
                f"The {success_topic} Race Around {subject} Is Getting Serious",
                f"What {subject} Means For Your Career",
            ],
            variant_hint,
        )
        return viral, aggressive
    viral = _rotate(
        [
            f"{actor} {_be_verb(actor)} Making A Quiet {success_topic} Bet",
            f"{_possessive(actor)} {success_topic} Push Says A Lot",
            f"The {success_topic} Shift Behind {actor}'s Move",
        ],
        variant_hint,
    )
    aggressive = _rotate(
        [
            f"What {actor}'s Move Means For Your Career",
            f"The {success_topic} Race Is Getting Serious",
            f"Why Workers Should Watch This {success_topic} Move",
        ],
        variant_hint,
    )
    return viral, aggressive


def _ceo_titles(actor: str, raw_title: str, classification: dict[str, Any], variant_hint: int) -> tuple[str, str]:
    specific = _specific_ceo_title(actor, raw_title, classification, variant_hint)
    if specific:
        return specific

    signal = _topic_signal(raw_title, classification)
    clean_actor = actor if actor.lower() not in WEAK_ACTORS else signal
    text = raw_title.lower()

    if "ipo" in text:
        viral_options = [
            f"{clean_actor} Could Rewrite The Founder Wealth Game",
            f"{clean_actor} Is Becoming A CEO-Level Power Move",
            f"The {signal} Move Every Founder Should Watch",
        ]
        aggressive_options = [
            f"Why {clean_actor} Could Change The Wealth Playbook",
            f"The Founder Lesson Hidden Inside {clean_actor}",
            f"What CEOs Should Learn From This {signal} Move",
        ]
    elif signal in {"Turnaround", "Restructuring"}:
        viral_options = [
            f"{clean_actor} Shows The Cost Of Slow Execution",
            f"{clean_actor} Is A Turnaround Lesson In Real Time",
            f"The {signal} Signal CEOs Should Not Ignore",
        ]
        aggressive_options = [
            f"Why {clean_actor} Became A Leadership Warning",
            f"The Execution Mistake Behind This {signal} Story",
            f"What Founders Should Learn From {clean_actor}",
        ]
    elif signal in {"AI", "AI Industry", "Hardware", "Innovation", "Talent"}:
        subject = _business_subject(clean_actor, raw_title, signal)
        viral_options = [
            f"{subject} Is Quietly Turning Into A Boardroom Advantage",
            f"The {signal} Race Around {subject} Is Heating Up",
            f"{subject} Shows Where The Next Business Edge Is Forming",
        ]
        aggressive_options = [
            f"Why Leaders Cannot Ignore This {signal} Shift",
            f"The CEO Lesson Hidden In {subject}",
            f"What {subject} Means For Ambitious Operators",
        ]
    elif signal in {"Labor", "Pricing", "Platform Risk", "Trade Deal", "Funding", "Startup Funding"}:
        viral_options = [
            f"{clean_actor} Reveals A Bigger CEO Problem",
            f"The {signal} Pressure Leaders Are Watching Closely",
            f"{clean_actor} Is A Business Lesson Hiding In Plain Sight",
        ]
        aggressive_options = [
            f"Why This {signal} Pressure Matters For CEOs",
            f"The Leadership Lesson Behind {clean_actor}",
            f"What Operators Should Learn From This {signal} Fight",
        ]
    else:
        viral_options = [
            f"{clean_actor} Has A Bigger Business Signal",
            f"The CEO Angle Behind {clean_actor}",
            f"What Leaders Should Notice About {clean_actor}",
        ]
        aggressive_options = [
            f"Why {clean_actor} Matters More Than It Looks",
            f"The Business Lesson Most People Missed Here",
            f"What Ambitious Operators Should Learn From This",
        ]

    return _rotate(viral_options, variant_hint), _rotate(aggressive_options, variant_hint)


def _india_titles(actor: str, topic: str, classification: dict[str, Any], variant_hint: int) -> tuple[str, str]:
    if _is_domestic_politics(classification):
        viral_options, aggressive_options = _politics_titles(actor, classification, variant_hint)
        return _rotate(viral_options, variant_hint), _rotate(aggressive_options, variant_hint)
    title_text = str(classification.get("_title_text", "")).lower()
    if "trade deal" in title_text and "gulf" in title_text:
        viral_options = [
            "The UK-Gulf Deal Could Matter For India's Trade Ambitions",
            "The World Is Rewiring Trade Routes Around The Gulf",
            "This Gulf Trade Deal Is A Signal India Should Watch",
        ]
        aggressive_options = [
            "Why India Should Watch The UK-Gulf Trade Deal",
            "The Trade Route Signal India Cannot Ignore",
            "What This Gulf Deal Could Mean For India's Global Play",
        ]
        return _rotate(viral_options, variant_hint), _rotate(aggressive_options, variant_hint)
    india_topic = _headline_topic(topic)
    if classification.get("country_relevance") == "India":
        viral_options = [
            f"India's {india_topic} Push Gets Real",
            f"India's {india_topic} Story Just Got Bigger",
            f"The {india_topic} Shift India Is Watching",
        ]
        aggressive_options = [
            f"Why India's {india_topic} Push Matters Now",
            f"India's Next {india_topic} Test Is Here",
            f"The {india_topic} Signal India Cannot Ignore",
        ]
    else:
        viral_options = [
            f"{_actor_topic_shift(actor, india_topic)} Could Matter For India",
            f"India Has A Window In The {india_topic} Race",
            f"The Global {india_topic} Shift India Should Watch",
        ]
        aggressive_options = [
            f"Why India Should Watch This {india_topic} Shift",
            f"The {india_topic} Race India Cannot Ignore",
            f"What This Global {india_topic} Move Means For India",
        ]
    return _rotate(viral_options, variant_hint), _rotate(aggressive_options, variant_hint)


def _politics_titles(
    actor: str,
    classification: dict[str, Any],
    variant_hint: int,
) -> tuple[list[str], list[str]]:
    text = str(classification.get("_title_text", "")).lower()
    if "constitution" in text:
        subject = "Constitution Claim"
    elif "reservation" in text:
        subject = "Reservation Claim"
    elif "pm" in text or "prime minister" in text or "modi" in text:
        subject = "PM Remark"
    elif "congress" in text:
        subject = "Congress Claim"
    else:
        subject = "Political Claim"
    actor_prefix = "Rahul Gandhi's " if "rahul" in text else ""
    return (
        [
            f"{actor_prefix}{subject} Sparks Debate",
            f"{subject} Becomes A Political Flashpoint",
            f"India's {subject} Returns To The Spotlight",
        ],
        [
            f"Why This {subject} Became A Flashpoint",
            f"The {subject} Everyone Will Be Debating Next",
            f"Why This {subject} Needs Careful Attention",
        ],
    )


def _female_titles(topic: str, classification: dict[str, Any], variant_hint: int) -> tuple[str, str]:
    categories = classification.get("categories", [])
    headline_topic = _headline_topic(topic, india_default="Trend")
    if "relationships" in categories:
        viral_options = [
            "Women Are Noticing This Pattern",
            "This Relationship Habit Says A Lot",
            "This Small Relationship Habit Says A Lot",
        ]
        aggressive_options = [
            "The Red Flag Women Stop Ignoring",
            "Why Standards Are Becoming Non-Negotiable",
            "Most People Miss This Pattern Too Long",
        ]
    elif "jobs" in categories or "business" in categories:
        viral_options = [
            "Women Are Rethinking The Career Playbook",
            "This Work Shift Says A Lot",
            "The Workplace Is Changing Fast",
        ]
        aggressive_options = [
            "The Career Rule Women Are Questioning",
            "How Women Build Power At Work Is Changing",
            "The Work Shift Smart Women Are Watching",
        ]
    else:
        viral_options = [
            f"Women Are Noticing This {headline_topic} Shift",
            "This Modern Pattern Says A Lot",
            "This Habit Says Where Culture Is Going",
        ]
        aggressive_options = [
            "The Trend Women Are Done Ignoring",
            "The Quiet Shift Changing Self-Worth",
            "The Pattern Is Too Obvious To Ignore",
        ]
    return _rotate(viral_options, variant_hint), _rotate(aggressive_options, variant_hint)


def _generic_titles(actor: str, topic: str, variant_hint: int) -> tuple[str, str]:
    headline_topic = _headline_topic(topic, india_default="Story")
    clean_actor = actor if actor.lower() not in WEAK_ACTORS else "This Move"
    return (
        _rotate(
            [
                f"{clean_actor} Has A Bigger Signal",
                f"The Real {headline_topic} Signal Here",
                "This Move Matters More Than It Looks",
            ],
            variant_hint,
        ),
        _rotate(
            [
                "This Could Move Faster Than Expected",
                "The Bigger Signal Is Hiding In Plain Sight",
                "People May Be Underestimating This",
            ],
            variant_hint,
        ),
    )


def _caption(
    raw_item: dict[str, Any],
    profile: dict[str, Any],
    classification: dict[str, Any],
    viral_title: str,
    tone_override: str | None,
) -> str:
    page_name = profile.get("page_name", "")
    actor = _actor_from_title(raw_item.get("title", ""))
    source_sentence = first_sentence(raw_item.get("summary", ""), fallback=raw_item.get("title", ""))
    topic = _topic_label(classification)
    tone = _tone_line(tone_override, profile.get("tone_rules", "Keep it punchy and clear."))

    if page_name == "SuccessAddictives":
        success_topic = "business" if topic == "India" else topic
        subject = _business_subject(actor, raw_item.get("title", ""), _topic_signal(raw_item.get("title", ""), classification))
        return (
            f"{source_sentence} The bigger story is not just the headline; it is what {subject} signals about leverage, "
            f"skills, and the future of work. {actor} is part of a wider {success_topic} race where companies are trying to "
            f"move faster with fewer limits. {tone} The question is what skill becomes more valuable if this trend keeps moving."
        )
    if page_name == "IndiaPulse":
        if _is_domestic_politics(classification):
            return _politics_caption(raw_item)
        if classification.get("country_relevance") == "India":
            return (
                f"{source_sentence} For India, the important part is what this could mean for growth, influence, and the next phase "
                f"of national momentum. This is the kind of story that can connect policy, talent, markets, and global attention. "
                f"{tone} Watch what happens next, because the second-order effects may matter more than the announcement."
            )
        return (
            f"{source_sentence} The global shift matters for India because talent, markets, and technology rarely stay local anymore. "
            f"If India positions itself well, this {topic} story could become an opportunity instead of just foreign news. "
            f"{tone} The real question is how quickly India can turn the opening into advantage."
        )
    if page_name == "HerSignal":
        return (
            f"{source_sentence} What makes this interesting is the emotional pattern underneath it. For modern women, stories like this "
            f"often connect back to self-worth, choices, ambition, relationships, or the pressure to keep up. {tone} Sometimes the trend "
            f"is less about what happened and more about what it reveals."
        )
    if page_name == "CEOBeingCEO":
        signal = _topic_signal(raw_item.get("title", ""), classification)
        subject = _business_subject(actor, raw_item.get("title", ""), signal)
        return (
            f"{source_sentence} The CEO angle is {subject}: what it says about {signal.lower()}, execution, leverage, or risk. "
            f"For ambitious operators, this is not just news; it is a lesson in how leaders spot specific market signals before everyone else reacts. "
            f"{tone} The question is what decision a sharper CEO would make after seeing this."
        )
    return (
        f"{source_sentence} The bigger angle is the signal behind the event. {viral_title} {tone} Keep the final post tied to the source."
    )


def _politics_caption(raw_item: dict[str, Any]) -> str:
    title = clean_text(raw_item.get("title", ""))
    summary = clean_text(raw_item.get("summary", "")).rstrip(".")
    summary_lower = summary.lower()
    claim = summary
    for prefix in ("congress leader says that ", "congress leader says ", "rahul says that ", "rahul gandhi says that "):
        if summary_lower.startswith(prefix):
            claim = summary[len(prefix):].strip()
            break
    if claim:
        claim = claim[:1].lower() + claim[1:]

    if "rahul" in title.lower() or "congress" in summary_lower:
        lead = f"Congress leader Rahul Gandhi alleged that {claim}."
    else:
        lead = f"The source reports a politically sensitive claim: {summary or title}."

    return (
        f"{lead} The claim should be treated as an allegation, not a verified conclusion. "
        "The bigger story is how Constitution, reservation, and election-season messaging are shaping India's political debate."
    )


def _carousel(raw_item: dict[str, Any], classification: dict[str, Any], viral_title: str) -> list[str]:
    topic = _topic_label(classification)
    source_sentence = first_sentence(raw_item.get("summary", ""), fallback=raw_item.get("title", ""))
    if _is_domestic_politics(classification):
        return [
            viral_title,
            f"What happened: {source_sentence}",
            "Why it matters: this is a political allegation and needs attribution.",
            "What to watch next: official responses, source verification, and election-season messaging.",
        ]
    return [
        viral_title,
        f"What happened: {source_sentence}",
        f"Why it matters: this is a {topic} signal, not just a headline.",
        "What to watch next: who benefits, who adapts, and who gets left behind.",
    ]


def _visual_direction(profile: dict[str, Any], raw_item: dict[str, Any], classification: dict[str, Any]) -> str:
    actor = _actor_from_title(raw_item.get("title", ""))
    if _is_domestic_politics(classification):
        return (
            "Use neutral Indian Parliament or Constitution imagery, no party colors as the dominant theme, "
            "no angry faces, no accusation text as fact. Add a clear source line and a high-risk review label."
        )
    categories = ", ".join(classification.get("categories", []))
    return (
        f"Use {actor} or topic-relevant imagery with {categories} cues. "
        f"{profile.get('visual_style')} Add a small source line and leave room for a bold headline."
    )


def _image_brief(profile: dict[str, Any], raw_item: dict[str, Any], classification: dict[str, Any]) -> dict[str, Any]:
    actor = _actor_from_title(raw_item.get("title", ""))
    page_name = profile.get("page_name", "")
    categories = classification.get("categories", [])

    if _is_domestic_politics(classification):
        return {
            "composition": "Neutral newsroom frame with Parliament or Constitution imagery, headline centered, source line visible.",
            "background_style": "Clean documentary news background with restrained contrast and no partisan treatment.",
            "mood": "Serious, cautious, factual.",
            "colors": ["black", "white", "muted yellow accent"],
            "object_suggestions": ["Constitution of India", "Parliament exterior", "neutral microphone", "newspaper texture"],
            "visual_references": ["Indian election desk graphic", "Reuters-style political explainer", "neutral civic news card"],
            "text_hierarchy": "Short headline first, attribution/source second, high-risk label small at the bottom.",
            "possible_overlays": ["Allegation", "Political debate", "Verify source"],
        }

    if page_name == "SuccessAddictives":
        return {
            "composition": f"{actor} or symbolic business object in the background, worker silhouettes, bold headline in the center.",
            "background_style": "Dark corporate office, AI console, boardroom, or market-screen environment.",
            "mood": "Dramatic, strategic, high-stakes.",
            "colors": ["black", "white", "electric blue", "yellow highlight"],
            "object_suggestions": ["office silhouettes", "AI interface", "company logo", "laptop", "charts"],
            "visual_references": ["modern business editorial cover", "dark tech explainer", "trading dashboard poster"],
            "text_hierarchy": "One big hook, smaller context line, source line bottom-left, page mark bottom-right.",
            "possible_overlays": ["Quiet move", "Future of work", "Skills warning"],
        }

    if page_name == "IndiaPulse":
        objects = ["India map", "city skyline", "infrastructure", "factory", "policy document"]
        if "geopolitics" in categories:
            objects.extend(["world map", "diplomatic handshake"])
        return {
            "composition": f"India-first editorial layout with {actor} or the main topic as the visual anchor.",
            "background_style": "Newsroom graphic with map, infrastructure, economy, or technology cues.",
            "mood": "Bold, informative, nationally relevant.",
            "colors": ["black", "white", "yellow accent", "small saffron or green cue if relevant"],
            "object_suggestions": objects,
            "visual_references": ["newsroom economy card", "geopolitical explainer thumbnail", "India tech bulletin"],
            "text_hierarchy": "Headline on top, India relevance as subline, source and date small at bottom.",
            "possible_overlays": ["India angle", "Why it matters", "Global signal"],
        }

    if page_name == "HerSignal":
        return {
            "composition": "Editorial portrait or lifestyle scene with clean space for a sharp observation headline.",
            "background_style": "Modern lifestyle, career, beauty, or relationship editorial setup.",
            "mood": "Relatable, emotional, modern.",
            "colors": ["black", "white", "soft yellow accent", "warm neutral support"],
            "object_suggestions": ["portrait", "phone", "mirror", "desk", "beauty product", "coffee"],
            "visual_references": ["magazine social trend card", "modern relationship explainer", "clean lifestyle editorial"],
            "text_hierarchy": "Conversational headline first, small insight line second, minimal branding.",
            "possible_overlays": ["Women are noticing", "Modern pattern", "Self-worth"],
        }

    return {
        "composition": f"Topic-led editorial card using {actor} as the visual anchor.",
        "background_style": "Minimal newsroom graphic with strong contrast and clear source space.",
        "mood": "Fast, clear, operational.",
        "colors": ["black", "white", "yellow accent"],
        "object_suggestions": [actor, *categories[:3]],
        "visual_references": ["newsroom brief", "social explainer card"],
        "text_hierarchy": "Headline first, source second, small category label last.",
        "possible_overlays": ["Why it matters", "What changed"],
    }


def _image_keywords(raw_item: dict[str, Any], classification: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    if _is_domestic_politics(classification):
        return ["India Parliament", "Constitution of India", "Rahul Gandhi", "BJP Congress", "reservation debate"]
    actor = _actor_from_title(raw_item.get("title", ""))
    keywords = [actor]
    keywords.extend(classification.get("categories", [])[:4])
    if classification.get("country_relevance") == "India":
        keywords.extend(["India", "economy", "map"])
    if profile.get("page_name") == "SuccessAddictives":
        keywords.extend(["office", "AI", "corporate"])
    if profile.get("page_name") == "HerSignal":
        keywords.extend(["modern woman", "lifestyle editorial"])
    return list(dict.fromkeys(keyword for keyword in keywords if keyword))


def build_angle(
    raw_item: dict[str, Any],
    classification: dict[str, Any],
    profile: dict[str, Any],
    *,
    variant_hint: int = 0,
    tone_override: str | None = None,
) -> dict[str, Any]:
    title = clean_text(raw_item.get("title", "Untitled topic"))
    neutral_title = title_case_soft(title)
    actor = _actor_from_title(title)
    topic = _topic_label(classification)
    page_name = profile.get("page_name", "")
    classification = {**classification, "_title_text": title}

    if page_name == "SuccessAddictives":
        viral_title, aggressive_title = _success_titles(actor, topic, title, classification, variant_hint)
    elif page_name == "CEOBeingCEO":
        viral_title, aggressive_title = _ceo_titles(actor, title, classification, variant_hint)
    elif page_name == "IndiaPulse":
        viral_title, aggressive_title = _india_titles(actor, topic, classification, variant_hint)
    elif page_name == "HerSignal":
        viral_title, aggressive_title = _female_titles(topic, classification, variant_hint)
    else:
        viral_title, aggressive_title = _generic_titles(actor, topic, variant_hint)

    match_score = float(profile.get("match_score", 4.0))
    virality = float(classification.get("virality_score", 5.0))
    confidence = round(max(1.0, min(10.0, 3.5 + match_score * 0.45 + virality * 0.28)), 1)

    return {
        "neutral_title": neutral_title,
        "viral_title": viral_title,
        "aggressive_title": aggressive_title,
        "caption": _caption(raw_item, profile, classification, viral_title, tone_override),
        "carousel_text": _carousel(raw_item, classification, viral_title),
        "visual_direction": _visual_direction(profile, raw_item, classification),
        "suggested_image_keywords": _image_keywords(raw_item, classification, profile),
        "image_brief": _image_brief(profile, raw_item, classification),
        "risk_notes": _risk_notes(classification.get("risk_level", "low"), classification),
        "source_url": raw_item.get("url"),
        "confidence_score": confidence,
    }
