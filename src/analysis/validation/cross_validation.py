#==========================================================================================\\\
#==================== src/analysis/validation/cross_validation.py ======================\\\
#==========================================================================================\\\

"""Cross-validation methods for analysis validation and model selection.

This module provides comprehensive cross-validation techniques for validating
analysis methods, selecting models, and assessing generalization performance
in control engineering applications.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any, Union, Callable
import numpy as np
from scipy import stats
import warnings
from dataclasses import dataclass, field
# Minimal sklearn replacements for basic cross-validation functionality
# This avoids heavyweight sklearn dependency while providing core interfaces

class KFold:
    def __init__(self, n_splits=5, shuffle=False, random_state=None):
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = random_state

    def split(self, X):
        n_samples = len(X)
        indices = np.arange(n_samples)
        if self.shuffle:
            if self.random_state:
                np.random.seed(self.random_state)
            np.random.shuffle(indices)

        fold_size = n_samples // self.n_splits
        for i in range(self.n_splits):
            start = i * fold_size
            end = start + fold_size if i < self.n_splits - 1 else n_samples
            test_idx = indices[start:end]
            train_idx = np.concatenate([indices[:start], indices[end:]])
            yield train_idx, test_idx

class StratifiedKFold:
    def __init__(self, n_splits=5, shuffle=False, random_state=None):
        self.n_splits = n_splits
        self.shuffle = shuffle
        self.random_state = random_state

    def split(self, X, y=None):
        # Simplified - just use regular KFold for now
        kfold = KFold(self.n_splits, self.shuffle, self.random_state)
        return kfold.split(X)

class TimeSeriesSplit:
    def __init__(self, n_splits=5):
        self.n_splits = n_splits

    def split(self, X):
        n_samples = len(X)
        for i in range(1, self.n_splits + 1):
            train_end = (n_samples * i) // (self.n_splits + 1)
            test_start = train_end
            test_end = (n_samples * (i + 1)) // (self.n_splits + 1)
            train_idx = np.arange(train_end)
            test_idx = np.arange(test_start, min(test_end, n_samples))
            if len(test_idx) > 0:
                yield train_idx, test_idx

class LeaveOneOut:
    def split(self, X):
        n_samples = len(X)
        for i in range(n_samples):
            train_idx = np.concatenate([np.arange(i), np.arange(i+1, n_samples)])
            test_idx = np.array([i])
            yield train_idx, test_idx

def mean_squared_error(y_true, y_pred):
    """Compute mean squared error."""
    return float(np.mean((y_true - y_pred) ** 2))

def mean_absolute_error(y_true, y_pred):
    """Compute mean absolute error."""
    return float(np.mean(np.abs(y_true - y_pred)))
import itertools

from ..core.interfaces import StatisticalValidator, AnalysisResult, AnalysisStatus, DataProtocol
from ..core.data_structures import StatisticalTestResult, ConfidenceInterval


@dataclass
class CrossValidationConfig:
    """Configuration for cross-validation methods."""
    # Basic CV parameters
    cv_method: str = "k_fold"  # "k_fold", "stratified", "time_series", "leave_one_out", "monte_carlo"
    n_splits: int = 5
    shuffle: bool = True
    random_state: Optional[int] = None

    # Time series specific
    max_train_size: Optional[int] = None
    test_size: Optional[int] = None
    gap: int = 0  # Gap between train and test

    # Monte Carlo CV
    n_repetitions: int = 100
    test_ratio: float = 0.2

    # Nested CV
    enable_nested_cv: bool = False
    inner_cv_splits: int = 3

    # Performance metrics
    regression_metrics: List[str] = field(default_factory=lambda: ["mse", "mae", "r2", "explained_variance"])
    classification_metrics: List[str] = field(default_factory=lambda: ["accuracy", "precision", "recall", "f1"])

    # Statistical testing
    significance_level: float = 0.05
    confidence_level: float = 0.95
    paired_tests: bool = True

    # Model selection
    enable_model_selection: bool = True
    selection_criterion: str = "cv_score"  # "cv_score", "aic", "bic", "validation_score"


class CrossValidator(StatisticalValidator):
    """Comprehensive cross-validation framework."""

    def __init__(self, config: Optional[CrossValidationConfig] = None):
        """Initialize cross-validator.

        Parameters
        ----------
        config : CrossValidationConfig, optional
            Configuration for cross-validation
        """
        self.config = config or CrossValidationConfig()

    @property
    def validation_methods(self) -> List[str]:
        """List of validation methods supported."""
        return [
            "k_fold_validation",
            "time_series_validation",
            "monte_carlo_validation",
            "nested_validation",
            "model_comparison",
            "bias_variance_analysis",
            "learning_curve_analysis"
        ]

    def validate(self, data: Union[List[Dict[str, float]], np.ndarray], **kwargs) -> AnalysisResult:
        """Perform cross-validation analysis.

        Parameters
        ----------
        data : Union[List[Dict[str, float]], np.ndarray]
            Data for cross-validation
        **kwargs
            Additional parameters:
            - models: List of models/functions to validate
            - target_variable: Name of target variable for prediction
            - feature_variables: List of feature variable names
            - prediction_function: Function for making predictions
            - scoring_function: Custom scoring function

        Returns
        -------
        AnalysisResult
            Comprehensive cross-validation results
        """
        try:
            results = {}

            # Preprocess data
            X, y = self._preprocess_data(data, **kwargs)

            if X is None or y is None:
                return AnalysisResult(
                    status=AnalysisStatus.ERROR,
                    message="Could not extract features and targets from data",
                    data={}
                )

            # Get models/methods to validate
            models = kwargs.get('models', [])
            prediction_function = kwargs.get('prediction_function')

            if not models and prediction_function is None:
                return AnalysisResult(
                    status=AnalysisStatus.ERROR,
                    message="No models or prediction function provided for validation",
                    data={}
                )

            # Perform different types of cross-validation
            if "k_fold_validation" in self.validation_methods:
                kfold_results = self._perform_k_fold_validation(X, y, models, prediction_function, **kwargs)
                results['k_fold_validation'] = kfold_results

            if "time_series_validation" in self.validation_methods and self.config.cv_method == "time_series":
                ts_results = self._perform_time_series_validation(X, y, models, prediction_function, **kwargs)
                results['time_series_validation'] = ts_results

            if "monte_carlo_validation" in self.validation_methods:
                mc_results = self._perform_monte_carlo_validation(X, y, models, prediction_function, **kwargs)
                results['monte_carlo_validation'] = mc_results

            if "nested_validation" in self.validation_methods and self.config.enable_nested_cv:
                nested_results = self._perform_nested_validation(X, y, models, **kwargs)
                results['nested_validation'] = nested_results

            if "model_comparison" in self.validation_methods and len(models) > 1:
                comparison_results = self._perform_model_comparison(X, y, models, **kwargs)
                results['model_comparison'] = comparison_results

            if "bias_variance_analysis" in self.validation_methods:
                bias_variance_results = self._perform_bias_variance_analysis(X, y, models, prediction_function, **kwargs)
                results['bias_variance_analysis'] = bias_variance_results

            if "learning_curve_analysis" in self.validation_methods:
                learning_curve_results = self._perform_learning_curve_analysis(X, y, models, prediction_function, **kwargs)
                results['learning_curve_analysis'] = learning_curve_results

            # Overall validation summary
            validation_summary = self._generate_validation_summary(results)
            results['validation_summary'] = validation_summary

            return AnalysisResult(
                status=AnalysisStatus.SUCCESS,
                message="Cross-validation completed successfully",
                data=results,
                metadata={
                    'validator': 'CrossValidator',
                    'config': self.config.__dict__,
                    'n_samples': len(X),
                    'n_features': X.shape[1] if X.ndim > 1 else 1
                }
            )

        except Exception as e:
            return AnalysisResult(
                status=AnalysisStatus.ERROR,
                message=f"Cross-validation failed: {str(e)}",
                data={'error_details': str(e)}
            )

    def _preprocess_data(self, data: Union[List[Dict[str, float]], np.ndarray], **kwargs) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Preprocess data for cross-validation."""
        target_variable = kwargs.get('target_variable')
        feature_variables = kwargs.get('feature_variables', [])

        if isinstance(data, list) and data and isinstance(data[0], dict):
            # Dictionary data
            if target_variable is None:
                # Use first variable as target, rest as features
                keys = list(data[0].keys())
                target_variable = keys[0]
                feature_variables = keys[1:] if len(keys) > 1 else keys[:1]

            # Extract features and targets
            X_list = []
            y_list = []

            for record in data:
                if target_variable in record:
                    y_list.append(record[target_variable])

                    if feature_variables:
                        features = [record.get(var, 0.0) for var in feature_variables]
                    else:
                        features = [v for k, v in record.items() if k != target_variable and isinstance(v, (int, float))]

                    X_list.append(features)

            if not X_list or not y_list:
                return None, None

            X = np.array(X_list)
            y = np.array(y_list)

        elif isinstance(data, np.ndarray):
            # Array data
            if data.ndim == 1:
                # 1D array - use lagged values as features
                X = self._create_lagged_features(data)
                y = data[len(data) - len(X):]
            else:
                # 2D array - use first column as target, rest as features
                y = data[:, 0]
                X = data[:, 1:] if data.shape[1] > 1 else data[:, :1]

        else:
            return None, None

        # Remove invalid values
        valid_mask = np.isfinite(y) & np.all(np.isfinite(X), axis=1)
        X = X[valid_mask]
        y = y[valid_mask]

        if len(X) == 0 or len(y) == 0:
            return None, None

        return X, y

    def _create_lagged_features(self, data: np.ndarray, n_lags: int = 3) -> np.ndarray:
        """Create lagged features from time series data."""
        n_samples = len(data) - n_lags
        X = np.zeros((n_samples, n_lags))

        for i in range(n_samples):
            X[i, :] = data[i:i+n_lags]

        return X

    def _get_cv_splitter(self, X: np.ndarray, y: np.ndarray):
        """Get cross-validation splitter based on configuration."""
        if self.config.cv_method == "k_fold":
            return KFold(n_splits=self.config.n_splits, shuffle=self.config.shuffle, random_state=self.config.random_state)

        elif self.config.cv_method == "stratified":
            # For regression, we bin the targets
            y_binned = np.digitize(y, np.percentile(y, np.linspace(0, 100, self.config.n_splits + 1)))
            return StratifiedKFold(n_splits=self.config.n_splits, shuffle=self.config.shuffle, random_state=self.config.random_state)

        elif self.config.cv_method == "time_series":
            return TimeSeriesSplit(
                n_splits=self.config.n_splits,
                max_train_size=self.config.max_train_size,
                test_size=self.config.test_size,
                gap=self.config.gap
            )

        elif self.config.cv_method == "leave_one_out":
            return LeaveOneOut()

        else:
            return KFold(n_splits=self.config.n_splits, shuffle=self.config.shuffle, random_state=self.config.random_state)

    def _perform_k_fold_validation(self, X: np.ndarray, y: np.ndarray,
                                  models: List[Any], prediction_function: Optional[Callable],
                                  **kwargs) -> Dict[str, Any]:
        """Perform k-fold cross-validation."""
        cv_splitter = self._get_cv_splitter(X, y)
        results = {}

        # Validate models
        if models:
            for i, model in enumerate(models):
                model_name = getattr(model, '__name__', f'model_{i}')
                model_results = self._validate_single_model(X, y, model, cv_splitter, **kwargs)
                results[model_name] = model_results

        # Validate prediction function
        if prediction_function:
            function_results = self._validate_prediction_function(X, y, prediction_function, cv_splitter, **kwargs)
            results['prediction_function'] = function_results

        return results

    def _perform_time_series_validation(self, X: np.ndarray, y: np.ndarray,
                                       models: List[Any], prediction_function: Optional[Callable],
                                       **kwargs) -> Dict[str, Any]:
        """Perform time series cross-validation."""
        # Use TimeSeriesSplit specifically
        ts_splitter = TimeSeriesSplit(
            n_splits=self.config.n_splits,
            max_train_size=self.config.max_train_size,
            test_size=self.config.test_size,
            gap=self.config.gap
        )

        results = {}

        # Time series specific metrics
        ts_metrics = ['mse', 'mae', 'mape', 'directional_accuracy']

        # Validate models
        if models:
            for i, model in enumerate(models):
                model_name = getattr(model, '__name__', f'model_{i}')
                model_results = self._validate_single_model(X, y, model, ts_splitter, metrics=ts_metrics, **kwargs)
                results[model_name] = model_results

        # Validate prediction function
        if prediction_function:
            function_results = self._validate_prediction_function(X, y, prediction_function, ts_splitter, metrics=ts_metrics, **kwargs)
            results['prediction_function'] = function_results

        return results

    def _perform_monte_carlo_validation(self, X: np.ndarray, y: np.ndarray,
                                       models: List[Any], prediction_function: Optional[Callable],
                                       **kwargs) -> Dict[str, Any]:
        """Perform Monte Carlo cross-validation."""
        results = {}
        n_samples = len(X)
        test_size = int(self.config.test_ratio * n_samples)

        all_scores = {f'model_{i}': [] for i in range(len(models))}
        if prediction_function:
            all_scores['prediction_function'] = []

        for rep in range(self.config.n_repetitions):
            # Random train-test split
            indices = np.random.permutation(n_samples)
            test_indices = indices[:test_size]
            train_indices = indices[test_size:]

            X_train, X_test = X[train_indices], X[test_indices]
            y_train, y_test = y[train_indices], y[test_indices]

            # Validate models
            for i, model in enumerate(models):
                try:
                    score = self._evaluate_model_on_split(model, X_train, y_train, X_test, y_test, **kwargs)
                    all_scores[f'model_{i}'].append(score)
                except Exception as e:
                    warnings.warn(f"Model {i} failed in repetition {rep}: {e}")

            # Validate prediction function
            if prediction_function:
                try:
                    score = self._evaluate_function_on_split(prediction_function, X_train, y_train, X_test, y_test, **kwargs)
                    all_scores['prediction_function'].append(score)
                except Exception as e:
                    warnings.warn(f"Prediction function failed in repetition {rep}: {e}")

        # Compute statistics
        for method_name, scores in all_scores.items():
            if scores:
                results[method_name] = {
                    'mean_score': float(np.mean(scores)),
                    'std_score': float(np.std(scores)),
                    'median_score': float(np.median(scores)),
                    'min_score': float(np.min(scores)),
                    'max_score': float(np.max(scores)),
                    'n_repetitions': len(scores),
                    'confidence_interval': self._compute_confidence_interval(scores)
                }

        return results

    def _perform_nested_validation(self, X: np.ndarray, y: np.ndarray, models: List[Any], **kwargs) -> Dict[str, Any]:
        """Perform nested cross-validation for unbiased performance estimation."""
        outer_cv = self._get_cv_splitter(X, y)
        inner_cv = KFold(n_splits=self.config.inner_cv_splits, shuffle=True, random_state=self.config.random_state)

        results = {}

        for i, model in enumerate(models):
            model_name = getattr(model, '__name__', f'model_{i}')
            outer_scores = []
            best_params_per_fold = []

            for train_idx, test_idx in outer_cv.split(X, y):
                X_train_outer, X_test_outer = X[train_idx], X[test_idx]
                y_train_outer, y_test_outer = y[train_idx], y[test_idx]

                # Inner CV for hyperparameter tuning (simplified)
                inner_scores = []
                for inner_train_idx, inner_val_idx in inner_cv.split(X_train_outer, y_train_outer):
                    X_train_inner = X_train_outer[inner_train_idx]
                    y_train_inner = y_train_outer[inner_train_idx]
                    X_val_inner = X_train_outer[inner_val_idx]
                    y_val_inner = y_train_outer[inner_val_idx]

                    # Evaluate model on inner fold
                    score = self._evaluate_model_on_split(model, X_train_inner, y_train_inner, X_val_inner, y_val_inner, **kwargs)
                    inner_scores.append(score)

                # Select best parameters (simplified - just use mean performance)
                best_params = {'performance': np.mean(inner_scores)}
                best_params_per_fold.append(best_params)

                # Evaluate on outer test set
                outer_score = self._evaluate_model_on_split(model, X_train_outer, y_train_outer, X_test_outer, y_test_outer, **kwargs)
                outer_scores.append(outer_score)

            results[model_name] = {
                'nested_cv_score': float(np.mean(outer_scores)),
                'nested_cv_std': float(np.std(outer_scores)),
                'outer_fold_scores': outer_scores,
                'best_params_per_fold': best_params_per_fold
            }

        return results

    def _perform_model_comparison(self, X: np.ndarray, y: np.ndarray, models: List[Any], **kwargs) -> Dict[str, Any]:
        """Perform statistical comparison between models."""
        if len(models) < 2:
            return {'error': 'Need at least 2 models for comparison'}

        cv_splitter = self._get_cv_splitter(X, y)
        model_scores = {}

        # Collect scores for each model
        for i, model in enumerate(models):
            model_name = getattr(model, '__name__', f'model_{i}')
            scores = []

            for train_idx, test_idx in cv_splitter.split(X, y):
                X_train, X_test = X[train_idx], X[test_idx]
                y_train, y_test = y[train_idx], y[test_idx]

                try:
                    score = self._evaluate_model_on_split(model, X_train, y_train, X_test, y_test, **kwargs)
                    scores.append(score)
                except Exception as e:
                    warnings.warn(f"Model {model_name} failed on fold: {e}")

            model_scores[model_name] = scores

        # Pairwise comparisons
        comparison_results = {}
        model_names = list(model_scores.keys())

        for i, model_a in enumerate(model_names):
            for j, model_b in enumerate(model_names):
                if i < j:  # Avoid duplicate comparisons
                    scores_a = model_scores[model_a]
                    scores_b = model_scores[model_b]

                    if len(scores_a) == len(scores_b) and len(scores_a) > 0:
                        # Paired t-test
                        if self.config.paired_tests:
                            t_stat, p_value = stats.ttest_rel(scores_a, scores_b)
                            test_name = "Paired t-test"
                        else:
                            t_stat, p_value = stats.ttest_ind(scores_a, scores_b)
                            test_name = "Independent t-test"

                        # Effect size (Cohen's d)
                        pooled_std = np.sqrt((np.var(scores_a) + np.var(scores_b)) / 2)
                        cohens_d = (np.mean(scores_a) - np.mean(scores_b)) / pooled_std if pooled_std > 0 else 0

                        comparison_key = f"{model_a}_vs_{model_b}"
                        comparison_results[comparison_key] = {
                            'test_statistic': float(t_stat),
                            'p_value': float(p_value),
                            'significant': bool(p_value < self.config.significance_level),
                            'effect_size': float(cohens_d),
                            'test_name': test_name,
                            'mean_diff': float(np.mean(scores_a) - np.mean(scores_b))
                        }

        # Overall ranking
        mean_scores = {name: np.mean(scores) for name, scores in model_scores.items() if scores}
        ranking = sorted(mean_scores.items(), key=lambda x: x[1], reverse=True)  # Assuming higher is better

        return {
            'pairwise_comparisons': comparison_results,
            'model_ranking': ranking,
            'model_scores_summary': {
                name: {
                    'mean': float(np.mean(scores)),
                    'std': float(np.std(scores)),
                    'min': float(np.min(scores)),
                    'max': float(np.max(scores))
                } for name, scores in model_scores.items() if scores
            }
        }

    def _perform_bias_variance_analysis(self, X: np.ndarray, y: np.ndarray,
                                       models: List[Any], prediction_function: Optional[Callable],
                                       **kwargs) -> Dict[str, Any]:
        """Perform bias-variance decomposition analysis."""
        results = {}
        n_bootstrap = 100  # Number of bootstrap samples
        n_samples = len(X)

        # Select a subset for testing
        test_size = min(50, n_samples // 4)
        test_indices = np.random.choice(n_samples, size=test_size, replace=False)
        X_test = X[test_indices]
        y_test = y[test_indices]

        # Remove test samples from training data
        train_mask = np.ones(n_samples, dtype=bool)
        train_mask[test_indices] = False
        X_train_full = X[train_mask]
        y_train_full = y[train_mask]

        # Analyze each model
        for i, model in enumerate(models):
            model_name = getattr(model, '__name__', f'model_{i}')

            predictions = []
            for bootstrap_iter in range(n_bootstrap):
                # Bootstrap sample
                bootstrap_indices = np.random.choice(len(X_train_full), size=len(X_train_full), replace=True)
                X_bootstrap = X_train_full[bootstrap_indices]
                y_bootstrap = y_train_full[bootstrap_indices]

                try:
                    # Train model and predict
                    y_pred = self._train_and_predict(model, X_bootstrap, y_bootstrap, X_test)
                    predictions.append(y_pred)
                except Exception as e:
                    warnings.warn(f"Bootstrap iteration {bootstrap_iter} failed for {model_name}: {e}")

            if predictions:
                predictions = np.array(predictions)

                # Compute bias and variance
                mean_predictions = np.mean(predictions, axis=0)
                bias_squared = np.mean((mean_predictions - y_test)**2)
                variance = np.mean(np.var(predictions, axis=0))
                noise = np.var(y_test)  # Assuming irreducible error is noise in targets

                results[model_name] = {
                    'bias_squared': float(bias_squared),
                    'variance': float(variance),
                    'noise': float(noise),
                    'total_error': float(bias_squared + variance + noise),
                    'bias_variance_ratio': float(bias_squared / (variance + 1e-12))
                }

        return results

    def _perform_learning_curve_analysis(self, X: np.ndarray, y: np.ndarray,
                                        models: List[Any], prediction_function: Optional[Callable],
                                        **kwargs) -> Dict[str, Any]:
        """Perform learning curve analysis."""
        results = {}

        # Define training set sizes
        n_samples = len(X)
        train_sizes = np.logspace(np.log10(10), np.log10(n_samples * 0.8), 10).astype(int)
        train_sizes = np.unique(train_sizes)

        # Use a fixed test set
        test_size = min(n_samples // 5, 100)
        test_indices = np.random.choice(n_samples, size=test_size, replace=False)
        X_test = X[test_indices]
        y_test = y[test_indices]

        # Remove test samples
        train_mask = np.ones(n_samples, dtype=bool)
        train_mask[test_indices] = False
        X_available = X[train_mask]
        y_available = y[train_mask]

        # Analyze each model
        for i, model in enumerate(models):
            model_name = getattr(model, '__name__', f'model_{i}')

            train_scores = []
            test_scores = []
            valid_train_sizes = []

            for train_size in train_sizes:
                if train_size > len(X_available):
                    continue

                # Multiple random subsets for each size
                size_train_scores = []
                size_test_scores = []

                for _ in range(5):  # 5 random subsets per size
                    # Random subset of training data
                    subset_indices = np.random.choice(len(X_available), size=train_size, replace=False)
                    X_train_subset = X_available[subset_indices]
                    y_train_subset = y_available[subset_indices]

                    try:
                        # Train score
                        y_train_pred = self._train_and_predict(model, X_train_subset, y_train_subset, X_train_subset)
                        train_score = self._compute_score(y_train_subset, y_train_pred)
                        size_train_scores.append(train_score)

                        # Test score
                        y_test_pred = self._train_and_predict(model, X_train_subset, y_train_subset, X_test)
                        test_score = self._compute_score(y_test, y_test_pred)
                        size_test_scores.append(test_score)

                    except Exception as e:
                        warnings.warn(f"Learning curve evaluation failed for {model_name} at size {train_size}: {e}")

                if size_train_scores and size_test_scores:
                    train_scores.append(np.mean(size_train_scores))
                    test_scores.append(np.mean(size_test_scores))
                    valid_train_sizes.append(train_size)

            results[model_name] = {
                'train_sizes': valid_train_sizes,
                'train_scores': train_scores,
                'test_scores': test_scores,
                'convergence_analysis': self._analyze_learning_curve_convergence(valid_train_sizes, test_scores)
            }

        return results

    def _validate_single_model(self, X: np.ndarray, y: np.ndarray, model: Any, cv_splitter, **kwargs) -> Dict[str, Any]:
        """Validate a single model using cross-validation."""
        scores = []
        predictions = []
        true_values = []

        for train_idx, test_idx in cv_splitter.split(X, y):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            try:
                score = self._evaluate_model_on_split(model, X_train, y_train, X_test, y_test, **kwargs)
                scores.append(score)

                # Store predictions for additional analysis
                y_pred = self._train_and_predict(model, X_train, y_train, X_test)
                predictions.extend(y_pred)
                true_values.extend(y_test)

            except Exception as e:
                warnings.warn(f"Model evaluation failed on fold: {e}")

        if not scores:
            return {'error': 'All folds failed'}

        return {
            'cv_scores': scores,
            'mean_cv_score': float(np.mean(scores)),
            'std_cv_score': float(np.std(scores)),
            'cv_score_confidence_interval': self._compute_confidence_interval(scores),
            'overall_metrics': self._compute_overall_metrics(true_values, predictions)
        }

    def _validate_prediction_function(self, X: np.ndarray, y: np.ndarray, prediction_function: Callable, cv_splitter, **kwargs) -> Dict[str, Any]:
        """Validate a prediction function using cross-validation."""
        scores = []

        for train_idx, test_idx in cv_splitter.split(X, y):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            try:
                score = self._evaluate_function_on_split(prediction_function, X_train, y_train, X_test, y_test, **kwargs)
                scores.append(score)
            except Exception as e:
                warnings.warn(f"Function evaluation failed on fold: {e}")

        if not scores:
            return {'error': 'All folds failed'}

        return {
            'cv_scores': scores,
            'mean_cv_score': float(np.mean(scores)),
            'std_cv_score': float(np.std(scores)),
            'cv_score_confidence_interval': self._compute_confidence_interval(scores)
        }

    def _evaluate_model_on_split(self, model: Any, X_train: np.ndarray, y_train: np.ndarray,
                                X_test: np.ndarray, y_test: np.ndarray, **kwargs) -> float:
        """Evaluate model on a single train-test split."""
        # Train and predict
        y_pred = self._train_and_predict(model, X_train, y_train, X_test)

        # Compute score
        return self._compute_score(y_test, y_pred, **kwargs)

    def _evaluate_function_on_split(self, prediction_function: Callable, X_train: np.ndarray, y_train: np.ndarray,
                                   X_test: np.ndarray, y_test: np.ndarray, **kwargs) -> float:
        """Evaluate prediction function on a single train-test split."""
        # Use function to make predictions
        y_pred = prediction_function(X_train, y_train, X_test)

        # Compute score
        return self._compute_score(y_test, y_pred, **kwargs)

    def _train_and_predict(self, model: Any, X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray) -> np.ndarray:
        """Train model and make predictions."""
        # This is a simplified interface - in practice would depend on model type
        if hasattr(model, 'fit') and hasattr(model, 'predict'):
            # Sklearn-like interface
            model.fit(X_train, y_train)
            return model.predict(X_test)
        elif callable(model):
            # Function interface
            return model(X_train, y_train, X_test)
        else:
            # Default: simple linear regression
            if X_train.shape[1] == 1:
                # Simple linear regression
                X_train_with_intercept = np.column_stack([np.ones(len(X_train)), X_train])
                X_test_with_intercept = np.column_stack([np.ones(len(X_test)), X_test])
                coeffs = np.linalg.lstsq(X_train_with_intercept, y_train, rcond=None)[0]
                return X_test_with_intercept @ coeffs
            else:
                # Multiple linear regression
                X_train_with_intercept = np.column_stack([np.ones(len(X_train)), X_train])
                X_test_with_intercept = np.column_stack([np.ones(len(X_test)), X_test])
                coeffs = np.linalg.lstsq(X_train_with_intercept, y_train, rcond=None)[0]
                return X_test_with_intercept @ coeffs

    def _compute_score(self, y_true: np.ndarray, y_pred: np.ndarray, **kwargs) -> float:
        """Compute score for predictions."""
        scoring_function = kwargs.get('scoring_function')

        if scoring_function is not None:
            return scoring_function(y_true, y_pred)
        else:
            # Default: negative MSE (so higher is better)
            return -mean_squared_error(y_true, y_pred)

    def _compute_overall_metrics(self, y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
        """Compute overall metrics across all folds."""
        y_true = np.array(y_true)
        y_pred = np.array(y_pred)

        metrics = {
            'mse': float(mean_squared_error(y_true, y_pred)),
            'mae': float(mean_absolute_error(y_true, y_pred)),
            'rmse': float(np.sqrt(mean_squared_error(y_true, y_pred)))
        }

        # R-squared
        ss_res = np.sum((y_true - y_pred)**2)
        ss_tot = np.sum((y_true - np.mean(y_true))**2)
        metrics['r2'] = float(1 - (ss_res / ss_tot)) if ss_tot > 0 else 0.0

        return metrics

    def _compute_confidence_interval(self, scores: List[float]) -> Dict[str, float]:
        """Compute confidence interval for scores."""
        if len(scores) < 2:
            return {'error': 'Insufficient scores for confidence interval'}

        scores_array = np.array(scores)
        mean_score = np.mean(scores_array)
        std_score = np.std(scores_array, ddof=1)
        n = len(scores)

        # t-distribution confidence interval
        alpha = 1 - self.config.confidence_level
        t_value = stats.t.ppf(1 - alpha/2, n - 1)
        margin_error = t_value * std_score / np.sqrt(n)

        return {
            'lower': float(mean_score - margin_error),
            'upper': float(mean_score + margin_error),
            'confidence_level': self.config.confidence_level
        }

    def _analyze_learning_curve_convergence(self, train_sizes: List[int], test_scores: List[float]) -> Dict[str, Any]:
        """Analyze convergence of learning curves."""
        if len(test_scores) < 3:
            return {'error': 'Insufficient data for convergence analysis'}

        # Check if performance is still improving
        recent_improvement = test_scores[-1] - test_scores[-2] if len(test_scores) >= 2 else 0
        overall_improvement = test_scores[-1] - test_scores[0]

        # Estimate saturation
        saturated = abs(recent_improvement) < 0.01 * abs(overall_improvement) if overall_improvement != 0 else True

        return {
            'recent_improvement': float(recent_improvement),
            'overall_improvement': float(overall_improvement),
            'saturated': bool(saturated),
            'recommended_training_size': int(train_sizes[-1]) if not saturated else int(train_sizes[-2])
        }

    def _generate_validation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall validation summary."""
        summary = {
            'validation_successful': True,
            'best_method': None,
            'recommendations': [],
            'key_findings': []
        }

        # Find best performing method
        best_score = -np.inf
        best_method = None

        for method_name, method_results in results.items():
            if isinstance(method_results, dict) and 'mean_cv_score' in method_results:
                score = method_results['mean_cv_score']
                if score > best_score:
                    best_score = score
                    best_method = method_name

        summary['best_method'] = best_method

        # Generate recommendations based on results
        if 'bias_variance_analysis' in results:
            for method_name, bv_results in results['bias_variance_analysis'].items():
                if isinstance(bv_results, dict):
                    bias_var_ratio = bv_results.get('bias_variance_ratio', 1.0)
                    if bias_var_ratio > 2.0:
                        summary['recommendations'].append(f'{method_name}: High bias - consider more complex model')
                    elif bias_var_ratio < 0.5:
                        summary['recommendations'].append(f'{method_name}: High variance - consider regularization')

        if 'learning_curve_analysis' in results:
            for method_name, lc_results in results['learning_curve_analysis'].items():
                if isinstance(lc_results, dict) and 'convergence_analysis' in lc_results:
                    conv_analysis = lc_results['convergence_analysis']
                    if not conv_analysis.get('saturated', True):
                        summary['recommendations'].append(f'{method_name}: Performance still improving - consider more training data')

        return summary


def create_cross_validator(config: Optional[Dict[str, Any]] = None) -> CrossValidator:
    """Factory function to create cross-validator.

    Parameters
    ----------
    config : Dict[str, Any], optional
        Configuration parameters

    Returns
    -------
    CrossValidator
        Configured cross-validator
    """
    if config is not None:
        cv_config = CrossValidationConfig(**config)
    else:
        cv_config = CrossValidationConfig()

    return CrossValidator(cv_config)