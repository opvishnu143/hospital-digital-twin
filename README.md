# Hospital Emergency Ward Digital Twin

Fresh prototype for operational scenario analysis in an emergency department.

## Data provenance

`data/ed_data.csv` is a **synthetic TEST dataset** included only so the code can run immediately. It is not hospital data and must not be presented as MIMIC data.

The production/reference input should be a preprocessed MIMIC-IV-ED file with the required columns documented in `parameters.py`.

## Model boundary

The simulator models patients competing for beds, nurses, doctors, diagnostics (CT/X-ray/lab), and treatment rooms. Hospital resource capacities are configurable inputs.

Service durations and diagnostic probabilities are currently explicit **model assumptions** pending calibration from timestamped event data or an appropriate published source. They must not be described as directly measured MIMIC values.

## Metrics

The core outputs include patient inflow/outflow, patients currently inside, unfinished patients at simulation end, bed wait, patient waiting time for nurse/doctor/diagnostics/treatment, ED length of stay, and resource utilization.
