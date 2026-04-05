# -----------------------------------------------
# 1. Install & import packages
# -----------------------------------------------
import yfinance as yf
import pandas as pd
import numpy as np
from scipy.optimize import minimize

# -----------------------------------------------
# 2. Define tickers for your portfolio
# -----------------------------------------------
tickers = {
    "VUSA": "VUSA.L",        # Vanguard S&P 500
    "STOXX600": "EXSA.DE",   # iShares STOXX 600
    "AGG_Bonds": "AGGH.L",   # Global Aggregate Bonds EUR hedged
    "Defence": "DFEN.MI",    # WisdomTree Defence (closest proxy)
    "Utilities": "U4NE.DE",  # Amundi Global Utilities
    "Commodities": "ICOM.L", # iShares Diversified Commodities
    "Microsoft": "MSFT",
    "Alphabet": "GOOGL"
}

# -----------------------------------------------
# 3. Download historical prices – last 3 years
# -----------------------------------------------
data = yf.download(list(tickers.values()), period="3y")["Adj Close"]

# Rename columns to readable names
data.columns = tickers.keys()

# Drop rows with missing data
data = data.dropna()

# -----------------------------------------------
# 4. Compute log returns
# -----------------------------------------------
returns = np.log(data / data.shift(1)).dropna()

# -----------------------------------------------
# 5. Portfolio optimization (Markowitz)
# -----------------------------------------------
n = len(returns.columns)

def portfolio_performance(weights):
    port_return = np.sum(weights * returns.mean() * 252)
    port_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov()*252, weights)))
    sharpe = port_return / port_vol
    return port_vol, port_return, sharpe

def negative_sharpe(weights):
    return -portfolio_performance(weights)[2]

constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
bounds = tuple((0, 1) for _ in range(n))
initial_weights = np.ones(n) / n

result = minimize(negative_sharpe, initial_weights,
                  method='SLSQP',
                  bounds=bounds,
                  constraints=constraints)

optimal_weights = result.x

# -----------------------------------------------
# 6. Apply weights to your total budget (10700 EUR)
# -----------------------------------------------
budget = 10700
allocation = optimal_weights * budget

# -----------------------------------------------
# 7. Display results
# -----------------------------------------------
print("\n✅ OPTIMAL MARKOWITZ PORTFOLIO (MAX SHARPE):")
for asset, weight in zip(returns.columns, optimal_weights):
    print(f"{asset}: {weight:.4f}  →  {weight*100:.2f}%")

print("\n✅ Allocation in EUR:")
for asset, amount in zip(returns.columns, allocation):
    print(f"{asset}: {amount:.2f} EUR")

vol, ret, sharpe = portfolio_performance(optimal_weights)
print("\n📌 Expected Annual Return:", round(ret, 4))
print("📌 Expected Annual Volatility:", round(vol, 4))
print("📌 Sharpe Ratio:", round(sharpe, 4))