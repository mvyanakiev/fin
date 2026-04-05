import numpy as np

# Monte Carlo simulation with zero mean returns
vols = np.array([0.2722, 0.2751, 0.0831, 0.0835, 0.0834, 0.058, 0.0445, 0.2353])
weights = np.array([0.2722, 0.2751, 0.0831, 0.0835, 0.0834, 0.0580, 0.0445, 0.0831])
cov = np.diag(vols ** 2)

# daily covariance
daily_cov = cov / 252

N = 252
sims = 10000

# simulate daily returns
returns = np.random.multivariate_normal(np.zeros(8), daily_cov, (sims, N))

# portfolio daily returns
port_daily = returns @ weights

# cumulative annual return
cum = (1 + port_daily).prod(axis=1) - 1

cum.mean(), np.percentile(cum, [5, 50, 95])
