from datetime import datetime
import streamlit as st

st.set_page_config(page_title="Kinetic eGFR (Chen) – ICU", page_icon="🧪", layout="centered")
st.title("Kinetic eGFR (Chen) for Non-Steady State")
st.caption("Educational tool. Correlate with clinical context and timed urine CrCl when feasible.")

def cockcroft_gault(age, sex, weight_kg, scr_mgdl):
    if any(x is None for x in (age, weight_kg, scr_mgdl)) or age <= 0 or weight_kg <= 0 or scr_mgdl <= 0:
        return None
    crcl = ((140 - age) * weight_kg) / (72 * scr_mgdl)
    if sex == "Female":
        crcl *= 0.85
    return crcl

def ke_gfr(scr_ss, crcl_ss, scr1, t1, scr2, t2, max_dscr_day=1.5, min_dt_hours=2.0):
    if None in (scr_ss, crcl_ss, scr1, scr2, t1, t2) or crcl_ss <= 0 or scr_ss <= 0:
        return None, None, None
    dt_hours = (t2 - t1).total_seconds() / 3600.0
    mean_scr = (scr1 + scr2) / 2.0
    d_scr = (scr2 - scr1)
    if mean_scr <= 0 or max_dscr_day <= 0 or dt_hours <= 0:
        return None, None, None
    term = 1.0 - (24.0 * d_scr) / (dt_hours * max_dscr_day)
    ke = (scr_ss * crcl_ss / mean_scr) * term
    return ke, d_scr, dt_hours

def dosing_band(gfr_mlmin):
    if gfr_mlmin is None: return "unknown"
    if gfr_mlmin >= 60: return "≥60 mL/min (standard dosing)"
    if gfr_mlmin >= 30: return "30–59 mL/min (moderate reduction)"
    if gfr_mlmin >= 15: return "15–29 mL/min (severe reduction)"
    if gfr_mlmin >= 0:  return "<15 mL/min (kidney failure range)"
    return "near-zero (treat as anuric)"

def interp_text(ke, crcl_ss, d_scr, dt_h):
    if ke is None or crcl_ss is None or dt_h is None:
        return "Insufficient input to interpret."
    ke_display = max(ke, 0.0)
    drop_pct = (100.0 * max(0.0, (1.0 - ke_display / crcl_ss))) if crcl_ss > 0 else None
    band = dosing_band(ke_display)
    parts = []
    if d_scr is not None:
        if d_scr > 0: parts.append(f"Serum creatinine is rising by {d_scr:.3f} mg/dL over {dt_h:.1f} h.")
        elif d_scr < 0: parts.append(f"Serum creatinine is falling by {abs(d_scr):.3f} mg/dL over {dt_h:.1f} h.")
        else: parts.append(f"Serum creatinine unchanged over {dt_h:.1f} h.")
    parts.append(f"Kinetic eGFR ≈ {ke_display:.1f} mL/min (unindexed). Dosing band: {band}.")
    if drop_pct is not None:
        parts.append(f"Relative to baseline GFR {crcl_ss:.1f} mL/min, functional reduction ≈ {drop_pct:.0f}%.")
    if dt_h < 6: parts.append("Caution: interval <6 h – kinetic estimate may be noisy; recheck later.")
    if ke is not None and ke < 0: parts.append("Computed KeGFR is negative; treat as ~0 mL/min (near-anuric).")
    if ke_display < 30: parts.append("High risk for drug accumulation; consider measured urine CrCl and review nephrotoxins.")
    if d_scr is not None and d_scr > 0 and ke_display < 60: parts.append("Early functional decline detected; increase monitoring and optimize hemodynamics.")
    parts.append("Do not rely on KeGFR alone in early shock; correlate with urine output.")
    return " ".join(parts)

st.subheader("Inputs")
colA, colB = st.columns(2)
with colA:
    age = st.number_input("Age (years)", min_value=1, max_value=120, value=55)
    sex = st.selectbox("Sex", ["Male", "Female"])
    weight = st.number_input("Weight (kg) for Cockcroft–Gault", min_value=1.0, max_value=400.0, value=70.0)
with colB:
    scr_ss = st.number_input("Baseline steady-state SCr_ss (mg/dL)", min_value=0.1, max_value=15.0, value=1.0, step=0.1)
    baseline_method = st.selectbox("Baseline GFR method", ["Enter CrCl_ss directly", "Compute via Cockcroft–Gault"])

crcl_ss = None
if baseline_method == "Enter CrCl_ss directly":
    crcl_ss = st.number_input("Baseline CrCl_ss (mL/min, unindexed)", min_value=1.0, max_value=300.0, value=90.0)
else:
    scr_for_cg = st.number_input("SCr for Cockcroft–Gault (mg/dL)", min_value=0.1, max_value=15.0, value=scr_ss)
    crcl_ss = cockcroft_gault(age, sex, weight, scr_for_cg)
    if crcl_ss: st.info(f"Calculated CrCl_ss by Cockcroft–Gault ≈ {crcl_ss:.1f} mL/min")
    else:       st.warning("Cannot compute Cockcroft–Gault with current inputs.")

st.markdown("---")
st.subheader("Creatinine pair for kinetic window")
col1, col2 = st.columns(2)
with col1:
    scr1 = st.number_input("SCr1 (mg/dL)", min_value=0.1, max_value=20.0, value=1.0, step=0.1)
    t1 = st.datetime_input("Time of SCr1", value=datetime.now().replace(hour=8, minute=0, second=0, microsecond=0))
with col2:
    scr2 = st.number_input("SCr2 (mg/dL)", min_value=0.1, max_value=20.0, value=1.3, step=0.1)
    t2 = st.datetime_input("Time of SCr2", value=datetime.now().replace(hour=20, minute=0, second=0, microsecond=0))

st.markdown("---")
st.subheader("Kinetic assumptions")
colx, coly = st.columns(2)
with colx:
    max_dscr_day = st.number_input("Max ΔSCr/day if anuric (mg/dL/day)", min_value=0.5, max_value=5.0, value=1.5, step=0.1)
with coly:
    min_dt = st.number_input("Minimum interval warning (hours)", min_value=0.0, max_value=24.0, value=2.0, step=0.5)

if st.button("Compute KeGFR"):
    if crcl_ss is None or crcl_ss <= 0:
        st.error("Provide a valid baseline CrCl_ss (>0 mL/min).")
    else:
        ke, d_scr, dt_h = ke_gfr(scr_ss, crcl_ss, scr1, t1, scr2, t2, max_dscr_day=max_dscr_day, min_dt_hours=min_dt)
        if ke is None:
            st.error("Unable to compute. Check inputs and time interval.")
        else:
            ke_display = max(0.0, ke)
            st.metric(label="Kinetic eGFR (Chen)", value=f"{ke_display:.1f} mL/min")
            st.metric(label="Time interval", value=f"{dt_h:.1f} h")
            st.metric(label="ΔSCr", value=f"{d_scr:+.3f} mg/dL")

            st.markdown("### Interpretation")
            st.write(interp_text(ke, crcl_ss, d_scr, dt_h))

            st.markdown("### Dosing band")
            st.write(dosing_band(ke_display))

            with st.expander("Details and formula"):
                st.markdown(
                    "KeGFR = (SCr_ss × CrCl_ss / MeanSCr) × [ 1 − (24 × ΔSCr) / (Δt × MaxΔSCr/day) ]  \n"
                    "Units: SCr mg/dL, CrCl_ss mL/min (unindexed), Δt hours, MaxΔSCr/day mg/dL/day."
                )
                st.markdown("Use a recent steady-state baseline. Recompute as new labs arrive. Consider timed urine CrCl when decisions are high-stakes.")
st.markdown("---")
st.caption("This tool does not provide medical advice.")
