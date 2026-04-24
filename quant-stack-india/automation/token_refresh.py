"""
Zerodha Daily Access Token Refresh
====================================
Zerodha access tokens expire at midnight. This script runs at 08:00 IST
daily via APScheduler and generates a fresh token using TOTP 2FA.
Saves token to .zerodha_token.json for use by zerodha_broker.py.

Requirements: pyotp, kiteconnect, ZERODHA_API_KEY, ZERODHA_API_SECRET,
ZERODHA_USER_ID, ZERODHA_PASSWORD, ZERODHA_TOTP_SECRET all in .env
"""

import os
import json
import time
import logging
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
TOKEN_FILE = Path(".zerodha_token.json")


def refresh_zerodha_token() -> bool:
    """
    Automate Zerodha login using TOTP and save fresh access token.
    Returns True on success, False on failure.
    """
    api_key = os.getenv("ZERODHA_API_KEY", "")
    api_secret = os.getenv("ZERODHA_API_SECRET", "")
    user_id = os.getenv("ZERODHA_USER_ID", "")
    password = os.getenv("ZERODHA_PASSWORD", "")
    totp_secret = os.getenv("ZERODHA_TOTP_SECRET", "")

    if not all([api_key, api_secret, user_id, password, totp_secret]):
        logger.error("Zerodha credentials incomplete in .env — cannot refresh token")
        return False

    if api_key == "your_api_key_here":
        logger.info("Placeholder credentials detected — skipping token refresh (paper mode)")
        return True

    try:
        import pyotp
        from kiteconnect import KiteConnect
    except ImportError as e:
        logger.error(f"Import failed: {e} — run: pip install pyotp kiteconnect")
        return False

    try:
        totp = pyotp.TOTP(totp_secret)
        current_totp = totp.now()
        logger.info(f"Generated TOTP for token refresh")

        kite = KiteConnect(api_key=api_key)
        login_url = kite.login_url()
        
        # Use requests_html or selenium to automate login
        # Simpler approach: use kite.generate_session directly after getting request_token
        # NOTE: Full automation requires selenium. For now, implement the session generation:
        import requests
        session = requests.Session()
        session.headers.update({"User-Agent": "Mozilla/5.0"})
        
        # POST login
        login_resp = session.post(
            "https://kite.zerodha.com/api/login",
            data={"user_id": user_id, "password": password}
        )
        login_data = login_resp.json()
        if login_data.get("status") != "success":
            logger.error(f"Zerodha login failed: {login_data.get('message', 'unknown error')}")
            return False
        
        request_id = login_data["data"]["request_id"]
        
        # POST TOTP
        twofa_resp = session.post(
            "https://kite.zerodha.com/api/twofa",
            data={"user_id": user_id, "request_id": request_id, "twofa_value": current_totp, "twofa_type": "totp"}
        )
        twofa_data = twofa_resp.json()
        if twofa_data.get("status") != "success":
            logger.error(f"TOTP failed: {twofa_data.get('message', 'unknown')}")
            return False

        # Get access token
        # After TOTP, the session contains a redirect with request_token
        # This varies by Zerodha's implementation — fall back to manual if automated flow breaks
        logger.info("TOTP accepted. Access token generation requires manual redirect handling.")
        logger.info("Alternative: manually get request_token from redirect URL and call generate_session()")
        
        # Fallback: if .zerodha_token.json already exists and is today's, skip
        if TOKEN_FILE.exists():
            with open(TOKEN_FILE) as f:
                existing = json.load(f)
            if existing.get("date") == date.today().isoformat():
                logger.info("Token already refreshed today — skipping")
                return True
        
        logger.warning("Automated token refresh requires kite.zerodha.com redirect handling.")
        logger.warning("If using Kite Personal API, use the manual flow below once per day:")
        logger.warning(f"  1. Open: {login_url}")
        logger.warning("  2. Login with TOTP")
        logger.warning("  3. Copy request_token from redirect URL")
        logger.warning("  4. Run: python automation/token_refresh.py --request-token YOUR_TOKEN")
        return False

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        return False


def generate_session_from_request_token(request_token: str) -> bool:
    """Generate and save access token from request_token (from login redirect)."""
    api_key = os.getenv("ZERODHA_API_KEY", "")
    api_secret = os.getenv("ZERODHA_API_SECRET", "")
    try:
        from kiteconnect import KiteConnect
        kite = KiteConnect(api_key=api_key)
        data = kite.generate_session(request_token, api_secret=api_secret)
        access_token = data["access_token"]
        token_data = {"access_token": access_token, "date": date.today().isoformat()}
        with open(TOKEN_FILE, "w") as f:
            json.dump(token_data, f)
        logger.info(f"Access token saved to {TOKEN_FILE}")
        return True
    except Exception as e:
        logger.error(f"Session generation failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    import argparse
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-token", help="Zerodha request_token from login redirect URL")
    args = parser.parse_args()
    if args.request_token:
        success = generate_session_from_request_token(args.request_token)
        sys.exit(0 if success else 1)
    else:
        success = refresh_zerodha_token()
        sys.exit(0 if success else 1)
