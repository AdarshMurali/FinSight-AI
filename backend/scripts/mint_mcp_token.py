"""
One-off script: mint a long-lived MCP token for a manager, to paste into that
manager's own claude_desktop_config.json env block as FINSIGHT_MCP_TOKEN.

Usage (from backend/):
    python scripts/mint_mcp_token.py sarah.chen@finsight.demo
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import User
from auth import create_mcp_token


def main():
    if len(sys.argv) != 2:
        print("Usage: python scripts/mint_mcp_token.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"No user found with email {email!r}")
            sys.exit(1)
        token = create_mcp_token(user)
        print(f"FINSIGHT_MCP_TOKEN for {user.full_name} ({user.role}):\n")
        print(token)
    finally:
        db.close()


if __name__ == "__main__":
    main()
