import numpy as np
from sklearn.datasets import make_classification, make_regression
from gsroptim.sgl_tools import generate_data
from gsroptim.logreg import logreg_path
from gsroptim.lasso import lasso_path
from gsroptim.multi_task_lasso import multitask_lasso_path
from gsroptim.sgl import sgl_path, build_lambdas

n_samples = 20
n_features = 100

X, y = make_classification(n_samples=n_samples, n_features=n_features,
                           n_classes=2)
lambda_max = np.linalg.norm(np.dot(X.T, 0.5 - y), ord=np.inf)
lambdas = lambda_max / np.arange(5, 30, 5)
betas, gaps = logreg_path(X, y, lambdas)[:2]


X, y = make_regression(n_samples=n_samples, n_features=n_features)
lambda_max = np.linalg.norm(np.dot(X.T, y), ord=np.inf)
lambdas = lambda_max / np.arange(5, 30, 5)
betas, gaps = lasso_path(X, y, lambdas)[1:3]

X, y = make_regression(n_samples=20, n_features=100, n_targets=4)
lambda_max = np.max(np.sqrt(np.sum(np.dot(X.T, y) ** 2, axis=1)))
lambdas = lambda_max / np.arange(5, 30, 5)
betas, gaps = multitask_lasso_path(X, y, lambdas)[:2]


size_group = 20  # all groups have size = size_group
size_groups = size_group * np.ones(int(n_features / size_group), order='F',
                                   dtype=np.intc)
X, y = generate_data(n_samples, n_features, size_groups, rho=0.4)
omega = np.sqrt(size_groups)
n_groups = len(size_groups)
g_start = np.cumsum(size_groups, dtype=np.intc) - size_groups[0]
lambda_max = build_lambdas(X, y, omega, size_groups, g_start, n_lambdas=1)[0]
lambdas = lambda_max / np.arange(5, 30, 5)
betas, gaps = sgl_path(X, y, size_groups, omega, lambdas)[:2]
