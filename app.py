from datetime import datetime
import streamlit as st

# ------------------- Page -------------------
st.set_page_config(page_title="Kinetic eGFR (Chen)", page_icon="🧪", layout="centered")
st.title("Kinetic eGFR (Chen) – Non-steady state")
st.caption("Educational aid. Correlate with urine output and, when high-stakes, a timed urine creatinine clearance.")

# ------------------- Helpers -------------------
UMOL_PER_MGDL = 88.4  # µmol/L per mg/dL

def to_mgdl(value, unit):
    if value is None: return None
    return value if unit == "mg/dL" else value / UMOL_PER_MGDL

def cockcroft_gault(age, sex, weight_kg, scr_mgdl):
    if any(x is None for x in (age, weight_kg, scr_mgdl)): return None
    if age <= 0 or weight_kg <= 0 or scr_mgdl <= 0: return None
    crcl = ((140 - age) * weight_kg) / (72 * scr_mgdl)
    if sex == "Female":
        crcl *= 0.85
    return crcl  # mL/min (unindexed)

def chen_ke_gfr(scr_ss, crcl_ss, scr1, t1, scr2, t2, max_dscr_day=1.5):
    # All SCr in mg/dL, CrCl_ss in mL/min, times are datetimes
    if None in (scr_ss, crcl_ss, scr1, t1, scr2, t2): return None, None, None, "missing"
    if scr_ss <= 0 or crcl_ss <= 0 or scr1 <= 0 or scr2 <= 0: return None, None, None, "nonpositive"
    dt_h = (t2 - t1).total_seconds() / 3600.0
    if dt_h <= 0: return None, None, None, "nonpositive_dt"
    mean_scr = (scr1 + scr2) / 2.0
    d_scr = (scr2 - scr1)
    if mean_scr <= 0 or max_dscr_day <= 0: return None, None, None, "bad_params"
    term = 1.0 - (24.0 * d_scr) / (dt_h * max_dscr_day)
    ke = (scr_ss * crcl_ss / mean_scr) * term
    return ke, d_scr, dt_h, None

def dosing_band(gfr):
    if gfr is None: return "unknown"
    if gfr >= 60: return "≥60 mL/min – standard dosing in most monographs"
    if gfr >= 30: return "30–59 mL/min – moderate reduction"
    if gfr >= 15: return "15–29 mL/min – severe reduction"
    if gfr >= 0:  return "<15 mL/min – kidney failure range"
    return "near-zero – treat as anuric"

def interpretation(ke, crcl_ss, d_scr, dt_h):
    if ke is None: return "Cannot compute with the current inputs."
    out = []
    if d_scr > 0:
        out.append(f"Serum creatinine is rising by {d_scr:.3f} mg/dL over {dt_h:.1f} h.")
    elif d_scr < 0:
        out.append(f"Serum creatinine is falling by {abs(d_scr):.3f} mg/dL over {dt_h:.1f} h.")
    else:
        out.append(f"Serum creatinine unchanged over {dt_h:.1f} h.")
    ke_display = max(0.0, ke)
    out.append(f"Kinetic eGFR ≈ {ke_display:.1f} mL/min (unindexed). Dosing band: {dosing_band(ke_display)}.")
    if crcl_ss and crcl_ss > 0:
        drop = max(0.0, 1.0 - ke_display / crcl_ss) * 100.0
        out.append(f"Functional reduction vs baseline ≈ {drop:.0f}%.")
    if dt_h < 6:
        out.append("Interval <6 h – kinetic estimate can be noisy; repeat later.")
    if ke < 0:
        out.append("Computed value is negative; treat clinically as ~0 mL/min (near-anuric).")
    if ke_display < 30:
        out.append("High risk for drug accumulation – consider measured urine CrCl and review nephrotoxins.")
    out.append("Caution in early shock/rapidly fluctuating states; correlate with urine output.")
    return " ".join(out)

# ------------------- Inputs -------------------
st.subheader("Baseline (steady state)")
unit = st.radio("Creatinine units", ["mg/dL", "µmol/L"], horizontal=True)

col0, col1 = st.columns(2)
with col0:
    scr_ss_in = st.number_input("Baseline SCr_ss", min_value=0.01, max_value=50.0, value=1.0, step=0.1)
with col1:
    baseline_mode = st.selectbox("Baseline GFR source", ["Enter CrCl_ss directly", "Compute via Cockcroft–Gault"])

crcl_ss = None
if baseline_mode == "Enter CrCl_ss directly":
    crcl_ss = st.number_input("Baseline CrCl_ss (mL/min, unindexed)", min_value=1.0, max_value=300.0, value=90.0)
else:
    ca, cb, cc, cd = st.columns(4)
    with ca: age = st.number_input("Age (y)", min_value=1, max_value=120, value=55)
    with cb: sex = st.selectbox("Sex", ["Male", "Female"])
    with cc: weight = st.number_input("Weight (kg)", min_value=1.0, max_value=400.0, value=70.0)
    with cd: scr_for_cg_in = st.number_input("SCr for CG", min_value=0.01, max_value=50.0, value=scr_ss_in, step=0.1)
    scr_for_cg = to_mgdl(scr_for_cg_in, unit)
    crcl_ss = cockcroft_gault(age, sex, weight, scr_for_cg)
    if crcl_ss:
        st.info(f"Cockcroft–Gault baseline CrCl_ss ≈ {crcl_ss:.1f} mL/min")
    else:
        st.warning("Cannot compute Cockcroft–Gault with current inputs.")

st.markdown("---")
st.subheader("Kinetic window (two creatinine values)")
col2, col3 = st.columns(2)
with col2:
    scr1_in = st.number_input("SCr1", min_value=0.01, max_value=50.0, value=1.0, step=0.1)
    t1 = st.datetime_input("Time of SCr1", value=datetime.now().replace(minute=0, second=0, microsecond=0))
with col3:
    scr2_in = st.number_input("SCr2", min_value=0.01, max_value=50.0, value=1.3, step=0.1)
    t2 = st.datetime_input("Time of SCr2", value=datetime.now().replace(minute=0, second=0, microsecond=0))

st.markdown("---")
st.subheader("Assumptions")
col4, col5 = st.columns(2)
with col4:
    max_choice = st.selectbox("Max ΔSCr/day method", ["Fixed 1.5 mg/dL/day", "Compute from weight (TBW)"])
with col5:
    # TBW: 0.6×wt male, 0.5×wt female → Max ΔSCr/day ≈ (SCr_ss × CrCl_ss) / TBW
    if max_choice == "Compute from weight (TBW)":
        wt_for_tbw = st.number_input("Weight for TBW (kg)", min_value=1.0, max_value=400.0, value=70.0)
    else:
        wt_for_tbw = None

# Convert all creatinine inputs to mg/dL
scr_ss = to_mgdl(scr_ss_in, unit)
scr1 = to_mgdl(scr1_in, unit)
scr2 = to_mgdl(scr2_in, unit)

# Determine Max ΔSCr/day
if max_choice == "Fixed 1.5 mg/dL/day":
    max_dscr_day = 1.5
else:
    if not crcl_ss or not scr_ss or not wt_for_tbw:
        max_dscr_day = 1.5  # fallback
    else:
        tbw = (0.5 if ('sex' in locals() and sex == "Female") else 0.6) * wt_for_tbw  # L
        # Units: (mg/dL * mL/min) / L → mg/dL per min → ×1440 → mg/dL/day
        max_dscr_day = (scr_ss * crcl_ss / tbw) * 1440.0 / 1000.0  # divide by 1000 to convert mL→L
        # Keep within reasonable bounds
        if max_dscr_day < 0.5 or max_dscr_day > 5.0:
            max_dscr_day = min(max(max_dscr_day, 0.5), 5.0)

if st.button("Compute KeGFR"):
    if not crcl_ss or crcl_ss <= 0:
        st.error("Provide a valid baseline CrCl_ss (>0).")
    else:
        ke, d_scr, dt_h, err = chen_ke_gfr(scr_ss, crcl_ss, scr1, t1, scr2, t2, max_dscr_day=max_dscr_day)
        if err:
            if err == "nonpositive_dt":
                st.error("Time of SCr2 must be after SCr1.")
            else:
                st.error("Unable to compute with current inputs. Check values and units.")
        else:
            ke_display = max(0.0, ke)
            st.metric("Kinetic eGFR (Chen)", f"{ke_display:.1f} mL/min")
            st.metric("Interval", f"{dt_h:.1f} h")
            st.metric("ΔSCr", f"{d_scr:+.3f} mg/dL")
            st.markdown("### Interpretation")
            st.write(interpretation(ke, crcl_ss, d_scr, dt_h))
            with st.expander("Details and formula"):
                st.write(
                    "KeGFR = (SCr_ss × CrCl_ss / MeanSCr) × [ 1 − (24 × ΔSCr) / (Δt × MaxΔSCr/day) ]\n"
                    "Units: creatinine mg/dL, CrCl_ss mL/min (unindexed), Δt hours, MaxΔSCr/day mg/dL/day."
                )

st.markdown("---")
st.caption("This tool does not provide medical advice. Validate with clinical context and measured urine creatinine clearance when important decisions depend on GFR.")
