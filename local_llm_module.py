# local_llm_module.py
# Version 4.0: Updated for Qwen and improved decision making
# Better fallback system and more intelligent responses

import requests
import json
import re
import time
import random

class LocalBrain:
    def __init__(self, server_url="http://100.64.150.78:5001"):
        # Updated for KoboldCpp API format
        self.api_url_generate = f"{server_url}/api/v1/generate"
        self.api_url_info = f"{server_url}/api/v1/info"
        self.consecutive_failures = 0
        self.max_failures_before_fallback = 2
        self.model_name = "Unknown"
        print(f"🧠 LocalBrain initialized - Target: {server_url}")

    def warm_up_model(self):
        """Test connection and get model info"""
        print("🔥 Testing connection to KoboldCpp server...")

        # First try to get model info
        try:
            info_response = requests.get(self.api_url_info, timeout=10)
            if info_response.status_code == 200:
                info_data = info_response.json()
                self.model_name = info_data.get('result', {}).get('model', 'Unknown Model')
                print(f"📡 Connected to: {self.model_name}")
            else:
                print("⚠️ Could not get model info, but server seems responsive")
        except Exception as e:
            print(f"⚠️ Info endpoint failed: {e}")

        # Test with a simple generation
        test_payload = {
            "prompt": "Hello, are you ready? Respond with just: Ready",
            "max_length": 10,
            "temperature": 0.1,
        }

        try:
            response = requests.post(self.api_url_generate, json=test_payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            # Check response format
            if 'results' in result and len(result['results']) > 0:
                generated_text = result['results'][0].get('text', '')
                print(f"✅ Model responded: {generated_text.strip()}")
                return True
            else:
                print(f"❌ Unexpected response format: {result}")
                return False

        except requests.exceptions.RequestException as e:
            print(f"❌ Connection failed: {e}")
            return False

    def get_plan(self, prompt):
        """Generate action plan with Qwen model"""

        # Use fallback if too many failures
        if self.consecutive_failures >= self.max_failures_before_fallback:
            print(f"⚡ Using smart fallback due to {self.consecutive_failures} consecutive failures")
            return self._generate_smart_fallback_plan(prompt)

        # Build enhanced prompt for Qwen
        enhanced_prompt = self._build_qwen_prompt(prompt)

        payload = {
            "prompt": enhanced_prompt,
            "max_length": 150,  # Shorter for faster response
            "temperature": 0.3,
            "top_p": 0.9,
            "rep_pen": 1.1,
            "stop_sequence": ["\n\n", "Human:", "User:"]
        }

        try:
            print("🧠 Asking Qwen for decision...")
            response = requests.post(self.api_url_generate, json=payload, timeout=60)
            response.raise_for_status()

            result = response.json()
            if 'results' in result and len(result['results']) > 0:
                result_text = result['results'][0].get('text', '')
                print(f"📝 Qwen response: {result_text[:100]}...")

                # Try to extract JSON
                plan = self._extract_plan_from_response(result_text)
                if plan:
                    self.consecutive_failures = 0
                    return plan
                else:
                    raise ValueError("Could not extract valid plan from response")
            else:
                raise ValueError("Invalid response format from server")

        except Exception as e:
            print(f"❌ Qwen failed: {e}")
            self.consecutive_failures += 1
            return self._generate_smart_fallback_plan(prompt)

    def _build_qwen_prompt(self, original_prompt):
        """Build a better prompt for Qwen"""

        # Extract key information from the original prompt
        situation_context = self._extract_situation_context(original_prompt)

        enhanced_prompt = f"""You are an AI assistant helping play Fallout 76. Based on the current situation, choose the best action.

SITUATION: {situation_context}

AVAILABLE ACTIONS:
- FORWARD: Move forward
- BACKWARD: Move backward
- STRAFE_LEFT/STRAFE_RIGHT: Move sideways
- SMOOTH_LOOK: Look around (specify dx, dy)
- INTERACT: Use/pick up objects
- VATS: Target enemies
- ATTACK: Fight enemies
- TAB: Open/close map
- WAIT: Pause briefly

Respond with a JSON object:
{{"action": "ACTION_NAME", "duration": 2.0, "reason": "brief explanation"}}

Example responses:
{{"action": "TAB", "duration": 0.1, "reason": "check map for orientation"}}
{{"action": "FORWARD", "duration": 2.0, "reason": "continue exploring"}}
{{"action": "VATS", "duration": 0.1, "reason": "target detected enemy"}}

Response:"""

        return enhanced_prompt

    def _extract_situation_context(self, prompt):
        """Extract key context from the original prompt"""

        prompt_lower = prompt.lower()

        # Look for key situation indicators
        contexts = []

        if 'threat' in prompt_lower or 'enemy' in prompt_lower or 'person' in prompt_lower:
            contexts.append("enemies detected")

        if 'loot' in prompt_lower or 'container' in prompt_lower or 'objects' in prompt_lower:
            contexts.append("loot available")

        if 'map' in prompt_lower or 'location unknown' in prompt_lower:
            contexts.append("need orientation")

        if 'clear' in prompt_lower and 'path' in prompt_lower:
            contexts.append("safe to explore")

        if not contexts:
            contexts.append("normal exploration")

        return "; ".join(contexts)

    def _extract_plan_from_response(self, response_text):
        """Extract JSON plan from Qwen's response"""

        # Try to find JSON in the response
        json_match = re.search(r'\{[^}]*\}', response_text, re.DOTALL)

        if json_match:
            try:
                json_str = json_match.group(0)
                plan = json.loads(json_str)

                # Validate required fields
                if 'action' in plan:
                    # Set defaults if missing
                    if 'duration' not in plan:
                        plan['duration'] = 1.0
                    if 'reason' not in plan:
                        plan['reason'] = 'AI decision'

                    return plan

            except json.JSONDecodeError as e:
                print(f"JSON parse error: {e}")

        # Try to extract action from natural language
        return self._extract_action_from_text(response_text)

    def _extract_action_from_text(self, text):
        """Extract action from natural language response"""

        text_lower = text.lower()

        # Look for action keywords
        if 'map' in text_lower or 'tab' in text_lower:
            return {'action': 'TAB', 'duration': 0.1, 'reason': 'check map'}
        elif 'forward' in text_lower or 'move ahead' in text_lower:
            return {'action': 'FORWARD', 'duration': 2.0, 'reason': 'move forward'}
        elif 'look' in text_lower and ('around' in text_lower or 'scan' in text_lower):
            return {'action': 'SMOOTH_LOOK', 'dx': 45, 'dy': 0, 'duration': 0.5, 'reason': 'look around'}
        elif 'attack' in text_lower or 'fight' in text_lower or 'vats' in text_lower:
            return {'action': 'VATS', 'duration': 0.1, 'reason': 'engage enemy'}
        elif 'interact' in text_lower or 'use' in text_lower or 'pick' in text_lower:
            return {'action': 'INTERACT', 'duration': 1.0, 'reason': 'interact with object'}
        elif 'wait' in text_lower or 'pause' in text_lower:
            return {'action': 'WAIT', 'duration': 2.0, 'reason': 'wait and observe'}

        # Default action
        return {'action': 'FORWARD', 'duration': 1.5, 'reason': 'continue exploration'}

    def _generate_smart_fallback_plan(self, prompt):
        """Generate intelligent fallback when AI fails"""

        prompt_lower = prompt.lower()

        # Analyze the situation from the prompt
        has_threats = any(word in prompt_lower for word in ['threat', 'enemy', 'combat', 'danger', 'person'])
        needs_orientation = any(word in prompt_lower for word in ['location unknown', 'map', 'bearings', 'orient'])
        has_objects = any(word in prompt_lower for word in ['objects', 'container', 'loot'])
        is_clear = 'clear' in prompt_lower or 'safe' in prompt_lower

        # Generate appropriate plan based on situation
        if has_threats:
            return self._combat_fallback_plan()
        elif needs_orientation:
            return self._orientation_fallback_plan()
        elif has_objects:
            return self._investigation_fallback_plan()
        elif is_clear:
            return self._exploration_fallback_plan()
        else:
            return self._default_fallback_plan()

    def _combat_fallback_plan(self):
        """Quick combat response plan"""
        return {
            "action": "VATS",
            "duration": 0.1,
            "reason": "engage_detected_threat",
            "source": "combat_fallback"
        }

    def _orientation_fallback_plan(self):
        """Map checking and orientation plan"""
        return {
            "action": "TAB",
            "duration": 0.1,
            "reason": "check_map_for_orientation",
            "source": "orientation_fallback"
        }

    def _investigation_fallback_plan(self):
        """Object investigation plan"""
        return {
            "action": "INTERACT",
            "duration": 1.0,
            "reason": "investigate_objects",
            "source": "investigation_fallback"
        }

    def _exploration_fallback_plan(self):
        """Clear area exploration plan"""
        return {
            "action": "FORWARD",
            "duration": 2.5,
            "reason": "continue_exploration",
            "source": "exploration_fallback"
        }

    def _default_fallback_plan(self):
        """Default safe plan when unsure"""
        return {
            "action": "SMOOTH_LOOK",
            "dx": 45,
            "dy": 0,
            "duration": 0.5,
            "reason": "assess_situation",
            "source": "default_fallback"
        }

    def reset_failure_counter(self):
        """Reset the failure counter"""
        self.consecutive_failures = 0
        print("🧠 AI failure counter reset - will attempt full AI again")

    def get_stats(self):
        """Get connection and model stats"""
        return {
            'model_name': self.model_name,
            'consecutive_failures': self.consecutive_failures,
            'server_url': self.api_url_generate
        }
