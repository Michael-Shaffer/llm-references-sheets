import os
import json
import requests
from typing import List, Dict, Any
from flask import Flask, send_from_directory, request, jsonify, Response, stream_with_context

app = Flask(__name__, static_folder=None)

VLLM_BASE = "http://localhost:8000"
VLLM_CHAT_COMPLETIONS = f"{VLLM_BASE}/v1/chat/completions"

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
    messages = request.json.get("messages", [])
    query = messages[-1].get("content")
    print(f"[DEBUG] Received query: {query}")
    print(f"[DEBUG] Sending to vLLM: {VLLM_CHAT_COMPLETIONS}")

    headers = {"Content-Type": "application/json"}
    data = {
        "model": "/models/Meta-Llama-3.1-8B-Instruct",
        "messages": messages,
        "stream": True
    }

    def generate_stream():
        try:
            response = requests.post(
                VLLM_CHAT_COMPLETIONS,
                headers=headers,
                json=data,
                stream=True,
                timeout=(5, 60)  # (connect timeout, read timeout)
            )
            response.raise_for_status()
        except requests.exceptions.ConnectionError:
            yield f"data: {json.dumps({'content': '[Error: Cannot connect to vLLM at ' + VLLM_BASE + ']'})}\n\n"
            return
        except requests.exceptions.Timeout:
            yield f"data: {json.dumps({'content': '[Error: vLLM request timed out]'})}\n\n"
            return
        except Exception as e:
            yield f"data: {json.dumps({'content': f'[Error: {str(e)}]'})}\n\n"
            return

        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    decoded_line = decoded_line[6:]

                if decoded_line.strip() == "[DONE]":
                    break

                try:
                    chunk = json.loads(decoded_line)
                    if "choices" in chunk and len(chunk["choices"]) > 0:
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield f"data: {json.dumps({'content': content})}\n\n"
                except json.JSONDecodeError:
                    pass

    return Response(
        stream_with_context(generate_stream()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

