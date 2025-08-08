# local_llm_with_rag.py
# Enhanced version of your local_llm_module.py that can access RAG knowledge
# Connects your KoboldCpp server with your existing RAG system

import requests
import json
import re
import time
import random
from typing import Optional, Dict, List

class LocalBrainWithRAG:
    """Enhanced LocalBrain that can access your existing RAG system"""

    def __init__(self, model_name="gemma:2b", rag_system=None):
        # Your existing KoboldCpp connection
        self.api_url_generate = "http://100.64.150.78:5001/api/v1/generate"
        self.model_name = model_name
        self.consecutive_failures = 0
        self.max_failures_before_fallback = 2

        # NEW: Connect to your RAG system
        self.rag_system = rag_system  # Your LongTermMemory instance

        # Fast lookup cache to avoid repeated RAG queries
        self.knowledge_cache = {}
        self.cache_max_age = 300  # 5 minutes

        # Pre-built instant responses (no RAG needed)
        self.instant_responses = {
            'enemy_close_low_health': {
                'action': 'BACKWARD', 'duration': 3.0,
                'reason': 'retreat_to_safety', 'source': 'survival_instinct'
            },
            'enemy_healthy': {
                'action': 'VATS', 'duration': 0.1,
                'reason': 'engage_with_targeting', 'source': 'combat_doctrine'
            },
            'loot_safe': {
                'action': 'INTERACT', 'duration': 0.5,
                'reason': 'collect_resources', 'source': 'looting_protocol'
            },
            'exploring_clear': {
                'action': 'FORWARD', 'duration': 2.0,
                'reason': 'continue_exploration', 'source': 'exploration_behavior'
            }
        }

        print(f"🧠 LocalBrain with RAG initialized: {self.model_name}")
        if rag_system:
            print("📚 Connected to RAG knowledge base")
        else:
            print("⚠️ No RAG system connected - using fallback responses only")

    def warm_up_model(self):
        """Your existing warm-up code"""
        print("Warming up AI Brain... This may take several minutes.")

        payload = {
            "model": self.model_name,
            "prompt": "Hello, are you ready? Respond with only the word 'Ready'.",
            "stream": False,
        }

        try:
            response = requests.post(self.api_url_generate, json=payload, timeout=300)
            response.raise_for_status()
            print("Model is warmed up and ready.")
            return True
        except requests.exceptions.RequestException as e:
            print(f"--- FATAL ERROR: Could not warm up model: {e}")
            return False

    def get_relevant_knowledge(self, situation_desc: str, goal: str = "") -> str:
        """Get relevant knowledge from RAG system with caching"""

        if not self.rag_system:
            return ""

        # Create cache key
        query = f"{goal} {situation_desc}".strip()
        cache_key = f"{hash(query)}"

        # Check cache first
        if cache_key in self.knowledge_cache:
            cached_data = self.knowledge_cache[cache_key]
            if time.time() - cached_data['timestamp'] < self.cache_max_age:
                return cached_data['knowledge']

        # Query RAG system
        try:
            knowledge = self.rag_system.retrieve_context(query, k=2)  # Limit to 2 for speed

            # Cache the result
            self.knowledge_cache[cache_key] = {
                'knowledge': knowledge,
                'timestamp': time.time()
            }

            return knowledge

        except Exception as e:
            print(f"RAG query failed: {e}")
            return ""

    def get_instant_response(self, situation_type: str) -> Optional[Dict]:
        """Check for instant responses that don't need AI or RAG"""

        return self.instant_responses.get(situation_type)

    def analyze_situation(self, vision_data: Dict, goals: List[str]) -> str:
        """Analyze current situation to determine response type"""

        detected_objects = vision_data.get('detected_objects', [])
        health = vision_data.get('health_percent', 100)

        # Check for people/enemies
        has_enemy = any('person' in obj.get('label', '').lower() for obj in detected_objects)

        if has_enemy and health < 30:
            return 'enemy_close_low_health'
        elif has_enemy and health > 60:
            return 'enemy_healthy'

        # Check for loot
        has_loot = any('container' in obj.get('label', '').lower() for obj in detected_objects)
        if has_loot and not has_enemy:
            return 'loot_safe'

        # Default to exploring
        return 'exploring_clear'

    def get_plan(self, prompt_or_situation, goals=None):
        """Enhanced get_plan that can work with situations or text prompts"""

        # Handle both old string prompts and new situation dictionaries
        if isinstance(prompt_or_situation, dict):
            # New situation-based approach
            vision_data = prompt_or_situation
            goals = goals or ['explore']

            # Check for instant responses first
            situation_type = self.analyze_situation(vision_data, goals)
            instant_response = self.get_instant_response(situation_type)

            if instant_response:
                return instant_response

            # Build enhanced prompt with RAG knowledge
            situation_desc = self.describe_situation(vision_data)
            current_goal = goals[0] if goals else 'explore'

            # Get relevant knowledge from RAG
            relevant_knowledge = self.get_relevant_knowledge(situation_desc, current_goal)

            # Build enhanced prompt
            prompt = self.build_enhanced_prompt(situation_desc, current_goal, relevant_knowledge)

        else:
            # Old string prompt approach (backward compatibility)
            prompt = prompt_or_situation

        # Use your existing KoboldCpp call with enhanced prompt
        return self._call_koboldcpp(prompt)

    def describe_situation(self, vision_data: Dict) -> str:
        """Convert vision data to text description"""

        parts = []

        detected_objects = vision_data.get('detected_objects', [])
        if detected_objects:
            obj_count = len(detected_objects)
            obj_types = [obj.get('label', 'unknown') for obj in detected_objects[:3]]
            parts.append(f"{obj_count} objects detected: {', '.join(obj_types)}")

        health = vision_data.get('health_percent', 100)
        if health < 50:
            parts.append(f"health at {health}%")

        location = vision_data.get('location', 'unknown location')
        parts.append(f"at {location}")

        return "; ".join(parts) if parts else "normal situation"

    def build_enhanced_prompt(self, situation: str, goal: str, knowledge: str) -> str:
        """Build prompt that includes RAG knowledge"""

        prompt_parts = [
            f"You are an AI playing Fallout 76.",
            f"GOAL: {goal}",
            f"SITUATION: {situation}"
        ]

        if knowledge.strip():
            # Include relevant RAG knowledge
            prompt_parts.append(f"RELEVANT KNOWLEDGE: {knowledge[:300]}")  # Limit knowledge to 300 chars

        prompt_parts.extend([
            "Decide your next action based on your goal and the situation.",
            "Respond with JSON: {\"action\": \"ACTION_NAME\", \"duration\": 2.0, \"reason\": \"brief explanation\"}",
            "Available actions: FORWARD, BACKWARD, STRAFE_LEFT, STRAFE_RIGHT, INTERACT, VATS, ATTACK, JUMP, WAIT, SMOOTH_LOOK"
        ])

        return "\n".join(prompt_parts)

    def _call_koboldcpp(self, prompt: str) -> Optional[Dict]:
        """Your existing KoboldCpp call logic"""

        if self.consecutive_failures >= self.max_failures_before_fallback:
            print(f"⚡ Using fast fallback due to {self.consecutive_failures} consecutive failures")
            return self._generate_smart_fallback_plan(prompt)

        payload = {
            "prompt": prompt,
            "max_context_length": 2048,
            "max_length": 200,
            "temperature": 0.2,
            "rep_pen": 1.1
        }

        try:
            print("🧠 Contacting OpenHermes (with RAG knowledge)...")
            response = requests.post(self.api_url_generate, json=payload, timeout=180)
            response.raise_for_status()
            result_text = response.json().get('response', '')

            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON object found in response")

            plan = json.loads(json_match.group(0))
            plan['source'] = 'openhermes_with_rag'

            # Reset failure counter on success
            self.consecutive_failures = 0
            return plan

        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"--- ERROR: AI Brain failed: {e}")
            self.consecutive_failures += 1
            return self._generate_smart_fallback_plan(prompt)

    def _generate_smart_fallback_plan(self, prompt):
        """Your existing smart fallback logic"""

        prompt_lower = prompt.lower()

        # Analyze the situation from the prompt
        has_threats = any(word in prompt_lower for word in ['threat', 'enemy', 'combat', 'danger', 'person'])
        has_loot = any(word in prompt_lower for word in ['loot', 'container', 'objects'])
        needs_orientation = any(word in prompt_lower for word in ['location unknown', 'map', 'orient'])
        is_clear = 'clear' in prompt_lower or 'normal situation' in prompt_lower

        # Generate appropriate plan based on situation
        if has_threats:
            return self._combat_fallback_plan()
        elif needs_orientation:
            return self._orientation_fallback_plan()
        elif has_loot:
            return self._investigation_fallback_plan()
        elif is_clear:
            return self._exploration_fallback_plan()
        else:
            return self._default_fallback_plan()

    def _combat_fallback_plan(self):
        return {
            "action": "VATS",
            "duration": 0.1,
            "reason": "engage_detected_threat",
            "source": "combat_fallback"
        }

    def _exploration_fallback_plan(self):
        return {
            "action": "FORWARD",
            "duration": 2.0,
            "reason": "continue_exploration",
            "source": "exploration_fallback"
        }

    def _investigation_fallback_plan(self):
        return {
            "action": "INTERACT",
            "duration": 1.0,
            "reason": "investigate_objects",
            "source": "investigation_fallback"
        }

    def _orientation_fallback_plan(self):
        return {
            "action": "TAB",
            "duration": 0.1,
            "reason": "check_map_for_orientation",
            "source": "orientation_fallback"
        }

    def _default_fallback_plan(self):
        return {
            "action": "WAIT",
            "duration": 1.0,
            "reason": "assess_situation",
            "source": "default_fallback"
        }

    def reset_failure_counter(self):
        """Reset the failure counter"""
        self.consecutive_failures = 0
        print("🧠 AI failure counter reset")

    def get_cache_stats(self):
        """Get RAG cache statistics"""
        return {
            'cached_queries': len(self.knowledge_cache),
            'consecutive_failures': self.consecutive_failures,
            'instant_responses': len(self.instant_responses)
        }

# Integration helper
def create_brain_with_rag(rag_system, model_name="gemma:2b"):
    """Helper function to create brain with RAG connection"""
    return LocalBrainWithRAG(model_name=model_name, rag_system=rag_system)
