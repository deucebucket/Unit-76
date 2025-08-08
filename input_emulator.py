# input_emulator.py
# FIXED VERSION: Proper Fallout 76 key mappings that actually work

import time
from evdev import UInput, ecodes as e

# --- CORRECT Fallout 76 Key Mapping ---
ACTION_TO_KEY = {
    # Movement
    "FORWARD": e.KEY_W,
    "BACKWARD": e.KEY_S,
    "STRAFE_LEFT": e.KEY_A,
    "STRAFE_RIGHT": e.KEY_D,
    "JUMP": e.KEY_SPACE,
    "SPRINT": e.KEY_LEFTSHIFT,

    # Interaction
    "INTERACT": e.KEY_E,
    "RELOAD": e.KEY_R,

    # Combat
    "VATS": e.KEY_Q,
    "ATTACK": e.BTN_LEFT,
    "AIM": e.BTN_RIGHT,

    # Interface
    "M": e.KEY_M,           # Map (correct for F76)
    "TAB": e.KEY_TAB,       # Pip-Boy
    "ESC": e.KEY_ESC,       # Menu/back
    "ENTER": e.KEY_ENTER,   # Confirm

    # Other F76 keys
    "C": e.KEY_C,           # Character
    "I": e.KEY_I,           # Inventory
    "F": e.KEY_F,           # Flashlight
    "CTRL": e.KEY_LEFTCTRL, # Sneak
}

class ActionController:
    """Fixed controller with correct F76 mappings"""

    def __init__(self):
        self.device = None
        capabilities = {
            e.EV_KEY: list(ACTION_TO_KEY.values()),
            e.EV_REL: [e.REL_X, e.REL_Y],
        }

        try:
            print("🎮 Creating Fixed Fallout 76 Action Controller...")
            self.device = UInput(capabilities, name="Fixed_F76_Controller")
            print("✅ Fixed Action Controller ready!")
        except Exception as error:
            print(f"\n❌ PERMISSION ERROR ❌")
            print(f"Details: {error}")
            print("🔧 Solution: Run with sudo privileges")
            print("   sudo python3 main_bot.py")
            raise error

    def press(self, action_name, duration=0.1):
        """Execute key press with proper F76 timing"""

        action_name = action_name.upper()

        # Special logging for key actions
        if action_name == "M":
            print(f"🗺️ Opening map")
        elif action_name == "TAB":
            print(f"📟 Opening Pip-Boy")
        elif action_name == "VATS":
            print(f"🎯 Activating VATS")
        elif action_name == "INTERACT":
            print(f"🤝 Interacting")
        elif action_name in ["FORWARD", "BACKWARD", "STRAFE_LEFT", "STRAFE_RIGHT"]:
            print(f"🚶 Moving: {action_name} for {duration}s")
        else:
            print(f"🎮 {action_name} for {duration}s")

        key_code = ACTION_TO_KEY.get(action_name)
        if key_code is None:
            print(f"❌ Unknown action: {action_name}")
            print(f"Available actions: {list(ACTION_TO_KEY.keys())}")
            return False

        try:
            # Press key
            self.device.write(e.EV_KEY, key_code, 1)
            self.device.syn()
            time.sleep(duration)

            # Release key
            self.device.write(e.EV_KEY, key_code, 0)
            self.device.syn()
            return True

        except Exception as e:
            print(f"❌ Failed to execute {action_name}: {e}")
            return False

    def smooth_look(self, dx, dy, duration=0.1):
        """Smooth mouse movement for camera control"""
        print(f"👀 Looking: dx={dx}, dy={dy}")

        steps = max(10, int(abs(dx) + abs(dy)) // 5)

        for step in range(steps):
            step_dx = dx // steps
            step_dy = dy // steps

            self.device.write(e.EV_REL, e.REL_X, step_dx)
            self.device.write(e.EV_REL, e.REL_Y, step_dy)
            self.device.syn()
            time.sleep(duration / steps)

    def emergency_stop_all(self):
        """Release all keys in case of stuck state"""
        print("🚨 Emergency: Releasing all keys")

        # Release all possible keys
        for key_code in ACTION_TO_KEY.values():
            if isinstance(key_code, int):  # Skip mouse buttons for now
                try:
                    self.device.write(e.EV_KEY, key_code, 0)
                except:
                    pass

        self.device.syn()

    def close(self):
        """Clean shutdown"""
        if self.device:
            print("🔧 Shutting down Action Controller...")
            self.emergency_stop_all()
            time.sleep(0.1)
            self.device.close()
            print("✅ Action Controller closed safely")
        else:
            print("⚠️ Action Controller was not initialized")
