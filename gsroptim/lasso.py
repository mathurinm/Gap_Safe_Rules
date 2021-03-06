from __future__ import print_function

import numpy as np
import scipy as sp
from numpy.linalg import norm
from .cd_lasso_fast import cd_lasso, matrix_column_norm

NO_SCREENING = 0
GAPSAFE_SEQ = 1
GAPSAFE = 2


def lasso_path(X, y, lambdas, beta_init=None, fit_intercept=False,
               eps=1e-4, max_iter=3000, screening=GAPSAFE, f=10,
               gap_active_warm_start=False, strong_active_warm_start=True):
    """Compute Lasso path with coordinate descent

    The Lasso optimization solves:

    argmin_{beta} 0.5 * norm(y - X beta, 2)^2 + lambda * norm(beta, 1)

    Parameters
    ----------
    X : {array-like}, shape (n_samples, n_features)
        Training data. Pass directly as Fortran-contiguous data to avoid
        unnecessary memory duplication.

    y : ndarray, shape = (n_samples,)
        Target values

    lambdas : ndarray
        List of lambdas where to compute the models.

    beta_init : array, shape (n_features, ), optional
        The initial values of the coefficients.

    eps : float, optional
        Prescribed accuracy on the duality gap.

    max_iter : float, optional
        Number of epochs of the coordinate descent.

    screening : integer
        Screening rule to be used: it must be choosen in the following list

        NO_SCREENING = 0: Standard method

        GAPSAFE_SEQ = 1: Proposed safe screening rule using duality gap
                          in a sequential way: Gap Safe (Seq.)

        GAPSAFE = 2: Proposed safe screening rule using duality gap in both a
                      sequential and dynamic way.: Gap Safe (Seq. + Dyn)

    f : float, optional
        The duality gap will be evaluated and screening rule executed at each f
        epochs.

    Returns
    -------
    intercepts : array, shape (n_lambdas)
        Fitted intercepts along the path.

    betas : array, shape (n_features, n_lambdas)
        Coefficients beta along the path.

    dual_gaps : array, shape (n_lambdas,)
        The dual gaps at the end of the optimization for each lambda.

    n_iters : array-like, shape (n_lambdas,)
        The number of iterations taken by the block coordinate descent
        optimizer to reach the specified accuracy for each lambda.

    n_active_features : array, shape (n_lambdas,)
        Number of active variables.

    """

    if type(lambdas) != np.ndarray:
        lambdas = np.array([lambdas])

    n_lambdas = len(lambdas)

    n_samples, n_features = X.shape
    betas = np.zeros((n_features, n_lambdas))

    if beta_init is None:
        beta_init = np.zeros(n_features, dtype=float, order='F')
    else:
        beta_init = np.asarray(beta_init, order='F')

    intercepts = np.zeros(n_lambdas)
    disabled_features = np.zeros(n_features, dtype=np.intc, order='F')
    gaps = np.ones(n_lambdas)
    n_iters = np.zeros(n_lambdas)
    n_active_features = np.zeros(n_lambdas)

    sparse = sp.sparse.issparse(X)
    center = fit_intercept
    active_warm_start = strong_active_warm_start or gap_active_warm_start
    run_active_warm_start = True

    if center:
        # We center the data for the intercept
        X_mean = np.asfortranarray(X.mean(axis=0)).ravel()
        y_mean = y.mean()
        y -= y_mean
        if not sparse:
            X -= X_mean
    else:
        X_mean = None

    if sparse:
        X_ = None
        X_data = X.data
        X_indices = X.indices
        X_indptr = X.indptr
        norm_Xcent = np.zeros(n_features, dtype=float, order='F')
        matrix_column_norm(n_samples, n_features, X_data, X_indices, X_indptr,
                           norm_Xcent, X_mean, center=center)
        if center:
            residual = np.asfortranarray(y - X.dot(beta_init) +
                                         X_mean.dot(beta_init))
            sum_residual = residual.sum()
        else:
            residual = np.asfortranarray(y - X.dot(beta_init))
            sum_residual = 0
    else:
        X_ = np.asfortranarray(X)
        X_data = None
        X_indices = None
        X_indptr = None
        norm_Xcent = (X_ ** 2).sum(axis=0)
        residual = np.asfortranarray(y - X.dot(beta_init))
        sum_residual = 0

    y = np.asfortranarray(y)
    nrm2_y = norm(y) ** 2
    XTR = np.asfortranarray(X.T.dot(residual))

    tol = eps * nrm2_y  # duality gap tolerance

    for t in range(n_lambdas):

        if active_warm_start and t != 0:

            if strong_active_warm_start:
                disabled_features = (np.abs(XTR) < 2. * lambdas[t] -
                                     lambdas[t - 1]).astype(np.intc)

            if gap_active_warm_start:
                run_active_warm_start = n_active_features[t] < n_features

            if run_active_warm_start:

                _, sum_residual, _, _ = \
                    cd_lasso(X_, X_data, X_indices, X_indptr, y, X_mean,
                             beta_init, norm_Xcent, XTR, residual,
                             disabled_features, nrm2_y, lambdas[t],
                             sum_residual, tol, max_iter, f, screening,
                             wstr_plus=1, sparse=sparse, center=center)

        gaps[t], sum_residual, n_iters[t], n_active_features[t] = \
            cd_lasso(X_, X_data, X_indices, X_indptr, y, X_mean, beta_init,
                     norm_Xcent, XTR, residual, disabled_features, nrm2_y,
                     lambdas[t], sum_residual, tol, max_iter, f, screening,
                     wstr_plus=0, sparse=sparse, center=center)

        betas[:, t] = beta_init.copy()
        if fit_intercept:
            intercepts[t] = y_mean - X_mean.dot(beta_init)

        if t == 0 and screening != NO_SCREENING:
            n_active_features[0] = 0

        if abs(gaps[t]) > tol:

            print("warning: did not converge, t = ", t)
            print("gap = ", gaps[t], "eps = ", eps)

    return intercepts, betas, gaps, n_iters, n_active_features
