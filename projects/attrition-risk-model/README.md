# Attrition Risk Model

Logistic regression and random forest predicting employee attrition, evaluated on a held-out test set, with the main drivers and guidance on responsible use.

- **Data:** IBM HR Analytics Employee Attrition & Performance sample dataset (`data/`). The employees are fictional.
- **Python:** `python/attrition_model.py` (scikit-learn pipeline, stratified 75/25 split, 5-fold cross-validation, fixed random seed). Age, gender and marital status are excluded from the features.
- **Outputs:** `outputs/metrics.json` and four charts
- **Report:** https://olajumokemedunoye.github.io/projects/attrition-risk-model.html

| Model | Test ROC AUC | Precision | Recall |
|---|---|---|---|
| Logistic regression | 0.794 | 0.373 | 0.644 |
| Random forest | 0.758 | 0.456 | 0.525 |

Run: `python python/attrition_model.py` from this folder.
