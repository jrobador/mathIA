# backend_2/api/ws_routes.py

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Optional # Import Optional
import json
import uuid
import traceback # Import traceback for detailed error logging
import asyncio # Import asyncio for sleep and other async operations
# Import the agent class
from agents.learning_agent import AdaptiveLearningAgent

router = APIRouter()

# Almacenamiento de conexiones activas (mantener aquí por ahora)
# Consider moving to a more robust connection manager for production scaling
active_connections: Dict[str, Dict[str, WebSocket]] = {}

# Helper to send JSON data safely, catching potential connection errors
async def send_json_to_websocket(websocket: WebSocket, data: Any):
    """Helper to send JSON data safely with retries."""
    max_retries = 2
    retry_delay = 0.5  # seconds
    
    for attempt in range(max_retries + 1):
        try:
            if websocket.client_state == websocket.client_state.CONNECTED:
                await websocket.send_json(data)
                return True
            else:
                print(f"Attempted to send to disconnected WebSocket: {websocket.client.host}:{websocket.client.port}")
                return False
        except RuntimeError as e:
            # Check if it's a "WebSocket is not connected" error
            if "WebSocket is not connected" in str(e) or "close frame has been sent" in str(e):
                print(f"WebSocket connection closed during send attempt: {e}")
                return False
            # For other runtime errors, retry if not the last attempt
            if attempt < max_retries:
                print(f"RuntimeError on send attempt {attempt+1}, retrying: {e}")
                await asyncio.sleep(retry_delay)
            else:
                print(f"Failed to send after {max_retries+1} attempts: {e}")
                return False
        except Exception as e:
            # For unexpected errors, log but don't retry
            print(f"Error sending message to WebSocket ({websocket.client.host}:{websocket.client.port}): {e}")
            return False
    
    return False

# Helper to send agent responses, including requestId
async def send_agent_responses(websocket: WebSocket, responses: List[Dict[str, Any]], request_id: Optional[str] = None):
    """Sends a list of agent responses to the WebSocket client."""
    if not responses:
        print(f"No agent responses to send back (requestId: {request_id}).")
        return

    print(f"DEBUG: Sending {len(responses)} agent response(s) back for requestId: {request_id}")
    for i, response_data in enumerate(responses):
        print(f"DEBUG: Response {i+1}/{len(responses)} - Action: {response_data.get('action')}, Content Type: {response_data.get('content_type')}")
        
        # Check for image reuse
        if 'image_url' in response_data:
            print(f"DEBUG: Image URL in response {i+1}: {response_data['image_url']}")
        
        payload = {
            "type": "agent_response",
            "data": response_data,
            "requestId": request_id  # Make sure requestId is included
        }
        
        print(f"DEBUG: Sending payload {i+1} with type: {payload['type']}, requestId: {payload['requestId']}")
        await send_json_to_websocket(websocket, payload)
        
        # Add a small delay between messages to help client processing
        if i < len(responses) - 1:
            print(f"DEBUG: Adding small delay between messages")
            await asyncio.sleep(0.1)  # 100ms delay between messages

# Endpoint for handling active learning sessions
@router.websocket("/ws/session/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str):
    """
    Endpoint WebSocket para una sesión específica. Gestiona la comunicación bidireccional.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    learning_agent: Optional[AdaptiveLearningAgent] = None

    # Access the agent instance via the websocket object safely
    try:
        learning_agent = websocket.app.state.learning_agent
        if not isinstance(learning_agent, AdaptiveLearningAgent):
             raise AttributeError("learning_agent in app.state is not the correct type.")
    except AttributeError:
         print("FATAL ERROR: learning_agent not found or incorrect type in app.state")
         await send_json_to_websocket(websocket, {"type": "error", "message": "Internal server error: Agent not configured."})
         await websocket.close()
         return # Stop execution if agent isn't available

    print(f"WS connection {connection_id} opened for session {session_id}")

    # Verify session exists in the agent
    initial_state = learning_agent.get_session_state(session_id)
    if not initial_state:
        print(f"Session {session_id} not found for WS connection {connection_id}")
        await send_json_to_websocket(websocket, {
            "type": "error",
            "message": f"Sesión {session_id} no encontrada o inválida."
        })
        await websocket.close()
        return

    # Register the connection
    if session_id not in active_connections: active_connections[session_id] = {}
    active_connections[session_id][connection_id] = websocket
    print(f"Added connection {connection_id} to active pool for session {session_id}.")

    try:
        # Send initial state to the newly connected client
        print(f"Sending initial state for session {session_id} to conn {connection_id}")
        await send_json_to_websocket(websocket, {
            "type": "state_update",
            "data": initial_state
            # No request_id needed for initial state push
        })

        # Main loop to receive messages from the client
        while True:
            request_id = None # Reset request_id for each message
            try:
                raw_data = await websocket.receive_text()
                message = json.loads(raw_data)
                action = message.get("action", "").lower()
                data_payload = message.get("data", {})
                request_id = message.get("requestId") # Capture the client's request ID

                print(f"Received action '{action}' for session {session_id} (conn: {connection_id}, reqId: {request_id})")

                # Process actions based on client message
                if action == "submit_answer":
                    answer = data_payload.get("answer") # Get answer, check type later
                    if not isinstance(answer, str):
                         print(f"Invalid answer format received: {type(answer)}")
                         await send_json_to_websocket(websocket, {"type": "error", "message": "Invalid answer format (must be string).", "requestId": request_id})
                         continue # Skip processing this message

                    # Agent handles evaluation and determines next steps
                    results: List[Dict[str, Any]] = await learning_agent.handle_user_input(session_id, answer)
                    # Send agent response(s) back, including the original request ID
                    await send_agent_responses(websocket, results, request_id)

                elif action == "continue":
                    # Agent processes the next step in the learning flow
                    result: Dict[str, Any] = await learning_agent.process_step(session_id)
                    # Send agent response back, including the original request ID
                    await send_agent_responses(websocket, [result], request_id) # Send single result as list

                elif action == "get_state":
                    # Retrieve current session state from the agent
                    current_state = learning_agent.get_session_state(session_id)
                    response_payload = {
                        "type": "state_update",
                        "data": current_state,
                        "requestId": request_id # Include requestId
                    } if current_state else {
                        "type": "error",
                        "message": "Failed to retrieve session state.",
                        "requestId": request_id
                    }
                    await send_json_to_websocket(websocket, response_payload)

                elif action == "ping":
                    # Respond to keepalive pings
                    await send_json_to_websocket(websocket, {
                        "type": "pong",
                        "timestamp": message.get("timestamp", 0),
                        "requestId": request_id # Echo requestId
                    })

                else:
                    # Handle unknown actions
                    print(f"Received unknown action: {action}")
                    await send_json_to_websocket(websocket, {
                        "type": "error",
                        "message": f"Acción desconocida: '{action}'",
                        "requestId": request_id # Include requestId in error response
                    })

            # Handle errors within the message processing loop
            except json.JSONDecodeError:
                print(f"Invalid JSON received from conn {connection_id}")
                await send_json_to_websocket(websocket, {"type": "error", "message": "Formato de mensaje inválido (no es JSON)."})
                # No request_id available if JSON parsing failed
            except WebSocketDisconnect:
                 print(f"WebSocketDisconnect received inside loop for conn {connection_id}.")
                 raise # Re-raise to be caught by the outer try/except for cleanup
            except Exception as e:
                # Catch unexpected errors during message processing
                print(f"Error processing message from conn {connection_id} (reqId: {request_id}):")
                traceback.print_exc()
                # Send error back to client, including request_id if available
                await send_json_to_websocket(websocket, {
                    "type": "error",
                    "message": f"Error procesando su solicitud: {str(e)}",
                    "requestId": request_id # Include ID if available
                })

    # Handle disconnection or major errors outside the main loop
    except WebSocketDisconnect:
        print(f"WS connection {connection_id} disconnected for session {session_id}")
    except Exception as e:
        # Catch unexpected errors during initial connection setup or fatal issues
        print(f"Unhandled error in WebSocket session {session_id} (conn: {connection_id}):")
        traceback.print_exc()
        # Attempt to notify client before closing if possible
        await send_json_to_websocket(websocket, {"type": "error", "message": f"Error inesperado en la sesión: {str(e)}"})
    finally:
        # Cleanup: Remove connection from the active pool
        if session_id in active_connections and connection_id in active_connections[session_id]:
            del active_connections[session_id][connection_id]
            print(f"Removed connection {connection_id} from active pool for session {session_id}.")
            # Remove the session entry entirely if no connections remain
            if not active_connections[session_id]:
                del active_connections[session_id]
                print(f"Removed session {session_id} entry from active WS connections pool.")
        # Ensure websocket is closed if not already
        try:
            # Check state before closing, avoid errors if already closed
            if websocket.client_state == websocket.client_state.CONNECTED:
                 await websocket.close()
                 print(f"Closed WebSocket connection {connection_id}.")
        except RuntimeError as e:
            # Ignore specific error if already closing/closed
            if "Cannot call 'close' once a close frame has been sent" not in str(e) and \
               "WebSocket is not connected" not in str(e):
                 print(f"Error during WebSocket cleanup close for {connection_id}: {e}")
        except Exception as e:
             print(f"Generic error during WebSocket cleanup close for {connection_id}: {e}")
        print(f"Finished cleanup for WS connection {connection_id}")


# Endpoint for creating new sessions or getting roadmaps
@router.websocket("/ws/new_session")
async def websocket_new_session_endpoint(websocket: WebSocket):
    """
    Endpoint WebSocket para crear una nueva sesión o listar roadmaps.
    Handles a single request then closes.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4()) # Use UUID for logging clarity
    print(f"WS connection {connection_id} opened for new_session endpoint.")
    learning_agent: Optional[AdaptiveLearningAgent] = None

    # Access the agent instance safely
    try:
        learning_agent = websocket.app.state.learning_agent
        if not isinstance(learning_agent, AdaptiveLearningAgent):
             raise AttributeError("learning_agent in app.state is not the correct type.")
    except AttributeError:
         print("FATAL ERROR: learning_agent not found or incorrect type in app.state for new_session")
         await send_json_to_websocket(websocket, {"type": "error", "message": "Internal server error: Agent not configured."})
         await websocket.close()
         return

    request_id = None # Initialize request_id
    try:
        # Expect a single message from the client for this endpoint
        raw_data = await websocket.receive_text()
        message = json.loads(raw_data)
        action = message.get("action", "").lower()
        data_payload = message.get("data", {})
        request_id = message.get("requestId") # Capture the client's request ID

        print(f"Received action '{action}' on new_session WS (conn: {connection_id}, reqId: {request_id}).")

        if action == "create_session":
            # Extract parameters for session creation
            topic_id = data_payload.get("topic_id", "fractions_introduction")
            user_id = data_payload.get("user_id") # Optional
            initial_mastery_str = data_payload.get("initial_mastery", "0.0")
            personalized_theme = data_payload.get("personalized_theme", "space")
            
            # NEW: Support for diagnostic results
            diagnostic_results = data_payload.get("diagnostic_results")
            
            # Safely convert initial_mastery to float
            try:
                initial_mastery = float(initial_mastery_str)
                if not (0.0 <= initial_mastery <= 1.0):
                    raise ValueError("Initial mastery must be between 0.0 and 1.0")
            except (ValueError, TypeError):
                print(f"Invalid initial_mastery value received: {initial_mastery_str}. Defaulting to 0.0.")
                initial_mastery = 0.0
            
            # NEW: Process diagnostic results if provided
            if diagnostic_results and isinstance(diagnostic_results, list) and len(diagnostic_results) > 0:
                try:
                    # Simple calculation: percentage of correct answers
                    total_questions = len(diagnostic_results)
                    correct_answers = sum(1 for result in diagnostic_results if result.get('correct', False))
                    
                    if total_questions > 0:
                        # Scale the calculated mastery between 0.1 and 0.8 to leave room for improvement
                        calculated_mastery = 0.1 + (0.7 * (correct_answers / total_questions))
                        initial_mastery = calculated_mastery
                        print(f"WS: Calculated initial mastery from diagnostics: {initial_mastery:.2f} ({correct_answers}/{total_questions} correct)")
                except Exception as e:
                    print(f"Error processing diagnostic results: {e}")
                    # Continue with default or provided initial_mastery if there's an error
            
            try:
                # Call agent method to create the session
                session_response = await learning_agent.create_session(
                    topic_id=topic_id,
                    personalized_theme=personalized_theme,
                    initial_mastery=initial_mastery,
                    user_id=user_id
                )

                # Send success response back to client, including requestId
                await send_json_to_websocket(websocket, {
                    "type": "session_created",
                    "data": session_response, # Contains session_id and initial_result
                    "requestId": request_id # Include original request ID
                })
                print(f"Sent session_created for {session_response.get('session_id')} back to conn {connection_id}")

            except ValueError as e: # Catch specific validation errors from agent
                print(f"ValueError during session creation: {e}")
                await send_json_to_websocket(websocket, {"type": "error", "message": str(e), "requestId": request_id})
            except Exception as e: # Catch unexpected errors during session creation
                print(f"Exception during session creation:")
                traceback.print_exc()
                await send_json_to_websocket(websocket, {"type": "error", "message": f"Error creating session: {str(e)}", "requestId": request_id})

        elif action == "get_roadmaps":
            # Get available learning roadmaps from the agent
            roadmaps = learning_agent.get_available_roadmaps()
            # Send list back to client, including requestId
            await send_json_to_websocket(websocket, {
                "type": "roadmaps_list",
                "data": roadmaps,
                "requestId": request_id # Include original request ID
            })
            print(f"Sent roadmaps_list back to conn {connection_id}")

        else:
            # Handle unknown actions for this specific endpoint
             print(f"Received unknown action on new_session WS: {action}")
             await send_json_to_websocket(websocket, {
                "type": "error",
                "message": f"Acción no válida para este endpoint: '{action}'",
                "requestId": request_id # Include original request ID
            })

    # Handle exceptions for the single message processing
    except json.JSONDecodeError:
        print(f"Invalid JSON received from new_session conn {connection_id}")
        await send_json_to_websocket(websocket, {"type": "error", "message": "Formato de mensaje inválido (no es JSON)."})
    except WebSocketDisconnect:
        # This might happen if client closes connection immediately after sending
        print(f"Client disconnected from new_session WS ({connection_id}) before/during processing.")
    except Exception as e:
        # Catch unexpected errors
        print(f"Error in new_session WebSocket ({connection_id}, reqId: {request_id}):")
        traceback.print_exc()
        # Attempt to send error back, include requestId if available
        await send_json_to_websocket(websocket, {"type": "error", "message": f"Error inesperado: {str(e)}", "requestId": request_id})
    finally:
         # Ensure websocket is closed for this endpoint as it's request/response
        try:
             if websocket.client_state == websocket.client_state.CONNECTED:
                 await websocket.close()
        except RuntimeError: pass # Ignore if already closed
        except Exception as e: print(f"Error closing new_session WS {connection_id}: {e}")
        print(f"Closed new_session WS connection {connection_id}.")


# Function to broadcast messages (e.g., for admin panel or multi-client sync)
# Currently unused in the main flow but kept for potential future use.
async def broadcast_to_session(session_id: str, message: Dict[str, Any]):
    """Envía un mensaje a todos los clientes conectados a una sesión."""
    if session_id in active_connections:
        # Create a list of (conn_id, websocket) tuples to iterate safely
        # as the dictionary might change during iteration if clients disconnect
        connections_to_broadcast = list(active_connections.get(session_id, {}).items())
        print(f"Broadcasting message to {len(connections_to_broadcast)} client(s) in session {session_id}...")

        disconnected_clients = []
        for conn_id, websocket in connections_to_broadcast:
            try:
                # Check if the specific websocket is still connected before sending
                if websocket.client_state == websocket.client_state.CONNECTED:
                    await websocket.send_json(message)
                else:
                     print(f"Skipping broadcast to disconnected client {conn_id} in session {session_id}.")
                     disconnected_clients.append(conn_id)
            except Exception as e:
                print(f"Error broadcasting to {conn_id} in session {session_id}: {e}. Marking for removal.")
                disconnected_clients.append(conn_id) # Mark for removal on error too

        # Clean up disconnected clients after broadcasting attempt
        if disconnected_clients:
             session_connections = active_connections.get(session_id)
             if session_connections: # Check if session entry still exists
                 cleaned_count = 0
                 for conn_id in set(disconnected_clients): # Use set to avoid duplicates
                     if conn_id in session_connections:
                         del session_connections[conn_id]
                         cleaned_count += 1
                 print(f"Cleaned up {cleaned_count} disconnected broadcast clients for session {session_id}.")
                 # Remove the session entry entirely if no connections remain
                 if not session_connections:
                     del active_connections[session_id]
                     print(f"Removed session {session_id} entry from active WS connections after broadcast cleanup.")
    # else:
    #     print(f"No active connections found for session {session_id} to broadcast.")