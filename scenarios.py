from simulation import run_replications


# ============================================================
# RUN ONE SCENARIO
# ============================================================

def run_scenario(
    hospital,
    reference,
    num_patients,
    duration_minutes,
    arrival_surge_pct,
    replications,
    seed,
):

    return run_replications(

        hospital=hospital,

        reference=reference,

        num_patients=num_patients,

        duration_minutes=duration_minutes,

        arrival_surge_pct=arrival_surge_pct,

        replications=replications,

        base_seed=seed,
    )


# ============================================================
# BASELINE VS SCENARIO
# ============================================================

def compare_scenarios(
    baseline_hospital,
    scenario_hospital,
    reference,
    num_patients,
    duration_minutes,
    scenario_arrival_surge_pct,
    replications,
):

    # --------------------------------------------------------
    # BASELINE
    # --------------------------------------------------------

    baseline = run_scenario(

        hospital=baseline_hospital,

        reference=reference,

        num_patients=num_patients,

        duration_minutes=duration_minutes,

        arrival_surge_pct=0,

        replications=replications,

        seed=42,
    )

    # --------------------------------------------------------
    # SCENARIO
    # --------------------------------------------------------

    scenario = run_scenario(

        hospital=scenario_hospital,

        reference=reference,

        num_patients=num_patients,

        duration_minutes=duration_minutes,

        arrival_surge_pct=scenario_arrival_surge_pct,

        replications=replications,

        seed=1042,
    )

    # --------------------------------------------------------
    # COMPARISON
    # --------------------------------------------------------

    metrics = [

        (
            "Average total waiting",
            "avg_total_wait"
        ),

        (
            "Average ED LOS",
            "avg_ed_los"
        ),

        (
            "Bed occupancy",
            "bed_occupancy_pct"
        ),

        (
            "Doctor utilization",
            "doctor_utilization_pct"
        ),

        (
            "Nurse utilization",
            "nurse_utilization_pct"
        ),

        (
            "Test utilization",
            "test_utilization_pct"
        ),

        (
            "Treatment utilization",
            "treatment_utilization_pct"
        ),

        (
            "Patients out",
            "departures"
        ),

        (
            "Patients inside at end",
            "patients_inside_end"
        ),
    ]

    rows = []

    for label, key in metrics:

        baseline_value = (
            baseline[key]["mean"]
        )

        scenario_value = (
            scenario[key]["mean"]
        )

        if baseline_value != 0:

            change_pct = (
                (
                    scenario_value
                    -
                    baseline_value
                )
                /
                baseline_value
                *
                100
            )

        else:

            change_pct = 0.0

        rows.append({

            "Metric":
                label,

            "Baseline":
                baseline_value,

            "Scenario":
                scenario_value,

            "% Change":
                change_pct,
        })

    # --------------------------------------------------------
    # BOTTLENECK
    # --------------------------------------------------------

    scenario_pressure = {

        "Beds":
            scenario[
                "bed_occupancy_pct"
            ]["mean"],

        "Nurses":
            scenario[
                "nurse_utilization_pct"
            ]["mean"],

        "Doctors":
            scenario[
                "doctor_utilization_pct"
            ]["mean"],

        "Tests":
            scenario[
                "test_utilization_pct"
            ]["mean"],

        "Treatment rooms":
            scenario[
                "treatment_utilization_pct"
            ]["mean"],
    }

    bottleneck = max(
        scenario_pressure,
        key=scenario_pressure.get
    )

    # --------------------------------------------------------
    # WAITING IMPROVEMENT
    # --------------------------------------------------------

    baseline_wait = (
        baseline[
            "avg_total_wait"
        ]["mean"]
    )

    scenario_wait = (
        scenario[
            "avg_total_wait"
        ]["mean"]
    )

    if baseline_wait > 0:

        wait_reduction_pct = (
            (
                baseline_wait
                -
                scenario_wait
            )
            /
            baseline_wait
            *
            100
        )

    else:

        wait_reduction_pct = 0.0

    return {

        "baseline":
            baseline,

        "scenario":
            scenario,

        "comparison":
            rows,

        "bottleneck":
            bottleneck,

        "bottleneck_pressure":
            scenario_pressure[
                bottleneck
            ],

        "wait_reduction_pct":
            wait_reduction_pct,
    }