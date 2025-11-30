import os
import json
import logging
from flask import Flask, send_from_directory, request, Response, stream_with_context
from core.conversation import session_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)

@app.route("/chat")
def chat_index():
    return send_from_directory("web/chat", "index.html")

@app.route("/static/<path:filename>")
def chat_static(filename):
    return send_from_directory("web/chat/static/", filename)

@app.route("/lib/<path:filename>")
def lib(filename):
    return send_from_directory("web/chat/lib/", filename)

@app.route("/api/chat", methods=["POST"])
def chat_api():
    try:
        data = request.get_json()
        session_id = data.get("session_id")
        message = data.get("message")

        if not session_id or not message:
            return Response(
                "Missing session_id or message", 
                status=400
            )

        logger.info(f"Received message for session {session_id}: {message}")

        def generate_stream():
            chain = session_manager.get_chain(session_id)
            
            # LangChain's stream method yields tokens directly
            try:
                for chunk in chain.stream({"input": message}):
                    # chunk is a dictionary like {'response': 'token'} or just the token depending on chain type
                    # For ConversationChain, it yields the full response incrementally if configured
                    # But standard ChatOpenAI stream yields ChatGenerationChunk
                    
                    # Actually, ConversationChain.stream() yields the final output key by default.
                    # Let's verify what `stream` yields. It usually yields the result dict.
                    # To get token-by-token streaming with ConversationChain, we rely on the LLM's streaming.
                    # However, chain.stream() waits for the full response in some versions.
                    
                    # Better approach for streaming with Memory:
                    # We can use the chain.astream() or use callbacks.
                    # But keeping it simple: chain.stream() works in newer LangChain.
                    
                    # Let's assume chain.stream() yields chunks of the response text.
                    if isinstance(chunk, dict) and "response" in chunk:
                         content = chunk["response"]
                    elif isinstance(chunk, str):
                         content = chunk
                    else:
                         content = str(chunk) # Fallback
                    
                    # If using ConversationChain with stream(), it might yield the FULL response at the end 
                    # rather than tokens. 
                    # To get tokens, we need to use a CallbackHandler or call the LLM directly with memory context.
                    pass
                
                # REVISION: chain.stream() with ConversationChain is tricky.
                # Let's use the LLM directly with memory loaded.
                
                memory_variables = chain.memory.load_memory_variables({})
                history = memory_variables["history"]
                
                # Construct full prompt manually? No, that defeats the purpose.
                
                # Let's stick to the simplest standard LangChain streaming:
                # chain.stream(...)
                
                for chunk in chain.stream(message):
                    # The chunk from ConversationChain stream is typically the response dict
                    # which might NOT be streaming token-by-token effectively without a callback.
                    
                    # Force token streaming:
                    # We will use the `astream_events` or just use the callback approach if needed.
                    # But let's try the direct stream first. 
                    # Actually, `chain.stream` yields the final output.
                    
                    # WAIT. `ConversationChain` does NOT support token-by-token streaming via `.stream()` easily
                    # because it buffers.
                    
                    # ALTERNATIVE: Use `RunnableWithMessageHistory` (modern LangChain) or manual handling.
                    
                    # Let's use a callback handler to capture the stream.
                    pass

            except Exception as e:
                yield f"data: {json.dumps({'content': f'[Error: {str(e)}]'})}\n\n"

        # RE-IMPLEMENTATION using a simpler streaming approach compatible with Flask
        # We will use the chain's predict method but we need to stream tokens.
        # We can pass a callback to the chain run.
        
        from langchain.callbacks import StreamingStdOutCallbackHandler
        from langchain.callbacks.base import BaseCallbackHandler
        from queue import Queue, Empty
        from threading import Thread

        class StreamCallback(BaseCallbackHandler):
            def __init__(self, queue):
                self.queue = queue

            def on_llm_new_token(self, token: str, **kwargs):
                self.queue.put(token)

            def on_llm_end(self, *args, **kwargs):
                self.queue.put(None)

            def on_llm_error(self, error, **kwargs):
                self.queue.put(None)

        def generate_stream_thread():
            q = Queue()
            chain = session_manager.get_chain(session_id)
            
            # Run chain in separate thread
            def run_chain():
                try:
                    chain.predict(input=message, callbacks=[StreamCallback(q)])
                except Exception as e:
                    logger.error(f"Chain error: {e}")
                    q.put(f"[Error: {e}]")
                    q.put(None)

            thread = Thread(target=run_chain)
            thread.start()

            while True:
                try:
                    token = q.get(timeout=60)
                    if token is None:
                        break
                    yield f"data: {json.dumps({'content': token})}\n\n"
                except Empty:
                    break

        return Response(
            stream_with_context(generate_stream_thread()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"API Error: {e}")
        return Response(f"Internal Server Error: {e}", status=500)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
