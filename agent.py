import os
import time
import json
import requests
from google import genai
from google.genai import types
from google_auth_oauthlib.flow import InstalledAppFlow

# --- 1. GOOGLE OAUTH SETUP ---
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email']

def get_google_auth_token():
    print("🔐 Starting Google OAuth flow (Headless Mode)...")
    flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
    creds = flow.run_local_server(port=8080, open_browser=False)
    print("✅ Google OAuth successful!")
    return creds.id_token

# --- 2. ENVOY AI GATEWAY CLIENT (Streamable HTTP) ---
GATEWAY_URL = "http://ai-gateway.aegle.info/mcp"

class StreamableHTTPClient:
    def __init__(self, endpoint, token):
        self.endpoint = endpoint
        self.token = token
        self.session_id = None
        self._request_counter = 0

    def _next_id(self):
        self._request_counter += 1
        return self._request_counter

    def _build_headers(self):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def send_request(self, method, params=None):
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params is not None:
            payload["params"] = params

        print(f"  → POST {self.endpoint} | method={method} | session={self.session_id[:20] + '...' if self.session_id else '(none)'}")
        resp = requests.post(self.endpoint, json=payload, headers=self._build_headers(), timeout=30)

        new_session = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
        if new_session:
            self.session_id = new_session

        if not resp.ok:
            print(f"  ❌ {method} failed: {resp.status_code} {resp.text[:500]}")
            resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "text/event-stream" in content_type:
            return self._parse_sse_response(resp.text)
        try:
            return resp.json()
        except Exception:
            return self._parse_sse_response(resp.text)

    def _parse_sse_response(self, text):
        last_result = {}
        for line in text.splitlines():
            if line.startswith("data:"):
                json_str = line.replace("data:", "", 1).strip()
                if json_str:
                    try:
                        parsed = json.loads(json_str)
                        if "result" in parsed or "error" in parsed:
                            last_result = parsed
                    except json.JSONDecodeError:
                        continue
        return last_result

    def send_notification(self, method, params=None):
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        requests.post(self.endpoint, json=payload, headers=self._build_headers(), timeout=10)

    def initialize(self):
        print("\n🤝 Initializing MCP Protocol with Envoy Gateway...")
        result = self.send_request("initialize", {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "kcd-demo-agent", "version": "1.0.0"}
        })
        self.send_notification("notifications/initialized")
        print("✅ MCP session initialized!")
        return result

    def close(self):
        if self.session_id:
            try:
                requests.delete(self.endpoint, headers=self._build_headers(), timeout=5)
                print("🔌 MCP session terminated.")
            except Exception:
                pass


# --- 3. SCHEMA SANITIZER FOR GEMINI ---

# Fields that Gemini's function calling API does NOT support
UNSUPPORTED_FIELDS = {
    "additional_properties",
    "additionalProperties",
    "$schema",
    "$id",
    "$ref",
    "$defs",
    "definitions",
    "examples",
    "default",
    "const",
    "title",
    "if",
    "then",
    "else",
    "allOf",
    "oneOf",
    "anyOf",
    "not",
    "patternProperties",
    "dependentSchemas",
    "dependentRequired",
    "unevaluatedProperties",
    "unevaluatedItems",
    "contentMediaType",
    "contentEncoding",
    "deprecated",
    "readOnly",
    "writeOnly",
}

def sanitize_schema(obj):
    """
    Recursively remove fields that Gemini doesn't understand
    from JSON Schema / OpenAPI parameter definitions.
    """
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            if key in UNSUPPORTED_FIELDS:
                continue
            cleaned[key] = sanitize_schema(value)
        return cleaned
    elif isinstance(obj, list):
        return [sanitize_schema(item) for item in obj]
    else:
        return obj


def mcp_tool_to_gemini(tool):
    """
    Convert an MCP tool definition to a Gemini function declaration,
    sanitizing the schema to remove unsupported fields.
    """
    schema = tool.get("inputSchema", {})
    sanitized = sanitize_schema(schema)

    # Gemini requires "type": "object" for parameters
    if "type" not in sanitized:
        sanitized["type"] = "object"

    # Gemini doesn't like empty properties
    if "properties" not in sanitized or not sanitized["properties"]:
        sanitized["properties"] = {"_placeholder": {"type": "string", "description": "Not used"}}

    return {
        "name": tool["name"],
        "description": tool.get("description", "No description")[:1024],
        "parameters": sanitized,
    }


# --- 4. THE AUTONOMOUS AGENT LOOP (WITH LOOP PROTECTION) ---

MAX_TOOL_CALLS = 15
MAX_SAME_TOOL_REPEATS = 3

def main():
    token = get_google_auth_token()
    mcp = StreamableHTTPClient(GATEWAY_URL, token)

    try:
        # Initialize
        init_result = mcp.initialize()
        print(f"📡 Server capabilities: {json.dumps(init_result, indent=2)[:500]}")

        # Discover tools
        print("\n⏳ Asking Envoy for the aggregated tool menu...")
        tools_response = mcp.send_request("tools/list")
        mcp_tools = tools_response.get("result", {}).get("tools", [])
        print(f"🛠️  Discovered {len(mcp_tools)} tools from Envoy AI Gateway!")
        for t in mcp_tools:
            print(f"   • {t['name']}: {t.get('description', 'N/A')[:80]}")

        if not mcp_tools:
            print("❌ No tools discovered!")
            return

        # Translate to Gemini schema WITH sanitization
        gemini_tools = []
        for t in mcp_tools:
            try:
                converted = mcp_tool_to_gemini(t)
                gemini_tools.append(converted)
            except Exception as e:
                print(f"   ⚠️  Skipping tool {t['name']}: {e}")

        print(f"\n✅ {len(gemini_tools)} tools converted for Gemini")

        # Initialize Gemini
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        config = types.GenerateContentConfig(
            tools=[{"function_declarations": gemini_tools}],
            temperature=0.1,
            system_instruction=(
                "You are an elite Kubernetes SRE. Use tools to investigate. "
                "If reading GitHub, assume owner 'devogopan' and repo 'crashing-pods'. "
                "IMPORTANT: Do NOT repeat the same tool call with the same arguments. "
                "If a tool returns no useful results, try a different approach or "
                "give your best answer with the information you have."
            )
        )

        chat = client.chats.create(model="gemini-2.5-flash-lite", config=config)

        prompt = (
            "The 'crashing-hello' service in the 'default' namespace is returning "
            "a 'connection refused' error. "
            "1. First, read Issues in the devogopan/crashing-pods GitHub repository "
            "to get the debugging runbook. "
            "2. Then, use the Kubernetes tools to investigate the cluster based on "
            "what the runbook suggests. "
            "3. Tell me exactly what the root cause is."
        )
        print(f"\n👨‍💻 User Prompt: {prompt}\n")

        response = chat.send_message(prompt)

        # === Agent loop with protection ===
        total_calls = 0
        call_history = {}

        while response.function_calls:
            if total_calls >= MAX_TOOL_CALLS:
                print(f"\n🛑 SAFETY: Reached max tool calls ({MAX_TOOL_CALLS}). Forcing final answer.")
                response = chat.send_message(
                    "You have reached the maximum number of tool calls. "
                    "Please provide your best answer NOW with the information gathered so far."
                )
                break

            tool_responses = []
            loop_detected = False

            for function_call in response.function_calls:
                tool_name = function_call.name
                tool_args = dict(function_call.args) if function_call.args else {}

                call_signature = f"{tool_name}|{json.dumps(tool_args, sort_keys=True)}"
                call_count = call_history.get(call_signature, 0) + 1
                call_history[call_signature] = call_count

                if call_count > MAX_SAME_TOOL_REPEATS:
                    print(f"\n🔄 LOOP DETECTED: {tool_name} called {call_count}x with same args!")
                    tool_responses.append(
                        types.Part.from_function_response(
                            name=tool_name,
                            response={
                                "result": {
                                    "isError": True,
                                    "content": [{
                                        "type": "text",
                                        "text": (
                                            f"ERROR: You already called {tool_name} with these "
                                            f"arguments {call_count} times. Try a DIFFERENT tool "
                                            f"or DIFFERENT arguments, or provide your final answer."
                                        )
                                    }]
                                }
                            }
                        )
                    )
                    loop_detected = True
                    continue

                print(f"\n🧠 Gemini calling: {tool_name} (call #{total_calls + 1})")
                print(f"   Args: {json.dumps(tool_args)[:300]}")

                mcp_result_raw = mcp.send_request(
                    "tools/call",
                    {"name": tool_name, "arguments": tool_args}
                )
                mcp_result = mcp_result_raw.get("result", {})
                total_calls += 1

                print(f"   ✅ Success! (total: {total_calls}/{MAX_TOOL_CALLS})")

                tool_responses.append(
                    types.Part.from_function_response(
                        name=tool_name,
                        response={"result": mcp_result}
                    )
                )

            print(f"\n🔄 Feeding {len(tool_responses)} results back to LLM...")

            if loop_detected and total_calls > 5:
                tool_responses.append(types.Part.from_text(
                    text="STOP calling tools. Provide your FINAL ANSWER now."
                ))

            response = chat.send_message(tool_responses)

        final_text = response.text if response.text else "Agent finished."
        print(f"\n{'='*60}")
        print(f"🤖 Agent Final Answer:\n{final_text}")
        print(f"{'='*60}")
        print(f"\n📊 Stats: {total_calls} total tool calls, {len(call_history)} unique calls")

    finally:
        mcp.close()


if __name__ == "__main__":
    main()