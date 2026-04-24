"""
Pre-run validation script for quant-stack-india.

This script checks all dependencies, API keys, and connectivity
before any trading operations are attempted.

Run as: python utils/validate_setup.py
"""

import sys
import os
import platform
from pathlib import Path
from typing import Tuple, List, Dict, Any

# Add colorama for cross-platform colored output
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False
    # Fallback to no colors
    class _Fore:
        GREEN = ""
        RED = ""
        YELLOW = ""
        RESET = ""
    class _Style:
        BRIGHT = ""
    Fore = _Fore()
    Style = _Style()


def print_success(message: str) -> None:
    """Print a success message with green checkmark."""
    print(f"{Fore.GREEN}✓{Style.RESET_ALL} {message}")


def print_error(message: str) -> None:
    """Print an error message with red X."""
    print(f"{Fore.RED}✗{Style.RESET_ALL} {message}")


def print_warning(message: str) -> None:
    """Print a warning message with yellow indicator."""
    print(f"{Fore.YELLOW}⚠{Style.RESET_ALL} {message}")


def check_python_version() -> Tuple[bool, str]:
    """Check Python version >= 3.11."""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    if version.major >= 3 and version.minor >= 11:
        return True, version_str
    return False, version_str


def check_packages() -> Tuple[bool, List[str], List[str]]:
    """
    Try to import every package in requirements.txt.
    Returns (all_ok, successful_imports, failed_imports).
    """
    packages = [
        "pandas",
        "numpy",
        "pandas_ta",
        "yfinance",
        "requests",
        "bs4",
        "lxml",
        "feedparser",
        "vectorbt",
        "backtrader",
        "statsmodels",
        "sklearn",
        "torch",
        "shap",
        "optuna",
        "pypfopt",
        "pykalman",
        "pyotp",
        "selenium",
        "apscheduler",
        "telegram",
        "streamlit",
        "plotly",
        "fredapi",
        "pytz",
        "scipy",
        "openpyxl",
        "sqlalchemy",
        "dotenv",
        "numba",
        "pytest",
        "holidays",
        "colorama",
        "yaml",
    ]
    
    successful = []
    failed = []
    
    for pkg in packages:
        try:
            if pkg == "bs4":
                __import__("bs4")
            elif pkg == "sklearn":
                __import__("sklearn")
            elif pkg == "pypfopt":
                __import__("pypfopt")
            elif pkg == "telegram":
                __import__("telegram")
            elif pkg == "apscheduler":
                __import__("apscheduler")
            elif pkg == "dotenv":
                __import__("dotenv")
            elif pkg == "yaml":
                __import__("yaml")
            else:
                __import__(pkg)
            successful.append(pkg)
        except ImportError as e:
            failed.append(f"{pkg}: {str(e)}")
    
    # Check optional packages separately
    optional_packages = [
        ("kiteconnect", "kiteconnect==5.0.1"),
        ("smartapi", "smartapi-python==1.3.9"),
        ("fyers_apiv3", "fyers-apiv3==3.1.3"),
        ("nsepython", "nsepython==2.9"),
        ("jugaad_data", "jugaad-data==0.27"),
        ("nsetools", "nsetools==1.0.11"),
    ]
    
    for pkg, install_cmd in optional_packages:
        try:
            __import__(pkg)
            successful.append(pkg)
        except ImportError:
            # These are optional but warn
            failed.append(f"{pkg} (optional, install with: pip install {install_cmd})")
    
    return len(failed) == 0 or all("(optional" in f for f in failed), successful, failed


def check_env_file() -> Tuple[bool, int, int, List[str]]:
    """
    Check .env file exists and all required variables are set.
    Returns (exists, vars_set, vars_total, missing_vars).
    """
    env_path = Path(".env")
    if not env_path.exists():
        return False, 0, 0, [".env file not found"]
    
    required_vars = [
        "ZERODHA_API_KEY",
        "ZERODHA_API_SECRET",
        "ZERODHA_USER_ID",
        "ZERODHA_PASSWORD",
        "ZERODHA_TOTP_SECRET",
        "ANGEL_API_KEY",
        "ANGEL_CLIENT_ID",
        "ANGEL_PASSWORD",
        "ANGEL_TOTP_SECRET",
        "FYERS_CLIENT_ID",
        "FYERS_SECRET_KEY",
        "FYERS_REDIRECT_URI",
        "ACTIVE_BROKER",
        "FRED_API_KEY",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TRADING_MODE",
    ]
    
    # Load .env file
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    
    missing = []
    set_count = 0
    
    for var in required_vars:
        value = os.getenv(var, "")
        if not value or value.startswith("your_") or value == "paper":
            if var in ["TRADING_MODE", "ACTIVE_BROKER"] and value:
                set_count += 1
            else:
                missing.append(var)
        else:
            set_count += 1
    
    return len(missing) == 0, set_count, len(required_vars), missing


def check_yfinance() -> Tuple[bool, str]:
    """Test yfinance by downloading RELIANCE.NS data."""
    try:
        import yfinance as yf
        ticker = yf.Ticker("RELIANCE.NS")
        data = ticker.history(period="5d")
        if data.empty:
            return False, "Empty DataFrame returned"
        return True, f"RELIANCE.NS — {len(data)} rows fetched"
    except Exception as e:
        return False, str(e)


def check_nsepython() -> Tuple[bool, str]:
    """Test nsepython connectivity."""
    try:
        import nsepython as nse
        # Try to get a quote
        try:
            quote = nse.nse_eq("RELIANCE")
            if quote and "priceInfo" in quote:
                return True, "connected"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
        return True, "connected"
    except ImportError:
        return False, "ModuleNotFoundError: nsepython not installed"
    except Exception as e:
        return False, f"Error: {str(e)}"


def check_broker_connectivity() -> Tuple[bool, str]:
    """Check broker API connectivity."""
    active_broker = os.getenv("ACTIVE_BROKER", "zerodha").lower()
    
    if active_broker == "zerodha":
        api_key = os.getenv("ZERODHA_API_KEY", "")
        if not api_key or api_key == "your_api_key_here":
            return False, "ZERODHA_API_KEY not set (will run in paper mode)"
        try:
            from kiteconnect import KiteConnect
            return True, "KiteConnect importable"
        except ImportError:
            return False, "kiteconnect not installed (pip install kiteconnect==5.0.1)"
    
    elif active_broker == "angel":
        api_key = os.getenv("ANGEL_API_KEY", "")
        if not api_key or api_key == "your_api_key_here":
            return False, "ANGEL_API_KEY not set"
        try:
            from smartapi import SmartConnect
            return True, "SmartAPI importable"
        except ImportError:
            return False, "smartapi not installed (pip install smartapi-python==1.3.9)"
    
    elif active_broker == "fyers":
        client_id = os.getenv("FYERS_CLIENT_ID", "")
        if not client_id or client_id == "your_client_id_here":
            return False, "FYERS_CLIENT_ID not set"
        try:
            from fyers_apiv3 import fyersModel
            return True, "Fyers API importable"
        except ImportError:
            return False, "fyers_apiv3 not installed (pip install fyers-apiv3==3.1.3)"
    
    return False, f"Unknown broker: {active_broker}"


def check_sqlite() -> Tuple[bool, str]:
    """Check SQLite directory is writable."""
    try:
        import sqlite3
        test_db = Path("data/test_write.db")
        test_db.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(test_db))
        conn.execute("CREATE TABLE IF NOT EXISTS test (id INTEGER)")
        conn.commit()
        conn.close()
        test_db.unlink(missing_ok=True)
        return True, "writable"
    except Exception as e:
        return False, str(e)


def check_data_directory() -> Tuple[bool, str]:
    """Check data/ directory exists and is writable."""
    data_dir = Path("data")
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        test_file = data_dir / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        return True, "exists and writable"
    except Exception as e:
        return False, str(e)


def run_validation(silent: bool = False) -> Tuple[bool, List[str]]:
    """
    Run all validation checks.
    
    Args:
        silent: If True, don't print output (for programmatic use)
        
    Returns:
        Tuple of (all_passed, list_of_errors)
    """
    errors = []
    
    if not silent:
        print(f"\n{Style.BRIGHT}=== quant-stack-india Validation ==={Style.RESET_ALL}\n")
    
    # Check 1: Python version
    ok, msg = check_python_version()
    if ok:
        if not silent:
            print_success(f"Python {msg}")
    else:
        if not silent:
            print_error(f"Python {msg} — Python 3.11+ required")
        errors.append(f"Python version: {msg}")
    
    # Check 2: Package imports
    ok, successful, failed = check_packages()
    if ok:
        if not silent:
            print_success(f"All {len(successful)} packages importable")
    else:
        critical_failures = [f for f in failed if "(optional" not in f]
        optional_failures = [f for f in failed if "(optional" in f]
        
        if critical_failures:
            if not silent:
                print_error(f"{len(critical_failures)} packages failed to import")
                for f in critical_failures:
                    print(f"  - {f}")
            errors.extend(critical_failures)
        
        if optional_failures and not silent:
            print_warning(f"{len(optional_failures)} optional packages missing")
            for f in optional_failures:
                print(f"  - {f}")
    
    # Check 3: .env file
    ok, set_count, total, missing = check_env_file()
    if ok:
        if not silent:
            print_success(f".env file: {set_count}/{total} variables set")
    else:
        if not silent:
            print_error(f".env file: {set_count}/{total} variables set")
            if ".env file not found" in missing:
                print(f"  Run: cp .env.example .env")
            else:
                print(f"  Missing: {', '.join(missing[:5])}")
                if len(missing) > 5:
                    print(f"  ... and {len(missing) - 5} more")
        errors.append(f".env variables: {set_count}/{total} set")
    
    # Check 4: yfinance
    ok, msg = check_yfinance()
    if ok:
        if not silent:
            print_success(f"yfinance: {msg}")
    else:
        if not silent:
            print_error(f"yfinance: {msg}")
        errors.append(f"yfinance: {msg}")
    
    # Check 5: nsepython
    ok, msg = check_nsepython()
    if ok:
        if not silent:
            print_success(f"nsepython: {msg}")
    else:
        if not silent:
            print_warning(f"nsepython: {msg}")
        # Don't add to errors as this is often due to NSE website issues
    
    # Check 6: Broker connectivity
    ok, msg = check_broker_connectivity()
    if ok:
        if not silent:
            print_success(f"Broker: {msg}")
    else:
        if not silent:
            print_warning(f"Broker: {msg}")
        # Don't add to errors as paper mode works without API keys
    
    # Check 7: SQLite
    ok, msg = check_sqlite()
    if ok:
        if not silent:
            print_success(f"SQLite: {msg}")
    else:
        if not silent:
            print_error(f"SQLite: {msg}")
        errors.append(f"SQLite: {msg}")
    
    # Check 8: Data directory
    ok, msg = check_data_directory()
    if ok:
        if not silent:
            print_success(f"Data directory: {msg}")
    else:
        if not silent:
            print_error(f"Data directory: {msg}")
        errors.append(f"Data directory: {msg}")
    
    # Final summary
    all_passed = len(errors) == 0
    
    if not silent:
        print()
        if all_passed:
            print(f"{Fore.GREEN}{Style.BRIGHT}✓ READY TO TRADE{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{Style.BRIGHT}✗ VALIDATION FAILED{Style.RESET_ALL}")
            print(f"\nFix the errors above before proceeding.")
            print(f"See EXECUTION_GUIDE.md for troubleshooting.")
        print()
    
    return all_passed, errors


def main() -> int:
    """Main entry point. Returns exit code 0 on success, 1 on failure."""
    all_passed, errors = run_validation(silent=False)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
