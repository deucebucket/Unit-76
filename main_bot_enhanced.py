# main_bot_enhanced.py
# Enhanced version of your main_bot.py with intelligent decision making
# Keeps YOUR existing smart AI system + adds goal management and hybrid thinking

import asyncio
import time
import json
import sqlite3
from collections import deque
from dataclasses import dataclass
from typing import Dict, List, Optional, Any

# YOUR existing modules - don't break anything
from vision_module import Vision
from input_emulator import ActionController
from local_llm_module import LocalBrain  # Your KoboldCpp connection
from web_server_module import EnhancedWebServer
from rag_module import LongTermMemory

@dataclass
class AIGoal:
    """Represents a persistent AI goal"""
    id: str
    name: str
    description: str
    enabled: bool
    priority: int
    success_count: int = 0
    failure_count: int = 0

@dataclass
class WorldLocation:
    """Represents a known location"""
    name: str
    coordinates: tuple
    location_type: str
    visit_count: int = 0
    notes: str = ""

class FastDecisionMaker:
    """Instant reflex decisions - no AI needed"""

    def __init__(self):
        # Instant survival reflexes
        self.survival_reflexes = {
            'enemy_close_health_low': {'action': 'BACKWARD', 'duration': 3.0, 'reason': 'retreat_survival'},
            'enemy_detected_healthy': {'action': 'VATS', 'duration': 0.1, 'reason': 'engage_enemy'},
            'loot_safe_nearby': {'action': 'INTERACT', 'duration': 0.5, 'reason': 'collect_loot'},
            'stuck_detected': {'action': 'BACKWARD', 'duration': 1.0, 'reason': 'unstuck_maneuver'},
            'path_clear_exploring': {'action': 'FORWARD', 'duration': 2.0, 'reason': 'continue_exploration'}
        }

    def check_instant_response(self, game_state, active_goals):
        """Check for instant reflex responses - 0ms decision time"""

        detected_objects = game_state.get('detected_objects', [])
        health = game_state.get('health', 100)

        # Enemy + low health = instant retreat
        has_enemy = any('person' in obj.get('label', '').lower() for obj in detected_objects)
        if has_enemy and health < 30:
            return self.survival_reflexes['enemy_close_health_low']

        # Enemy + healthy = engage
        if has_enemy and health > 60:
            return self.survival_reflexes['enemy_detected_healthy']

        # Loot + safe = grab it
        has_loot = any('container' in obj.get('label', '').lower() for obj in detected_objects)
        if has_loot and not has_enemy and 'manage_inventory' in active_goals:
            return self.survival_reflexes['loot_safe_nearby']

        # If exploring goal and path clear
        if 'explore' in active_goals and not has_enemy:
            return self.survival_reflexes['path_clear_exploring']

        return None

class GoalManager:
    """Manages persistent goals with checkboxes"""

    def __init__(self):
        self.goals = {
            'do_public_events': AIGoal(
                id='do_public_events',
                name='Public Events',
                description='Join and complete public events automatically',
                enabled=False,
                priority=9
            ),
            'manage_inventory': AIGoal(
                id='manage_inventory',
                name='Inventory Management',
                description='Auto-sell junk, known plans, manage weight',
                enabled=False,
                priority=7
            ),
            'fishing': AIGoal(
                id='fishing',
                name='Fishing Activities',
                description='Fish at locations when no events active',
                enabled=False,
                priority=4
            ),
            'daily_challenges': AIGoal(
                id='daily_challenges',
                name='Daily Challenges',
                description='Complete daily and weekly challenges',
                enabled=False,
                priority=6
            ),
            'vendor_rounds': AIGoal(
                id='vendor_rounds',
                name='Vendor Shopping',
                description='Visit vendors for deals and selling',
                enabled=False,
                priority=5
            ),
            'explore_and_map': AIGoal(
                id='explore_and_map',
                name='Exploration & Mapping',
                description='Discover locations and build world knowledge',
                enabled=True,  # Always enabled for learning
                priority=2
            )
        }

    def set_goal_enabled(self, goal_id: str, enabled: bool):
        """Enable/disable a goal"""
        if goal_id in self.goals:
            self.goals[goal_id].enabled = enabled
            return True
        return False

    def get_active_goals(self) -> List[str]:
        """Get list of active goal IDs"""
        return [goal_id for goal_id, goal in self.goals.items() if goal.enabled]

    def get_highest_priority_goal(self) -> Optional[AIGoal]:
        """Get the most important active goal"""
        active = [goal for goal in self.goals.values() if goal.enabled]
        if not active:
            return None
        return max(active, key=lambda g: g.priority)

class WorldDatabase:
    """AI's knowledge of the game world"""

    def __init__(self):
        self.locations = {}
        self.item_knowledge = {}

        # Load from your existing RAG system
        self.rag_memory = LongTermMemory()

    def learn_location(self, name: str, location_type: str = 'general'):
        """Learn about a new location"""
        if name not in self.locations:
            location = WorldLocation(
                name=name,
                coordinates=(0, 0),  # Would get from vision
                location_type=location_type
            )
            self.locations[name] = location
            print(f"📍 Learned new location: {name}")

    def should_keep_item(self, item_name: str) -> str:
        """Quick item decision"""
        item_lower = item_name.lower()

        if 'plan' in item_lower:
            return 'learn_then_sell'
        elif 'legendary' in item_lower:
            return 'evaluate'
        elif any(word in item_lower for word in ['scrap', 'junk']):
            return 'scrap'
        else:
            return 'sell'

class IntelligentFallout76AI:
    """Complete AI system with fast/strategic hybrid thinking"""

    def __init__(self):
        print("🧠 Initializing Intelligent Fallout 76 AI System...")

        # YOUR existing modules - tested and working
        self.vision = Vision()
        self.controller = ActionController()
        # Use a lightweight local model instead of Gemma 2B
        # Since we have OpenHermes for strategy, local model just needs to be fast
        self.brain = LocalBrain("qwen2:0.5b")  # Much lighter than Gemma 2B
        self.memory = LongTermMemory()

        # New intelligent components
        self.fast_decisions = FastDecisionMaker()
        self.goal_manager = GoalManager()
        self.world_db = WorldDatabase()

        # Performance tracking
        self.stats = {
            'session_start': time.time(),
            'decisions_made': 0,
            'reflex_decisions': 0,
            'strategic_decisions': 0,
            'local_decisions': 0,
            'locations_discovered': 0,
            'current_action': 'Idle',
            'last_strategic_think': 0
        }

        # Enhanced web server integration
        self.shared_state = {
            'status': 'idle',
            'log': [],
            'goals': {goal_id: goal.enabled for goal_id, goal in self.goal_manager.goals.items()},
            'stats': self.stats,
            'ai_started': False  # Key addition - AI waits for this
        }
        self.web_server = EnhancedWebServer(self.shared_state, None)

        print("✅ Intelligent AI system ready")

    async def make_intelligent_decision(self, game_state):
        """Multi-tier decision making system"""

        active_goals = self.goal_manager.get_active_goals()
        current_goal = self.goal_manager.get_highest_priority_goal()

        # TIER 1: Instant Reflexes (0ms)
        reflex_response = self.fast_decisions.check_instant_response(game_state, active_goals)
        if reflex_response:
            reflex_response['tier'] = 'REFLEX'
            self.stats['reflex_decisions'] += 1
            self._log_decision('⚡ REFLEX', reflex_response)
            return reflex_response

        # TIER 2: Strategic Thinking (when needed)
        current_time = time.time()
        needs_strategic = (
            current_time - self.stats['last_strategic_think'] > 30 or  # Every 30s
            self._situation_is_complex(game_state) or
            current_goal and current_goal.priority >= 7  # High priority goals
        )

        if needs_strategic:
            strategic_response = await self._strategic_decision(game_state, current_goal)
            if strategic_response:
                strategic_response['tier'] = 'STRATEGIC'
                self.stats['strategic_decisions'] += 1
                self.stats['last_strategic_think'] = current_time
                self._log_decision('🧠 STRATEGIC', strategic_response)
                return strategic_response

        # TIER 3: Simple Local Decision (fallback)
        local_response = self._simple_local_decision(game_state, active_goals)
        local_response['tier'] = 'LOCAL'
        self.stats['local_decisions'] += 1
        self._log_decision('🔄 LOCAL', local_response)
        return local_response

    def _situation_is_complex(self, game_state) -> bool:
        """Determine if situation needs strategic thinking"""

        detected_objects = game_state.get('detected_objects', [])

        # Multiple objects = complex
        if len(detected_objects) > 3:
            return True

        # Multiple threats = complex
        threats = [obj for obj in detected_objects if 'person' in obj.get('label', '').lower()]
        if len(threats) > 1:
            return True

        # Low health + enemies = complex
        if game_state.get('health', 100) < 50 and threats:
            return True

        return False

    async def _strategic_decision(self, game_state, current_goal):
        """Use YOUR LocalBrain for strategic decisions"""

        if not current_goal:
            return None

        # Build context for your brain
        situation_desc = self._build_situation_context(game_state, current_goal)

        prompt = f"""You are an expert AI playing Fallout 76.

CURRENT GOAL: {current_goal.name} - {current_goal.description}
SITUATION: {situation_desc}

This is a complex situation requiring strategic thinking. Plan your next actions carefully.

Respond with JSON:
{{
    "strategy": "overall approach",
    "action": "PRIMARY_ACTION",
    "duration": 2.0,
    "reason": "detailed strategic reasoning",
    "backup_action": "FALLBACK_ACTION",
    "learning_note": "what this teaches"
}}

Available actions: FORWARD, BACKWARD, STRAFE_LEFT, STRAFE_RIGHT, INTERACT, VATS, ATTACK, JUMP, WAIT, SMOOTH_LOOK
"""

        # Use YOUR existing brain that connects to KoboldCpp
        try:
            decision = self.brain.get_plan(prompt)
            if decision:
                # Add learning note to knowledge base
                if 'learning_note' in decision:
                    learning_context = f"Goal: {current_goal.name}. Situation: {situation_desc}. Learning: {decision['learning_note']}"
                    # Add to your RAG system
                    # self.memory would handle this

                return decision
        except Exception as e:
            print(f"Strategic brain error: {e}")

        return None

    def _build_situation_context(self, game_state, current_goal):
        """Build detailed context for strategic decisions"""

        context_parts = []

        detected_objects = game_state.get('detected_objects', [])
        if detected_objects:
            obj_summary = f"{len(detected_objects)} objects: " + ", ".join([obj.get('label', 'unknown') for obj in detected_objects[:3]])
            context_parts.append(obj_summary)

        health = game_state.get('health', 100)
        if health < 70:
            context_parts.append(f"health at {health}%")

        # Add goal-specific context
        if current_goal.id == 'do_public_events':
            context_parts.append("looking for public events")
        elif current_goal.id == 'fishing':
            context_parts.append("seeking fishing locations")
        elif current_goal.id == 'manage_inventory':
            context_parts.append("managing inventory and weight")

        return "; ".join(context_parts) if context_parts else "normal exploration"

    def _simple_local_decision(self, game_state, active_goals):
        """Simple local decision without AI"""

        detected_objects = game_state.get('detected_objects', [])

        # If fishing goal and near water
        if 'fishing' in active_goals:
            return {'action': 'INTERACT', 'duration': 2.0, 'reason': 'fishing_activity'}

        # If objects detected, investigate
        if detected_objects:
            return {'action': 'INTERACT', 'duration': 1.0, 'reason': 'investigate_object'}

        # Default: keep exploring
        return {'action': 'FORWARD', 'duration': 2.0, 'reason': 'continue_exploration'}

    def _log_decision(self, tier, decision):
        """Log decision with tier info - reduced spam"""
        action = decision.get('action', 'UNKNOWN')
        reason = decision.get('reason', 'no reason')

        self.stats['current_action'] = f"{action} ({tier})"

        # Only log strategic decisions and important changes to reduce spam
        if tier == 'STRATEGIC' or action != getattr(self, '_last_action', None):
            print(f"{tier}: {action} - {reason}")
            self._last_action = action

            # Update shared state for web interface (limited to important logs)
            log_entry = f"{tier}: {action} - {reason}"
            self.shared_state['log'].insert(0, log_entry)
            if len(self.shared_state['log']) > 20:  # Reduced from 50
                self.shared_state['log'] = self.shared_state['log'][:20]

    def set_goal_enabled(self, goal_id: str, enabled: bool):
        """Enable/disable goal (called from web interface)"""
        success = self.goal_manager.set_goal_enabled(goal_id, enabled)
        if success:
            self.shared_state['goals'][goal_id] = enabled
            print(f"🎯 Goal '{goal_id}' {'enabled' if enabled else 'disabled'}")
        return success

    def get_goal_states(self) -> Dict[str, bool]:
        """Get current goal states"""
        return {goal_id: goal.enabled for goal_id, goal in self.goal_manager.goals.items()}

    async def capture_game_state(self):
        """Capture game state using YOUR vision system"""

        try:
            if not self.vision.is_game_active():
                return {'game_active': False}

            # Use YOUR vision system
            horizon_image = self.vision.capture_roi_image("HORIZON")

            game_state = {
                'game_active': True,
                'timestamp': time.time(),
                'detected_objects': [],
                'health': 100,  # Would parse from HUD
                'location': 'unknown'  # Would determine from vision
            }

            if horizon_image:
                detected_objects = self.vision.analyze_image(horizon_image)
                game_state['detected_objects'] = detected_objects

                # Learn about new locations
                if detected_objects:
                    # Could identify locations from landmarks
                    pass

            return game_state

        except Exception as e:
            print(f"⚠️ Vision error: {e}")
            return {'game_active': False, 'error': str(e)}

    async def execute_action(self, decision):
        """Execute action using YOUR input controller"""

        action = decision.get('action', 'WAIT')
        duration = decision.get('duration', 1.0)

        try:
            if action == 'SMOOTH_LOOK':
                dx = decision.get('dx', 45)
                dy = decision.get('dy', 0)
                self.controller.smooth_look(dx, dy, duration)
            elif hasattr(self.controller, 'press') and action in ['FORWARD', 'BACKWARD', 'STRAFE_LEFT', 'STRAFE_RIGHT', 'INTERACT', 'VATS', 'ATTACK', 'JUMP']:
                self.controller.press(action, duration)
            elif action == 'WAIT':
                await asyncio.sleep(duration)
            else:
                print(f"⚠️ Unknown action: {action}")

        except Exception as e:
            print(f"❌ Action execution failed: {e}")

    async def start_intelligent_system(self):
        """Start the complete intelligent AI system"""

        # Start web server
        self.web_server.run()
        print("🌐 Web interface: http://localhost:8000")

        # Wait for game
        print("👁️ Waiting for Fallout 76...")
        while True:
            if self.vision.is_game_active():
                self.vision.calibrate()
                print("✅ Game detected and calibrated")
                break
            await asyncio.sleep(3)

        # Main intelligent loop
        print("🧠 Starting intelligent AI loop...")
        while True:
            try:
                # Check for active goals
                active_goals = self.goal_manager.get_active_goals()
                if not active_goals:
                    print("💤 No active goals - set goals in web interface")
                    await asyncio.sleep(5)
                    continue

                # Capture game state
                game_state = await self.capture_game_state()
                if not game_state.get('game_active'):
                    await asyncio.sleep(2)
                    continue

                # Make intelligent decision (multi-tier)
                decision = await self.make_intelligent_decision(game_state)

                # Execute action
                await self.execute_action(decision)

                # Update stats
                self.stats['decisions_made'] += 1
                self.shared_state['stats'] = self.stats

                # Brief pause
                await asyncio.sleep(1.0)

            except KeyboardInterrupt:
                print("🛑 Intelligent AI stopping...")
                break
            except Exception as e:
                print(f"❌ AI loop error: {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    async def main():
        ai = IntelligentFallout76AI()
        await ai.start_intelligent_system()

    print("🧠 Starting Intelligent Fallout 76 AI...")
    asyncio.run(main())
