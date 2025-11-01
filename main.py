## pip install --upgrade google-genai==0.2.2 ##
import asyncio
import json
import os
import websockets
from google import genai
import base64
from dotenv import load_dotenv
from recipe_manager import RecipeManager, TimerManager, ActionDetector

# Load API key from environment
load_dotenv()
MODEL = "models/gemini-2.5-flash-native-audio-preview-09-2025"

client = genai.Client(
  http_options={
    'api_version': 'v1beta',
  }
)

# Initialize managers
recipe_manager = RecipeManager(recipes_dir="recipes")
timer_manager = TimerManager()
action_detector = ActionDetector()


async def handle_function_call(function_call):
    """Handle function calls from Gemini."""
    function_name = function_call.name
    args = function_call.args
    print(f"Handling function call: {function_name} with args: {args}")

    if function_name == "get_next_recipe_step":
        result = recipe_manager.get_next_recipe_step(args["recipe_id"], args["current_step"])
    elif function_name == "explain_ingredient":
        result = recipe_manager.explain_ingredient(args["ingredient_name"], args.get("language", "darija"))
    elif function_name == "start_timer":
        result = timer_manager.start_timer(args["duration"], args["label"])
    elif function_name == "get_cultural_context":
        result = recipe_manager.get_cultural_context(args["topic"])
    elif function_name == "detect_kitchen_action":
        result = action_detector.detect_kitchen_action(
            args["action"], 
            args["confidence"], 
            args.get("object")
        )
    else:
        result = {"error": f"Unknown function: {function_name}"}

    print(f"Function result: {result}")
    return result


async def gemini_session_handler(client_websocket):
  
    try:
        config_message = await client_websocket.recv()
        config_data = json.loads(config_message)
        setup_config = config_data.get("setup", {})
        
        # Build proper config for Gemini Live API
        from google.genai import types
        
        # Extract system instruction text
        system_text = None
        if "system_instruction" in setup_config:
            system_text = setup_config["system_instruction"]["parts"][0]["text"]
        
        # Extract tools - pass as dict directly
        tools = None
        if "tools" in setup_config:
            tools = setup_config["tools"]
        
        # Simple config without speech_config
        config = {
            "response_modalities": ["AUDIO"]
        }
        
        if system_text:
            config["system_instruction"] = {"parts": [{"text": system_text}]}
        if tools:
            config["tools"] = tools

        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("Connected to Gemini API")

            async def send_to_gemini():
                """Sends messages from the client websocket to the Gemini API."""
                try:
                  async for message in client_websocket:
                      try:
                          data = json.loads(message)
                          if "realtime_input" in data:
                              for chunk in data["realtime_input"]["media_chunks"]:
                                  # Send data directly to session
                                  await session.send(input=chunk)
                          elif "client_content" in data and data["client_content"].get("turn_complete"):
                              # Signal end of turn to trigger assistant response
                              print("Client signaled turn complete")
                              # Send a simple text prompt to trigger response
                              await session.send(input="Please respond to what you've heard and seen.", end_of_turn=True)
                                      
                      except Exception as e:
                          print(f"Error sending to Gemini: {e}")
                  print("Client connection closed (send)")
                except Exception as e:
                     print(f"Error sending to Gemini: {e}")
                finally:
                   print("send_to_gemini closed")



            async def receive_from_gemini():
                """Receives responses from the Gemini API and forwards them to the client."""
                try:
                    while True:
                        try:
                            turn = session.receive()
                            async for response in turn:
                                print(f"Received response: {response}")
                                
                                # Handle audio data
                                if hasattr(response, 'data') and response.data:
                                    print(f"Sending audio data, length: {len(response.data)}")
                                    base64_audio = base64.b64encode(response.data).decode('utf-8')
                                    await client_websocket.send(json.dumps({"audio": base64_audio}))
                                
                                # Handle text responses
                                if hasattr(response, 'text') and response.text:
                                    print(f"text: {response.text}", end="")
                                    await client_websocket.send(json.dumps({"text": response.text}))
                                
                                # Handle tool calls (function calls)
                                if hasattr(response, 'tool_call') and response.tool_call:
                                    if hasattr(response.tool_call, 'function_calls'):
                                        for function_call in response.tool_call.function_calls:
                                            print(f"Handling function call: {function_call.name}")
                                            result = await handle_function_call(function_call)
                                            # Send function response back as content
                                            from google.genai import types
                                            func_response = types.LiveClientRealtimeInput(
                                                media_chunks=[
                                                    types.Part(
                                                        function_response=types.FunctionResponse(
                                                            id=function_call.id,
                                                            name=function_call.name,
                                                            response=result
                                                        )
                                                    )
                                                ]
                                            )
                                            await session.send(func_response)
                            
                            print('\n<Turn complete>')
                            
                        except websockets.exceptions.ConnectionClosedOK:
                            print("Client connection closed normally (receive)")
                            break
                        except Exception as e:
                            print(f"Error receiving from Gemini: {e}")
                            break

                except Exception as e:
                      print(f"Error receiving from Gemini: {e}")
                finally:
                      print("Gemini connection closed (receive)")


            # Start send loop
            send_task = asyncio.create_task(send_to_gemini())
            # Launch receive loop as a background task
            receive_task = asyncio.create_task(receive_from_gemini())
            await asyncio.gather(send_task, receive_task)


    except Exception as e:
        print(f"Error in Gemini session: {e}")
    finally:
        print("Gemini session closed.")


async def main() -> None:
    async with websockets.serve(gemini_session_handler, "localhost", 9080):
        print("Running websocket server localhost:9080...")
        await asyncio.Future()  # Keep the server running indefinitely


if __name__ == "__main__":
    asyncio.run(main())
