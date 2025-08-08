# rag_lightweight.py
# Smart RAG system that pre-processes knowledge for instant lookups
# Small brain gets pre-digested answers, big brain does complex synthesis

import json
import time
from collections import defaultdict
from typing import Dict, List, Optional

class FastRAGSystem:
    """Pre-processes knowledge for instant small-brain lookups"""

    def __init__(self, rag_memory):
        self.rag_memory = rag_memory  # Your existing RAG system

        # Pre-processed instant lookup tables
        self.situation_responses = {}
        self.goal_procedures = {}
        self.threat_responses = {}
        self.item_actions = {}

        self._build_instant_lookups()
        print("⚡ Fast RAG system ready - instant knowledge lookups")

    def _build_instant_lookups(self):
        """Pre-process RAG knowledge into instant lookup tables"""

        # Situation → Action mappings (for small brain)
        self.situation_responses = {
            'enemy_detected': {
                'action': 'VATS',
                'duration': 0.1,
                'reason': 'engage_with_vats',
                'source': 'combat_knowledge'
            },
            'low_health_combat': {
                'action': 'BACKWARD',
                'duration': 3.0,
                'reason': 'retreat_heal',
                'source': 'survival_knowledge'
            },
            'loot_container_safe': {
                'action': 'INTERACT',
                'duration': 0.5,
                'reason': 'collect_resources',
                'source': 'looting_knowledge'
            },
            'stuck_on_geometry': {
                'action': 'BACKWARD',
                'duration': 1.0,
                'reason': 'unstuck_protocol',
                'source': 'movement_knowledge'
            },
            'public_event_active': {
                'action': 'FORWARD',
                'duration': 2.0,
                'reason': 'approach_event',
                'source': 'event_knowledge'
            }
        }

        # Goal-specific procedures (for small brain)
        self.goal_procedures = {
            'fishing': {
                'at_water': {'action': 'INTERACT', 'duration': 5.0, 'reason': 'cast_fishing_line'},
                'no_water': {'action': 'FORWARD', 'duration': 3.0, 'reason': 'find_water_body'},
                'has_fish': {'action': 'INTERACT', 'duration': 1.0, 'reason': 'collect_catch'}
            },
            'inventory_management': {
                'overweight': {'action': 'INTERACT', 'duration': 2.0, 'reason': 'manage_inventory'},
                'junk_visible': {'action': 'INTERACT', 'duration': 0.5, 'reason': 'collect_junk'},
                'vendor_nearby': {'action': 'FORWARD', 'duration': 2.0, 'reason': 'approach_vendor'}
            },
            'public_events': {
                'event_marker': {'action': 'FORWARD', 'duration': 3.0, 'reason': 'join_event'},
                'event_active': {'action': 'VATS', 'duration': 0.1, 'reason': 'participate_combat'},
                'event_complete': {'action': 'WAIT', 'duration': 2.0, 'reason': 'collect_rewards'}
            }
        }

        # Quick item decisions (for small brain)
        self.item_actions = {
            'plan_known': 'sell',
            'plan_unknown': 'learn',
            'legendary_weapon': 'evaluate',
            'junk_item': 'collect',
            'aid_item': 'collect_limited',
            'ammo': 'collect_matching'
        }

    def get_instant_response(self, situation_type: str) -> Optional[Dict]:
        """Instant lookup for small brain - no AI processing needed"""

        if situation_type in self.situation_responses:
            response = self.situation_responses[situation_type].copy()
            response['lookup_type'] = 'instant_situation'
            return response

        return None

    def get_goal_procedure(self, goal_id: str, context: str) -> Optional[Dict]:
        """Quick goal-specific procedure lookup"""

        if goal_id in self.goal_procedures:
            procedures = self.goal_procedures[goal_id]
            if context in procedures:
                response = procedures[context].copy()
                response['lookup_type'] = 'goal_procedure'
                response['goal'] = goal_id
                return response

        return None

    def get_item_action(self, item_type: str) -> str:
        """Instant item decision for inventory management"""
        return self.item_actions.get(item_type, 'evaluate')

    def get_strategic_context(self, query: str, goal_id: str = None) -> str:
        """Complex RAG retrieval for big brain strategic decisions"""

        # This is where your existing RAG system does heavy lifting
        # Only called for complex strategic decisions
        if self.rag_memory:
            return self.rag_memory.retrieve_context(query, k=3)

        return ""

class SmartDecisionRouter:
    """Routes decisions between small brain + fast RAG vs big brain + complex RAG"""

    def __init__(self, fast_rag: FastRAGSystem):
        self.fast_rag = fast_rag
        self.decision_stats = {
            'instant_lookups': 0,
            'small_brain_calls': 0,
            'strategic_calls': 0
        }

    def route_decision(self, situation: Dict, goals: List[str]) -> Dict:
        """Smart routing: instant → small brain → strategic brain"""

        # TIER 1: Instant RAG lookup (0ms)
        situation_type = self._classify_situation(situation, goals)

        instant_response = self.fast_rag.get_instant_response(situation_type)
        if instant_response:
            self.decision_stats['instant_lookups'] += 1
            return instant_response

        # TIER 2: Goal-specific procedures
        for goal in goals:
            context = self._extract_goal_context(situation, goal)
            procedure = self.fast_rag.get_goal_procedure(goal, context)
            if procedure:
                self.decision_stats['instant_lookups'] += 1
                return procedure

        # TIER 3: Needs strategic thinking
        return {'needs_strategic': True, 'situation': situation, 'goals': goals}

    def _classify_situation(self, situation: Dict, goals: List[str]) -> str:
        """Classify situation for instant lookup"""

        detected_objects = situation.get('detected_objects', [])
        health = situation.get('health', 100)

        # Threat detection
        has_enemy = any('person' in obj.get('label', '').lower() for obj in detected_objects)
        if has_enemy:
            if health < 30:
                return 'low_health_combat'
            else:
                return 'enemy_detected'

        # Loot detection
        has_loot = any('container' in obj.get('label', '').lower() for obj in detected_objects)
        if has_loot:
            return 'loot_container_safe'

        # Event detection
        if situation.get('event_active'):
            return 'public_event_active'

        # Movement issues
        if situation.get('stuck'):
            return 'stuck_on_geometry'

        return 'unknown_situation'

    def _extract_goal_context(self, situation: Dict, goal_id: str) -> str:
        """Extract context relevant to specific goal"""

        if goal_id == 'fishing':
            if situation.get('near_water'):
                return 'at_water'
            elif situation.get('has_fish'):
                return 'has_fish'
            else:
                return 'no_water'

        elif goal_id == 'inventory_management':
            if situation.get('overweight'):
                return 'overweight'
            elif situation.get('vendor_nearby'):
                return 'vendor_nearby'
            else:
                return 'junk_visible'

        elif goal_id == 'public_events':
            if situation.get('event_active'):
                return 'event_active'
            elif situation.get('event_complete'):
                return 'event_complete'
            else:
                return 'event_marker'

        return 'general'

    def get_performance_stats(self) -> Dict:
        """Show how decisions are being routed"""

        total = sum(self.decision_stats.values())
        if total == 0:
            return self.decision_stats

        return {
            **self.decision_stats,
            'instant_percentage': (self.decision_stats['instant_lookups'] / total) * 100,
            'small_brain_percentage': (self.decision_stats['small_brain_calls'] / total) * 100,
            'strategic_percentage': (self.decision_stats['strategic_calls'] / total) * 100
        }

# Integration example
class HybridRAGBrain:
    """Combines fast lookups with strategic thinking"""

    def __init__(self, rag_memory, lightweight_brain, strategic_brain):
        self.fast_rag = FastRAGSystem(rag_memory)
        self.router = SmartDecisionRouter(self.fast_rag)
        self.lightweight_brain = lightweight_brain
        self.strategic_brain = strategic_brain

    async def make_decision(self, situation: Dict, goals: List[str]) -> Dict:
        """Hybrid decision making with smart RAG usage"""

        # Try fast routing first
        routed_decision = self.router.route_decision(situation, goals)

        if not routed_decision.get('needs_strategic'):
            # Got instant answer from RAG
            return routed_decision

        # Check if situation is complex enough for strategic brain
        if self._is_complex_situation(situation, goals):
            # Use strategic brain with complex RAG
            strategic_context = self.fast_rag.get_strategic_context(
                f"Goals: {goals}. Situation: {situation}",
                goals[0] if goals else None
            )

            return await self.strategic_brain.make_decision(situation, goals, strategic_context)

        else:
            # Use lightweight brain with simple context
            simple_prompt = f"Quick action for: {goals[0] if goals else 'explore'}"
            self.router.decision_stats['small_brain_calls'] += 1
            return self.lightweight_brain.get_plan(simple_prompt)

    def _is_complex_situation(self, situation: Dict, goals: List[str]) -> bool:
        """Determine if situation needs strategic brain"""

        # Multiple threats
        detected = situation.get('detected_objects', [])
        if len(detected) > 3:
            return True

        # High priority goals
        high_priority_goals = ['public_events', 'inventory_management']
        if any(goal in high_priority_goals for goal in goals):
            return True

        # Health + enemies = complex
        if situation.get('health', 100) < 50 and detected:
            return True

        return False
