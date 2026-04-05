import numpy as np

# import pandas as pd

# Using synthetic assumptions due to missing data: zero correlations, expected returns 0.
# volatilities annualized
vols = np.array([0.2722, 0.2751, 0.0831, 0.0835, 0.0834, 0.058, 0.0445, 0.2353])

# weights: portfolio weights including defence ETF substituted volatility
weights = np.array([0.2722, 0.2751, 0.0831, 0.0835, 0.0834, 0.0580, 0.0445, 0.0831])

# covariance matrix (diagonal)
cov = np.diag(vols ** 2)

# portfolio variance and volatility
port_var = weights.T @ cov @ weights
port_vol = np.sqrt(port_var)
port_vol = port_vol * 100

print(f"Portfolio Volatility: {port_vol:.2f}%")
