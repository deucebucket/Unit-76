# main_bot.py
# FIXED VERSION: Actually waits for START button and works properly
# Uses the original simple structure but with F76 intelligence

import time
import threading
import queue
from collections import deque
from vision_module import Vision
from input_emulator import ActionController
from local_llm_module import LocalBrain
from web_server_module import EnhancedWebServer
from rag_module import LongTermMemory
from smart_goal_generator import SmartGoalGenerator
import json

# --- Shared State & Command Queue ---
mission_log = deque(maxlen=50)
shared_state = {"status": "Idle", "log": list(mission_log), "cycle_count": 0, "execution_count": 0}
command_queue = queue.Queue()

def add_log(message, log_type="info"):
    """Enhanced logging with better formatting for dashboard."""
    timestamp = time.strftime('%H:%M:%S')
    formatted_message = f"[{timestamp}] {message}"
    mission_log.appendleft(formatted_message)
    shared_state["log"] = list(mission_log)

    if log_type == "error":
        print(f"❌ {formatted_message}")
    elif log_type == "success":
        print(f"✅ {formatted_message}")
    else:
        print(formatted_message)

class F76GoalManager:
    """Manages F76-specific goals with smart generation"""

    def __init__(self, knowledge_base=None):
        self.goals = {}
        self.smart_generator = SmartGoalGenerator(knowledge_base)
        self.setup_default_goals()

    def setup_default_goals(self):
        """Setup built-in F76 goals"""
        self.goals = {
            'explore_safely': {
                'name': 'Explore Safely',
                'description': 'Basic exploration with threat avoidance',
                'ai_context': 'Move forward cautiously, scan for threats, avoid combat when health is low, prioritize survival over objectives',
                'enabled': True,
                'priority': 5,
                'type': 'builtin'
            },
            'collect_junk': {
                'name': 'Collect Resources',
                'description': 'Gather junk and resources for crafting',
                'ai_context': 'Look for containers and junk items, use workbenches to scrap when found, manage inventory weight, prioritize valuable materials',
                'enabled': False,
                'priority': 4,
                'type': 'builtin'
            },
            'public_events': {
                'name': 'Public Events',
                'description': 'Monitor and participate in public events',
                'ai_context': 'Check map every 30 seconds for yellow hexagon event markers, fast travel to events immediately (always free), prioritize completion for rewards',
                'enabled': False,
                'priority': 8,
                'type': 'builtin'
            }
        }

    def get_active_goals(self):
        """Get list of currently enabled goals"""
        return [goal_id for goal_id, goal in self.goals.items() if goal.get('enabled', False)]

    def set_goal_state(self, goal_id, enabled):
        """Enable/disable a goal"""
        if goal_id in self.goals:
            self.goals[goal_id]['enabled'] = enabled
            add_log(f"🎯 Goal '{self.goals[goal_id]['name']}' {'enabled' if enabled else 'disabled'}")

    def add_custom_goal(self, goal_id, goal_data):
        """Add a new custom goal"""
        self.goals[goal_id] = goal_data
        add_log(f"📝 Added custom goal: {goal_data['name']}")

class IntelligentF76AI:
    """Main AI system that actually understands Fallout 76"""

    def __init__(self):
        # Initialize components
        self.vision = Vision()
        self.controller = ActionController()
        self.brain = LocalBrain()
        self.memory = LongTermMemory()
        self.goal_manager = F76GoalManager(self.memory)

        # Web server
        self.web_server = EnhancedWebServer(shared_state, command_queue)
        self.web_server.set_goal_manager(self.goal_manager, self.memory)

        # State
        self.running = False
        self.paused = False

        add_log("🧠 Intelligent Fallout 76 AI initialized")

    def start_web_server(self):
        """Start the web interface"""
        self.web_server.run()

    def wait_for_game(self):
        """Wait for Fallout 76 to be active"""
        add_log("👁️ Waiting for Fallout 76...")
        while not self.vision.is_game_active():
            add_log("⏳ Game not detected, waiting...")
            time.sleep(3)

        add_log("🎮 Fallout 76 detected!", "success")
        self.vision.calibrate()
        add_log("📐 Vision calibrated", "success")

    def get_current_context(self):
        """Get current situation context for AI decision making"""
        # Capture vision data
        horizon_image = self.vision.capture_roi_image("HORIZON")
        detected_objects = []

        if horizon_image:
            detected_objects = self.vision.analyze_image(horizon_image)

        # Get active goals
        active_goals = self.goal_manager.get_active_goals()

        # Build context string
        context_parts = []

        if detected_objects:
            obj_summary = f"{len(detected_objects)} objects detected: " + ", ".join([obj['label'] for obj in detected_objects[:3]])
            context_parts.append(f"VISION: {obj_summary}")
        else:
            context_parts.append("VISION: Clear area, no objects detected")

        if active_goals:
            goal_names = [self.goal_manager.goals[g]['name'] for g in active_goals]
            context_parts.append(f"ACTIVE GOALS: {', '.join(goal_names)}")
        else:
            context_parts.append("ACTIVE GOALS: Basic exploration")

        return "\n".join(context_parts)

    def make_intelligent_decision(self, context):
        """Make an AI decision based on current context"""
        # Try the brain first
        prompt = f"""You are an AI playing Fallout 76. Based on the current situation, choose ONE action.

CURRENT SITUATION:
{context}

AVAILABLE ACTIONS: FORWARD, BACKWARD, STRAFE_LEFT, STRAFE_RIGHT, JUMP, INTERACT, VATS, ATTACK, AIM, M (map), WAIT

Respond with JSON: {{"action": "ACTION_NAME", "duration": 2.0, "reason": "why you chose this"}}

Be strategic and safe. Explain your reasoning."""

        # Get AI decision
        brain_response = self.brain.get_plan(prompt)

        if brain_response and 'action' in brain_response:
            return brain_response

        # Fallback to simple logic if AI fails
        return self.fallback_decision(context)

    def fallback_decision(self, context):
        """Simple fallback logic when AI brain fails"""
        if "person" in context.lower() or "creature" in context.lower():
            return {"action": "VATS", "duration": 0.1, "reason": "Detected potential threat"}
        elif "container" in context.lower() and "collect" in context.lower():
            return {"action": "INTERACT", "duration": 1.0, "reason": "Found lootable container"}
        else:
            return {"action": "FORWARD", "duration": 2.0, "reason": "Continue exploration"}

    def execute_action(self, action_data):
        """Execute an action with proper F76 timing"""
        action = action_data.get('action', 'WAIT').upper()
        duration = action_data.get('duration', 1.0)
        reason = action_data.get('reason', 'No reason given')

        add_log(f"🎮 {action} - {reason}")

        # Execute the action
        if action == "M":
            # Special handling for map
            self.controller.press("M", duration=0.1)
            time.sleep(2.0)  # Give time to read map
            self.controller.press("M", duration=0.1)  # Close map
        elif action in ["FORWARD", "BACKWARD", "STRAFE_LEFT", "STRAFE_RIGHT", "JUMP", "INTERACT", "VATS", "ATTACK", "AIM", "WAIT"]:
            if action == "WAIT":
                time.sleep(duration)
            else:
                self.controller.press(action, duration=duration)
        else:
            add_log(f"❌ Unknown action: {action}", "error")

        # Update stats
        shared_state["execution_count"] = shared_state.get("execution_count", 0) + 1

    def main_loop(self):
        """Main AI decision loop"""
        add_log("🧠 Starting intelligent decision loop", "success")
        shared_state["status"] = "Running"

        cycle_count = 0

        while self.running:
            # Handle pause
            if self.paused:
                time.sleep(1)
                continue

            # Check if game is still active
            if not self.vision.is_game_active():
                add_log("⚠️ Game no longer detected, waiting...")
                self.wait_for_game()

            cycle_count += 1
            shared_state["cycle_count"] = cycle_count

            try:
                # Get current situation
                context = self.get_current_context()

                # Make intelligent decision
                action_data = self.make_intelligent_decision(context)

                # Execute action
                self.execute_action(action_data)

                # Brief pause between actions
                time.sleep(1.5)

            except Exception as e:
                add_log(f"💥 Error in main loop: {e}", "error")
                time.sleep(2)

        shared_state["status"] = "Idle"
        add_log("🛑 AI decision loop stopped")

    def start(self):
        """Start the AI system"""
        if self.running:
            add_log("⚠️ AI already running")
            return

        add_log("🚀 Starting Intelligent Fallout 76 AI", "success")
        self.running = True
        self.paused = False

        # Wait for game in separate thread to not block
        game_thread = threading.Thread(target=self.wait_for_game, daemon=True)
        game_thread.start()
        game_thread.join()

        # Start main loop
        main_thread = threading.Thread(target=self.main_loop, daemon=True)
        main_thread.start()

    def stop(self):
        """Stop the AI system"""
        add_log("🛑 Stopping AI system")
        self.running = False
        self.paused = False

    def pause(self):
        """Pause the AI system"""
        add_log("⏸️ Pausing AI system")
        self.paused = True
        shared_state["status"] = "Paused"

    def resume(self):
        """Resume the AI system"""
        add_log("▶️ Resuming AI system")
        self.paused = False
        shared_state["status"] = "Running"

def main():
    """Main entry point"""
    print("🧠 Initializing Intelligent Fallout 76 AI...")

    try:
        # Initialize AI system
        ai = IntelligentF76AI()

        # Start web server
        ai.start_web_server()

        add_log("✅ System ready - Use web interface to control AI", "success")
        add_log("🌐 Web interface: http://localhost:8000", "success")
        add_log("💤 Waiting for START command...", "success")

        # Command processing loop
        while True:
            try:
                # Wait for command from web interface
                cmd_obj = command_queue.get(timeout=1.0)

                if cmd_obj.command == 'start':
                    ai.start()
                elif cmd_obj.command == 'stop':
                    ai.stop()
                elif cmd_obj.command == 'pause':
                    ai.pause()
                elif cmd_obj.command == 'resume':
                    ai.resume()

            except queue.Empty:
                # No command received, continue
                continue
            except KeyboardInterrupt:
                add_log("🛑 Shutdown requested")
                break

    except Exception as e:
        add_log(f"💥 FATAL ERROR: {e}", "error")
        import traceback
        traceback.print_exc()

    finally:
        add_log("🔧 Shutting down...")
        if 'ai' in locals():
            ai.stop()
            if hasattr(ai, 'vision'):
                ai.vision.close()
            if hasattr(ai, 'controller'):
                ai.controller.close()
        add_log("✅ Shutdown complete")

if __name__ == "__main__":
    main()
