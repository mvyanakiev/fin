#!/usr/bin/env python3
"""
Program to fetch stock prices for given ISIN and exchange pairs.
Reads input from terminal (ISIN,exchange format) and outputs ISIN, exchange, and price.
"""

import sys
import yfinance as yf
from datetime import datetime, timedelta
import requests
import warnings
import logging
import threading
import time

# Suppress yfinance warnings and errors
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)


class ProgressSpinner:
    """Shows animated progress spinner while processing"""
    def __init__(self):
        self.spinner_chars = ['-', '\\', '|', '/']
        self.running = False
        self.thread = None
        self.idx = 0

    def start(self, message="Processing"):
        """Start the spinner animation"""
        self.running = True
        self.idx = 0
        self.message = message
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()

    def _spin(self):
        """Internal method to animate the spinner"""
        while self.running:
            sys.stderr.write(f'\r{self.message}... {self.spinner_chars[self.idx]} ')
            sys.stderr.flush()
            self.idx = (self.idx + 1) % len(self.spinner_chars)
            time.sleep(0.1)

    def stop(self):
        """Stop the spinner animation"""
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stderr.write('\r' + ' ' * (len(self.message) + 10) + '\r')
        sys.stderr.flush()

# Manual ISIN to ticker mapping for known mismatches between OpenFIGI and yfinance
ISIN_TICKER_OVERRIDES = {
    # German ETFs where OpenFIGI ticker doesn't match yfinance
    "DE0002635307": {  # iShares STOXX Europe 600 UCITS ETF (DE)
        "XETRA": "EXSA",
        "EAM": "EXSA",
        "TDG": "EXSA",
    },
    # Add more manual mappings here as needed
    # "ISIN": {"EXCHANGE": "TICKER", ...}
}


def isin_to_ticker_candidates(isin, exchange):
    """
    Convert ISIN to ticker symbol(s) using OpenFIGI API.
    Returns a list of (ticker, exchCode) tuples to try.
    """
    candidates = []

    try:
        url = "https://api.openfigi.com/v3/mapping"
        headers = {
            "Content-Type": "application/json",
            "X-OPENFIGI-APIKEY": ""  # Works without API key for limited requests
        }

        payload = [{
            "idType": "ID_ISIN",
            "idValue": isin
        }]

        response = requests.post(url, json=payload, headers=headers, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0 and "data" in data[0]:
                results = data[0]["data"]

                # Map exchange input to OpenFIGI exchange codes
                exchange_code_groups = {
                    "XETRA": ["GR", "GF", "GD", "GS", "GM", "XETR", "XFRA"],
                    "NYSE": ["US", "XNYS"],
                    "NASDAQ": ["US", "XNAS"],
                    "LSE": ["LN", "XLON"],
                    "TSE": ["JP", "XTKS"],
                    "EAM": ["XA", "XAMS"],  # Euronext Amsterdam
                    "EURONEXT": ["XA", "FP", "XB", "XL"],  # Amsterdam, Paris, Brussels, Lisbon
                    "TDG": ["GT", "GD", "GF", "GS", "GM"],  # Tradegate (German exchanges)
                }

                target_codes = exchange_code_groups.get(exchange.upper(), [])

                # Prioritize tickers from the target exchange
                for result in results:
                    result_code = result.get("exchCode", "")
                    ticker = result.get("ticker")
                    if ticker and target_codes and result_code in target_codes:
                        candidates.insert(0, (ticker, result_code))
                    elif ticker:
                        candidates.append((ticker, result_code))

    except Exception:
        pass

    return candidates


def get_ticker_symbols(isin, exchange):
    """
    Get list of ticker symbol candidates from ISIN with various exchange suffixes.
    Returns list of ticker symbols to try (limited to avoid excessive attempts).
    """
    # Check manual override mapping first
    if isin in ISIN_TICKER_OVERRIDES:
        override_tickers = ISIN_TICKER_OVERRIDES[isin]
        if exchange.upper() in override_tickers:
            manual_ticker = override_tickers[exchange.upper()]
            # Return the manual ticker with appropriate suffix
            exchange_suffix_map = {
                "XETRA": [".DE", ".F"],
                "LSE": [".L"],
                "EAM": [".AS"],
                "EURONEXT": [".PA", ".AS"],
                "TDG": [".DE", ".F"],
            }
            suffixes = exchange_suffix_map.get(exchange.upper(), [""])
            return [f"{manual_ticker}{suffix}" for suffix in suffixes]

    candidates = isin_to_ticker_candidates(isin, exchange)

    if not candidates:
        return []

    # Limit to first 5 ticker candidates to avoid excessive lookups
    candidates = candidates[:5]

    # Map exchange to yfinance suffixes to try (limited list)
    exchange_suffix_map = {
        "XETRA": [".DE", ".F"],
        "LSE": [".L"],
        "NYSE": [""],
        "NASDAQ": [""],
        "TSE": [".T"],
        "HKEX": [".HK"],
        "TSX": [".TO"],
        "ASX": [".AX"],
        "EAM": [".AS"],  # Euronext Amsterdam
        "EURONEXT": [".PA", ".AS", ".BR", ".LS"],  # Paris, Amsterdam, Brussels, Lisbon
        "TDG": [".DE", ".F"],  # Tradegate uses same suffixes as German exchanges
        "BSE": [".BO"],
        "NSE": [".NS"],
    }

    suffixes = exchange_suffix_map.get(exchange.upper(), [""])

    # Generate all combinations of tickers and suffixes
    ticker_symbols = []
    base_tickers_tried = set()

    for ticker, _ in candidates:
        # If ticker already has a suffix, try it as-is first
        if '.' in ticker:
            ticker_symbols.append(ticker)
        else:
            for suffix in suffixes:
                ticker_symbols.append(f"{ticker}{suffix}")

                # For tickers ending in '1', also try without the '1'
                # (OpenFIGI sometimes returns IUSA1 when yfinance needs IUSA)
                if ticker.endswith('1') or ticker.endswith('EUR') or ticker.endswith('USD') or ticker.endswith('GBP') or ticker.endswith('CHF'):
                    # Extract base ticker (remove currency suffix or '1')
                    if ticker.endswith('EUR') or ticker.endswith('USD') or ticker.endswith('GBP') or ticker.endswith('CHF'):
                        base_ticker = ticker[:-3]
                    elif ticker.endswith('1'):
                        base_ticker = ticker[:-1]

                    # Only add if we haven't tried this base ticker yet
                    if base_ticker not in base_tickers_tried:
                        ticker_symbols.append(f"{base_ticker}{suffix}")
                        base_tickers_tried.add(base_ticker)

    return ticker_symbols


def get_latest_trading_price(ticker_symbols, show_source=False):
    """
    Try to fetch price and name using a list of ticker symbol candidates.
    Returns (ticker_symbol, price, name, exchange) tuple or (None, None, None, None) if not found.
    """
    import os
    from contextlib import redirect_stderr

    for ticker_symbol in ticker_symbols:
        try:
            # Suppress yfinance errors by redirecting stderr
            with open(os.devnull, 'w') as devnull:
                with redirect_stderr(devnull):
                    ticker = yf.Ticker(ticker_symbol)

                    # Fetch historical data for the last 10 days (reduced from 30)
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=10)

                    hist = ticker.history(start=start_date, end=end_date, raise_errors=False)

                    if not hist.empty:
                        # Get the most recent closing price
                        latest_price = hist['Close'].iloc[-1]

                        # Get product name and exchange from ticker info
                        try:
                            info = ticker.info
                            name = info.get('longName') or info.get('shortName') or ticker_symbol
                            exchange_name = info.get('exchange', 'Unknown')
                        except:
                            name = ticker_symbol
                            exchange_name = 'Unknown'

                        # Outside the context manager now
                        result = (ticker_symbol, round(latest_price, 2), name, exchange_name)

            if 'result' in locals():
                return result

        except Exception:
            # Silently try next ticker
            continue

    return (None, None, None, None)


def main():
    """
    Main function to read input and process each ISIN/exchange pair.
    """
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        # Check for end command
        if line.lower() == 'end':
            break

        try:
            # Parse input line (tab-separated)
            parts = line.split('\t')
            if len(parts) != 2:
                continue

            isin = parts[0].strip()
            exchange = parts[1].strip()

            # Check if user wants to see data source (TDG = Tradegate, a special exchange code)
            show_source = exchange.upper() == "TDG"

            # Get ticker symbol candidates and try to fetch price
            ticker_symbols = get_ticker_symbols(isin, exchange)
            if not ticker_symbols:
                print(f"Unknown\tN/A\t{isin}")
                continue

            ticker_used, price, name, exchange_name = get_latest_trading_price(ticker_symbols, show_source)

            if price is None:
                price_str = "N/A"
                name = "Unknown"
            else:
                # Format price with comma as decimal separator
                price_str = f"{price:.2f}".replace('.', ',')

            # Print result immediately
            print(f"{name}\t{price_str}\t{isin}")
            sys.stdout.flush()  # Ensure output is displayed immediately

        except Exception:
            continue


if __name__ == "__main__":
    main()
