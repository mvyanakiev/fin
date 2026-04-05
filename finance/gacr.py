import numpy as np

# Set parameters
cagr = np.array([0.1304, 0.0948, 0.15, 0.2064, 0.1088, 0.0876, 0.2249, 0.15])
vols = np.array([0.2722, 0.2751, 0.2353, 0.0835, 0.0834, 0.058, 0.0445, 0.0831])
weights = np.array([0.2722, 0.2751, 0.0831, 0.0835, 0.0834, 0.058, 0.0445, 0.0831])

# daily expected returns
daily_mu = (1 + cagr) ** (1 / 252) - 1

# zero-correlation covariance
cov = np.diag(vols ** 2)
daily_cov = cov / 252

N = 252
sims = 20000

returns = np.random.multivariate_normal(daily_mu, daily_cov, (sims, N))
port_daily = returns @ weights
cum = (1 + port_daily).prod(axis=1) - 1

cum.mean(), np.percentile(cum, [5, 50, 95])

print(f"Expected Annual Return: {cum.mean():.4f}")
