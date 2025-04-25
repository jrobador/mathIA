"""
WebSocket routes for handling real-time communication with clients.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List, Optional
import json
import uuid
import traceback
import asyncio

from agents.learning_agent import AdaptiveLearningAgent

router = APIRouter()

active_connections: Dict[str, Dict[str, WebSocket]] = {}

async def send_json_to_websocket(websocket: WebSocket, data: Any):
    """Helper to send JSON data safely with retries."""
    max_retries = 2
    retry_delay = 0.5

    for attempt in range(max_retries + 1):
        try:
            if websocket.client_state == websocket.client_state.CONNECTED:
                await websocket.send_json(data)
                return True
            else:
                print(f"Attempted to send to disconnected WebSocket: {websocket.client.host}:{websocket.client.port}")
                return False
        except RuntimeError as e:
            if "WebSocket is not connected" in str(e) or "close frame has been sent" in str(e):
                print(f"WebSocket connection closed during send attempt: {e}")
                return False
            if attempt < max_retries:
                print(f"RuntimeError on send attempt {attempt+1}, retrying: {e}")
                await asyncio.sleep(retry_delay)
            else:
                print(f"Failed to send after {max_retries+1} attempts: {e}")
                return False
        except Exception as e:
            print(f"Error sending message to WebSocket ({websocket.client.host}:{websocket.client.port}): {e}")
            return False

    return False

async def send_agent_responses(websocket: WebSocket, responses: List[Dict[str, Any]], request_id: Optional[str] = None):
    """Sends a list of agent responses to the WebSocket client."""
    if not responses:
        print(f"No agent responses to send back (requestId: {request_id}).")
        return

    print(f"DEBUG: Sending {len(responses)} agent response(s) back for requestId: {request_id}")
    for i, response_data in enumerate(responses):
        print(f"DEBUG: Response {i+1}/{len(responses)} - Action: {response_data.get('action')}, Content Type: {response_data.get('content_type')}")

        if 'image_url' in response_data:
            print(f"DEBUG: Image URL in response {i+1}: {response_data['image_url']}")

        payload = {
            "type": "agent_response",
            "data": response_data,
            "requestId": request_id
        }

        print(f"DEBUG: Sending payload {i+1} with type: {payload['type']}, requestId: {payload['requestId']}")
        await send_json_to_websocket(websocket, payload)

        if i < len(responses) - 1:
            print(f"DEBUG: Adding small delay between messages")
            await asyncio.sleep(0.1)

@router.websocket("/ws/session/{session_id}")
async def websocket_session_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for a specific session. Manages bidirectional communication.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    learning_agent: Optional[AdaptiveLearningAgent] = None

    try:
        learning_agent = websocket.app.state.learning_agent
        if not isinstance(learning_agent, AdaptiveLearningAgent):
             raise AttributeError("learning_agent in app.state is not the correct type.")
    except AttributeError:
         print("FATAL ERROR: learning_agent not found or incorrect type in app.state")
         await send_json_to_websocket(websocket, {"type": "error", "message": "Internal server error: Agent not configured."})
         await websocket.close()
         return

    print(f"WS connection {connection_id} opened for session {session_id}")

    initial_state = learning_agent.get_session_state(session_id)
    if not initial_state:
        print(f"Session {session_id} not found for WS connection {connection_id}")
        await send_json_to_websocket(websocket, {
            "type": "error",
            "message": f"Session {session_id} not found or invalid."
        })
        await websocket.close()
        return

    if session_id not in active_connections: active_connections[session_id] = {}
    active_connections[session_id][connection_id] = websocket
    print(f"Added connection {connection_id} to active pool for session {session_id}.")

    try:
        print(f"Sending initial state for session {session_id} to conn {connection_id}")
        await send_json_to_websocket(websocket, {
            "type": "state_update",
            "data": initial_state
        })

        while True:
            request_id = None
            try:
                raw_data = await websocket.receive_text()
                message = json.loads(raw_data)
                action = message.get("action", "").lower()
                data_payload = message.get("data", {})
                request_id = message.get("requestId")

                print(f"Received action '{action}' for session {session_id} (conn: {connection_id}, reqId: {request_id})")

                if action == "submit_answer":
                    answer = data_payload.get("answer")
                    if not isinstance(answer, str):
                        print(f"Invalid answer format received: {type(answer)}")
                        await send_json_to_websocket(websocket, {"type": "error", "message": "Invalid answer format (must be string).", "requestId": request_id})
                        continue

                    print(f"Calling handle_user_input with answer: '{answer}'")
                    raw_results = await learning_agent.handle_user_input(session_id, answer)

                    results_list = []
                    if isinstance(raw_results, list):
                        results_list = raw_results
                    elif isinstance(raw_results, dict):
                        results_list = [raw_results]
                    else:
                        print(f"ERROR: Unexpected result type from handle_user_input: {type(raw_results)}")
                        await send_json_to_websocket(websocket, {"type": "error", "message": "Internal server error processing answer.", "requestId": request_id})
                        continue

                    await send_agent_responses(websocket, results_list, request_id)

                    if results_list:
                        last_result = results_list[-1]
                        if last_result.get("action") == "evaluation_result":
                            if not last_result.get("waiting_for_input", False):
                                print(f"DEBUG: Evaluation result sent, and it doesn't require input. Frontend should handle progression via 'continue'.")
                            else:
                                print(f"DEBUG: Evaluation result sent, and it requires input (unexpected).")

                elif action == "continue":
                    print(f"WS received 'continue', calling agent.process_step for session {session_id}")
                    result = await learning_agent.process_step(session_id)
                    await send_agent_responses(websocket, [result], request_id)

                elif action == "get_state":
                    current_state = learning_agent.get_session_state(session_id)
                    response_payload = {
                        "type": "state_update",
                        "data": current_state,
                        "requestId": request_id
                    } if current_state else {
                        "type": "error",
                        "message": "Failed to retrieve session state.",
                        "requestId": request_id
                    }
                    await send_json_to_websocket(websocket, response_payload)

                elif action == "ping":
                    await send_json_to_websocket(websocket, {
                        "type": "pong",
                        "timestamp": message.get("timestamp", 0),
                        "requestId": request_id
                    })

                else:
                    print(f"Received unknown action: {action}")
                    await send_json_to_websocket(websocket, {
                        "type": "error",
                        "message": f"Unknown action: '{action}'",
                        "requestId": request_id
                    })

            except json.JSONDecodeError:
                print(f"Invalid JSON received from conn {connection_id}")
                await send_json_to_websocket(websocket, {"type": "error", "message": "Invalid message format (not JSON)."})
            except WebSocketDisconnect:
                print(f"WebSocketDisconnect received inside loop for conn {connection_id}.")
                raise
            except Exception as e:
                print(f"Error processing message from conn {connection_id} (reqId: {request_id}):")
                traceback.print_exc()
                await send_json_to_websocket(websocket, {
                    "type": "error",
                    "message": f"Error processing your request: {str(e)}",
                    "requestId": request_id
                })
    except WebSocketDisconnect:
        print(f"WS connection {connection_id} disconnected for session {session_id}")
    except Exception as e:
        print(f"Unhandled error in WebSocket session {session_id} (conn: {connection_id}):")
        traceback.print_exc()
        await send_json_to_websocket(websocket, {"type": "error", "message": f"Unexpected session error: {str(e)}"})
    finally:
        if session_id in active_connections and connection_id in active_connections[session_id]:
            del active_connections[session_id][connection_id]
            print(f"Removed connection {connection_id} from active pool for session {session_id}.")
            if not active_connections[session_id]:
                del active_connections[session_id]
                print(f"Removed session {session_id} entry from active WS connections pool.")
        try:
            if websocket.client_state == websocket.client_state.CONNECTED:
                 await websocket.close()
                 print(f"Closed WebSocket connection {connection_id}.")
        except RuntimeError as e:
            if "Cannot call 'close' once a close frame has been sent" not in str(e) and \
               "WebSocket is not connected" not in str(e):
                 print(f"Error during WebSocket cleanup close for {connection_id}: {e}")
        except Exception as e:
             print(f"Generic error during WebSocket cleanup close for {connection_id}: {e}")
        print(f"Finished cleanup for WS connection {connection_id}")


@router.websocket("/ws/new_session")
async def websocket_new_session_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for creating a new session or listing roadmaps.
    Handles a single request then closes.
    """
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    print(f"WS connection {connection_id} opened for new_session endpoint.")
    learning_agent: Optional[AdaptiveLearningAgent] = None

    try:
        learning_agent = websocket.app.state.learning_agent
        if not isinstance(learning_agent, AdaptiveLearningAgent):
             raise AttributeError("learning_agent in app.state is not the correct type.")
    except AttributeError:
         print("FATAL ERROR: learning_agent not found or incorrect type in app.state for new_session")
         await send_json_to_websocket(websocket, {"type": "error", "message": "Internal server error: Agent not configured."})
         await websocket.close()
         return

    request_id = None
    try:
        raw_data = await websocket.receive_text()
        message = json.loads(raw_data)
        action = message.get("action", "").lower()
        data_payload = message.get("data", {})
        request_id = message.get("requestId")

        print(f"Received action '{action}' on new_session WS (conn: {connection_id}, reqId: {request_id}).")

        if action == "create_session":
            topic_id = data_payload.get("topic_id", "fractions_introduction")
            user_id = data_payload.get("user_id")
            initial_mastery_str = data_payload.get("initial_mastery", "0.0")
            personalized_theme = data_payload.get("personalized_theme", "space")
            diagnostic_results = data_payload.get("diagnostic_results")

            try:
                initial_mastery = float(initial_mastery_str)
                if not (0.0 <= initial_mastery <= 1.0):
                    raise ValueError("Initial mastery must be between 0.0 and 1.0")
            except (ValueError, TypeError):
                print(f"Invalid initial_mastery value received: {initial_mastery_str}. Defaulting to 0.0.")
                initial_mastery = 0.0

            if diagnostic_results and isinstance(diagnostic_results, list) and len(diagnostic_results) > 0:
                try:
                    total_questions = len(diagnostic_results)
                    correct_answers = sum(1 for result in diagnostic_results if result.get('correct', False))

                    if total_questions > 0:
                        calculated_mastery = 0.1 + (0.7 * (correct_answers / total_questions))
                        initial_mastery = calculated_mastery
                        print(f"WS: Calculated initial mastery from diagnostics: {initial_mastery:.2f} ({correct_answers}/{total_questions} correct)")
                except Exception as e:
                    print(f"Error processing diagnostic results: {e}")

            try:
                session_response = await learning_agent.create_session(
                    topic_id=topic_id,
                    personalized_theme=personalized_theme,
                    initial_mastery=initial_mastery,
                    user_id=user_id
                )

                await send_json_to_websocket(websocket, {
                    "type": "session_created",
                    "data": {
                        "session_id": session_response.get('session_id'),
                        "initial_output": {
                            "text": session_response.get('initial_result', {}).get('text', ''),
                            "image_url": session_response.get('initial_result', {}).get('image_url'),
                            "audio_url": session_response.get('initial_result', {}).get('audio_url'),
                            "prompt_for_answer": session_response.get('initial_result', {}).get('waiting_for_input', False),
                            "evaluation": session_response.get('initial_result', {}).get('evaluation_type'),
                            "is_final_step": session_response.get('initial_result', {}).get('is_final_step', False),
                        },
                        "initial_result": session_response.get('initial_result', {}),
                        "state_metadata": session_response.get('state_metadata', {})
                    },
                    "requestId": request_id
                })
                print(f"Sent session_created for {session_response.get('session_id')} back to conn {connection_id}")

            except ValueError as e:
                print(f"ValueError during session creation: {e}")
                await send_json_to_websocket(websocket, {"type": "error", "message": str(e), "requestId": request_id})
            except Exception as e:
                print(f"Exception during session creation:")
                traceback.print_exc()
                await send_json_to_websocket(websocket, {"type": "error", "message": f"Error creating session: {str(e)}", "requestId": request_id})

        elif action == "get_roadmaps":
            roadmaps = learning_agent.get_available_roadmaps()
            await send_json_to_websocket(websocket, {
                "type": "roadmaps_list",
                "data": roadmaps,
                "requestId": request_id
            })
            print(f"Sent roadmaps_list back to conn {connection_id}")

        else:
             print(f"Received unknown action on new_session WS: {action}")
             await send_json_to_websocket(websocket, {
                "type": "error",
                "message": f"Action not valid for this endpoint: '{action}'",
                "requestId": request_id
            })

    except json.JSONDecodeError:
        print(f"Invalid JSON received from new_session conn {connection_id}")
        await send_json_to_websocket(websocket, {"type": "error", "message": "Invalid message format (not JSON)."})
    except WebSocketDisconnect:
        print(f"Client disconnected from new_session WS ({connection_id}) before/during processing.")
    except Exception as e:
        print(f"Error in new_session WebSocket ({connection_id}, reqId: {request_id}):")
        traceback.print_exc()
        await send_json_to_websocket(websocket, {"type": "error", "message": f"Unexpected error: {str(e)}", "requestId": request_id})
    finally:
         try:
             if websocket.client_state == websocket.client_state.CONNECTED:
                 await websocket.close()
         except RuntimeError: pass
         except Exception as e: print(f"Error closing new_session WS {connection_id}: {e}")
         print(f"Closed new_session WS connection {connection_id}.")

async def broadcast_to_session(session_id: str, message: Dict[str, Any]):
    """Sends a message to all clients connected to a session."""
    if session_id in active_connections:
        connections_to_broadcast = list(active_connections.get(session_id, {}).items())
        print(f"Broadcasting message to {len(connections_to_broadcast)} client(s) in session {session_id}...")

        disconnected_clients = []
        for conn_id, websocket in connections_to_broadcast:
            try:
                if websocket.client_state == websocket.client_state.CONNECTED:
                    await websocket.send_json(message)
                else:
                     print(f"Skipping broadcast to disconnected client {conn_id} in session {session_id}.")
                     disconnected_clients.append(conn_id)
            except Exception as e:
                print(f"Error broadcasting to {conn_id} in session {session_id}: {e}. Marking for removal.")
                disconnected_clients.append(conn_id)

        if disconnected_clients:
             session_connections = active_connections.get(session_id)
             if session_connections:
                 cleaned_count = 0
                 for conn_id in set(disconnected_clients):
                     if conn_id in session_connections:
                         del session_connections[conn_id]
                         cleaned_count += 1
                 print(f"Cleaned up {cleaned_count} disconnected broadcast clients for session {session_id}.")
                 if not session_connections:
                     del active_connections[session_id]
                     print(f"Removed session {session_id} entry from active WS connections after broadcast cleanup.")