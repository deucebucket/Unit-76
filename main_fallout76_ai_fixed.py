# main_fallout76_ai_fixed.py
# Using YOUR existing modules and setup - no breaking changes

import asyncio
import time
from collections import deque

# Use YOUR existing modules
from vision_module import Vision
from input_emulator import ActionController
from local_llm_module import LocalBrain  # Your existing KoboldCpp connection
from web_server_module import EnhancedWebServer
from rag_module import LongTermMemory

class FixedFallout76AI:
    """Integration using your existing working modules"""

    def __init__(self):
        print("🚀 Starting Fallout 76 AI with your existing setup...")

        # Use YOUR existing modules - don't break anything
        self.vision = Vision()
        self.controller = ActionController()
        self.brain = LocalBrain()  # Your KoboldCpp connection
        self.memory = LongTermMemory()

        # Simple goal state management
        self.goals = {
            'do_events': False,
            'manage_inventory': False,
            'fishing': False,
            'daily_challenges': False,
            'explore': True  # Always keep exploring
        }

        # Stats
        self.stats = {
            'session_start': time.time(),
            'decisions_made': 0,
            'strategic_calls': 0,
            'local_calls': 0
        }

        # Set up web server with goal management
        shared_state = {"status": "Idle", "log": [], "goals": self.goals}
        command_queue = None  # We'll handle this ourselves
        self.web_server = EnhancedWebServer(shared_state, command_queue)

        print("✅ Using your existing modules - no breaking changes")

    def update_goal(self, goal_name, enabled):
        """Update a goal state"""
        if goal_name in self.goals:
            self.goals[goal_name] = enabled
            print(f"🎯 Goal '{goal_name}' {'enabled' if enabled else 'disabled'}")
            return True
        return False

    def get_active_goals(self):
        """Get list of active goals"""
        return [goal for goal, enabled in self.goals.items() if enabled]

    async def make_decision(self, game_state):
        """Make a decision using your existing brain"""

        # Get active goals
        active_goals = self.get_active_goals()
        if not active_goals:
            active_goals = ['explore']  # Default fallback

        current_goal = active_goals[0]  # Pick first active goal

        # Create prompt for your existing brain
        situation_desc = self.describe_situation(game_state)

        prompt = f"""You are playing Fallout 76.

CURRENT GOAL: {current_goal}
SITUATION: {situation_desc}

Make a decision. Respond with JSON:
{{"action": "ACTION_NAME", "duration": 2.0, "reason": "brief explanation"}}

Available actions: FORWARD, BACKWARD, STRAFE_LEFT, STRAFE_RIGHT, INTERACT, VATS, ATTACK, JUMP, WAIT, SMOOTH_LOOK
"""

        # Use YOUR existing brain
        decision = self.brain.get_plan(prompt)

        if decision:
            self.stats['strategic_calls'] += 1
        else:
            # Fallback decision
            decision = {"action": "FORWARD", "duration": 2.0, "reason": "exploring"}
            self.stats['local_calls'] += 1

        self.stats['decisions_made'] += 1
        return decision

    def describe_situation(self, game_state):
        """Describe current situation"""

        situation_parts = []

        if game_state.get('detected_objects'):
            obj_count = len(game_state['detected_objects'])
            situation_parts.append(f"{obj_count} objects detected")

        if game_state.get('health', 100) < 50:
            situation_parts.append("low health")

        if not situation_parts:
            situation_parts.append("clear area")

        return ", ".join(situation_parts)

    async def capture_game_state(self):
        """Capture game state using YOUR vision system"""

        try:
            # Use YOUR existing vision system
            if not self.vision.is_game_active():
                return {'game_active': False}

            # Capture horizon image
            horizon_image = self.vision.capture_roi_image("HORIZON")

            game_state = {
                'game_active': True,
                'detected_objects': [],
                'health': 100,  # Would parse from UI
                'timestamp': time.time()
            }

            if horizon_image:
                detected_objects = self.vision.analyze_image(horizon_image)
                game_state['detected_objects'] = detected_objects

            return game_state

        except Exception as e:
            print(f"⚠️ Vision error: {e}")
            return {'game_active': False, 'error': str(e)}

    async def execute_action(self, decision):
        """Execute action using YOUR input controller"""

        action = decision.get('action', 'WAIT')
        duration = decision.get('duration', 1.0)
        reason = decision.get('reason', 'no reason')

        print(f"🎮 Action: {action} ({duration}s) - {reason}")

        try:
            if action == 'SMOOTH_LOOK':
                dx = decision.get('dx', 45)
                dy = decision.get('dy', 0)
                self.controller.smooth_look(dx, dy, duration)
            elif action in ['FORWARD', 'BACKWARD', 'STRAFE_LEFT', 'STRAFE_RIGHT',
                           'INTERACT', 'VATS', 'ATTACK', 'JUMP']:
                self.controller.press(action, duration)
            elif action == 'WAIT':
                await asyncio.sleep(duration)
            else:
                print(f"⚠️ Unknown action: {action}")

        except Exception as e:
            print(f"❌ Action failed: {e}")

    async def start_game_loop(self):
        """Main game loop"""

        # Start web server
        self.web_server.run()
        print("🌐 Web server started at http://localhost:8000")

        # Wait for game to be active
        print("👁️ Waiting for game to be active...")
        while True:
            if self.vision.is_game_active():
                self.vision.calibrate()
                print("✅ Game detected and calibrated")
                break
            await asyncio.sleep(3)

        # Main loop
        print("🎮 Starting game loop...")
        while True:
            try:
                # Check if we have active goals
                if not any(self.goals.values()):
                    print("💤 No active goals - waiting...")
                    await asyncio.sleep(5)
                    continue

                # Capture game state
                game_state = await self.capture_game_state()

                if not game_state.get('game_active'):
                    print("⏸️ Game not active - waiting...")
                    await asyncio.sleep(3)
                    continue

                # Make decision
                decision = await self.make_decision(game_state)

                # Execute action
                await self.execute_action(decision)

                # Brief pause
                await asyncio.sleep(1.0)

            except KeyboardInterrupt:
                print("🛑 Stopping AI...")
                break
            except Exception as e:
                print(f"❌ Loop error: {e}")
                await asyncio.sleep(2)

if __name__ == "__main__":
    async def main():
        ai = FixedFallout76AI()
        await ai.start_game_loop()

    print("🤖 Starting Fixed Fallout 76 AI...")
    asyncio.run(main())
