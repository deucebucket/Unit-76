# web_server_enhanced.py
# Enhanced version of your web_server_module.py with goal checkboxes
# Adds persistent goal management to your existing web interface

import threading
import time
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn

class GoalUpdate(BaseModel):
    goal_id: str
    enabled: bool

class GoalsBatch(BaseModel):
    goals: Dict[str, bool]

class ServerConfig(BaseModel):
    kobold_server_url: str

class EnhancedFallout76WebServer:
    """Enhanced web server with persistent goals and KoboldCpp integration"""

    def __init__(self, ai_system=None):
        self.ai_system = ai_system
        self.app = FastAPI()

        # Enhanced stats tracking
        self.stats = {
            'session_start': None,
            'decisions_made': 0,
            'strategic_calls': 0,
            'local_calls': 0,
            'events_completed': 0,
            'items_managed': 0,
            'locations_discovered': 0,
            'current_action': 'Idle',
            'current_goal': 'None',
            'kobold_status': 'Unknown'
        }

        self.setup_routes()

    def setup_routes(self):
        """Setup all API routes"""

        @self.app.get("/")
        async def get_index():
            """Serve the updated HTML interface"""
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
            return FileResponse('enhanced_index.html', headers=headers)

        @self.app.get("/status")
        async def get_status():
            """Get comprehensive system status"""

            if not self.ai_system:
                return {
                    'status': 'not_initialized',
                    'message': 'AI system not connected'
                }

            # Get goal states
            goal_states = self.ai_system.get_goal_states()
            active_goals = [goal_id for goal_id, enabled in goal_states.items() if enabled]

            # Get session report
            session_report = self.ai_system.get_session_report()

            # Update stats
            self.stats.update({
                'current_goal': active_goals[0] if active_goals else 'None',
                'kobold_status': 'Connected' if self.ai_system.decision_maker.remote_available else 'Disconnected',
                **session_report
            })

            return {
                'status': 'running' if active_goals else 'idle',
                'stats': self.stats,
                'goal_states': goal_states,
                'active_goals': active_goals,
                'session_report': session_report,
                'timestamp': time.time()
            }

        @self.app.post("/goals/set")
        async def set_goal(goal_update: GoalUpdate):
            """Enable/disable a single goal"""

            if not self.ai_system:
                raise HTTPException(status_code=400, detail="AI system not initialized")

            try:
                self.ai_system.set_goal_state(goal_update.goal_id, goal_update.enabled)

                return {
                    'status': 'success',
                    'goal_id': goal_update.goal_id,
                    'enabled': goal_update.enabled,
                    'message': f"Goal '{goal_update.goal_id}' {'enabled' if goal_update.enabled else 'disabled'}"
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to set goal: {str(e)}")

        @self.app.post("/goals/batch")
        async def set_goals_batch(goals_batch: GoalsBatch):
            """Set multiple goals at once"""

            if not self.ai_system:
                raise HTTPException(status_code=400, detail="AI system not initialized")

            try:
                results = {}
                for goal_id, enabled in goals_batch.goals.items():
                    self.ai_system.set_goal_state(goal_id, enabled)
                    results[goal_id] = enabled

                return {
                    'status': 'success',
                    'updated_goals': results,
                    'message': f"Updated {len(results)} goals"
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to set goals: {str(e)}")

        @self.app.get("/goals")
        async def get_goals():
            """Get all available goals and their states"""

            if not self.ai_system:
                raise HTTPException(status_code=400, detail="AI system not initialized")

            goal_states = self.ai_system.get_goal_states()
            goal_details = {}

            for goal_id, enabled in goal_states.items():
                if goal_id in self.ai_system.goal_manager.goals:
                    goal = self.ai_system.goal_manager.goals[goal_id]
                    goal_details[goal_id] = {
                        'id': goal.id,
                        'name': goal.name,
                        'description': goal.description,
                        'enabled': enabled,
                        'priority': goal.priority,
                        'success_count': goal.success_count,
                        'failure_count': goal.failure_count
                    }

            return {
                'goals': goal_details,
                'total_count': len(goal_details),
                'active_count': sum(1 for enabled in goal_states.values() if enabled)
            }

        @self.app.post("/config/kobold")
        async def update_kobold_config(config: ServerConfig):
            """Update KoboldCpp server configuration"""

            if not self.ai_system:
                raise HTTPException(status_code=400, detail="AI system not initialized")

            try:
                # Update the decision maker's server URL
                old_url = self.ai_system.decision_maker.remote_server_url
                self.ai_system.decision_maker.remote_server_url = config.kobold_server_url

                # Test new connection
                self.ai_system.decision_maker._test_kobold_connection()

                return {
                    'status': 'success',
                    'old_url': old_url,
                    'new_url': config.kobold_server_url,
                    'connected': self.ai_system.decision_maker.remote_available,
                    'model_detected': getattr(self.ai_system.decision_maker, 'is_openhermes', False)
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to update config: {str(e)}")

        @self.app.post("/control/start")
        async def start_ai():
            """Start AI assistance - called by START button"""

            if not self.ai_system:
                raise HTTPException(status_code=400, detail="AI system not initialized")

            self.ai_system.start_ai()  # Signal AI to start

            return {
                'status': 'started',
                'message': 'AI assistance started',
                'active_goals': [goal_id for goal_id, enabled in self.ai_system.get_goal_states().items() if enabled]
            }

        @self.app.post("/control/stop")
        async def stop_ai():
            """Stop AI assistance - called by STOP button"""

            if not self.ai_system:
                raise HTTPException(status_code=400, detail="AI system not initialized")

            self.ai_system.stop_ai()  # Signal AI to stop

            return {
                'status': 'stopped',
                'message': 'AI assistance stopped'
            }

        @self.app.get("/world/locations")
        async def get_world_locations():
            """Get discovered world locations"""

            if not self.ai_system:
                return {'locations': {}, 'count': 0}

            locations = {}
            for name, location in self.ai_system.world_db.locations.items():
                locations[name] = {
                    'name': location.name,
                    'type': location.location_type,
                    'visit_count': location.visit_count,
                    'last_visited': location.last_visited,
                    'notes': location.notes
                }

            return {
                'locations': locations,
                'count': len(locations)
            }

        @self.app.get("/world/items")
        async def get_item_knowledge():
            """Get AI's item knowledge database"""

            if not self.ai_system:
                return {'items': {}, 'count': 0}

            items = {}
            for name, item in self.ai_system.world_db.item_knowledge.items():
                items[name] = {
                    'name': item.item_name,
                    'type': item.item_type,
                    'is_god_roll': item.is_god_roll,
                    'action': item.keep_or_sell,
                    'rarity': item.rarity,
                    'value': item.vendor_value
                }

            return {
                'items': items,
                'count': len(items),
                'god_rolls': sum(1 for item in self.ai_system.world_db.item_knowledge.values() if item.is_god_roll)
            }

    def set_ai_system(self, ai_system):
        """Connect AI system to web server"""
        self.ai_system = ai_system
        print("🌐 AI system connected to web server")

    def run(self, host="0.0.0.0", port=8000):
        """Run the web server"""

        def run_server():
            uvicorn.run(self.app, host=host, port=port, log_level="warning")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print(f"🌐 Enhanced web server started at http://{host}:{port}")
        print("📱 Access from phone/tablet for goal management")

if __name__ == "__main__":
    # Test server standalone
    server = EnhancedFallout76WebServer()
    server.run()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Server stopped")
