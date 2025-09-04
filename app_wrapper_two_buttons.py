# -*- coding: utf-8 -*-
# app_wrapper_two_buttons.py
# Streamlit wrapper με 2 κουμπιά, ΧΩΡΙΣ καμία συγχώνευση ή αλλαγή λογικής.
# Κουμπί 1: Εκτέλεση Βήματα 1–6  (διαβάζει STEP1, βγάζει STEP6)
# Κουμπί 2: Τελική κατανομή — Εκτέλεση Βήματα 7–8 (διαβάζει STEP6, βγάζει BEST_ONLY)
#
# Απαιτεί τα δικά σου αρχεία .py στον ΙΔΙΟ φάκελο:
# step1_immutable_ALLINONE.py
# step_2_helpers_FIXED.py
# step_2_zoiroi_idiaterotites_FIXED_v3_PATCHED.py
# step3_amivaia_filia_FIXED.py
# step4_corrected.py
# step5_enhanced.py           (για το Βήμα 5)
# step6_compliant.py          (για το Βήμα 6)
# step7_fixed_final.py        (για scoring στο Βήμα 7)
# step8.py                    (περιέχει build_best_only_workbook για Βήμα 8)
# export_step1__per_scenario.py  ή  export_step1_4_per_scenario.py  (exporter MIN 1→5)
#
# Εγκατάσταση:
#   pip install streamlit pandas numpy openpyxl xlsxwriter
# Εκτέλεση:
#   streamlit run app_wrapper_two_buttons.py

import streamlit as st
import tempfile, os, importlib.util, sys
from pathlib import Path

st.set_page_config(page_title="Wrapper 1–6 & 7–8", layout="centered")
st.title("Wrapper 1–6 και 7–8 (MIN μορφή)")
st.caption("Δεν αλλάζω λογική/συγχωνεύσεις — απλώς καλώ τα δικά σου scripts.")

WORKDIR = Path(__file__).parent

# ----------------- Utility: dynamic import by absolute path -----------------
def _import_by_path(modname: str, path: Path):
    spec = importlib.util.spec_from_file_location(modname, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod

def _first_existing(*names: str) -> Path | None:
    for n in names:
        p = WORKDIR / n
        if p.exists():
            return p
    return None

st.markdown("## Κουμπί 1 — Εκτέλεση Βήματα 1–6")
st.write("Ανέβασε το Excel του Βήματος 1 (STEP1). Θα παραχθεί ένα νέο Excel μέχρι **Βήμα 6** (MIN μορφή).")

uploaded_step1 = st.file_uploader("Ανέβασε STEP1_IMMUTABLE_*.xlsx", type=["xlsx"], key="up1")
col1, col2 = st.columns([1,1])
run_1_6 = col1.button("▶️ Εκτέλεση Βήματα 1–6")

if run_1_6:
    if not uploaded_step1:
        st.error("Πρώτα ανέβασε αρχείο Βήματος 1.")
        st.stop()
    # Βρες exporter (1→5)
    exporter_path = _first_existing("export_step1__per_scenario.py", "export_step1_4_per_scenario.py")
    if exporter_path is None:
        st.error("Δεν βρέθηκε exporter (export_step1__per_scenario.py ή export_step1_4_per_scenario.py). Βάλε το αρχείο στον ίδιο φάκελο.")
        st.stop()
    step6_path = _first_existing("step6_compliant.py", "step6.py")
    if step6_path is None:
        st.error("Δεν βρέθηκε step6_compliant.py. Βάλε το αρχείο στον ίδιο φάκελο.")
        st.stop()

    with st.spinner("Τρέχουν τα Βήματα 1→6 ..."):
        with tempfile.TemporaryDirectory() as tmpd:
            tmpd = Path(tmpd)
            in_path = tmpd / "STEP1_input.xlsx"
            out_1_5 = tmpd / "STEP1_to_5_PER_SCENARIO_MIN.xlsx"
            out_1_6 = tmpd / "STEP1_to_6_PER_SCENARIO_MIN.xlsx"

            # write uploaded STEP1
            with open(in_path, "wb") as f:
                f.write(uploaded_step1.read())

            # import exporter
            exp = _import_by_path("exporter_min", exporter_path)

            # 1→5
            if hasattr(exp, "build_step1_4_per_scenario"):
                exp.build_step1_4_per_scenario(str(in_path), str(out_1_5), pick_step4="best")
            elif hasattr(exp, "build_step1_5_per_scenario"):
                # Σε περίπτωση που ονομάζεται έτσι
                exp.build_step1_5_per_scenario(str(in_path), str(out_1_5), pick_step4="best")
            else:
                st.error("Δεν βρέθηκε συνάρτηση build_step1_4_per_scenario στο exporter.")
                st.stop()

            # 6
            m6 = _import_by_path("step6_mod", step6_path)
            if hasattr(m6, "export_single_noaudit"):
                m6.export_single_noaudit(str(out_1_5), str(out_1_6))
            else:
                st.error("Στο step6_compliant.py δεν βρέθηκε export_single_noaudit(...).")
                st.stop()

            # provide download
            st.success("Έτοιμο το Βήμα 6!")
            st.download_button(
                "⬇️ Κατέβασε STEP1_to_6_PER_SCENARIO_MIN.xlsx",
                data=open(out_1_6, "rb").read(),
                file_name="STEP1_to_6_PER_SCENARIO_MIN.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

st.markdown("---")
st.markdown("## Κουμπί 2 — Τελική κατανομή (Εκτέλεση Βήματα 7–8)")
st.write("Ανέβασε το Excel του Βήματος 6 (το MIN από το κουμπί 1) και τα scripts **step7_fixed_final.py** και **step8.py** να υπάρχουν στον ίδιο φάκελο. Θα παραχθεί το τελικό αρχείο με τον νικητή και λίστες ονομάτων ανά τμήμα.")

uploaded_step6 = st.file_uploader("Ανέβασε STEP1_to_6_PER_SCENARIO_MIN.xlsx", type=["xlsx"], key="up2")
seed_val = st.number_input("Seed για tie-break (προαιρετικό)", value=42, step=1)
run_7_8 = st.button("🏁 Τελική κατανομή — Εκτέλεση Βήματα 7–8")

if run_7_8:
    if not uploaded_step6:
        st.error("Πρώτα ανέβασε το αρχείο του Βήματος 6.")
        st.stop()
    step7_path = _first_existing("step7_fixed_final.py")
    step8_path = _first_existing("step8.py")
    if step7_path is None or step8_path is None:
        st.error("Χρειάζονται στον ίδιο φάκελο τα αρχεία: step7_fixed_final.py και step8.py.")
        st.stop()

    with st.spinner("Τρέχουν τα Βήματα 7→8 ..."):
        with tempfile.TemporaryDirectory() as tmpd:
            tmpd = Path(tmpd)
            in_path = tmpd / "STEP1_to_6_PER_SCENARIO_MIN.xlsx"
            out_best = tmpd / "BEST_ONLY_EXPORT.xlsx"

            # write uploaded STEP6
            with open(in_path, "wb") as f:
                f.write(uploaded_step6.read())

            # import step8 and call public API (build_best_only_workbook)
            step8 = _import_by_path("step8_mod", step8_path)
            if hasattr(step8, "build_best_only_workbook"):
                step8.build_best_only_workbook(str(in_path), str(step7_path), str(out_best), seed=int(seed_val) if seed_val else None)
            else:
                st.error("Στο step8.py δεν βρέθηκε build_best_only_workbook(...).")
                st.stop()

            st.success("Έτοιμο το τελικό (Βήματα 7–8)!")
            st.download_button(
                "⬇️ Κατέβασε BEST_ONLY_EXPORT.xlsx",
                data=open(out_best, "rb").read(),
                file_name="BEST_ONLY_EXPORT.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

st.markdown("---")
st.info("Tip: Βάλε ΟΛΑ τα .py στον ίδιο φάκελο με το app. Το app **δεν αλλάζει** καμία λογική — απλώς καλεί τα δικά σου modules.")
