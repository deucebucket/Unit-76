# web_server_module.py
# Enhanced Web Server with Smart AI Goal Generation
# Now automatically generates AI context from simple user descriptions

import threading
import time
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import uvicorn
from smart_goal_generator import SmartGoalGenerator

class Command(BaseModel):
    command: str
    goal: Optional[str] = None

class GoalUpdate(BaseModel):
    goal_id: str
    enabled: bool

class SmartCustomGoal(BaseModel):
    goal_id: str
    name: str
    description: str  # Simple user description like "Complete Events"
    priority: int = 5

class GoalsBatch(BaseModel):
    goals: Dict[str, bool]

class EnhancedWebServer:
    def __init__(self, shared_state, command_queue):
        self.shared_state = shared_state
        self.command_queue = command_queue
        self.app = FastAPI()

        # Goal manager and smart generator
        self.goal_manager = None
        self.smart_generator = None

        self.setup_routes()

    def set_goal_manager(self, goal_manager, knowledge_base=None):
        """Connect goal manager and create smart generator"""
        self.goal_manager = goal_manager
        self.smart_generator = SmartGoalGenerator(knowledge_base)
        print("🌐 Enhanced goal manager with smart AI generation connected")

    def setup_routes(self):
        @self.app.get("/")
        async def get_index():
            headers = {
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
            return FileResponse('index.html', headers=headers)

        @self.app.get("/status")
        async def get_status():
            status_data = {
                **self.shared_state,
                'timestamp': time.time()
            }

            if self.goal_manager:
                active_goals = self.goal_manager.get_active_goals()
                status_data['active_goals'] = active_goals
                status_data['goal_count'] = len(active_goals)
                status_data['total_goals'] = len(self.goal_manager.goals)

                status_data['ai_intelligence'] = {
                    'current_strategy': self.shared_state.get('current_strategy', 'unknown'),
                    'current_location': self.shared_state.get('current_location', 'unknown'),
                    'execution_count': self.shared_state.get('execution_count', 0),
                    'cycle_count': self.shared_state.get('cycle_count', 0)
                }

            return status_data

        @self.app.post("/command")
        async def post_command(command: Command):
            if command.command in ["start", "stop", "pause", "resume"]:
                self.command_queue.put(command)
                return {"message": f"Command '{command.command}' received by intelligent AI."}
            else:
                raise HTTPException(status_code=400, detail="Invalid command")

        @self.app.get("/goals")
        async def get_goals():
            """Get all available goals with enhanced F76 context"""
            if not self.goal_manager:
                raise HTTPException(status_code=400, detail="Goal manager not available")

            goals_data = {}
            for goal_id, goal_info in self.goal_manager.goals.items():
                goals_data[goal_id] = {
                    'id': goal_id,
                    'name': goal_info.get('name', goal_id.replace('_', ' ').title()),
                    'description': goal_info.get('description', 'No description'),
                    'enabled': goal_info.get('enabled', False),
                    'priority': goal_info.get('priority', 5),
                    'type': goal_info.get('type', 'unknown'),
                    'ai_context': goal_info.get('ai_context', 'No AI context provided'),
                    'success_indicators': goal_info.get('success_indicators', []),
                    'failure_conditions': goal_info.get('failure_conditions', [])
                }

            return {
                'goals': goals_data,
                'total_count': len(goals_data),
                'active_count': len(self.goal_manager.get_active_goals()),
                'custom_count': len([g for g in goals_data.values() if g['type'] in ['custom', 'ai_generated']])
            }

        @self.app.post("/goals/set")
        async def set_goal(goal_update: GoalUpdate):
            if not self.goal_manager:
                raise HTTPException(status_code=400, detail="Goal manager not available")

            try:
                self.goal_manager.set_goal_state(goal_update.goal_id, goal_update.enabled)
                goal_name = self.goal_manager.goals[goal_update.goal_id].get('name', goal_update.goal_id)

                return {
                    'status': 'success',
                    'goal_id': goal_update.goal_id,
                    'goal_name': goal_name,
                    'enabled': goal_update.enabled,
                    'message': f"Goal '{goal_name}' {'enabled' if goal_update.enabled else 'disabled'}"
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to set goal: {str(e)}")

        @self.app.post("/goals/batch")
        async def set_goals_batch(goals_batch: GoalsBatch):
            if not self.goal_manager:
                raise HTTPException(status_code=400, detail="Goal manager not available")

            try:
                results = {}
                for goal_id, enabled in goals_batch.goals.items():
                    if goal_id in self.goal_manager.goals:
                        self.goal_manager.set_goal_state(goal_id, enabled)
                        results[goal_id] = enabled

                return {
                    'status': 'success',
                    'updated_goals': results,
                    'message': f"Updated {len(results)} goals"
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to set goals: {str(e)}")

        @self.app.post("/goals/smart/generate")
        async def generate_smart_goal(smart_goal: SmartCustomGoal):
            """Generate AI context from simple user description"""
            if not self.smart_generator:
                raise HTTPException(status_code=400, detail="Smart goal generator not available")

            try:
                # Generate the smart context
                generated_data = self.smart_generator.generate_goal_context(
                    smart_goal.description,
                    smart_goal.name
                )

                # Override user priority if specified
                if smart_goal.priority != 5:
                    generated_data['priority'] = smart_goal.priority

                return {
                    'status': 'success',
                    'generated_goal': generated_data,
                    'ai_context_preview': generated_data['ai_context'][:200] + '...',
                    'message': f"AI generated context for '{smart_goal.description}'"
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to generate goal context: {str(e)}")

        @self.app.post("/goals/smart/add")
        async def add_smart_goal(smart_goal: SmartCustomGoal):
            """Generate AI context and add the goal in one step"""
            if not self.goal_manager or not self.smart_generator:
                raise HTTPException(status_code=400, detail="Smart goal system not available")

            try:
                # Generate the smart context
                generated_data = self.smart_generator.generate_goal_context(
                    smart_goal.description,
                    smart_goal.name
                )

                # Override user priority if specified
                if smart_goal.priority != 5:
                    generated_data['priority'] = smart_goal.priority

                # Add enabled flag
                generated_data['enabled'] = True

                # Add to goal manager
                self.goal_manager.add_custom_goal(smart_goal.goal_id, generated_data)

                return {
                    'status': 'success',
                    'goal_id': smart_goal.goal_id,
                    'goal_name': generated_data['name'],
                    'ai_context': generated_data['ai_context'],
                    'message': f"Smart goal '{generated_data['name']}' created with AI-generated context"
                }
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to create smart goal: {str(e)}")

        @self.app.delete("/goals/custom/{goal_id}")
        async def delete_custom_goal(goal_id: str):
            if not self.goal_manager:
                raise HTTPException(status_code=400, detail="Goal manager not available")

            try:
                if goal_id not in self.goal_manager.goals:
                    raise HTTPException(status_code=404, detail="Goal not found")

                goal_info = self.goal_manager.goals[goal_id]
                if goal_info.get('type') not in ['custom', 'ai_generated']:
                    raise HTTPException(status_code=400, detail="Cannot delete built-in goals")

                goal_name = goal_info.get('name', goal_id)
                del self.goal_manager.goals[goal_id]
                self.goal_manager.save_custom_goals()

                return {
                    'status': 'success',
                    'goal_id': goal_id,
                    'message': f"Goal '{goal_name}' deleted successfully"
                }
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to delete goal: {str(e)}")

        @self.app.get("/goals/suggestions/{partial_input}")
        async def get_goal_suggestions(partial_input: str):
            """Get smart goal suggestions based on partial input"""
            if not self.smart_generator:
                return {'suggestions': []}

            try:
                suggestions = self.smart_generator.get_goal_suggestions(partial_input)
                return {
                    'suggestions': suggestions,
                    'count': len(suggestions)
                }
            except Exception as e:
                return {'suggestions': [], 'error': str(e)}

        @self.app.get("/goals/templates")
        async def get_goal_templates():
            """Get F76-specific goal templates with AI-generated contexts"""
            templates = {
                'complete_events': {
                    'name': 'Complete Public Events',
                    'description': 'Monitor and participate in all public events',
                    'user_input_example': 'Complete Events',
                    'ai_generated_context': 'Monitor map every 30 seconds for yellow hexagon event markers, fast travel to events immediately (always free), prioritize high-XP events like Radiation Rumble and Scorched Earth'
                },
                'daily_ops': {
                    'name': 'Daily Operations',
                    'description': 'Complete daily ops for Elder rank',
                    'user_input_example': 'Daily Ops',
                    'ai_generated_context': 'Access Daily Ops via map menu, join team if needed, complete objectives efficiently, prioritize Elder rank (under 8 minutes) for best rewards'
                },
                'legendary_farming': {
                    'name': 'Legendary Farming',
                    'description': 'Farm legendary items and scrip',
                    'user_input_example': 'Farm Legendaries',
                    'ai_generated_context': 'Target high-level areas like West Tek, Whitespring Golf Club, or active public events. Look for crown icons on enemies, use VATS to identify legendary status'
                },
                'vendor_runs': {
                    'name': 'Vendor Shopping',
                    'description': 'Visit vendors for trading',
                    'user_input_example': 'Vendor Shopping',
                    'ai_generated_context': 'Fast travel to major vendor hubs: Whitespring, Foundation, Crater, Fort Atlas. Check for good legendary items, sell excess gear, manage caps efficiently'
                },
                'resource_farming': {
                    'name': 'Resource Collection',
                    'description': 'Collect crafting materials',
                    'user_input_example': 'Collect Resources',
                    'ai_generated_context': 'Visit high-yield locations like Charleston Herald, Sugar Grove, or workshops. Prioritize adhesive, ballistic fiber, aluminum, lead'
                }
            }

            return {
                'templates': templates,
                'template_count': len(templates),
                'usage': 'Just type the simple description (like "Complete Events") and the AI will generate the detailed context automatically!'
            }

        @self.app.get("/ai/intelligence")
        async def get_ai_intelligence():
            if not self.goal_manager:
                return {'intelligence': 'unavailable'}

            intelligence_data = {
                'current_strategy': self.shared_state.get('current_strategy', 'unknown'),
                'current_location': self.shared_state.get('current_location', 'unknown'),
                'active_goals': self.goal_manager.get_active_goals(),
                'decision_cycles': self.shared_state.get('cycle_count', 0),
                'actions_executed': self.shared_state.get('execution_count', 0),
                'ai_status': self.shared_state.get('status', 'unknown'),
                'knowledge_base': 'Fallout 76 Deep Game Mechanics + Smart Goal Generation',
                'intelligence_level': 'Enhanced with F76 Expertise + AI Context Generation'
            }

            return intelligence_data

    def run(self):
        def run_server():
            uvicorn.run(self.app, host="0.0.0.0", port=8000, log_level="warning")

        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        print("🌐 Enhanced Intelligent F76 Web Server with Smart Goal Generation started")
        print("📱 Now with AI-powered goal context generation!")

# Maintain backward compatibility
WebServer = EnhancedWebServer
