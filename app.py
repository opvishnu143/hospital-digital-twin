import secrets

import streamlit as st
import pandas as pd
import plotly.express as px

from simulation import run_simulation


st.set_page_config(
  page_title="Hospital Emergency Ward Digital Twin",
  page_icon="🏥",
  layout="wide",
)

if "simulation_done" not in st.session_state:
  st.session_state.simulation_done = False
if "results" not in st.session_state:
  st.session_state.results = None
if "utilization" not in st.session_state:
  st.session_state.utilization = None
if "custom_result" not in st.session_state:
  st.session_state.custom_result = None
if "simulation_seed" not in st.session_state:
  st.session_state.simulation_seed = secrets.randbelow(2**32)
if "seed_patient_count" not in st.session_state:
  st.session_state.seed_patient_count = None


def classify_load(value):
  if value >= 80:
    return "High Load"
  if value >= 50:
    return "Moderate Load"
  return "Low Load"


def calculate_pressure(
  maximum_utilization,
  current_patients,
  net_flow,
  surge,
  queue_accumulation,
):
  if (
    maximum_utilization >= 95
    or current_patients >= 15
    or net_flow >= 20
    or queue_accumulation >= 15
    or surge >= 70
  ):
    return "Critical Pressure"
  if (
    maximum_utilization >= 85
    or current_patients >= 8
    or net_flow >= 10
    or queue_accumulation >= 8
    or surge >= 40
  ):
    return "High Pressure"
  if (
    maximum_utilization >= 65
    or current_patients >= 4
    or net_flow > 0
    or queue_accumulation > 0
    or surge >= 20
  ):
    return "Moderate Pressure"
  return "Stable"


def run_scenario(
  scenario_name,
  patients,
  beds,
  doctors,
  nurses,
  treatment_rooms,
  ct,
  xray,
  lab,
  surge,
  seed=None,
):
  if seed is None:
    seed = st.session_state.simulation_seed
  if "weekend_doctors" in st.session_state:
    doctor_change = doctors - st.session_state.get(
      "num_doctors",
      doctors,
    )
    weekend_doctors = max(
      1,
      st.session_state.weekend_doctors + doctor_change,
    )
  else:
    weekend_doctors = max(1, doctors - 1)

  scenario_results, scenario_utilization = run_simulation(
    num_patients=patients,
    num_beds=beds,
    num_doctors=doctors,
    num_nurses=nurses,
    num_treatment_rooms=treatment_rooms,
    num_ct=ct,
    num_xray=xray,
    num_lab=lab,
    arrival_surge=surge,
    seed=seed,
    weekend_doctors=weekend_doctors,
  )

  utilization_values = {
    "Beds": scenario_utilization["Bed Utilization"],
    "Doctors": scenario_utilization["Doctor Utilization"],
    "Nurses": scenario_utilization["Nurse Utilization"],
    "Treatment Rooms": scenario_utilization[
      "Treatment Room Utilization"
    ],
    "CT": scenario_utilization["CT Utilization"],
    "X-Ray": scenario_utilization["X-Ray Utilization"],
    "Laboratory": scenario_utilization["Laboratory Utilization"],
  }

  maximum_utilization = max(utilization_values.values())
  current_patients = scenario_utilization["Current Patients"]
  net_flow = scenario_utilization["Net Flow"]
  queue_accumulation = scenario_utilization["Queue Accumulation"]
  bottleneck = scenario_utilization["Bottleneck"]
  resource_waits = scenario_utilization["Resource Waits"]
  pressure = calculate_pressure(
    maximum_utilization,
    current_patients,
    net_flow,
    surge,
    queue_accumulation,
  )

  return {
    "Scenario": scenario_name,
    "Arrival Surge (%)": surge,
    "Patient Inflow": scenario_utilization["Patient Inflow"],
    "Patient Outflow": scenario_utilization["Patient Outflow"],
    "Current Patients": current_patients,
    "Net Flow": net_flow,
    "Bed Occupancy (%)": round(
      scenario_utilization["Occupied Beds"]
      / scenario_utilization["resource_capacities"]["Beds"]
      * 100,
      1,
    ),
    "Average Total Time (min)": scenario_utilization[
      "Average Total Time"
    ],
    "Average Bed Wait (min)": round(resource_waits["Beds"], 1),
    "Average Bottleneck Wait (min)": round(
      resource_waits[bottleneck],
      1,
    ),
    "Maximum Utilization (%)": round(maximum_utilization, 1),
    "Pressure Level": pressure,
    "Bottleneck": bottleneck,
  }


st.title("Hospital Emergency Ward Digital Twin")
st.markdown(
  "**A virtual emergency department for testing patient demand, "
  "resource constraints, bottlenecks, and operational decisions.**"
)

st.sidebar.header("Simulation Controls")

st.sidebar.divider()
st.sidebar.subheader("Hospital Configuration")

num_patients = st.sidebar.slider(
  "Number of Patients", 20, 200, 50, step=10
)
num_beds = st.sidebar.slider("Number of Beds", 1, 20, 5)
num_doctors = st.sidebar.slider("Number of Doctors", 1, 10, 2)
weekend_doctors = st.sidebar.slider(
  "Weekend Doctors",
  1,
  10,
  1,
  help="Doctor capacity used on Saturday and Sunday.",
)
num_nurses = st.sidebar.slider("Number of Nurses", 1, 15, 2)
num_treatment_rooms = st.sidebar.slider(
  "Treatment Rooms", 1, 10, 2
)
num_ct = st.sidebar.slider("CT Scanners", 0, 5, 1)
num_xray = st.sidebar.slider("X-Ray Units", 0, 5, 1)
num_lab = st.sidebar.slider("Laboratory Capacity", 0, 5, 2)
arrival_surge = st.sidebar.slider(
  "Patient Arrival Surge (%)", 0, 100, 0, step=10
)

run_button = st.sidebar.button(
  "Run Simulation",
  type="primary",
)


if run_button:
  if st.session_state.seed_patient_count != num_patients:
    st.session_state.simulation_seed = secrets.randbelow(2**32)
    st.session_state.seed_patient_count = num_patients

  results, utilization = run_simulation(
    num_patients=num_patients,
    num_beds=num_beds,
    num_doctors=num_doctors,
    num_nurses=num_nurses,
    num_treatment_rooms=num_treatment_rooms,
    num_ct=num_ct,
    num_xray=num_xray,
    num_lab=num_lab,
    arrival_surge=arrival_surge,
    seed=st.session_state.simulation_seed,
    weekend_doctors=weekend_doctors,
  )

  st.session_state.results = results
  st.session_state.utilization = utilization
  st.session_state.simulation_done = True
  st.session_state.num_patients = num_patients
  st.session_state.num_beds = num_beds
  st.session_state.num_doctors = num_doctors
  st.session_state.weekend_doctors = weekend_doctors
  st.session_state.num_nurses = num_nurses
  st.session_state.num_treatment_rooms = num_treatment_rooms
  st.session_state.num_ct = num_ct
  st.session_state.num_xray = num_xray
  st.session_state.num_lab = num_lab
  st.session_state.arrival_surge = arrival_surge
  st.session_state.custom_result = None


if st.session_state.simulation_done:
  results = st.session_state.results
  utilization = st.session_state.utilization
  df = pd.DataFrame(results)

  sim_patients = st.session_state.num_patients
  sim_beds = st.session_state.num_beds
  sim_doctors = st.session_state.num_doctors
  sim_weekend_doctors = st.session_state.weekend_doctors
  sim_nurses = st.session_state.num_nurses
  sim_treatment_rooms = st.session_state.num_treatment_rooms
  sim_ct = st.session_state.num_ct
  sim_xray = st.session_state.num_xray
  sim_lab = st.session_state.num_lab
  sim_surge = st.session_state.arrival_surge

  patient_inflow = utilization["Patient Inflow"]
  patient_outflow = utilization["Patient Outflow"]
  current_patients = utilization["Current Patients"]
  net_flow = utilization["Net Flow"]
  occupied_beds = utilization["Occupied Beds"]
  average_total_time = utilization["Average Total Time"]
  bottleneck = utilization["Bottleneck"]

  average_bed_wait = df["bed_wait"].mean()
  average_ct_wait = df.loc[
    df["test_type"] == "CT", "ct_wait"
  ].mean()
  average_xray_wait = df.loc[
    df["test_type"] == "X-Ray", "xray_wait"
  ].mean()
  average_laboratory_wait = df.loc[
    df["test_type"] == "Laboratory", "laboratory_wait"
  ].mean()
  average_treatment_wait = df["treatment_wait"].mean()
  average_treatment_time = df["treatment_time"].mean()

  utilization_values = {
    "Beds": utilization["Bed Utilization"],
    "Doctors": utilization["Doctor Utilization"],
    "Nurses": utilization["Nurse Utilization"],
    "Treatment Rooms": utilization["Treatment Room Utilization"],
    "CT Scanners": utilization["CT Utilization"],
    "X-Ray": utilization["X-Ray Utilization"],
    "Laboratory": utilization["Laboratory Utilization"],
  }
  maximum_utilization = max(utilization_values.values())

  pressure_level = calculate_pressure(
    maximum_utilization,
    current_patients,
    net_flow,
    sim_surge,
    utilization["Queue Accumulation"],
  )

  st.header("Executive Decision Dashboard")

  c1, c2, c3, c4 = st.columns(4)
  c1.metric("Patient Inflow", patient_inflow)
  c2.metric("Patient Outflow", patient_outflow)
  c3.metric("Bottleneck", bottleneck)
  c4.metric(
    "Pressure",
    pressure_level,
  )
  st.caption(
    f"Current patients: {current_patients} | "
    f"Net flow: {net_flow:+d} | "
    f"Maximum utilization: {maximum_utilization:.1f}%"
  )

  if pressure_level == "Critical Pressure":
    st.error(f"CURRENT STATUS: **{pressure_level}**")
  elif pressure_level == "High Pressure":
    st.warning(f"CURRENT STATUS: **{pressure_level}**")
  elif pressure_level == "Moderate Pressure":
    st.info(f"CURRENT STATUS: **{pressure_level}**")
  else:
    st.success(f"CURRENT STATUS: **{pressure_level}**")

  if sim_surge > 0:
    st.warning(
      f"Patient arrivals are **{sim_surge}% above normal**."
    )

  st.header("Hospital Performance")
  c1, c2, c3, c4, c5, c6 = st.columns(6)
  c1.metric("Patient Inflow", patient_inflow)
  c2.metric("Patient Outflow", patient_outflow)
  c3.metric("Current Patients", current_patients)
  c4.metric("Net Flow", f"{net_flow:+d}")
  c5.metric("Average Total Time", f"{average_total_time:.1f} min")
  c6.metric("Average Bed Wait", f"{average_bed_wait:.1f} min")

  st.metric(
    "Bed Occupancy",
    f"{occupied_beds} / {sim_beds}",
    delta=f"{occupied_beds / sim_beds * 100:.1f}% occupied",
  )

  st.header("Patient Flow Analysis")
  c1, c2 = st.columns(2)

  with c1:
    severity_counts = (
      df["severity"].value_counts()
      .reindex(["Critical", "Serious", "Normal"], fill_value=0)
      .reset_index()
    )
    severity_counts.columns = ["Severity", "Patients"]

    fig = px.bar(
      severity_counts,
      x="Severity",
      y="Patients",
      title="Patient Severity Distribution",
      text="Patients",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

  with c2:
    test_counts = (
      df["test"].value_counts()
      .reindex(
        ["CT", "X-Ray", "Laboratory", "No Test"],
        fill_value=0,
      )
      .reset_index()
    )
    test_counts.columns = ["Test", "Patients"]

    fig = px.bar(
      test_counts,
      x="Test",
      y="Patients",
      title="Diagnostic Demand",
      text="Patients",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

  st.header("Operational Flow State")
  flow_df = pd.DataFrame(
    {
      "Metric": [
        "Patient Inflow",
        "Patient Outflow",
        "Current Patients",
        "Net Flow",
        "Throughput (patients/hour)",
      ],
      "Value": [
        patient_inflow,
        patient_outflow,
        current_patients,
        net_flow,
        utilization["Throughput"],
      ],
    }
  )

  fig = px.bar(
    flow_df,
    x="Metric",
    y="Value",
    title="Simulated Patient Flow",
    text="Value",
  )
  fig.update_traces(
    texttemplate="%{text:.1f}",
    textposition="outside",
  )
  fig.update_layout(showlegend=False)
  st.plotly_chart(fig, use_container_width=True)

  st.subheader("Operational Wait and Treatment Metrics")
  operational_metrics_df = pd.DataFrame(
    {
      "Metric": [
        "Average Bed Wait",
        "Average CT Wait",
        "Average X-Ray Wait",
        "Average Laboratory Wait",
        "Average Treatment Room Wait",
        "Average Treatment Time",
      ],
      "Minutes": [
        average_bed_wait,
        average_ct_wait,
        average_xray_wait,
        average_laboratory_wait,
        average_treatment_wait,
        average_treatment_time,
      ],
    }
  ).fillna(0.0)
  operational_metrics_df["Minutes"] = operational_metrics_df[
    "Minutes"
  ].round(1)
  st.dataframe(
    operational_metrics_df,
    use_container_width=True,
    hide_index=True,
  )

  st.subheader("Detected Bottleneck")
  st.error(
    f"Primary bottleneck: **{bottleneck}** — "
    f"highest combined utilization and queue pressure."
  )

  st.header("Resource Utilization")
  utilization_df = pd.DataFrame(
    {
      "Resource": list(utilization_values.keys()),
      "Utilization (%)": list(utilization_values.values()),
    }
  )
  utilization_df["Load Status"] = (
    utilization_df["Utilization (%)"].apply(classify_load)
  )

  st.dataframe(
    utilization_df,
    use_container_width=True,
    hide_index=True,
  )

  fig = px.bar(
    utilization_df,
    x="Resource",
    y="Utilization (%)",
    title="Hospital Resource Utilization",
    text="Utilization (%)",
  )
  fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
  fig.update_layout(yaxis=dict(range=[0, 100]), showlegend=False)
  st.plotly_chart(fig, use_container_width=True)

  st.header("Simulation Insight")
  insight_map = {
    "Beds": "Bed capacity is limiting patient flow. Additional emergency beds should be evaluated.",
    "Nurses": "Nursing capacity is the next constraint on patient flow.",
    "Doctors": "Doctor capacity is limiting patient flow.",
    "Treatment Rooms": "Treatment-room capacity is constraining throughput.",
    "CT": "CT capacity is constraining diagnostic throughput.",
    "X-Ray": "X-Ray capacity is constraining diagnostic throughput.",
    "Laboratory": "Laboratory capacity is constraining diagnostic throughput.",
  }
  st.info(f"**Simulation Insight:** {insight_map[bottleneck]}")

  st.header("What-If Resource Comparison")
  scenarios = [
    run_scenario(
      "Baseline",
      sim_patients,
      sim_beds,
      sim_doctors,
      sim_nurses,
      sim_treatment_rooms,
      sim_ct,
      sim_xray,
      sim_lab,
      sim_surge,
    ),
    run_scenario(
      "+1 Bed",
      sim_patients,
      sim_beds + 1,
      sim_doctors,
      sim_nurses,
      sim_treatment_rooms,
      sim_ct,
      sim_xray,
      sim_lab,
      sim_surge,
    ),
    run_scenario(
      "+1 Doctor",
      sim_patients,
      sim_beds,
      sim_doctors + 1,
      sim_nurses,
      sim_treatment_rooms,
      sim_ct,
      sim_xray,
      sim_lab,
      sim_surge,
    ),
    run_scenario(
      "+1 Nurse",
      sim_patients,
      sim_beds,
      sim_doctors,
      sim_nurses + 1,
      sim_treatment_rooms,
      sim_ct,
      sim_xray,
      sim_lab,
      sim_surge,
    ),
    run_scenario(
      "+1 Treatment Room",
      sim_patients,
      sim_beds,
      sim_doctors,
      sim_nurses,
      sim_treatment_rooms + 1,
      sim_ct,
      sim_xray,
      sim_lab,
      sim_surge,
    ),
    run_scenario(
      "+1 CT",
      sim_patients,
      sim_beds,
      sim_doctors,
      sim_nurses,
      sim_treatment_rooms,
      sim_ct + 1,
      sim_xray,
      sim_lab,
      sim_surge,
    ),
    run_scenario(
      "+1 X-Ray",
      sim_patients,
      sim_beds,
      sim_doctors,
      sim_nurses,
      sim_treatment_rooms,
      sim_ct,
      sim_xray + 1,
      sim_lab,
      sim_surge,
    ),
    run_scenario(
      "+1 Laboratory",
      sim_patients,
      sim_beds,
      sim_doctors,
      sim_nurses,
      sim_treatment_rooms,
      sim_ct,
      sim_xray,
      sim_lab + 1,
      sim_surge,
    ),
  ]

  resource_scenarios = pd.DataFrame(scenarios)
  st.dataframe(
    resource_scenarios,
    use_container_width=True,
    hide_index=True,
  )
  st.caption(
    "Interventions use the same seeded patient arrivals and service-time "
    "draws. A resource is recommended only when the tested scenario "
    "reduces average total patient time; bottlenecks are ranked from "
    "that resource's own utilization and matched queue wait."
  )

  fig = px.bar(
    resource_scenarios,
    x="Scenario",
    y="Average Total Time (min)",
    title="What-If Intervention Comparison",
    text="Average Total Time (min)",
  )
  fig.update_traces(
    texttemplate="%{text:.1f}",
    textposition="outside",
  )
  fig.update_layout(showlegend=False)
  st.plotly_chart(fig, use_container_width=True)

  best_resource = resource_scenarios.loc[
    resource_scenarios["Average Total Time (min)"].idxmin()
  ]
  baseline_total_time = scenarios[0]["Average Total Time (min)"]
  best_total_time = best_resource["Average Total Time (min)"]
  improvement = max(baseline_total_time - best_total_time, 0)
  improvement_pct = (
    improvement / baseline_total_time * 100
    if baseline_total_time > 0 else 0
  )

  st.subheader("Best Intervention")
  if best_resource["Scenario"] == "Baseline":
    st.info(
      "None of the tested resource additions improved "
      "average total patient time."
    )
  else:
    c1, c2, c3 = st.columns(3)
    c1.metric("Recommended", best_resource["Scenario"])
    c2.metric("New Avg Total Time", f"{best_total_time:.1f} min")
    c3.metric("Reduction", f"{improvement_pct:.1f}%")
    st.success(
      f"Recommended tested intervention: "
      f"**{best_resource['Scenario']}**."
    )

  st.header("Demand Surge Simulator")
  surge_scenarios = [
    ("Normal", 0),
    ("+20% Arrivals", 20),
    ("+30% Arrivals", 30),
    ("+50% Arrivals", 50),
    ("+70% Arrivals", 70),
  ]

  surge_results = [
    run_scenario(
      name,
      sim_patients,
      sim_beds,
      sim_doctors,
      sim_nurses,
      sim_treatment_rooms,
      sim_ct,
      sim_xray,
      sim_lab,
      surge,
    )
    for name, surge in surge_scenarios
  ]

  surge_df = pd.DataFrame(surge_results)
  st.dataframe(
    surge_df,
    use_container_width=True,
    hide_index=True,
  )

  fig = px.line(
    surge_df,
    x="Arrival Surge (%)",
    y="Average Total Time (min)",
    markers=True,
    title="Arrival Surge vs Average Total Time",
  )
  st.plotly_chart(fig, use_container_width=True)

  st.header("Custom What-If Scenario")

  custom_surge = st.slider(
    "Custom Patient Arrival Surge (%)",
    0,
    100,
    sim_surge,
    step=10,
    key="custom_surge",
  )

  c1, c2, c3, c4 = st.columns(4)
  with c1:
    custom_beds = st.number_input(
      "Additional Beds", 0, 10, 0, key="custom_beds"
    )
  with c2:
    custom_doctors = st.number_input(
      "Additional Doctors", 0, 5, 0, key="custom_doctors"
    )
  with c3:
    custom_nurses = st.number_input(
      "Additional Nurses", 0, 10, 0, key="custom_nurses"
    )
  with c4:
    custom_rooms = st.number_input(
      "Additional Treatment Rooms", 0, 5, 0,
      key="custom_rooms",
    )

  c1, c2, c3 = st.columns(3)
  with c1:
    custom_ct = st.number_input(
      "Additional CT Scanners", 0, 5, 0, key="custom_ct"
    )
  with c2:
    custom_xray = st.number_input(
      "Additional X-Ray Units", 0, 5, 0, key="custom_xray"
    )
  with c3:
    custom_lab = st.number_input(
      "Additional Laboratory Capacity", 0, 5, 0,
      key="custom_lab",
    )

  custom_run = st.button(
    "Run Custom Scenario",
    type="primary",
  )

  if custom_run:
    st.session_state.custom_result = run_scenario(
      "Custom Scenario",
      sim_patients,
      sim_beds + custom_beds,
      sim_doctors + custom_doctors,
      sim_nurses + custom_nurses,
      sim_treatment_rooms + custom_rooms,
      sim_ct + custom_ct,
      sim_xray + custom_xray,
      sim_lab + custom_lab,
      custom_surge,
    )

  if st.session_state.custom_result is not None:
    custom_result = st.session_state.custom_result
    st.subheader("Custom Scenario Result")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
      "Patient Inflow",
      custom_result["Patient Inflow"],
    )
    c2.metric(
      "Average Total Time",
      f"{custom_result['Average Total Time (min)']:.1f} min",
    )
    c3.metric(
      "Max Utilization",
      f"{custom_result['Maximum Utilization (%)']:.1f}%",
    )
    c4.metric("Pressure", custom_result["Pressure Level"])

    st.info(
      f"**Custom Bottleneck:** {custom_result['Bottleneck']}"
    )

  st.header("Final Decision Recommendation")

  if pressure_level == "Critical Pressure":
    decision = (
      f"Immediate action is required. Prioritize "
      f"**{best_resource['Scenario']}** and prepare additional "
      f"surge-management measures."
    )
  elif pressure_level == "High Pressure":
    decision = (
      f"High pressure detected. Prioritize "
      f"**{best_resource['Scenario']}** to reduce waiting time."
    )
  elif pressure_level == "Moderate Pressure":
    decision = (
      f"Moderate pressure detected. Monitor the "
      f"**{bottleneck}** bottleneck and consider "
      f"**{best_resource['Scenario']}** if demand increases."
    )
  else:
    decision = (
      f"The emergency department is currently stable. "
      f"Continue monitoring **{bottleneck}**."
    )

  st.success(f"**Recommended Action:** {decision}")

  st.header("Decision Impact")
  c1, c2, c3 = st.columns(3)
  c1.metric("Baseline Total Time", f"{baseline_total_time:.1f} min")
  c2.metric("Best Intervention", f"{best_total_time:.1f} min")
  c3.metric("Waiting Reduction", f"{improvement_pct:.1f}%")

  st.header("Executive Summary")
  summary_df = pd.DataFrame(
    {
      "Metric": [
        "Patient Demand",
        "Arrival Surge",
        "Pressure Level",
        "Primary Bottleneck",
        "Maximum Utilization",
        "Average Total Patient Time",
        "Best Intervention",
        "Waiting Time Reduction",
      ],
      "Result": [
        f"{sim_patients} patients",
        f"{sim_surge}%",
        pressure_level,
        bottleneck,
        f"{maximum_utilization:.1f}%",
        f"{average_total_time:.1f} min",
        best_resource["Scenario"],
        f"{improvement_pct:.1f}%",
      ],
    }
  )
  st.dataframe(
    summary_df,
    use_container_width=True,
    hide_index=True,
  )

  with st.expander("View Detailed Patient Results"):
    display_df = df.drop(
      columns=["doctor_wait", "nurse_wait"],
      errors="ignore",
    )
    st.dataframe(
      display_df,
      use_container_width=True,
      hide_index=True,
    )
    st.caption(
      f"Recorded parameters: {sim_patients} generated patients, "
      f"seed={st.session_state.simulation_seed}, "
      f"{sim_surge}% arrival surge, beds={sim_beds}, "
      f"weekday doctors={sim_doctors}, weekend doctors={sim_weekend_doctors}, "
      f"nurses={sim_nurses}, treatment rooms={sim_treatment_rooms}, "
      f"CT={sim_ct}, X-Ray={sim_xray}, laboratory={sim_lab}. "
      "Wait values are simulated queue times; they are not real hospital "
      "measurements."
    )

else:
  st.info(
    "Configure the emergency ward using the sidebar and "
    "click **Run Simulation** to start."
  )
