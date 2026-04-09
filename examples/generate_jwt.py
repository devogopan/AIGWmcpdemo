"""
Example: Generate a JWT token for use with the AI Gateway.

Usage
-----
  pip install pyjwt
  export AIGW_JWT_SECRET=my-demo-secret
  python examples/generate_jwt.py
"""

from __future__ import annotations

import os
import time

try:
    import jwt
except ImportError:
    raise SystemExit("Please install PyJWT first: pip install pyjwt")

SECRET = os.environ.get("AIGW_JWT_SECRET", "my-demo-secret")

payload = {
    "sub": "demo-user-1",
    "name": "Demo User",
    "iat": int(time.time()),
    "exp": int(time.time()) + 3600,  # 1-hour expiry
}

token = jwt.encode(payload, SECRET, algorithm="HS256")

print("Generated JWT token:")
print(token)
print()
print("Export it as an environment variable:")
print(f"  export AIGW_JWT={token}")
