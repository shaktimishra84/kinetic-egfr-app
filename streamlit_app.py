from datetime import datetime, date, time
import streamlit as st

st.set_page_config(page_title="Kinetic eGFR (Chen)", page_icon="🧪", layout="centered")
st.title("Kinetic eGFR (Chen) – Non-steady state")
st.caption("Educational aid. Correlate with urine output and, when high-stakes, a timed urine creatinine clearance.")

UMOL_PER_MGDL = 88.4

def to_mgdl(x, unit):
    return None if x is None else (x if unit=="mg/dL" else x/UMOL_PER_MGDL)

def cockcroft_gault(age, sex, wt, scr):
    if None in (age, wt, scr) or age<=0 or wt<=0 or scr<=0: return None
    v=((140-age)*wt)/(72*scr)
    return v*0.85 if sex=="Female" else v

def chen_ke_gfr(scr_ss, crcl_ss, scr1, t1, scr2, t2, max_dscr_day=1.5):
    if None in (scr_ss,crcl_ss,scr1,t1,scr2,t2) or min(scr_ss,crcl_ss,scr1,scr2)<=0: return None,(None,None),"bad_input"
    dt_h=(t2-t1).total_seconds()/3600.0
    if dt_h<=0: return None,(None,None),"bad_dt"
    mean_scr=(scr1+scr2)/2.0
    d_scr=(scr2-scr1)
    if mean_scr<=0 or max_dscr_day<=0: return None,(None,None),"bad_param"
    ke=(scr_ss*crcl_ss/mean_scr)*(1.0-(24.0*d_scr)/(dt_h*max_dscr_day))
    return ke,(d_scr,dt_h),None

def dosing_band(g):
    if g is None: return "unknown"
    if g>=60: return "≥60 mL/min – standard dosing"
    if g>=30: return "30–59 mL/min – moderate reduction"
    if g>=15: return "15–29 mL/min – severe reduction"
    if g>=0:  return "<15 mL/min – kidney failure range"
    return "near-zero – treat as anuric"

def interp(ke, crcl_ss, d_scr, dt_h):
    if ke is None: return "Cannot compute with current inputs."
    parts=[]
    if d_scr>0:  parts.append(f"Creatinine rising by {d_scr:.3f} mg/dL over {dt_h:.1f} h.")
    elif d_scr<0:parts.append(f"Creatinine falling by {abs(d_scr):.3f} mg/dL over {dt_h:.1f} h.")
    else:        parts.append(f"Creatinine unchanged over {dt_h:.1f} h.")
    ke_disp=max(0.0,ke)
    parts.append(f"Kinetic eGFR ≈ {ke_disp:.1f} mL/min. Dosing band: {dosing_band(ke_disp)}.")
    if crcl_ss and crcl_ss>0:
        drop=max(0.0,1.0-ke_disp/crcl_ss)*100.0
        parts.append(f"Functional reduction vs baseline ≈ {drop:.0f}%.")
    if dt_h<6: parts.append("Interval <6 h – estimate may be noisy; repeat later.")
    if ke<0:   parts.append("Negative value → treat clinically as ~0 mL/min (near-anuric).")
    if ke_disp<30: parts.append("High risk for drug accumulation – consider measured urine CrCl and review nephrotoxins.")
    parts.append("Caution in early shock/rapid swings; correlate with urine output.")
    return " ".join(parts)

def dt_picker(label, default_date: date, default_time: time):
    c1,c2=st.columns(2)
    with c1: d=st.date_input(f"{label} date", value=default_date)
    with c2: tm=st.time_input(f"{label} time", value=default_time)
    return datetime.combine(d,tm)

st.subheader("Baseline (steady state)")
unit=st.radio("Creatinine units", ["mg/dL","µmol/L"], horizontal=True)

c0,c1=st.columns(2)
with c0: scr_ss_in=st.number_input("Baseline SCr_ss", min_value=0.01, max_value=50.0, value=1.0, step=0.1)
with c1: base_mode=st.selectbox("Baseline GFR source", ["Enter CrCl_ss directly","Compute via Cockcroft–Gault"])

if base_mode=="Enter CrCl_ss directly":
    crcl_ss=st.number_input("Baseline CrCl_ss (mL/min, unindexed)", min_value=1.0, max_value=300.0, value=90.0)
else:
    ca,cb,cc,cd=st.columns(4)
    with ca: age=st.number_input("Age (y)",1,120,55)
    with cb: sex=st.selectbox("Sex",["Male","Female"])
    with cc: wt=st.number_input("Weight (kg)",1.0,400.0,70.0)
    with cd: scr_for_cg_in=st.number_input("SCr for CG",0.01,50.0,scr_ss_in,step=0.1)
    crcl_ss=cockcroft_gault(age,sex,wt,to_mgdl(scr_for_cg_in,unit))
    st.info(f"Cockcroft–Gault CrCl_ss ≈ {crcl_ss:.1f} mL/min" if crcl_ss else "Cannot compute Cockcroft–Gault.")

st.markdown("---")
st.subheader("Kinetic window (two creatinine values)")
today=date.today()
c2,c3=st.columns(2)
with c2:
    scr1_in=st.number_input("SCr1",0.01,50.0,1.0,step=0.1)
    t1=dt_picker("SCr1", today, time(8,0))
with c3:
    scr2_in=st.number_input("SCr2",0.01,50.0,1.3,step=0.1)
    t2=dt_picker("SCr2", today, time(20,0))

st.markdown("---")
st.subheader("Assumptions")
c4,c5=st.columns(2)
with c4: max_mode=st.selectbox("Max ΔSCr/day", ["Fixed 1.5 mg/dL/day","Compute from weight (TBW)"])
with c5:
    wt_tbw=st.number_input("Weight for TBW (kg)",1.0,400.0,70.0) if max_mode!="Fixed 1.5 mg/dL/day" else None

scr_ss=to_mgdl(scr_ss_in,unit); scr1=to_mgdl(scr1_in,unit); scr2=to_mgdl(scr2_in,unit)
if max_mode=="Fixed 1.5 mg/dL/day":
    max_dscr_day=1.5
else:
    if not (crcl_ss and scr_ss and wt_tbw):
        max_dscr_day=1.5
    else:
        tbw=((0.5 if ('sex' in locals() and sex=="Female") else 0.6)*wt_tbw)  # L
        max_dscr_day=(scr_ss*crcl_ss/tbw)*1440.0/1000.0
        if max_dscr_day<0.5 or max_dscr_day>5.0:
            max_dscr_day=min(max(max_dscr_day,0.5),5.0)

if st.button("Compute KeGFR"):
    if not (crcl_ss and crcl_ss>0):
        st.error("Provide a valid baseline CrCl_ss (>0).")
    else:
        ke,(d_scr,dt_h),err=chen_ke_gfr(scr_ss,crcl_ss,scr1,t1,scr2,t2,max_dscr_day=max_dscr_day)
        if err=="bad_dt": st.error("Time of SCr2 must be after SCr1.")
        elif err:         st.error("Unable to compute. Check values/units.")
        else:
            ke_disp=max(0.0,ke)
            st.metric("Kinetic eGFR (Chen)", f"{ke_disp:.1f} mL/min")
            st.metric("Interval", f"{dt_h:.1f} h")
            st.metric("ΔSCr", f"{d_scr:+.3f} mg/dL")
            st.markdown("### Interpretation")
            st.write(interp(ke,crcl_ss,d_scr,dt_h))
            with st.expander("Details and formula"):
                st.write("KeGFR = (SCr_ss × CrCl_ss / MeanSCr) × [1 − (24 × ΔSCr)/(Δt × MaxΔSCr/day)]")

st.markdown("---")
st.caption("No medical advice; validate with clinical context and measured urine creatinine clearance when decisions depend on GFR.")
