"""
Pure Python Hidden Markov Model Implementation
M3.3: Fallback cuando hmmlearn no está disponible.

Basado en algoritmo de Baum-Welch (EM) para Gaussian HMM.
"""
from __future__ import annotations

from typing import Optional
import numpy as np
from enum import Enum


class HMMState(str, Enum):
    """Estados del HMM"""
    BULL_TRENDING_STRONG = "bull_trending_strong"
    BULL_TRENDING_WEAK = "bull_trending_weak"
    BEAR_TRENDING_STRONG = "bear_trending_strong"
    BEAR_TRENDING_WEAK = "bear_trending_weak"
    RANGE_BOUND_NARROW = "range_bound_narrow"
    RANGE_BOUND_WIDE = "range_bound_wide"
    TRANSITION = "transition"
    CRISIS = "crisis"


class PureGaussianHMM:
    """
    Gaussian Hidden Markov Model implementado en pure Python/numpy.
    Sin dependencias externas (solo numpy).
    """

    def __init__(
        self,
        n_components: int = 8,
        n_iter: int = 100,
        tol: float = 1e-4,
        random_state: int = 42,
    ):
        self.n_components = n_components
        self.n_iter = n_iter
        self.tol = tol
        self.random_state = random_state

        self._startprob: Optional[np.ndarray] = None
        self._transmat: Optional[np.ndarray] = None
        self._means: Optional[np.ndarray] = None
        self._covars: Optional[np.ndarray] = None

        self._init_params = {}

    def _initialize(self, X: np.ndarray) -> None:
        """Initialize parameters using smart approach based on data quantiles."""
        np.random.seed(self.random_state)
        n_samples, n_features = X.shape

        self._startprob = np.random.dirichlet(np.ones(self.n_components))

        self._transmat = np.random.dirichlet(
            np.ones(self.n_components), size=self.n_components
        )

        percentiles = np.linspace(0, 100, self.n_components + 2)[1:-1]
        self._means = np.percentile(X, percentiles, axis=0)

        var = np.var(X, axis=0, keepdims=True) + 1e-6
        self._covars = np.tile(var, (self.n_components, 1))

    def fit(self, X: np.ndarray) -> "PureGaussianHMM":
        """Fit the HMM using Baum-Welch algorithm (EM)."""
        X = np.array(X, dtype=np.float64)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        n_samples, n_features = X.shape

        self._initialize(X)

        for iteration in range(self.n_iter):
            alpha = self._compute_forward(X)
            beta = self._compute_backward(X)
            gamma = alpha * beta
            gamma /= gamma.sum(axis=1, keepdims=True) + 1e-10

            xi = self._compute_xi(X, alpha, beta)

            new_startprob = gamma[0].copy()

            new_transmat = np.zeros((self.n_components, self.n_components))
            for i in range(self.n_components):
                row_sum = xi[i, :].sum() + 1e-10
                new_transmat[i, :] = xi[i, :] / row_sum

            new_means = np.zeros((self.n_components, n_features))
            new_covars = np.zeros((self.n_components, n_features))

            for k in range(self.n_components):
                gamma_k = gamma[:, k]
                denom = gamma_k.sum() + 1e-10
                new_means[k] = (gamma_k[:, np.newaxis] * X).sum(axis=0) / denom

                diff = X - new_means[k]
                new_covars[k] = (gamma_k[:, np.newaxis] * diff ** 2).sum(axis=0) / denom

            self._startprob = new_startprob
            self._transmat = new_transmat
            self._means = new_means
            self._covars = new_covars + 1e-6

        return self

    def _compute_forward(self, X: np.ndarray) -> np.ndarray:
        """Forward algorithm."""
        n_samples = X.shape[0]

        alpha = np.zeros((n_samples, self.n_components))
        alpha[0] = self._startprob * self._pdf(X[0])

        for t in range(1, n_samples):
            alpha[t] = (alpha[t - 1] @ self._transmat) * self._pdf(X[t])

        return alpha

    def _compute_backward(self, X: np.ndarray) -> np.ndarray:
        """Backward algorithm."""
        n_samples = X.shape[0]

        beta = np.ones((n_samples, self.n_components))

        for t in range(n_samples - 2, -1, -1):
            beta[t] = (self._transmat * (beta[t + 1] * self._pdf(X[t + 1]))).sum(axis=1)

        return beta

    def _compute_xi(
        self, X: np.ndarray, alpha: np.ndarray, beta: np.ndarray
    ) -> np.ndarray:
        """Compute xi (joint posterior)."""
        n_samples = X.shape[0]

        xi = np.zeros((self.n_components, self.n_components))

        for t in range(n_samples - 1):
            numerator = (
                alpha[t][:, np.newaxis]
                * self._transmat
                * (beta[t + 1] * self._pdf(X[t + 1]))[np.newaxis, :]
            )
            denominator = numerator.sum() + 1e-10
            xi += numerator / denominator

        return xi

    def _pdf(self, x: np.ndarray) -> np.ndarray:
        """Compute Gaussian PDF for each component."""
        if x.ndim == 0:
            x = x.reshape(1, -1)

        diff = x - self._means
        exponent = -0.5 * np.sum(diff ** 2 / self._covars, axis=1)
        factor = 1.0 / np.sqrt((2 * np.pi) ** x.shape[0] * np.prod(self._covars, axis=1))

        return factor * np.exp(exponent)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict hidden states."""
        X = np.array(X, dtype=np.float64)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        alpha = self._compute_forward(X)
        return alpha.argmax(axis=1)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict posterior probabilities."""
        X = np.array(X, dtype=np.float64)
        if X.ndim == 1:
            X = X.reshape(-1, 1)

        alpha = self._compute_forward(X)
        return alpha / alpha.sum(axis=1, keepdims=True) + 1e-10


def create_hmm_detector(n_states: int = 8) -> PureGaussianHMM:
    """Factory function to create HMM detector."""
    return PureGaussianHMM(n_components=n_states, n_iter=100)


def fit_hmm_on_data(
    data: np.ndarray,
    n_states: int = 8,
) -> tuple[PureGaussianHMM, np.ndarray]:
    """
    Fit HMM on market data and return model + predictions.

    Args:
        data: Feature matrix (n_samples, n_features)
        n_states: Number of hidden states

    Returns:
        (fitted_model, predictions)
    """
    model = create_hmm_detector(n_states)
    model.fit(data)
    predictions = model.predict(data)
    return model, predictions


if __name__ == "__main__":
    np.random.seed(42)

    n_samples = 500
    n_features = 5

    X = np.random.randn(n_samples, n_features)

    model = PureGaussianHMM(n_components=8, n_iter=50)
    model.fit(X)

    predictions = model.predict(X)

    print(f"Fitted HMM with {8} states")
    print(f"Predictions shape: {predictions.shape}")
    print(f"State distribution: {np.bincount(predictions, minlength=8)}")