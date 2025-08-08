# comprehensive_fo76_ai.py
# Complete Fallout 76 AI Companion - Works with existing characters
# Handles complex goals, inventory management, world mapping, and strategic decisions

import json
import time
import asyncio
import sqlite3
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from collections import deque
import ollama
import chromadb
import anthropic  # For strategic decisions
import threading
import queue

@dataclass
class AIGoal:
    """Represents a persistent AI goal with checkbox state"""
    id: str
    name: str
    description: str
    enabled: bool
    priority: int
    conditions: Dict[str, Any]
    last_executed: Optional[float] = None
    success_count: int = 0
    failure_count: int = 0

@dataclass
class WorldLocation:
    """Represents a known location in the game world"""
    name: str
    coordinates: tuple
    location_type: str  # event, vendor, resource, fast_travel
    landmarks: List[str]
    connected_locations: List[str]
    notes: str
    visit_count: int = 0
    last_visited: Optional[float] = None

@dataclass
class ItemKnowledge:
    """AI's knowledge about items - god rolls, values, etc."""
    item_name: str
    item_type: str
    base_value: int
    is_god_roll: bool
    god_roll_effects: List[str]
    vendor_value: int
    keep_or_sell: str  # "keep", "sell", "scrap", "trade"
    rarity: str
    notes: str

class WorldDatabase:
    """AI's knowledge of the Fallout 76 world"""

    def __init__(self, db_path: str = "fo76_world.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

        # In-memory caches for fast access
        self.locations: Dict[str, WorldLocation] = {}
        self.item_knowledge: Dict[str, ItemKnowledge] = {}
        self.fast_travel_network: Dict[str, List[str]] = {}

        self._load_from_database()

    def _create_tables(self):
        """Create database tables for world knowledge"""

        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                name TEXT PRIMARY KEY,
                coordinates TEXT,
                location_type TEXT,
                landmarks TEXT,
                connected_locations TEXT,
                notes TEXT,
                visit_count INTEGER DEFAULT 0,
                last_visited REAL
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS item_knowledge (
                item_name TEXT PRIMARY KEY,
                item_type TEXT,
                base_value INTEGER,
                is_god_roll BOOLEAN,
                god_roll_effects TEXT,
                vendor_value INTEGER,
                keep_or_sell TEXT,
                rarity TEXT,
                notes TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events_schedule (
                event_name TEXT PRIMARY KEY,
                typical_times TEXT,
                location TEXT,
                requirements TEXT,
                rewards TEXT,
                participation_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0
            )
        ''')

        self.conn.commit()

    def add_location(self, location: WorldLocation):
        """Add or update a location in the world database"""

        self.locations[location.name] = location

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO locations
            (name, coordinates, location_type, landmarks, connected_locations, notes, visit_count, last_visited)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            location.name,
            json.dumps(location.coordinates),
            location.location_type,
            json.dumps(location.landmarks),
            json.dumps(location.connected_locations),
            location.notes,
            location.visit_count,
            location.last_visited
        ))
        self.conn.commit()

    def get_nearest_location(self, current_pos: tuple, location_type: str = None) -> Optional[WorldLocation]:
        """Find nearest location of specified type"""

        best_location = None
        best_distance = float('inf')

        for location in self.locations.values():
            if location_type and location.location_type != location_type:
                continue

            # Simple distance calculation
            distance = ((location.coordinates[0] - current_pos[0])**2 +
                       (location.coordinates[1] - current_pos[1])**2)**0.5

            if distance < best_distance:
                best_distance = distance
                best_location = location

        return best_location

    def add_item_knowledge(self, item: ItemKnowledge):
        """Add knowledge about an item"""

        self.item_knowledge[item.item_name] = item

        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO item_knowledge
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item.item_name, item.item_type, item.base_value,
            item.is_god_roll, json.dumps(item.god_roll_effects),
            item.vendor_value, item.keep_or_sell, item.rarity, item.notes
        ))
        self.conn.commit()

    def should_keep_item(self, item_name: str) -> str:
        """Determine if AI should keep, sell, or scrap an item"""

        if item_name in self.item_knowledge:
            return self.item_knowledge[item_name].keep_or_sell

        # Default logic for unknown items
        if "plan" in item_name.lower():
            return "learn_then_sell"  # Learn plans, then sell duplicates
        elif "legendary" in item_name.lower():
            return "evaluate"  # Need to check if it's a god roll
        else:
            return "sell"  # Regular items can be sold

class GoalManager:
    """Manages persistent AI goals with checkbox interface"""

    def __init__(self):
        self.goals: Dict[str, AIGoal] = {}
        self.active_goals: List[str] = []

        # Initialize default goals
        self._create_default_goals()

    def _create_default_goals(self):
        """Create the standard set of AI goals"""

        default_goals = [
            AIGoal(
                id="do_public_events",
                name="Participate in Public Events",
                description="Automatically join and complete public events when they appear",
                enabled=False,
                priority=8,
                conditions={"min_level": 5, "max_deaths_per_event": 2}
            ),
            AIGoal(
                id="manage_inventory",
                name="Smart Inventory Management",
                description="Auto-sell junk, known plans, and non-god-roll legendaries",
                enabled=False,
                priority=5,
                conditions={"weight_threshold": 0.8, "caps_threshold": 1000}
            ),
            AIGoal(
                id="fishing",
                name="Fishing Activities",
                description="Fish at various locations when not doing events",
                enabled=False,
                priority=3,
                conditions={"preferred_locations": ["Fisherman's Rest", "Rivers", "Lakes"]}
            ),
            AIGoal(
                id="daily_challenges",
                name="Complete Daily Challenges",
                description="Automatically complete daily and weekly challenges",
                enabled=False,
                priority=6,
                conditions={"max_time_per_challenge": 900}  # 15 minutes
            ),
            AIGoal(
                id="vendor_rounds",
                name="Vendor Shopping Rounds",
                description="Visit vendors for good deals and selling items",
                enabled=False,
                priority=4,
                conditions={"min_caps": 500, "check_frequency": 3600}  # Every hour
            ),
            AIGoal(
                id="resource_farming",
                name="Resource Collection",
                description="Farm specific resources based on current needs",
                enabled=False,
                priority=2,
                conditions={"resources": ["screws", "springs", "adhesive"]}
            ),
            AIGoal(
                id="camp_maintenance",
                name="C.A.M.P. Maintenance",
                description="Maintain and optimize C.A.M.P. setup",
                enabled=False,
                priority=1,
                conditions={"check_frequency": 1800}  # Every 30 minutes
            ),
            AIGoal(
                id="explore_and_map",
                name="Exploration & Mapping",
                description="Discover new locations and update world database",
                enabled=True,  # Always enabled for learning
                priority=1,
                conditions={"discovery_radius": 100}
            )
        ]

        for goal in default_goals:
            self.goals[goal.id] = goal
            if goal.enabled:
                self.active_goals.append(goal.id)

    def set_goal_enabled(self, goal_id: str, enabled: bool):
        """Enable/disable a goal (for checkbox interface)"""

        if goal_id in self.goals:
            self.goals[goal_id].enabled = enabled

            if enabled and goal_id not in self.active_goals:
                self.active_goals.append(goal_id)
            elif not enabled and goal_id in self.active_goals:
                self.active_goals.remove(goal_id)

    def get_highest_priority_goal(self, current_context: Dict) -> Optional[AIGoal]:
        """Get the most important goal to work on right now"""

        eligible_goals = []

        for goal_id in self.active_goals:
            goal = self.goals[goal_id]

            # Check if goal conditions are met
            if self._goal_conditions_met(goal, current_context):
                eligible_goals.append(goal)

        if not eligible_goals:
            return None

        # Sort by priority (higher number = higher priority)
        eligible_goals.sort(key=lambda g: g.priority, reverse=True)
        return eligible_goals[0]

    def _goal_conditions_met(self, goal: AIGoal, context: Dict) -> bool:
        """Check if goal conditions are satisfied"""

        # Public events - check if event is active
        if goal.id == "do_public_events":
            return context.get("public_event_active", False)

        # Inventory management - check weight threshold
        elif goal.id == "manage_inventory":
            weight_ratio = context.get("weight_ratio", 0)
            return weight_ratio >= goal.conditions["weight_threshold"]

        # Fishing - no conflicting activities
        elif goal.id == "fishing":
            return not context.get("public_event_active", False) and context.get("at_water", False)

        # Always allow exploration and other goals
        return True

class IntelligentDecisionMaker:
    """Combines local SLM with remote KoboldCpp server for optimal decision making"""

    def __init__(self, config: Dict):
        # Local model for fast decisions
        self.local_client = ollama.Client()
        self.local_model = "gemma:2b"

        # Remote KoboldCpp server for strategic decisions
        self.remote_server_url = config.get("kobold_server_url", "http://100.64.150.78:5001")
        self.remote_available = False

        # Test connection to KoboldCpp server
        self._test_kobold_connection()

        # Decision thresholds
        self.complex_decision_threshold = 0.7  # When to use remote server
        self.last_remote_call = 0
        self.remote_call_cooldown = 60  # Will be optimized based on detected model
        self.is_openhermes = False  # Will be set during connection test

    def _test_kobold_connection(self):
        """Test connection to KoboldCpp server and detect model"""

        try:
            response = requests.get(f"{self.remote_server_url}/api/v1/model", timeout=3)
            if response.status_code == 200:
                model_info = response.json()
                model_name = model_info.get('result', 'Unknown model')
                print(f"🔗 Connected to KoboldCpp server: {model_name}")

                # Detect OpenHermes and optimize parameters
                if 'openhermes' in model_name.lower() or 'hermes' in model_name.lower():
                    print("🧠 Detected OpenHermes model - optimizing for Fallout 76 strategic thinking")
                    self.is_openhermes = True
                    self.complex_decision_threshold = 0.6  # Use strategic thinking more often
                    self.remote_call_cooldown = 30  # OpenHermes is fast, reduce cooldown
                else:
                    self.is_openhermes = False

                self.remote_available = True
            else:
                print(f"⚠️ KoboldCpp server responded with status {response.status_code}")
                self.remote_available = False
                self.is_openhermes = False
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to connect to KoboldCpp server: {e}")
            self.remote_available = False
            self.is_openhermes = False

    async def make_decision(self, context: Dict, goal: AIGoal) -> Dict:
        """Make intelligent decision based on complexity"""

        # Calculate decision complexity
        complexity = self._calculate_complexity(context, goal)

        # Use remote KoboldCpp server for complex strategic decisions
        if (complexity >= self.complex_decision_threshold and
            self.remote_available and
            time.time() - self.last_remote_call >= self.remote_call_cooldown):

            return await self._strategic_decision_kobold(context, goal)

        # Use local LLM for routine decisions
        else:
            return await self._routine_decision(context, goal)

    def _calculate_complexity(self, context: Dict, goal: AIGoal) -> float:
        """Calculate decision complexity score (0-1)"""

        complexity = 0.0

        # Goal-specific complexity
        if goal.id == "do_public_events":
            complexity += 0.6  # Events are moderately complex
        elif goal.id == "manage_inventory":
            complexity += 0.4  # Inventory is routine
        elif goal.id == "fishing":
            complexity += 0.2  # Fishing is simple

        # Context complexity
        if context.get("multiple_threats", False):
            complexity += 0.3

        if context.get("unknown_location", False):
            complexity += 0.2

        if context.get("inventory_full", False):
            complexity += 0.2

        if context.get("low_resources", False):
            complexity += 0.2

        return min(complexity, 1.0)

    async def _routine_decision(self, context: Dict, goal: AIGoal) -> Dict:
        """Fast local decision for routine tasks"""

        prompt = f"""
You are an AI playing Fallout 76. Make a quick decision for this situation:

GOAL: {goal.name}
SITUATION: {context.get('situation', 'normal')}
LOCATION: {context.get('location', 'unknown')}
HEALTH: {context.get('health_percent', 100)}%
WEIGHT: {context.get('weight_ratio', 0.5)}/1.0

Quick action needed. Respond with JSON:
{{"action": "ACTION_NAME", "duration": 2.0, "reason": "brief"}}

Keep it simple and direct.
"""

        try:
            response = self.local_client.generate(
                model=self.local_model,
                prompt=prompt,
                options={'temperature': 0.2, 'num_predict': 80}
            )

            # Parse response
            import re
            json_match = re.search(r'\{.*\}', response['response'], re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(0))
                decision['source'] = 'local_llm'
                return decision

        except Exception as e:
            print(f"Local LLM failed: {e}")

        # Fallback decision
        return self._fallback_decision(context, goal)

    async def _strategic_decision_kobold(self, context: Dict, goal: AIGoal) -> Dict:
        """Strategic decision using OpenHermes on KoboldCpp server"""

        # Optimize prompt format for OpenHermes 2.5
        if self.is_openhermes:
            prompt = f"""<|im_start|>system
You are an expert AI companion for Fallout 76. You provide strategic analysis and optimal action plans for complex situations.
<|im_end|>
<|im_start|>user
Analyze this Fallout 76 situation and provide strategic guidance:

CURRENT GOAL: {goal.name} - {goal.description}

GAME STATE:
- Location: {context.get('location', 'unknown')}
- Level: {context.get('character_level', 1)}
- Health: {context.get('health_percent', 100)}%
- Inventory: {int(context.get('weight_ratio', 0.5) * 100)}% full
- Caps: {context.get('caps', 0)}
- Threats: {context.get('threats', [])}
- Opportunities: {context.get('opportunities', [])}

KNOWN LOCATIONS: {list(context.get('known_locations', {}).keys())[:5]}

Provide optimal strategy as JSON:
{{
    "strategy": "brief overall approach",
    "immediate_actions": [
        {{"action": "ACTION_NAME", "duration": 2.0, "reason": "why this action"}},
        {{"action": "NEXT_ACTION", "duration": 3.0, "reason": "what this accomplishes"}}
    ],
    "contingencies": {{"if_fails": "backup plan", "if_interrupted": "adaptation strategy"}},
    "learning_notes": "key insight for future situations"
}}

Focus on efficiency and goal progression while maintaining safety.
<|im_end|>
<|im_start|>assistant"""
        else:
            # Fallback format for other models
            prompt = f"""You are an expert AI companion for Fallout 76. Analyze this situation:

GOAL: {goal.name}
CONTEXT: Level {context.get('character_level', 1)}, {context.get('health_percent', 100)}% health, {int(context.get('weight_ratio', 0.5) * 100)}% inventory

Provide strategy as JSON with actions and reasoning."""

        try:
            # Optimized parameters for OpenHermes
            if self.is_openhermes:
                payload = {
                    "prompt": prompt,
                    "max_context_length": 4096,  # OpenHermes handles more context well
                    "max_length": 500,           # Allow longer strategic responses
                    "temperature": 0.4,          # Slightly more creative for strategy
                    "top_p": 0.8,               # Good balance for strategic thinking
                    "top_k": 40,                # Focused vocabulary
                    "rep_pen": 1.05,            # Light repetition penalty
                    "stop_sequence": ["<|im_end|>", "\n\n\n"]  # OpenHermes stop tokens
                }
            else:
                # Conservative parameters for unknown models
                payload = {
                    "prompt": prompt,
                    "max_context_length": 2048,
                    "max_length": 300,
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "rep_pen": 1.1
                }

            response = requests.post(
                f"{self.remote_server_url}/api/v1/generate",
                json=payload,
                timeout=45 if self.is_openhermes else 30  # OpenHermes might need more time for strategic thinking
            )

            if response.status_code == 200:
                result = response.json()
                content = result.get('results', [{}])[0].get('text', '')

                # Clean up OpenHermes response format
                if self.is_openhermes:
                    content = content.split('<|im_end|>')[0].strip()

                # Parse JSON from response
                import re
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    decision = json.loads(json_match.group(0))
                    decision['source'] = 'openhermes_strategic'
                    decision['model'] = 'OpenHermes-2.5-Mistral-7B'
                    self.last_remote_call = time.time()

                    strategy_summary = decision.get('strategy', 'Complex strategy')[:50]
                    print(f"🧠 OpenHermes Strategy: {strategy_summary}...")
                    return decision
                else:
                    print(f"⚠️ Could not parse JSON from OpenHermes response: {content[:100]}")

        except Exception as e:
            print(f"OpenHermes server failed: {e}")
            self.remote_available = False

        # Fall back to local decision
        return await self._routine_decision(context, goal)

    def _fallback_decision(self, context: Dict, goal: AIGoal) -> Dict:
        """Hardcoded fallback decisions"""

        if goal.id == "do_public_events":
            return {"action": "JOIN_EVENT", "duration": 1.0, "reason": "event_active"}
        elif goal.id == "fishing":
            return {"action": "CAST_LINE", "duration": 5.0, "reason": "fishing_goal"}
        elif goal.id == "manage_inventory":
            return {"action": "OPEN_INVENTORY", "duration": 1.0, "reason": "inventory_management"}
        else:
            return {"action": "EXPLORE", "duration": 3.0, "reason": "default_action"}

class ComprehensiveAI:
    """Main AI system that orchestrates all components"""

    def __init__(self, config: Dict):
        self.config = config

        # Core components
        self.world_db = WorldDatabase()
        self.goal_manager = GoalManager()
        self.decision_maker = IntelligentDecisionMaker(config)

        # State tracking
        self.current_context = {}
        self.session_stats = {
            'events_completed': 0,
            'items_managed': 0,
            'locations_discovered': 0,
            'fishing_sessions': 0,
            'total_decisions': 0
        }

        print("🤖 Comprehensive Fallout 76 AI initialized")
        print(f"📍 World database: {len(self.world_db.locations)} locations")
        print(f"🎯 Available goals: {len(self.goal_manager.goals)}")

    async def update_context(self, game_state: Dict):
        """Update AI's understanding of current game state"""

        self.current_context.update({
            'timestamp': time.time(),
            'location': game_state.get('location', 'unknown'),
            'character_level': game_state.get('level', 1),
            'health_percent': game_state.get('health', 100),
            'weight_ratio': game_state.get('weight', 0) / game_state.get('max_weight', 1000),
            'caps': game_state.get('caps', 0),
            'public_event_active': game_state.get('event_active', False),
            'at_water': game_state.get('near_water', False),
            'threats': game_state.get('enemies', []),
            'opportunities': game_state.get('loot', []),
            'inventory_items': game_state.get('inventory', [])
        })

        # Update world knowledge
        if game_state.get('location') != 'unknown':
            self._learn_location(game_state)

    def _learn_location(self, game_state: Dict):
        """Learn about current location"""

        location_name = game_state.get('location')
        if location_name and location_name not in self.world_db.locations:

            new_location = WorldLocation(
                name=location_name,
                coordinates=game_state.get('coordinates', (0, 0)),
                location_type=self._classify_location(game_state),
                landmarks=game_state.get('landmarks', []),
                connected_locations=[],
                notes=f"Discovered on {time.strftime('%Y-%m-%d')}"
            )

            self.world_db.add_location(new_location)
            self.session_stats['locations_discovered'] += 1
            print(f"📍 Learned new location: {location_name}")

    def _classify_location(self, game_state: Dict) -> str:
        """Classify location type based on game state"""

        if game_state.get('event_active'):
            return 'event'
        elif game_state.get('vendors_present'):
            return 'vendor'
        elif game_state.get('near_water'):
            return 'fishing'
        elif game_state.get('workbenches_present'):
            return 'crafting'
        else:
            return 'general'

    async def make_intelligent_decision(self) -> Dict:
        """Main decision-making method"""

        # Get highest priority goal
        current_goal = self.goal_manager.get_highest_priority_goal(self.current_context)

        if not current_goal:
            # Default to exploration
            current_goal = self.goal_manager.goals['explore_and_map']

        # Make decision based on goal and context
        decision = await self.decision_maker.make_decision(self.current_context, current_goal)

        # Track decision
        self.session_stats['total_decisions'] += 1
        decision['goal'] = current_goal.name
        decision['timestamp'] = time.time()

        return decision

    def get_goal_states(self) -> Dict[str, bool]:
        """Get current goal enabled/disabled states for UI"""

        return {goal_id: goal.enabled for goal_id, goal in self.goal_manager.goals.items()}

    def set_goal_state(self, goal_id: str, enabled: bool):
        """Set goal enabled state from UI"""

        self.goal_manager.set_goal_enabled(goal_id, enabled)
        print(f"🎯 Goal '{goal_id}' {'enabled' if enabled else 'disabled'}")

    def get_session_report(self) -> Dict:
        """Generate comprehensive session report"""

        return {
            **self.session_stats,
            'active_goals': [self.goal_manager.goals[gid].name for gid in self.goal_manager.active_goals],
            'world_knowledge': {
                'locations': len(self.world_db.locations),
                'items': len(self.world_db.item_knowledge)
            },
            'current_context': self.current_context
        }

# Example Decky Plugin Integration
class DeckyComprehensivePlugin:
    """Decky plugin for the comprehensive AI system"""

    def __init__(self):
        # Configuration with KoboldCpp server support
        self.config = {
            'kobold_server_url': 'http://100.64.150.78:5001',
            'local_model': 'gemma:2b',
            'update_frequency': 1.0,  # seconds
            'max_session_hours': 8
        }

        self.ai_system = None
        self.running = False

    async def initialize_ai(self, kobold_server_url: str = 'http://100.64.150.78:5001'):
        """Initialize AI system with KoboldCpp server"""

        self.config['kobold_server_url'] = kobold_server_url

        self.ai_system = ComprehensiveAI(self.config)

        return {
            'status': 'initialized',
            'local_model': self.config['local_model'],
            'remote_server': kobold_server_url,
            'remote_available': self.ai_system.decision_maker.remote_available,
            'available_goals': list(self.ai_system.goal_manager.goals.keys())
        }

    async def set_goals(self, goal_states: Dict[str, bool]):
        """Update goal enabled/disabled states"""

        if not self.ai_system:
            return {'error': 'AI not initialized'}

        for goal_id, enabled in goal_states.items():
            self.ai_system.set_goal_state(goal_id, enabled)

        return {
            'status': 'goals_updated',
            'active_goals': self.ai_system.goal_manager.active_goals
        }

    async def start_ai_assistance(self):
        """Start AI assistance with current character"""

        if not self.ai_system:
            return {'error': 'AI not initialized'}

        self.running = True

        # Start AI loop
        asyncio.create_task(self._ai_loop())

        return {
            'status': 'started',
            'message': 'AI is now assisting with your Fallout 76 gameplay'
        }

    async def _ai_loop(self):
        """Main AI assistance loop"""

        while self.running:
            try:
                # Get current game state (from your existing vision system)
                game_state = await self._capture_game_state()

                # Update AI context
                await self.ai_system.update_context(game_state)

                # Make intelligent decision
                decision = await self.ai_system.make_intelligent_decision()

                # Execute decision (via your input system)
                await self._execute_decision(decision)

                # Wait before next decision
                await asyncio.sleep(self.config['update_frequency'])

            except Exception as e:
                print(f"AI loop error: {e}")
                await asyncio.sleep(1)

    async def get_status(self):
        """Get current AI status for UI"""

        if not self.ai_system:
            return {'status': 'not_initialized'}

        if self.running:
            report = self.ai_system.get_session_report()
            return {
                'status': 'running',
                'report': report,
                'goal_states': self.ai_system.get_goal_states()
            }
        else:
            return {
                'status': 'idle',
                'goal_states': self.ai_system.get_goal_states()
            }

    async def _capture_game_state(self) -> Dict:
        """Capture current game state (integrate with your vision system)"""
        # This would use your existing perception system
        return {
            'location': 'Vault 76',
            'level': 25,
            'health': 85,
            'weight': 180,
            'max_weight': 220,
            'caps': 1500,
            'event_active': True,
            'near_water': False,
            'enemies': [],
            'loot': ['stimpak', 'ammo'],
            'inventory': []
        }

    async def _execute_decision(self, decision: Dict):
        """Execute AI decision (integrate with your input system)"""

        action = decision.get('action', 'WAIT')
        print(f"🎮 AI Decision: {action} - {decision.get('reason', 'no reason')}")

        # This would use your existing input controller
        pass

if __name__ == "__main__":
    # Example usage with your KoboldCpp server
    plugin = DeckyComprehensivePlugin()

    # Initialize with your KoboldCpp server
    asyncio.run(plugin.initialize_ai(kobold_server_url="http://100.64.150.78:5001"))

    # Set some goals
    goal_config = {
        'do_public_events': True,
        'manage_inventory': True,
        'fishing': True,
        'daily_challenges': False
    }
    asyncio.run(plugin.set_goals(goal_config))

    # Start AI assistance
    asyncio.run(plugin.start_ai_assistance())
