"""
dice.py — Shared dice logic for Enchantify.

Imported by roll-dice.py and belief-attack.py.
Do not call directly.
"""
import random

DIFFICULTY_MODIFIERS = {
    "routine":   +15,   # exploration, low-stakes dialogue, familiar territory
    "standard":   0,    # default — most actions
    "dramatic":  -15,   # antagonists, major choices, arc pivots
    "desperate": -25,   # Nothing encounters, saving someone, impossible odds
}

NEAR_MISS_MARGIN = 10


def base_threshold(belief: int) -> int:
    """min(85, int(40 + belief * 0.45)) — 40% at Belief 0, caps at 85% at Belief 100."""
    return min(85, int(40 + belief * 0.45))


def final_threshold(belief: int, difficulty: str) -> int:
    """Apply difficulty modifier; clamp to [20, 90]."""
    modifier = DIFFICULTY_MODIFIERS.get(difficulty, 0)
    return max(20, min(90, base_threshold(belief) + modifier))


def roll_d100(belief: int, difficulty: str = "standard") -> dict:
    """
    Roll d100 and return a structured result dict.

    Returns:
        {
            "belief":     int,
            "difficulty": str,
            "threshold":  int,
            "roll":       int,
            "margin":     int,   # roll - threshold (negative = under = success)
            "outcome":    str,   # CRITICAL_SUCCESS | SUCCESS | NEAR_MISS | FAILURE | CRITICAL_FAILURE
        }
    """
    belief = max(0, min(100, belief))
    if difficulty not in DIFFICULTY_MODIFIERS:
        difficulty = "standard"

    thresh = final_threshold(belief, difficulty)
    roll = random.randint(1, 100)
    margin = roll - thresh  # negative = succeeded by that many; positive = failed by that many

    if roll <= 5:
        outcome = "CRITICAL_SUCCESS"
    elif roll >= 96:
        outcome = "CRITICAL_FAILURE"
    elif roll <= thresh:
        outcome = "NEAR_MISS" if margin >= -NEAR_MISS_MARGIN else "SUCCESS"
    else:
        outcome = "NEAR_MISS" if margin <= NEAR_MISS_MARGIN else "FAILURE"

    return {
        "belief":     belief,
        "difficulty": difficulty,
        "threshold":  thresh,
        "roll":       roll,
        "margin":     margin,
        "outcome":    outcome,
    }


def combat_deal(spend: int, result: dict) -> int:
    """
    Translate a dice result into Belief damage dealt in combat.

    Returns:
        Positive int  → damage dealt to target
        Zero          → attack failed; attacker still loses spend
        Negative int  → backfire; attacker takes |value| EXTRA damage
                        (on top of the spend cost already paid)

    Ratios:
        CRITICAL_SUCCESS  → ×1.5 (spend 5 → deal 7–8)
        SUCCESS           → ×1.0 (spend 5 → deal 5)
        NEAR_MISS         → ×0.5 rounded up, min 1 (partial effect)
        FAILURE           → ×0.0 (attacker spent, nothing landed)
        CRITICAL_FAILURE  → backfire: ×0, attacker takes extra damage equal to spend
    """
    outcome = result["outcome"]
    if outcome == "CRITICAL_SUCCESS":
        return max(1, round(spend * 1.5))
    elif outcome == "SUCCESS":
        return spend
    elif outcome == "NEAR_MISS":
        return max(1, round(spend * 0.5))
    elif outcome == "FAILURE":
        return 0
    elif outcome == "CRITICAL_FAILURE":
        return -spend   # negative → backfire signal
    return 0
