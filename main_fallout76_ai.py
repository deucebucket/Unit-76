# main_fallout76_ai.py
# Main integration file - connects all components together

import asyncio
import time
from comprehensive_fo76_ai import ComprehensiveAI, DeckyComprehensivePlugin
from enhanced_web_server import EnhancedFallout76WebServer
from vision_module import Vision
from input_emulator import ActionController

class IntegratedFallout76System:
    """Complete integration of all system components"""

    def __init__(self):
        print("🚀 Initializing Integrated Fallout 76 AI System...")

        # Core AI system
        self.config = {
            'kobold_server_url': 'http://100.64.150.78:5001',
            'local_model': 'gemma:2b',
            'update_frequency': 1.0
        }

        # Initialize components
        self.ai_system = ComprehensiveAI(self.config)
        self.web_server = EnhancedFallout76WebServer(self.ai_system)

        # Vision and input (your existing modules)
        self.vision = Vision()
        self.input_controller = ActionController()

        print("✅ All components initialized")

    async def start_complete_system(self):
        """Start the complete AI system with all components"""

        # Start web server
        self.web_server.run(port=8000)

        # Test vision system
        print("🔧 Calibrating vision system...")
        if self.vision.is_game_active():
            self.vision.calibrate()
            print("👁️ Vision system calibrated")
        else:
            print("⚠️ Game not detected - vision will calibrate when game starts")

        # Start main game loop
        print("🎮 Starting main AI loop...")
        await self.main_game_loop()

    async def main_game_loop(self):
        """Main game loop integrating vision, AI decisions, and input"""

        running = True

        while running:
            try:
                # Check if any goals are active
                goal_states = self.ai_system.get_goal_states()
                active_goals = [goal_id for goal_id, enabled in goal_states.items() if enabled]

                if not active_goals:
                    # No active goals - wait
                    await asyncio.sleep(2)
                    continue

                # Capture current game state
                game_state = await self.capture_game_state()

                # Update AI context
                await self.ai_system.update_context(game_state)

                # Make intelligent decision
                decision = await self.ai_system.make_intelligent_decision()

                # Execute decision
                await self.execute_decision(decision)

                # Brief pause
                await asyncio.sleep(self.config['update_frequency'])

            except KeyboardInterrupt:
                print("🛑 Shutdown requested")
                running = False
            except Exception as e:
                print(f"❌ Game loop error: {e}")
                await asyncio.sleep(1)

    async def capture_game_state(self):
        """Capture current game state using vision system"""

        try:
            # Capture different regions of the screen
            horizon_image = self.vision.capture_roi_image("HORIZON")
            compass_image = self.vision.capture_roi_image("COMPASS")

            game_state = {
                'timestamp': time.time(),
                'game_active': self.vision.is_game_active(),
                'detected_objects': [],
                'location': 'unknown',
                'level': 25,  # Would extract from UI
                'health': 100,  # Would extract from health bar
                'weight': 180,
                'max_weight': 220,
                'caps': 1500,
                'event_active': False,  # Would detect from UI
                'near_water': False,    # Would detect visually
                'enemies': [],
                'loot': [],
                'inventory': []
            }

            # Analyze horizon for objects
            if horizon_image:
                detected_objects = self.vision.analyze_image(horizon_image)
                game_state['detected_objects'] = detected_objects

                # Classify situation based on objects
                if any('person' in obj['label'].lower() for obj in detected_objects):
                    game_state['enemies'] = ['person_detected']

                if any('container' in obj['label'].lower() for obj in detected_objects):
                    game_state['loot'] = ['container_detected']

            return game_state

        except Exception as e:
            print(f"⚠️ Vision capture failed: {e}")
            # Return minimal state
            return {
                'timestamp': time.time(),
                'game_active': False,
                'location': 'unknown',
                'level': 1,
                'health': 100
            }

    async def execute_decision(self, decision):
        """Execute AI decision using input controller"""

        action = decision.get('action', 'WAIT')
        duration = decision.get('duration', 1.0)
        reason = decision.get('reason', 'No reason')
        source = decision.get('source', 'unknown')

        print(f"🎮 Executing ({source}): {action} for {duration}s - {reason}")

        try:
            # Map actions to input controller methods
            if action == 'FORWARD':
                self.input_controller.press('FORWARD', duration)
            elif action == 'BACKWARD':
                self.input_controller.press('BACKWARD', duration)
            elif action == 'STRAFE_LEFT':
                self.input_controller.press('STRAFE_LEFT', duration)
            elif action == 'STRAFE_RIGHT':
                self.input_controller.press('STRAFE_RIGHT', duration)
            elif action == 'INTERACT':
                self.input_controller.press('INTERACT', duration)
            elif action == 'VATS':
                self.input_controller.press('VATS', duration)
            elif action == 'ATTACK':
                self.input_controller.press('ATTACK', duration)
            elif action == 'SMOOTH_LOOK':
                dx = decision.get('dx', 0)
                dy = decision.get('dy', 0)
                self.input_controller.smooth_look(dx, dy, duration)
            elif action == 'WAIT':
                await asyncio.sleep(duration)
            else:
                print(f"⚠️ Unknown action: {action}")

        except Exception as e:
            print(f"❌ Action execution failed: {e}")

# For Decky Plugin Integration
class DeckyIntegratedPlugin(DeckyComprehensivePlugin):
    """Enhanced Decky plugin with complete system integration"""

    def __init__(self):
        super().__init__()
        self.integrated_system = None

    async def initialize_complete_system(self, kobold_server_url='http://100.64.150.78:5001'):
        """Initialize the complete integrated system"""

        # Update config
        self.config['kobold_server_url'] = kobold_server_url

        # Initialize integrated system
        self.integrated_system = IntegratedFallout76System()
        self.ai_system = self.integrated_system.ai_system

        return {
            'status': 'initialized',
            'components': ['AI System', 'Web Server', 'Vision', 'Input Controller'],
            'kobold_server': kobold_server_url,
            'kobold_connected': self.ai_system.decision_maker.remote_available,
            'available_goals': list(self.ai_system.goal_manager.goals.keys())
        }

    async def start_integrated_ai(self):
        """Start the complete AI system"""

        if not self.integrated_system:
            return {'error': 'System not initialized'}

        # Start the integrated system
        asyncio.create_task(self.integrated_system.start_complete_system())

        return {
            'status': 'started',
            'message': 'Complete AI system is now running',
            'web_interface': 'http://localhost:8000',
            'components_active': ['Vision', 'AI Brain', 'Input Controller', 'Web Interface']
        }

if __name__ == "__main__":
    # Test the integrated system
    async def main():
        system = IntegratedFallout76System()
        await system.start_complete_system()

    print("🤖 Starting Integrated Fallout 76 AI System...")
    asyncio.run(main())
