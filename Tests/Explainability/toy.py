import numpy as np
from sklearn.linear_model import LinearRegression
import shap

def get_shapley_values_linear_independent_variables(
    weights: np.ndarray, data: np.ndarray
) -> np.ndarray:
    return weights * data


def get_shap(weights: np.ndarray, data: np.ndarray):
    model = LinearRegression()
    model.coef_ = weights  # Inject your weights
    model.intercept_ = 0
    background = np.zeros((1, weights.shape[0]))
    explainer = shap.LinearExplainer(model, background) # Assume independent between all features
    results = explainer.shap_values(data) 
    return results

DIM_SPACE = 100

np.random.seed(42)
weights = np.random.rand(DIM_SPACE)
weights[0] = 10
weights[1] = 0
data = np.random.rand(1, DIM_SPACE)
data[0, 0:2] = 1

shap_res = get_shapley_values_linear_independent_variables(weights, data)
shap_res_pacakge = get_shap(weights, data)
idx_max = shap_res.argmax()
idx_min = shap_res.argmin()

print(f"Expected: idx_max 0, idx_min 1\nActual: idx_max {idx_max},  idx_min: {idx_min}")

print(abs(shap_res_pacakge - shap_res).max())
# All variables are randomly and independent.
# This is simple use case where the weights * value is the theoritical shapley values result for each prediction. The variables are independent
# so let's break the shapley values equation.
# The first variable magnitude to 10 (be most important by far in most cases).
