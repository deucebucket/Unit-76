# local_llm_lightweight.py
# Ultra-lightweight local brain for fast decisions alongside the game
# Uses smaller, faster models since OpenHermes handles strategic thinking

import requests
import json
import re
import time

class LightweightBrain:
    """Lightweight local brain optimized for speed over intelligence"""

    def __init__(self, model_name="qwen2:0.5b"):
        self.api_url_generate = "http://127.0.0.1:11434/api/generate"
        self.model_name = model_name  # Much lighter than Gemma 2B
        self.consecutive_failures = 0
        self.max_failures_before_fallback = 1  # Fail faster to fallbacks

        print(f"⚡ Lightweight local brain using: {self.model_name}")

        # Simple decision templates for instant responses
        self.quick_decisions = {
            'enemy_detected': {'action': 'VATS', 'duration': 0.1, 'reason': 'engage_target'},
            'loot_nearby': {'action': 'INTERACT', 'duration': 0.5, 'reason': 'collect_loot'},
            'health_low': {'action': 'BACKWARD', 'duration': 2.0, 'reason': 'seek_safety'},
            'exploring': {'action': 'FORWARD', 'duration': 2.0, 'reason': 'continue_exploration'},
            'stuck': {'action': 'BACKWARD', 'duration': 1.0, 'reason': 'unstuck'}
        }

    def warm_up_model(self):
        """Quick warm-up for lightweight model"""
        print("⚡ Quick-warming lightweight model...")

        payload = {
            "model": self.model_name,
            "prompt": "Action?",
            "stream": False,
        }

        try:
            # Much shorter timeout for lightweight models
            response = requests.post(self.api_url_generate, json=payload, timeout=10)
            response.raise_for_status()
            print(f"✅ {self.model_name} ready for fast decisions")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Lightweight model failed: {e}")
            print("🔄 Falling back to template decisions only")
            return False

    def get_quick_decision(self, situation_type):
        """Instant template decision - no AI call needed"""

        if situation_type in self.quick_decisions:
            decision = self.quick_decisions[situation_type].copy()
            decision['source'] = 'template'
            return decision

        # Default fallback
        return self.quick_decisions['exploring']

    def get_plan(self, prompt):
        """Fast local decision with aggressive timeouts"""

        # For lightweight model, use template decisions when possible
        prompt_lower = prompt.lower()

        if 'enemy' in prompt_lower or 'person' in prompt_lower:
            return self.get_quick_decision('enemy_detected')
        elif 'loot' in prompt_lower or 'container' in prompt_lower:
            return self.get_quick_decision('loot_nearby')
        elif 'health' in prompt_lower and 'low' in prompt_lower:
            return self.get_quick_decision('health_low')
        elif 'stuck' in prompt_lower:
            return self.get_quick_decision('stuck')

        # Only use AI for non-template situations
        if self.consecutive_failures >= self.max_failures_before_fallback:
            return self.get_quick_decision('exploring')

        payload = {
            "model": self.model_name,
            "prompt": f"Quick Fallout 76 action for: {prompt[:200]}. JSON only: {{\"action\":\"FORWARD\",\"duration\":2.0,\"reason\":\"brief\"}}",
            "stream": False,
            "options": {
                "temperature": 0.1,  # Very focused
                "num_predict": 50,   # Very short
                "stop": ["\n", "```"]
            }
        }

        try:
            # Aggressive timeout for alongside-game performance
            response = requests.post(self.api_url_generate, json=payload, timeout=3)
            response.raise_for_status()
            result_text = response.json().get('response', '')

            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                plan = json.loads(json_match.group(0))
                plan['source'] = 'lightweight_ai'
                self.consecutive_failures = 0
                return plan

        except Exception as e:
            self.consecutive_failures += 1
            # Don't log every failure to reduce spam
            if self.consecutive_failures == 1:
                print(f"⚡ Lightweight AI failed, using templates: {e}")

        # Fast fallback to template
        return self.get_quick_decision('exploring')

# Recommended lightweight models for Steam Deck alongside games:
LIGHTWEIGHT_MODELS = {
    "qwen2:0.5b": {
        "size": "350MB",
        "speed": "Very Fast",
        "description": "Tiny but capable, great alongside games"
    },
    "phi3:mini": {
        "size": "2.3GB",
        "speed": "Fast",
        "description": "Small Microsoft model, good balance"
    },
    "tinyllama": {
        "size": "700MB",
        "speed": "Ultra Fast",
        "description": "Fastest option, basic decisions only"
    },
    "gemma:2b": {
        "size": "1.7GB",
        "speed": "Medium",
        "description": "Your current model - good but heavier"
    }
}

def recommend_model_for_steamdeck():
    """Recommend best lightweight model for Steam Deck gaming"""
    print("\n🎮 Steam Deck Gaming Model Recommendations:")
    print("=" * 50)

    for model, info in LIGHTWEIGHT_MODELS.items():
        print(f"{model:15} | {info['size']:8} | {info['speed']:12} | {info['description']}")

    print("\n⚡ RECOMMENDATION: qwen2:0.5b")
    print("   - Smallest RAM footprint")
    print("   - Fastest inference")
    print("   - Works great with your OpenHermes strategic brain")
    print("   - Won't impact game performance")

    print(f"\n📥 To install: ollama pull qwen2:0.5b")

if __name__ == "__main__":
    recommend_model_for_steamdeck()
