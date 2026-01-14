import numpy as np
from sklearn.linear_model import LinearRegression
import shap
import pandas as pd

def get_shapley_values_linear_independent_variables(
    weights: np.ndarray, data: np.ndarray
) -> np.ndarray:
    res = weights * data
    duplicated_indices = np.array(
        [0] + list(range(data.shape[1] - DUPLICATE_FACTOR, data.shape[1]))
    )
    # we will sum those contributions and split contribution among them
    full_contrib = np.sum(res[:, duplicated_indices], axis=1)
    duplicate_feature_factor = np.ones(data.shape[1])
    duplicate_feature_factor[duplicated_indices] = 1 / (DUPLICATE_FACTOR + 1)
    full_contrib = np.tile(full_contrib, (DUPLICATE_FACTOR+1, 1)).T
    res[:, duplicated_indices] = full_contrib
    res *= duplicate_feature_factor
    return res


def get_shap(weights: np.ndarray, data: np.ndarray):
    model = LinearRegression()
    model.coef_ = weights  # Inject your weights
    model.intercept_ = 0
    explainer = shap.LinearExplainer(model, data, feature_perturbation="correlation_dependent")    
    results = explainer.shap_values(data) #
    return results

DIM_SPACE = 100
DUPLICATE_FACTOR = 100

np.random.seed(42)
weights = np.random.rand(DIM_SPACE)
weights[0] = 10
weights[1] = 0
data = np.random.rand(int(1e5), DIM_SPACE)
data[0, 0:2] = 1

# Duplicate copy of feature 0, 100 times:
dup_data = np.tile(data[:, 0], (DUPLICATE_FACTOR, 1)).T
data = np.concatenate((data, dup_data), axis=1)
# We will put zero weight for all those added features:
weights = np.concatenate((weights, np.tile(0, (DUPLICATE_FACTOR))))


shap_res = get_shapley_values_linear_independent_variables(weights, data)
shap_res_pacakge = get_shap(weights, data)

shap_res = shap_res[0, :]
shap_res_pacakge = shap_res_pacakge[0, :]
df = pd.DataFrame({"theory": shap_res, "shap": shap_res_pacakge})

idx_max = shap_res.argmax()
idx_min = shap_res.argmin()

print(f"Expected: idx_max 0, idx_min 1\nActual: idx_max {idx_max},  idx_min: {idx_min}")

print(abs(shap_res_pacakge - shap_res).max())
