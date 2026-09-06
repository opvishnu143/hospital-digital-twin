import random

import pandas as pd
import simpy


SEVERITY_RANGES = {
    "Critical": {
        "triage": (4, 7),
        "consultation": (8, 12),
        "treatment": (12, 20),
    },
    "Serious": {
        "triage": (5, 9),
        "consultation": (6, 10),
        "treatment": (8, 15),
    },
    "Normal": {
        "triage": (6, 10),
        "consultation": (4, 8),
        "treatment": (5, 10),
    },
}

TEST_DURATIONS = {
    "CT": (8, 15),
    "X-Ray": (5, 10),
    "Laboratory": (5, 10),
}

DAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def _sample_duration(duration_range, rng):
    return rng.uniform(*duration_range)


def _utilization(busy_time, capacity, simulation_time):
    if capacity <= 0 or simulation_time <= 0:
        return 0.0

    return min(
        100.0,
        max(
            0.0,
            busy_time / (capacity * simulation_time) * 100,
        ),
    )


def _scheduled_capacity_minutes(schedule, simulation_time, week_start_day):
    if simulation_time <= 0:
        return 0.0

    capacity_minutes = 0.0
    cursor = 0.0
    start_index = DAY_NAMES.index(week_start_day)

    while cursor < simulation_time:
        day_index = (
            start_index + int(cursor // (24 * 60))
        ) % 7
        shift = "weekend" if day_index >= 5 else "weekday"
        remaining_day = (24 * 60) - (cursor % (24 * 60))
        interval = min(remaining_day, simulation_time - cursor)
        capacity_minutes += schedule[shift] * interval
        cursor += interval

    return capacity_minutes


def _severity_and_priority():
    probability = random.random()

    if probability < 0.15:
        return "Critical", 0
    if probability < 0.45:
        return "Serious", 1
    return "Normal", 2


def _patient(
    env,
    patient_id,
    arrival_time,
    severity,
    priority,
    beds,
    nurses,
    doctor_resources,
    week_start_day,
    treatment_rooms,
    diagnostics,
    capacities,
    results,
    busy_time,
    arrival_times,
    bed_events,
    rng,
):
    yield env.timeout(arrival_time)

    arrival_times.append(env.now)

    record = {
        "patient_id": patient_id,
        "arrival_time": round(env.now, 1),
        "severity": severity,
        "priority": priority,
        "bed_wait": 0.0,
        "nurse_wait": 0.0,
        "doctor_wait": 0.0,
        "test_wait": 0.0,
        "ct_wait": 0.0,
        "xray_wait": 0.0,
        "laboratory_wait": 0.0,
        "treatment_wait": 0.0,
        "treatment_time": 0.0,
        "test_type": "No Test",
        "test": "No Test",
        "total_time": 0.0,
        "discharge_time": 0.0,
    }

    bed_request_time = env.now
    with beds.request(priority=priority) as bed_request:
        yield bed_request
        record["bed_wait"] = env.now - bed_request_time
        bed_start_time = env.now
        bed_events.append((env.now, 1))

        nurse_request_time = env.now
        with nurses.request(priority=priority) as nurse_request:
            yield nurse_request
            record["nurse_wait"] = env.now - nurse_request_time
            triage_start_time = env.now
            yield env.timeout(
                _sample_duration(SEVERITY_RANGES[severity]["triage"], rng)
            )
            busy_time["nurse"] += env.now - triage_start_time

        day_index = (
            DAY_NAMES.index(week_start_day)
            + int(env.now // (24 * 60))
        ) % 7
        doctor_shift = (
            "weekend" if day_index >= 5 else "weekday"
        )
        doctors = doctor_resources[doctor_shift]
        doctor_request_time = env.now
        with doctors.request(priority=priority) as doctor_request:
            yield doctor_request
            record["doctor_wait"] = env.now - doctor_request_time
            doctor_start_time = env.now
            yield env.timeout(
                _sample_duration(
                    SEVERITY_RANGES[severity]["consultation"],
                    rng,
                )
            )
            busy_time["doctor"] += env.now - doctor_start_time

        available_tests = [
            test_type
            for test_type in ("CT", "X-Ray", "Laboratory")
            if capacities[test_type] > 0
        ]

        if available_tests and rng.random() < 0.625:
            test_type = rng.choice(available_tests)
            test_resource = diagnostics[test_type]
            test_request_time = env.now

            with test_resource.request(priority=priority) as test_request:
                yield test_request
                record["test_wait"] = env.now - test_request_time
                test_start_time = env.now
                yield env.timeout(
                    _sample_duration(TEST_DURATIONS[test_type], rng)
                )
                busy_time[test_type] += env.now - test_start_time

            if test_type == "CT":
                record["ct_wait"] = record["test_wait"]
            elif test_type == "X-Ray":
                record["xray_wait"] = record["test_wait"]
            else:
                record["laboratory_wait"] = record["test_wait"]

            record["test_type"] = test_type
            record["test"] = test_type

        treatment_request_time = env.now
        with (
            treatment_rooms.request(priority=priority) as room_request,
            nurses.request(priority=priority) as treatment_nurse_request,
        ):
            yield room_request & treatment_nurse_request
            record["treatment_wait"] = env.now - treatment_request_time
            treatment_start_time = env.now
            yield env.timeout(
                _sample_duration(SEVERITY_RANGES[severity]["treatment"], rng)
            )
            treatment_busy_time = env.now - treatment_start_time
            busy_time["treatment_room"] += treatment_busy_time
            busy_time["nurse"] += treatment_busy_time
            record["treatment_time"] = treatment_busy_time

        busy_time["bed"] += env.now - bed_start_time
        bed_events.append((env.now, -1))
        record["discharge_time"] = round(env.now, 1)
        record["total_time"] = round(env.now - arrival_time, 1)

    results.append(record)


def run_simulation(
    num_patients=50,
    num_beds=5,
    num_doctors=2,
    num_nurses=2,
    num_treatment_rooms=2,
    num_ct=1,
    num_xray=1,
    num_lab=2,
    arrival_surge=0,
    seed=42,
    weekend_doctors=None,
    week_start_day="Monday",
):
    """Run the emergency department simulation."""
    capacities = {
        "Beds": max(0, int(num_beds)),
        "Doctors": max(0, int(num_doctors)),
        "Nurses": max(0, int(num_nurses)),
        "Treatment Rooms": max(0, int(num_treatment_rooms)),
        "CT": max(0, int(num_ct)),
        "X-Ray": max(0, int(num_xray)),
        "Laboratory": max(0, int(num_lab)),
    }

    if week_start_day not in DAY_NAMES:
        raise ValueError(
            f"week_start_day must be one of {DAY_NAMES}."
        )

    if weekend_doctors is None:
        weekend_doctors = max(1, capacities["Doctors"] - 1)
    weekend_doctors = max(1, int(weekend_doctors))
    doctor_shift_schedule = {
        "weekday": capacities["Doctors"],
        "weekend": weekend_doctors,
    }

    required_capacities = (
        "Beds",
        "Doctors",
        "Nurses",
        "Treatment Rooms",
    )
    if any(capacities[name] == 0 for name in required_capacities):
        raise ValueError(
            "Beds, doctors, nurses, and treatment rooms must have capacity above zero."
        )

    random.seed(seed)
    env = simpy.Environment()

    beds = simpy.PriorityResource(env, capacity=capacities["Beds"])
    nurses = simpy.PriorityResource(env, capacity=capacities["Nurses"])
    doctor_resources = {
        shift: simpy.PriorityResource(env, capacity=capacity)
        for shift, capacity in doctor_shift_schedule.items()
    }
    treatment_rooms = simpy.PriorityResource(
        env,
        capacity=capacities["Treatment Rooms"],
    )
    ct_scanners = simpy.PriorityResource(
        env,
        capacity=max(1, capacities["CT"]),
    )
    xray = simpy.PriorityResource(
        env,
        capacity=max(1, capacities["X-Ray"]),
    )
    lab = simpy.PriorityResource(
        env,
        capacity=max(1, capacities["Laboratory"]),
    )

    diagnostics = {
        "CT": ct_scanners,
        "X-Ray": xray,
        "Laboratory": lab,
    }
    busy_time = {
        "bed": 0.0,
        "nurse": 0.0,
        "doctor": 0.0,
        "CT": 0.0,
        "X-Ray": 0.0,
        "Laboratory": 0.0,
        "treatment_room": 0.0,
    }
    results = []
    arrival_times = []
    bed_events = []

    surge_multiplier = 1 + arrival_surge / 100
    if surge_multiplier <= 0:
        raise ValueError("arrival_surge must be greater than -100 percent.")

    arrival_interval = 5 / surge_multiplier
    current_arrival = 0.0

    for patient_id in range(1, int(num_patients) + 1):
        current_arrival += random.expovariate(1 / arrival_interval)
        severity, priority = _severity_and_priority()
        patient_rng = random.Random(random.randrange(2**32))
        env.process(
            _patient(
                env,
                patient_id,
                current_arrival,
                severity,
                priority,
                beds,
                nurses,
                doctor_resources,
                week_start_day,
                treatment_rooms,
                diagnostics,
                capacities,
                results,
                busy_time,
                arrival_times,
                bed_events,
                patient_rng,
            )
        )

    env.run()
    simulation_time = env.now
    state_time = max(arrival_times, default=0.0)
    patient_inflow = len(arrival_times)
    patient_outflow = sum(
        record["discharge_time"] <= state_time
        for record in results
    )
    current_patients = patient_inflow - patient_outflow
    occupied_beds = 0

    for event_time, change in sorted(bed_events):
        if event_time > state_time:
            break
        occupied_beds += change

    utilization = {
        "Bed Utilization": _utilization(
            busy_time["bed"], capacities["Beds"], simulation_time
        ),
        "Doctor Utilization": _utilization(
            busy_time["doctor"],
            _scheduled_capacity_minutes(
                doctor_shift_schedule,
                simulation_time,
                week_start_day,
            ),
            1,
        ),
        "CT Utilization": _utilization(
            busy_time["CT"], capacities["CT"], simulation_time
        ),
        "Laboratory Utilization": _utilization(
            busy_time["Laboratory"], capacities["Laboratory"], simulation_time
        ),
        "Nurse Utilization": _utilization(
            busy_time["nurse"], capacities["Nurses"], simulation_time
        ),
        "X-Ray Utilization": _utilization(
            busy_time["X-Ray"], capacities["X-Ray"], simulation_time
        ),
        "Treatment Room Utilization": _utilization(
            busy_time["treatment_room"],
            capacities["Treatment Rooms"],
            simulation_time,
        ),
        "resource_capacities": capacities,
        "Doctor Shift Schedule": doctor_shift_schedule,
        "Week Start Day": week_start_day,
        "Patient Inflow": patient_inflow,
        "Patient Outflow": patient_outflow,
        "Current Patients": current_patients,
        "Net Flow": current_patients,
        "Occupied Beds": occupied_beds,
        "Simulation Time": simulation_time,
        "State Time": state_time,
        "Throughput": (
            patient_outflow / state_time * 60
            if state_time > 0 else 0.0
        ),
    }

    result_columns = [
        "patient_id",
        "arrival_time",
        "severity",
        "priority",
        "bed_wait",
        "nurse_wait",
        "doctor_wait",
        "test_wait",
        "ct_wait",
        "xray_wait",
        "laboratory_wait",
        "treatment_wait",
        "treatment_time",
        "test_type",
        "test",
        "total_time",
        "discharge_time",
    ]
    results_df = pd.DataFrame(results, columns=result_columns)

    for column in (
        "bed_wait",
        "nurse_wait",
        "doctor_wait",
        "test_wait",
        "ct_wait",
        "xray_wait",
        "laboratory_wait",
        "treatment_wait",
        "treatment_time",
    ):
        results_df[column] = results_df[column].round(1)

    for key in (
        "Bed Utilization",
        "Doctor Utilization",
        "CT Utilization",
        "Laboratory Utilization",
        "Nurse Utilization",
        "X-Ray Utilization",
        "Treatment Room Utilization",
    ):
        utilization[key] = round(utilization[key], 1)

    def mean_wait(records_for_resource, field):
        if not records_for_resource:
            return 0.0
        return sum(record[field] for record in records_for_resource) / len(
            records_for_resource
        )

    wait_records = {
        "Beds": (results, "bed_wait"),
        "Doctors": (results, "doctor_wait"),
        "Nurses": (results, "nurse_wait"),
        "Treatment Rooms": (results, "treatment_wait"),
        "CT": ([record for record in results if record["test_type"] == "CT"], "ct_wait"),
        "X-Ray": ([record for record in results if record["test_type"] == "X-Ray"], "xray_wait"),
        "Laboratory": ([record for record in results if record["test_type"] == "Laboratory"], "laboratory_wait"),
    }
    resource_waits = {
        resource: mean_wait(records_for_resource, field)
        for resource, (records_for_resource, field) in wait_records.items()
    }

    resource_utilization = {
        "Beds": utilization["Bed Utilization"],
        "Doctors": utilization["Doctor Utilization"],
        "Nurses": utilization["Nurse Utilization"],
        "Treatment Rooms": utilization["Treatment Room Utilization"],
        "CT": utilization["CT Utilization"],
        "X-Ray": utilization["X-Ray Utilization"],
        "Laboratory": utilization["Laboratory Utilization"],
    }
    bottleneck_scores = {}
    for resource, utilization_value in resource_utilization.items():
        wait_value = min(100.0, resource_waits[resource] / 10 * 100)
        activity_score = utilization_value * 0.6 + wait_value * 0.4
        has_demand = resource not in {"CT", "X-Ray", "Laboratory"} or any(
            record["test_type"] == resource for record in results
        )
        if has_demand:
            bottleneck_scores[resource] = activity_score

    utilization["Bottleneck"] = max(
        bottleneck_scores,
        key=bottleneck_scores.get,
    )
    utilization["Resource Waits"] = resource_waits
    utilization["Bottleneck Scores"] = bottleneck_scores
    utilization["Queue Accumulation"] = current_patients
    utilization["Average Total Time"] = round(
        sum(record["total_time"] for record in results)
        / len(results) if results else 0.0,
        1,
    )

    return results_df, utilization
