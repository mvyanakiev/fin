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

# Suppress yfinance warnings and errors
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)


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

    except Exception as e:
        print(f"OpenFIGI lookup failed: {e}", file=sys.stderr)

    return candidates


def get_ticker_symbols(isin, exchange):
    """
    Get list of ticker symbol candidates from ISIN with various exchange suffixes.
    Returns list of ticker symbols to try (limited to avoid excessive attempts).
    """
    candidates = isin_to_ticker_candidates(isin, exchange)

    if not candidates:
        return []

    # Limit to first 3 ticker candidates to avoid excessive lookups
    candidates = candidates[:3]

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
        "EURONEXT": [".PA"],
        "BSE": [".BO"],
        "NSE": [".NS"],
    }

    suffixes = exchange_suffix_map.get(exchange.upper(), [""])

    # Generate all combinations of tickers and suffixes
    ticker_symbols = []
    for ticker, _ in candidates:
        # If ticker already has a suffix, try it as-is first
        if '.' in ticker:
            ticker_symbols.append(ticker)
        else:
            for suffix in suffixes:
                ticker_symbols.append(f"{ticker}{suffix}")

    return ticker_symbols


def get_latest_trading_price(ticker_symbols):
    """
    Try to fetch price and name using a list of ticker symbol candidates.
    Returns (ticker_symbol, price, name) tuple or (None, None, None) if not found.
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

                        # Get product name from ticker info
                        try:
                            info = ticker.info
                            name = info.get('longName') or info.get('shortName') or ticker_symbol
                        except:
                            name = ticker_symbol

                        return (ticker_symbol, round(latest_price, 2), name)

        except Exception:
            # Silently try next ticker
            continue

    return (None, None, None)


def main():
    """
    Main function to read input and process each ISIN/exchange pair.
    """
    print("Enter ISIN<tab>exchange pairs (one per line). Type 'end' to finish:", file=sys.stderr)

    results = []

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
                print(f"Invalid input format: {line}", file=sys.stderr)
                continue

            isin = parts[0].strip()
            exchange = parts[1].strip()

            # Get ticker symbol candidates and try to fetch price
            ticker_symbols = get_ticker_symbols(isin, exchange)
            if not ticker_symbols:
                results.append((isin, "Unknown", "N/A"))
                continue

            ticker_used, price, name = get_latest_trading_price(ticker_symbols)

            if price is None:
                price_str = "N/A"
                name = "Unknown"
            else:
                # Format price with comma as decimal separator
                price_str = f"{price:.2f}".replace('.', ',')

            results.append((isin, name, price_str))

        except Exception as e:
            print(f"Error processing line '{line}': {e}", file=sys.stderr)
            continue

    # Print all results at the end
    for isin, name, price in results:
        print(f"{name}\t{price}\t{isin}")


if __name__ == "__main__":
    main()
