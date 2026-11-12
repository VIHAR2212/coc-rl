"""Baseline attacker strategies for CoCEnv."""
from agents.rule_based import rule_based_action
from agents.smart_funnel import smart_funnel_action
from agents.surround import surround_action

STRATEGIES = {
    "left_wave": rule_based_action,
    "surround": surround_action,
    "smart_funnel": smart_funnel_action,
}

__all__ = ["STRATEGIES", "rule_based_action", "surround_action", "smart_funnel_action"]

