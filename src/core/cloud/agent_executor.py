"""Agent execution engine - receives natural language instructions and executes via VLM feedback loop"""
import time
import base64
from typing import Optional, Dict, Any, List
from enum import Enum


class AgentState(Enum):
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_FEEDBACK = "waiting_feedback"
    DONE = "done"
    ERROR = "error"


class AgentExecutor:
    """Agent executor that processes natural language instructions through VLM feedback loop"""

    def __init__(self, communicator, screen_capture, touch_executor, config=None, device_serial: str = ""):
        self.communicator = communicator
        self.screen_capture = screen_capture
        self.touch_executor = touch_executor
        self.config = config or {}
        self.device_serial = device_serial
        self.state = AgentState.IDLE
        self.conversation_history: List[Dict[str, str]] = []
        self.session_id: Optional[str] = None
        self.model_tag: str = config.get('inference', {}).get('model_tag', 'exploration_deep') if config else 'exploration_deep'
        self.device_width = 1920
        self.device_height = 1080

    def send_instruction(self, instruction: str) -> Dict[str, Any]:
        """Send natural language instruction to server agent and execute response"""
        self.state = AgentState.THINKING
        
        # Validate dependencies
        if not self.communicator:
            return {"status": "error", "message": "Communicator not initialized"}
        if not self.screen_capture:
            return {"status": "error", "message": "Screen capture module not initialized"}
        
        # Capture screenshot
        if self.device_serial:
            screenshot_result = self.screen_capture.capture_screen(self.device_serial)
        else:
            screenshot_result = None
        if not screenshot_result:
            return {"status": "error", "message": "Screenshot capture failed"}
        
        # Handle screenshot tuple or direct bytes
        if isinstance(screenshot_result, tuple):
            success, img_bytes = screenshot_result
            if not success:
                return {"status": "error", "message": "Screenshot capture failed"}
        else:
            img_bytes = screenshot_result
            
        img_b64 = base64.b64encode(img_bytes).decode("utf-8")
        
        # Get device info
        device_info = {}
        if hasattr(self.communicator, 'get_device_info') and self.communicator.get_device_info:
            device_info = self.communicator.get_device_info() or {}
        self.device_width = device_info.get('width', self.device_width)
        self.device_height = device_info.get('height', self.device_height)
        
        # Send to agent
        try:
            response = self.communicator.send_request("agent_chat", {
                "instruction": instruction,
                "screenshot": img_b64,
                "device_width": self.device_width,
                "device_height": self.device_height,
                "model_tag": self.model_tag,
                "history": self.conversation_history[-10:] if self.conversation_history else [],
                "session_id": self.session_id or ""
            })
        except Exception as e:
            self.state = AgentState.ERROR
            return {"status": "error", "message": f"Agent request failed: {str(e)}"}
            
        if not response or response.get("status") != "success":
            self.state = AgentState.ERROR
            return response or {"status": "error", "message": "No response from server"}

        self.session_id = response.get("session_id", self.session_id)
        self.conversation_history.append({"role": "user", "content": instruction})
        self.conversation_history.append({"role": "assistant", "content": response.get("reply", "")})

        actions = response.get("actions", [])
        
        if not actions:
            self.state = AgentState.DONE
            return {"status": "success", "reply": response.get("reply", "Done")}
        
        # Execute actions
        self.state = AgentState.EXECUTING
        
        if not self.touch_executor:
            self.state = AgentState.ERROR
            return {"status": "error", "message": "Touch executor not initialized"}
        
        execution_results = []
        for action in actions:
            try:
                result = self._execute_action(action)
            except Exception as e:
                result = {"action": action.get("type", "unknown"), "success": False, "error": str(e)}
            execution_results.append(result)
            
            if not result.get("success"):
                self.state = AgentState.ERROR
                break
        
        self.state = AgentState.DONE
        return {
            "status": "success",
            "reply": response.get("reply", "Done"),
            "execution_results": execution_results,
            "actions": actions
        }

    def reset_conversation(self):
        """Reset agent conversation context"""
        self.conversation_history = []
        self.session_id = None
        self.state = AgentState.IDLE

    def _execute_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single action"""
        if not self.touch_executor:
            return {"action": "error", "success": False, "error": "Touch executor not initialized"}
        
        action_type = action.get("type", "")
        params = action.get("params", {})
        
        try:
            if action_type == "tap":
                x = int(params["x"] * self.device_width / 1920) if params.get("x", 0) <= 1 else int(params["x"])
                y = int(params["y"] * self.device_height / 1080) if params.get("y", 0) <= 1 else int(params["y"])
                self.touch_executor.safe_press(x, y)
            elif action_type == "swipe":
                x1 = int(params["x1"]) if params.get("x1", 0) > 1 else int(params["x1"] * self.device_width / 1920)
                y1 = int(params["y1"]) if params.get("y1", 0) > 1 else int(params["y1"] * self.device_height / 1080)
                x2 = int(params["x2"]) if params.get("x2", 0) > 1 else int(params["x2"] * self.device_width / 1920)
                y2 = int(params["y2"]) if params.get("y2", 0) > 1 else int(params["y2"] * self.device_height / 1080)
                duration = params.get("duration", 300)
                self.touch_executor.safe_swipe(x1, y1, x2, y2, duration=duration)
            elif action_type == "wait":
                time.sleep(params.get("duration", 1.0))
            elif action_type == "screenshot_check":
                pass
            else:
                return {"action": action_type, "success": False, "error": f"Unknown action: {action_type}"}
                
            return {"action": action_type, "success": True}
        except Exception as e:
            return {"action": action_type, "success": False, "error": str(e)}
