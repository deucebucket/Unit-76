# smart_goal_generator.py
# AI-powered goal context generator for Fallout 76
# Automatically converts user goals into actionable AI context

import re
from typing import Dict, List, Optional

class SmartGoalGenerator:
    """Generates AI context from simple user goal descriptions"""

    def __init__(self, knowledge_base=None):
        self.knowledge_base = knowledge_base

        # F76-specific goal patterns and their AI contexts
        self.goal_patterns = {
            # Events
            r'(?i)(complete|do|farm)\s*(public\s*)?events?': {
                'ai_context': 'Monitor map every 30 seconds for yellow hexagon event markers, fast travel to events immediately (always free), prioritize high-XP events like Radiation Rumble and Scorched Earth, stay until completion for maximum rewards',
                'priority': 8,
                'success_indicators': ['event_completed', 'legendary_rewards', 'treasury_notes'],
                'failure_conditions': ['event_failed', 'arrived_too_late']
            },

            # Daily Ops
            r'(?i)(daily\s*ops?|do\s*ops?)': {
                'ai_context': 'Access Daily Ops via map menu, join team if needed, complete objectives efficiently, prioritize Elder rank (under 8 minutes) for best rewards, focus on killing enemies in uplink zones',
                'priority': 7,
                'success_indicators': ['elder_rank', 'rare_rewards'],
                'failure_conditions': ['failed_time_limit', 'team_disbanded']
            },

            # Legendary farming
            r'(?i)(legendary|legendaries|farm\s*legendary)': {
                'ai_context': 'Target high-level areas like West Tek, Whitespring Golf Club, or active public events. Look for crown icons on enemies, use VATS to identify legendary status, prioritize 3-star legendaries for scrip value',
                'priority': 6,
                'success_indicators': ['legendary_items', 'scrip_gained'],
                'failure_conditions': ['no_legendaries_found', 'inventory_full']
            },

            # Resource farming
            r'(?i)(farm|collect|gather)\s*(resources?|materials?|junk)': {
                'ai_context': 'Visit high-yield locations like Charleston Herald, Sugar Grove, or workshops. Prioritize adhesive, ballistic fiber, aluminum, lead. Use workbenches to scrap junk immediately, manage weight carefully',
                'priority': 5,
                'success_indicators': ['resources_collected', 'junk_scrapped'],
                'failure_conditions': ['overencumbered', 'no_resources_found']
            },

            # XP farming
            r'(?i)(xp|experience|level|leveling)': {
                'ai_context': 'Target West Tek Super Mutants, Whitespring ghouls, or active public events. Use XP buffs when available, focus on high-XP enemies, participate in events for bonus XP',
                'priority': 6,
                'success_indicators': ['level_gained', 'xp_earned'],
                'failure_conditions': ['died_frequently', 'low_xp_rate']
            },

            # Vendor runs
            r'(?i)(vendor|shop|shopping|buy|sell)': {
                'ai_context': 'Fast travel to major vendor hubs: Whitespring, Foundation, Crater, Fort Atlas. Check for good legendary items, sell excess gear, manage caps efficiently, reset daily at 8pm EST',
                'priority': 4,
                'success_indicators': ['items_purchased', 'caps_earned'],
                'failure_conditions': ['vendors_empty', 'insufficient_caps']
            },

            # Workshop claiming
            r'(?i)(workshop|claim\s*workshop)': {
                'ai_context': 'Locate unclaimed workshops on map (workbench icons), fast travel and clear enemies, claim workshop, build basic defenses, defend against waves, collect resources periodically',
                'priority': 7,
                'success_indicators': ['workshop_claimed', 'resources_generated'],
                'failure_conditions': ['workshop_contested', 'pvp_threat']
            },

            # Exploration
            r'(?i)(explore|discovery|discover|map)': {
                'ai_context': 'Target undiscovered map locations (gray icons), prioritize fast travel points for future use, check for treasure maps and magazines, clear areas systematically',
                'priority': 3,
                'success_indicators': ['locations_discovered', 'map_completion'],
                'failure_conditions': ['too_dangerous', 'already_explored']
            },

            # Combat training
            r'(?i)(combat|fight|kill|enemies)': {
                'ai_context': 'Engage enemies strategically using VATS, target weak points, use cover effectively, manage ammunition and stimpaks, retreat when health is low, practice weapon switching',
                'priority': 5,
                'success_indicators': ['enemies_defeated', 'combat_efficiency'],
                'failure_conditions': ['died_repeatedly', 'ran_out_of_ammo']
            },

            # C.A.M.P building
            r'(?i)(camp|build|base|building)': {
                'ai_context': 'Find suitable flat location away from threats, place C.A.M.P device, build essential structures (workbenches, bed, stash), manage budget efficiently, add defenses if needed',
                'priority': 4,
                'success_indicators': ['camp_built', 'functional_base'],
                'failure_conditions': ['build_limit_reached', 'location_unsuitable']
            },

            # Challenges completion
            r'(?i)(challenges?|daily|weekly|score)': {
                'ai_context': 'Check Challenges menu regularly, prioritize easy daily challenges for SCORE points, adapt gameplay to challenge requirements (specific weapons, locations, actions)',
                'priority': 6,
                'success_indicators': ['challenges_completed', 'score_earned'],
                'failure_conditions': ['challenges_too_difficult', 'time_expired']
            }
        }

    def generate_goal_context(self, user_goal: str, goal_name: str = None) -> Dict:
        """Generate AI context from user's simple goal description"""

        user_goal = user_goal.strip()

        # Try to match against known patterns
        for pattern, context_data in self.goal_patterns.items():
            if re.search(pattern, user_goal):
                # Generate goal name if not provided
                if not goal_name:
                    goal_name = self._generate_goal_name(user_goal, pattern)

                return {
                    'name': goal_name,
                    'description': f"AI-generated goal: {user_goal}",
                    'ai_context': context_data['ai_context'],
                    'priority': context_data['priority'],
                    'success_indicators': context_data['success_indicators'],
                    'failure_conditions': context_data['failure_conditions'],
                    'type': 'ai_generated'
                }

        # If no pattern matches, use RAG knowledge to generate context
        if self.knowledge_base:
            return self._generate_with_rag(user_goal, goal_name)

        # Fallback to generic context
        return self._generate_generic_context(user_goal, goal_name)

    def _generate_goal_name(self, user_goal: str, pattern: str) -> str:
        """Generate a clean goal name from user input"""

        # Clean up the user goal
        cleaned = re.sub(r'\b(complete|do|farm|collect|gather)\b', '', user_goal, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        # Capitalize first letter of each word
        return ' '.join(word.capitalize() for word in cleaned.split())

    def _generate_with_rag(self, user_goal: str, goal_name: str) -> Dict:
        """Use RAG knowledge base to generate context"""

        try:
            # Query knowledge base for relevant context
            relevant_knowledge = self.knowledge_base.retrieve_context(user_goal, k=2)

            # Extract actionable steps from knowledge
            ai_context = self._extract_actionable_context(relevant_knowledge, user_goal)

            # Determine priority based on goal type
            priority = self._determine_priority(user_goal)

            return {
                'name': goal_name or user_goal.title(),
                'description': f"AI-generated from F76 knowledge: {user_goal}",
                'ai_context': ai_context,
                'priority': priority,
                'success_indicators': ['objective_completed'],
                'failure_conditions': ['objective_failed'],
                'type': 'rag_generated'
            }

        except Exception as e:
            print(f"RAG generation failed: {e}")
            return self._generate_generic_context(user_goal, goal_name)

    def _extract_actionable_context(self, knowledge: str, goal: str) -> str:
        """Extract actionable AI context from knowledge base text"""

        # Look for action-oriented sentences
        sentences = knowledge.split('.')
        actionable_sentences = []

        action_keywords = ['use', 'press', 'navigate', 'activate', 'target', 'prioritize', 'focus', 'execute']

        for sentence in sentences:
            if any(keyword in sentence.lower() for keyword in action_keywords):
                actionable_sentences.append(sentence.strip())

        if actionable_sentences:
            return '. '.join(actionable_sentences[:3])  # Limit to 3 sentences

        # Fallback: use first few sentences
        return '. '.join(sentences[:2]).strip()

    def _determine_priority(self, goal: str) -> int:
        """Determine goal priority based on keywords"""

        high_priority_keywords = ['event', 'daily', 'legendary', 'ops']
        medium_priority_keywords = ['farm', 'xp', 'level', 'workshop']

        goal_lower = goal.lower()

        if any(keyword in goal_lower for keyword in high_priority_keywords):
            return 7
        elif any(keyword in goal_lower for keyword in medium_priority_keywords):
            return 5
        else:
            return 4

    def _generate_generic_context(self, user_goal: str, goal_name: str) -> Dict:
        """Generate generic but helpful context for unknown goals"""

        return {
            'name': goal_name or user_goal.title(),
            'description': f"Custom goal: {user_goal}",
            'ai_context': f"Focus on achieving: {user_goal}. Use map for navigation, engage enemies when necessary, prioritize safety and efficiency, check objectives regularly",
            'priority': 5,
            'success_indicators': ['objective_achieved'],
            'failure_conditions': ['objective_failed', 'too_dangerous'],
            'type': 'generic'
        }

    def get_goal_suggestions(self, partial_input: str) -> List[str]:
        """Get goal suggestions based on partial input"""

        suggestions = []
        partial_lower = partial_input.lower()

        # Common F76 goals
        common_goals = [
            "Complete Public Events",
            "Daily Ops",
            "Farm Legendary Items",
            "Collect Resources",
            "Level Up/XP Farm",
            "Vendor Shopping Run",
            "Claim Workshop",
            "Explore New Areas",
            "Complete Daily Challenges",
            "Build C.A.M.P."
        ]

        for goal in common_goals:
            if partial_lower in goal.lower():
                suggestions.append(goal)

        return suggestions[:5]  # Limit to 5 suggestions

# Integration helper
def create_smart_goal_generator(knowledge_base=None):
    """Helper to create goal generator with optional RAG integration"""
    return SmartGoalGenerator(knowledge_base=knowledge_base)
