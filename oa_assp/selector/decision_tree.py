"""Interpretable Decision Tree algorithm selector with near-tie evaluation."""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
from sklearn.tree import DecisionTreeClassifier, export_text
import time
from typing import Any, Dict, List, Optional, Tuple

from oa_assp.benchmark.oracle import OracleInstance
from oa_assp.selector.dataset import DatasetSplit
from oa_assp.benchmark.timing import time_callable


def _solver_cost_for_prediction(pred_algo: str, oracle: OracleInstance) -> float:
    """Cost of executing the predicted algorithm on this instance.

    A* falls back to Dijkstra when A* was not oracle-eligible for the instance
    (no admissible heuristic), which mirrors what a real dispatcher would do.
    """
    if pred_algo == "Dijkstra":
        return oracle.dijkstra_cost
    if pred_algo == "Bidirectional Dijkstra":
        return oracle.bidirectional_cost
    if pred_algo == "A*":
        return oracle.astar_cost if oracle.valid_astar else oracle.dijkstra_cost
    return oracle.dijkstra_cost


@dataclass
class QuerySelectionResult:
    """Individual selection and evaluation result for a query."""

    graph_id: str
    query_id: str
    selected_algorithm: str
    predicted_class: str
    actual_vbs_algorithm: str
    exact_correct: bool
    near_best: bool
    selection_time: float
    feature_time: float
    selected_solver_runtime: float
    vbs_runtime: float
    graph_feature_time: float = 0.0
    query_feature_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "query_id": self.query_id,
            "selected_algorithm": self.selected_algorithm,
            "predicted_class": self.predicted_class,
            "actual_vbs_algorithm": self.actual_vbs_algorithm,
            "exact_correct": self.exact_correct,
            "near_best": self.near_best,
            "selection_time": self.selection_time,
            "feature_time": self.feature_time,
            "graph_feature_time": self.graph_feature_time,
            "query_feature_time": self.query_feature_time,
            "selected_solver_runtime": self.selected_solver_runtime,
            "vbs_runtime": self.vbs_runtime,
        }


@dataclass
class SelectorEvaluationResult:
    """Aggregate evaluation summary for a selector on a test split."""

    exact_accuracy: float
    near_best_accuracy: float
    epsilon: float
    num_queries: int
    class_distribution: Dict[str, int]
    predicted_distribution: Dict[str, int]
    feature_importances: Dict[str, float]
    tree_text: str
    mean_selection_time: float
    mean_feature_time: float
    total_selected_solver_runtime: float = 0.0
    query_results: List[QuerySelectionResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "exact_accuracy": self.exact_accuracy,
            "near_best_accuracy": self.near_best_accuracy,
            "epsilon": self.epsilon,
            "num_queries": self.num_queries,
            "class_distribution": self.class_distribution,
            "predicted_distribution": self.predicted_distribution,
            "feature_importances": self.feature_importances,
            "tree_text": self.tree_text,
            "mean_selection_time": self.mean_selection_time,
            "mean_feature_time": self.mean_feature_time,
            "total_selected_solver_runtime": self.total_selected_solver_runtime,
        }


class DecisionTreeSelector:
    """Interpretable Decision Tree algorithm selector."""

    def __init__(
        self,
        max_depth: int = 4,
        min_samples_leaf: int = 5,
        random_state: int = 42,
        class_weight: Optional[str] = None,
        criterion: str = "gini",
    ) -> None:
        self.max_depth = max_depth
        self.min_samples_leaf = min_samples_leaf
        self.random_state = random_state
        self.class_weight = class_weight
        self.criterion = criterion
        self.model = DecisionTreeClassifier(
            max_depth=max_depth,
            min_samples_leaf=min_samples_leaf,
            random_state=random_state,
            class_weight=class_weight,
            criterion=criterion,
        )
        self.feature_names: List[str] = []
        self.classes: List[str] = []
        self.is_fitted: bool = False

    # ------------------------------------------------------------------ fitting
    def fit(self, train_split: DatasetSplit) -> DecisionTreeSelector:
        """Fit the decision tree on the training dataset split."""
        if len(train_split.X) == 0:
            raise ValueError("Training split is empty.")

        self.feature_names = list(train_split.feature_names)
        self.model.fit(train_split.X, train_split.y)
        self.classes = [str(c) for c in self.model.classes_]
        self.is_fitted = True
        return self

    def fit_arrays(self, X: np.ndarray, y: List[str], feature_names: List[str]) -> DecisionTreeSelector:
        """Fit directly from arrays (used by the generalization experiments)."""
        if len(X) == 0:
            raise ValueError("Training matrix is empty.")
        self.feature_names = list(feature_names)
        self.model.fit(X, list(y))
        self.classes = [str(c) for c in self.model.classes_]
        self.is_fitted = True
        return self

    # -------------------------------------------------------------- prediction
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, float]:
        """Predict the best algorithm with batch selection wall-clock timing."""
        if not self.is_fitted:
            raise RuntimeError("Selector model is not fitted.")
        t0 = time.perf_counter()
        predictions = self.model.predict(X)
        elapsed = time.perf_counter() - t0
        return predictions, elapsed

    def predict_one(self, x: np.ndarray) -> Tuple[str, float]:
        """Predict for a single instance, as an online dispatcher would."""
        if not self.is_fitted:
            raise RuntimeError("Selector model is not fitted.")
        row = np.asarray(x, dtype=float).reshape(1, -1)
        t0 = time.perf_counter()
        pred = self.model.predict(row)
        elapsed = time.perf_counter() - t0
        return str(pred[0]), elapsed

    def measure_single_row_latency(self, x: np.ndarray, repetitions: int = 20, warmup_runs: int = 2) -> Dict[str, Any]:
        """Measure the single-row inference latency with the project timing protocol."""
        return time_callable(lambda: self.predict_one(x), repetitions=repetitions, warmup_runs=warmup_runs, batch=1)

    # ------------------------------------------------ compiled (rule) inference
    def compile_rules(self) -> Any:
        """Compile the fitted tree into plain nested conditionals.

        An interpretable tree can be deployed as a handful of comparisons rather than
        through a general-purpose model-inference call. This is the deployment form
        that the interpretability argument actually buys, so it is measured separately
        from library inference and the difference is reported.
        """
        if not self.is_fitted:
            raise RuntimeError("Selector model is not fitted.")
        tree = self.model.tree_
        feature = tree.feature
        threshold = tree.threshold
        left = tree.children_left
        right = tree.children_right
        value = tree.value
        classes = self.classes

        def build(node: int) -> Any:
            if left[node] == right[node]:
                idx = int(np.argmax(value[node]))
                label = str(classes[idx]) if idx < len(classes) else "Unknown"
                return lambda x: label
            f = int(feature[node])
            thr = float(threshold[node])
            lc = build(int(left[node]))
            rc = build(int(right[node]))

            def decide(x, f=f, thr=thr, lc=lc, rc=rc):
                return lc(x) if x[f] <= thr else rc(x)

            return decide

        return build(0)

    def predict_compiled(self, x: np.ndarray) -> Tuple[str, float]:
        """Predict one instance by walking the compiled rules, with timing."""
        if not hasattr(self, "_compiled"):
            self._compiled = self.compile_rules()
        t0 = time.perf_counter()
        label = self._compiled(x)
        return str(label), time.perf_counter() - t0

    def measure_compiled_latency(self, x: np.ndarray, repetitions: int = 20, warmup_runs: int = 2) -> Dict[str, Any]:
        """Measure compiled-rule inference latency with the project timing protocol."""
        if not hasattr(self, "_compiled"):
            self._compiled = self.compile_rules()
        return time_callable(
            lambda: self._compiled(x), repetitions=repetitions, warmup_runs=warmup_runs, batch=1
        )

    # ------------------------------------------------------------ evaluation
    def evaluate(
        self,
        test_split: DatasetSplit,
        epsilon: float = 0.05,
        selection_latency: Optional[float] = None,
    ) -> SelectorEvaluationResult:
        """Evaluate the selector on unseen test graphs with near-tie analysis.

        ``selection_latency`` overrides the per-query selection charge. When
        ``None`` the historical batch-amortized value is used; the corrected
        pipeline passes a measured single-row latency instead so that Q=1 is not
        charged a batch-amortized cost.
        """
        if not self.is_fitted:
            raise RuntimeError("Selector model is not fitted.")
        if len(test_split.X) == 0:
            raise ValueError("Test split is empty.")

        n_samples = len(test_split.X)
        preds, total_pred_time = self.predict(test_split.X)
        mean_sel_time = selection_latency if selection_latency is not None else total_pred_time / max(1, n_samples)

        exact_correct_count = 0
        near_best_count = 0
        query_results: List[QuerySelectionResult] = []
        class_dist: Dict[str, int] = {}
        pred_dist: Dict[str, int] = {}
        total_solver = 0.0
        feature_times: List[float] = []

        for true_label in test_split.y:
            lbl = str(true_label)
            class_dist[lbl] = class_dist.get(lbl, 0) + 1
        for pred_label in preds:
            lbl = str(pred_label)
            pred_dist[lbl] = pred_dist.get(lbl, 0) + 1

        for i in range(n_samples):
            pred_algo = str(preds[i])
            meta = test_split.metadata[i]
            oracle: OracleInstance = meta["oracle_instance"]
            g_feat_time = float(meta.get("graph_feature_time", 0.0))
            q_feat_time = float(meta.get("query_feature_time", 0.0))
            feature_times.append(q_feat_time)

            pred_runtime = _solver_cost_for_prediction(pred_algo, oracle)
            vbs_runtime = oracle.vbs_cost
            is_exact = pred_algo == oracle.vbs_algorithm
            if is_exact:
                exact_correct_count += 1

            is_near_best = pred_runtime <= (1.0 + epsilon) * vbs_runtime + 1e-12
            if is_near_best:
                near_best_count += 1

            total_solver += pred_runtime
            query_results.append(
                QuerySelectionResult(
                    graph_id=meta["graph_id"],
                    query_id=meta["query_id"],
                    selected_algorithm=pred_algo,
                    predicted_class=pred_algo,
                    actual_vbs_algorithm=oracle.vbs_algorithm,
                    exact_correct=is_exact,
                    near_best=is_near_best,
                    selection_time=mean_sel_time,
                    feature_time=q_feat_time,
                    graph_feature_time=g_feat_time,
                    query_feature_time=q_feat_time,
                    selected_solver_runtime=pred_runtime,
                    vbs_runtime=vbs_runtime,
                )
            )

        importances = {
            fname: float(imp) for fname, imp in zip(self.feature_names, self.model.feature_importances_)
        }
        tree_str = export_text(self.model, feature_names=self.feature_names)

        return SelectorEvaluationResult(
            exact_accuracy=float(exact_correct_count / n_samples),
            near_best_accuracy=float(near_best_count / n_samples),
            epsilon=epsilon,
            num_queries=n_samples,
            class_distribution=class_dist,
            predicted_distribution=pred_dist,
            feature_importances=importances,
            tree_text=tree_str,
            mean_selection_time=mean_sel_time,
            mean_feature_time=float(np.mean(feature_times)) if feature_times else 0.0,
            total_selected_solver_runtime=total_solver,
            query_results=query_results,
        )

    def export_tree_nodes(self) -> List[Dict[str, Any]]:
        """Export node-by-node details of the fitted decision tree."""
        if not self.is_fitted:
            raise RuntimeError("Selector model is not fitted.")
        tree = self.model.tree_
        nodes = []
        for i in range(tree.node_count):
            is_leaf = bool(tree.children_left[i] == tree.children_right[i])
            feat_idx = int(tree.feature[i])
            feat_name = self.feature_names[feat_idx] if feat_idx >= 0 else None
            threshold = float(tree.threshold[i]) if feat_idx >= 0 else None
            n_samples = int(tree.n_node_samples[i])
            impurity = float(tree.impurity[i])
            class_idx = int(np.argmax(tree.value[i]))
            pred_class = str(self.classes[class_idx]) if class_idx < len(self.classes) else "Unknown"
            nodes.append({
                "node_id": int(i),
                "is_leaf": bool(is_leaf),
                "feature": feat_name,
                "threshold": threshold,
                "sample_count": n_samples,
                "predicted_class": pred_class,
                "impurity": impurity,
                "left_child": int(tree.children_left[i]),
                "right_child": int(tree.children_right[i]),
            })
        return nodes
