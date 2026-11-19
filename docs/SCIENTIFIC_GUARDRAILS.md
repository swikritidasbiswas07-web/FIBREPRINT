# Scientific guardrails

1. **No model has been trained.** The initial interface is a research workbench and data-readiness prototype.
2. **No numerical predictions appear.** Any example fabric or wash values are user inputs, not empirical observations or model results.
3. **Published findings are study-specific.** Never infer from Kelly et al. (2019) that delicate washing universally increases or decreases emissions.
4. **Record protocols.** Before combining studies, record fibre collection thresholds, washing device, batch size, detection method, normalisation units, replication, and fabric characteristics.
5. **Distinguish microfibres from microplastics.** Cotton and other natural materials may shed fibres, but these are not necessarily microplastics.
6. **Prevent data leakage.** Validation should split at the study and fabric/specimen level when data permit, not only random rows.
7. **Do not promise accuracy without testing.** Report MAE/RMSE and uncertainty interval coverage only after independent validation.
8. **Scenario comparisons must respect evidence coverage.** Avoid extrapolating to unknown blends, wash cycles and material treatments without warnings.
9. **CSV validation checks structure only.** Passing the column checker does not certify units, source provenance, chemistry, or compatibility.
10. **Claims about environmental benefit require evaluation.** Predicted lower shedding is not proof of avoided pollution.
