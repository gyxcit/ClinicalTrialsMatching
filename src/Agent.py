"""Agent module defining an intelligent agent with memory and tool capabilities."""
import json
import logging
from typing import Optional
from src.ModelClient import ModelClient
from src.memory import Memory
from src.tools import TOOL_MAP, TOOLS

# Configure logging
logger = logging.getLogger(__name__)


class Agent(ModelClient):
    """Intelligent agent with memory and tool capabilities."""

    def __init__(
        self,
        name: str = "assistant",
        system_prompt: str = "You are a helpful assistant.",
        model: str = "groq/llama-3.3-70b-versatile",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        max_tool_iterations: int = 5,
    ):
        super().__init__(model=model, api_key=api_key, api_base=api_base)

        self.name = name
        self.memory = Memory()
        self.system_role = system_prompt
        self.max_tool_iterations = max_tool_iterations

        # tools expected as list of tool def
        self.tools = TOOLS if TOOLS else None
        self.tool_map = TOOL_MAP

    def chat(self, user_message: str) -> str:
        """Send a message to the agent with tool support and error handling.
        
        Args:
            user_message: The user's message to send to the agent
            
        Returns:
            The agent's response as a string
            
        Raises:
            Exception: If tool execution fails or max iterations exceeded
        """
        try:
            # build messages
            messages = [{"role": "system", "content": self.system_role}]
            messages += self.memory.get()
            messages.append({"role": "user", "content": user_message})

            iteration = 0
            while iteration < self.max_tool_iterations:
                # Call the model
                response = self.generate_response(messages, tools=self.tools)
                assistant_message = response["choices"][0]["message"]
                logger.debug(f"Assistant message: {assistant_message}")
                
                # Check if tool is requested - use hasattr for Message objects
                has_tool_calls = (hasattr(assistant_message, 'tool_calls') and assistant_message.tool_calls) or \
                                (isinstance(assistant_message, dict) and "tool_calls" in assistant_message and assistant_message["tool_calls"])
                
                if has_tool_calls:
                    iteration += 1
                    logger.info(f"Tool iteration {iteration}/{self.max_tool_iterations}")
                    
                    # Get tool_calls list (works for both Message objects and dicts)
                    tool_calls = assistant_message.tool_calls if hasattr(assistant_message, 'tool_calls') else assistant_message["tool_calls"]
                    
                    # Add assistant message with tool_calls to conversation
                    messages.append(assistant_message)
                    
                    # Process all tool calls
                    for tool_call in tool_calls:
                        # Extract function name and args (works for both Message objects and dicts)
                        func = tool_call.function if hasattr(tool_call, 'function') else tool_call["function"]
                        tool_name = func.name if hasattr(func, 'name') else func["name"]
                        tool_args_str = func.arguments if hasattr(func, 'arguments') else func.get("arguments", "{}")
                        
                        try:
                            # Parse arguments if they're a string
                            if isinstance(tool_args_str, str):
                                tool_args = json.loads(tool_args_str) if tool_args_str and tool_args_str != "null" else {}
                            elif tool_args_str is None:
                                tool_args = {}
                            else:
                                tool_args = tool_args_str
                            
                            logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
                            
                            # Execute tool
                            if tool_name not in self.tool_map:
                                raise ValueError(f"Tool {tool_name} not found in tool_map")
                            
                            tool_result = self.tool_map[tool_name](**tool_args)
                            logger.debug(f"Tool {tool_name} result: {tool_result}")
                            
                            # Get tool_call_id (works for both Message objects and dicts)
                            tool_id = tool_call.id if hasattr(tool_call, 'id') else tool_call.get("id", tool_name)
                            
                            # Add tool result to messages
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": tool_name,
                                "content": str(tool_result)
                            })
                            
                        except Exception as e:
                            error_msg = f"Error executing tool {tool_name}: {str(e)}"
                            logger.error(error_msg)
                            
                            # Get tool_call_id (works for both Message objects and dicts)
                            tool_id = tool_call.id if hasattr(tool_call, 'id') else tool_call.get("id", tool_name)
                            
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_id,
                                "name": tool_name,
                                "content": error_msg
                            })
                    
                    # Continue loop to get next response
                    continue
                
                # No tool calls - we have final answer
                # Get content (works for both Message objects and dicts)
                final_msg = (assistant_message.content if hasattr(assistant_message, 'content') 
                           else assistant_message.get("content")) or ""
                
                if not final_msg:
                    logger.warning(f"Empty response - assistant_message: {assistant_message}")
                logger.info(f"Final response content: {repr(final_msg)}")
                
                # Save to memory
                self.memory.add("user", user_message)
                self.memory.add("assistant", final_msg)
                
                return final_msg
            
            # Max iterations exceeded
            error_msg = f"Max tool iterations ({self.max_tool_iterations}) exceeded"
            logger.warning(error_msg)
            self.memory.add("user", user_message)
            self.memory.add("assistant", error_msg)
            return error_msg
            
        except Exception as e:
            error_msg = f"Error in chat: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise

