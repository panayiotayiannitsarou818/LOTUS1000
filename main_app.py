#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Κύρια εφαρμογή Streamlit για την εκτέλεση των βημάτων κατανομής μαθητών
"""
import streamlit as st
import pandas as pd
import io
from pathlib import Path
from typing import Dict, Optional, Any
import sys

# Import των υπαρχόντων modules
try:
    from step1_immutable import create_immutable_step1, Step1Results
    from main_step2_with_lock import run_step2_with_lock
    from step4_corrected import run_step4_complete
    from step5_enhanced import apply_step5_to_all_scenarios
    from step6_compliant import apply_step6_to_step5_scenarios
    from step7_fixed_final import pick_best_scenario, score_to_dataframe
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής modules: {e}")
    st.stop()

st.set_page_config(
    page_title="Κατανομή Μαθητών σε Τμήματα",
    page_icon="🏫",
    layout="wide"
)

def load_excel_file(uploaded_file) -> pd.DataFrame:
    """Φόρτωση Excel αρχείου με error handling"""
    try:
        df = pd.read_excel(uploaded_file, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"Σφάλμα φόρτωσης αρχείου: {e}")
        return None

def validate_required_columns(df: pd.DataFrame) -> bool:
    """Έλεγχος απαραίτητων στηλών"""
    required_cols = ["ΟΝΟΜΑ", "ΦΥΛΟ", "ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ", "ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        st.error(f"Λείπουν απαραίτητες στήλες: {', '.join(missing_cols)}")
        st.info("Διαθέσιμες στήλες: " + ", ".join(df.columns.tolist()))
        return False
    return True

def export_to_excel(dataframes_dict: Dict[str, pd.DataFrame], filename: str = "ΑΝΑΛΥΤΙΚΑ_ΒΗΜΑΤΑ.xlsx") -> bytes:
    """Εξαγωγή πολλαπλών DataFrames σε Excel με διαφορετικά sheets"""
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dataframes_dict.items():
            # Περιορισμός μήκους ονόματος sheet στα 31 χαρακτήρες
            safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
            df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
    
    return output.getvalue()

def run_step1(df: pd.DataFrame, num_classes: Optional[int] = None) -> tuple:
    """Εκτέλεση Βήματος 1 - Immutable"""
    try:
        with st.spinner("Εκτέλεση Βήματος 1 (Παιδιά Εκπαιδευτικών)..."):
            df_step1, step1_results = create_immutable_step1(df, num_classes)
            st.success(f"Βήμα 1: Δημιουργήθηκαν {len(step1_results.scenarios)} σενάρια")
            return df_step1, step1_results
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 1: {e}")
        return None, None

def run_step2(df_step1: pd.DataFrame, step1_column: str) -> Optional[pd.DataFrame]:
    """Εκτέλεση Βήματος 2 - Ζωηροί & Ιδιαιτερότητες"""
    try:
        with st.spinner("Εκτέλεση Βήματος 2 (Ζωηροί & Ιδιαιτερότητες)..."):
            # Χρήση temporary directory για outputs
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                # Αποθήκευση προσωρινού αρχείου
                temp_file = Path(temp_dir) / "temp_step1.xlsx"
                df_step1.to_excel(temp_file, index=False)
                
                # Εκτέλεση step2
                run_step2_with_lock(
                    input_file=str(temp_file),
                    step1_column=step1_column,
                    output_dir=temp_dir,
                    max_scenarios=5
                )
                
                # Φόρτωση αποτελεσμάτων
                result_files = list(Path(temp_dir).glob("step2_locked_scenario_*.xlsx"))
                if result_files:
                    # Επιλογή πρώτου σεναρίου για απλότητα
                    df_step2 = pd.read_excel(result_files[0])
                    st.success(f"Βήμα 2: Επιτυχής ολοκλήρωση με {len(result_files)} σενάρια")
                    return df_step2
                else:
                    st.error("Δεν βρέθηκαν αποτελέσματα από το Βήμα 2")
                    return None
                    
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 2: {e}")
        return None

def run_step4(df_step3: pd.DataFrame, assigned_column: str = 'ΒΗΜΑ3_ΣΕΝΑΡΙΟ_1') -> Optional[pd.DataFrame]:
    """Εκτέλεση Βήματος 4 - Αμοιβαίες Φιλίες"""
    try:
        with st.spinner("Εκτέλεση Βήματος 4 (Αμοιβαίες Φιλίες)..."):
            df_step4 = run_step4_complete(df_step3, assigned_column)
            st.success("Βήμα 4: Επιτυχής ολοκλήρωση")
            return df_step4
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 4: {e}")
        return None

def run_step5(df_step4: pd.DataFrame, scenario_col: str) -> Optional[tuple]:
    """Εκτέλεση Βήματος 5 - Υπόλοιποι Μαθητές"""
    try:
        with st.spinner("Εκτέλεση Βήματος 5 (Υπόλοιποι Μαθητές)..."):
            # Για απλότητα, χρησιμοποιούμε ένα σενάριο
            scenarios_dict = {"ΣΕΝΑΡΙΟ_1": df_step4}
            
            best_df, best_penalty, best_scenario = apply_step5_to_all_scenarios(
                scenarios_dict, scenario_col
            )
            st.success(f"Βήμα 5: Επιλέχθηκε {best_scenario} με penalty score: {best_penalty}")
            return best_df, best_penalty
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 5: {e}")
        return None, None

def run_step6(df_step5: pd.DataFrame) -> Optional[Dict]:
    """Εκτέλεση Βήματος 6 - Τελικός Έλεγχος"""
    try:
        with st.spinner("Εκτέλεση Βήματος 6 (Τελικός Έλεγχος)..."):
            # Για απλότητα, χρησιμοποιούμε ένα σενάριο
            step5_outputs = {"ΣΕΝΑΡΙΟ_1": df_step5}
            
            results = apply_step6_to_step5_scenarios(step5_outputs)
            if "ΣΕΝΑΡΙΟ_1" in results:
                result = results["ΣΕΝΑΡΙΟ_1"]
                st.success(f"Βήμα 6: {result['summary']['status']} σε {result['summary']['iterations']} επαναλήψεις")
                return result
            else:
                st.error("Δεν βρέθηκαν αποτελέσματα από το Βήμα 6")
                return None
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 6: {e}")
        return None

def run_step7(df_step6: pd.DataFrame) -> Optional[Dict]:
    """Εκτέλεση Βήματος 7 - Τελικό Score"""
    try:
        with st.spinner("Εκτέλεση Βήματος 7 (Τελικό Score)..."):
            # Εύρεση στήλης σεναρίου
            scenario_cols = [col for col in df_step6.columns if col.startswith('ΒΗΜΑ6_ΣΕΝΑΡΙΟ_')]
            if not scenario_cols:
                scenario_cols = ['ΒΗΜΑ6_ΤΜΗΜΑ', 'ΤΜΗΜΑ']
                scenario_cols = [col for col in scenario_cols if col in df_step6.columns]
            
            if scenario_cols:
                result = pick_best_scenario(df_step6, scenario_cols[:1])  # Χρήση πρώτης διαθέσιμης
                scores_df = score_to_dataframe(df_step6, scenario_cols[:1])
                st.success("Βήμα 7: Υπολογισμός τελικού score ολοκληρώθηκε")
                return {"result": result, "scores": scores_df}
            else:
                st.error("Δεν βρέθηκαν κατάλληλες στήλες σεναρίων για το Βήμα 7")
                return None
                
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 7: {e}")
        return None

def main():
    """Κύρια συνάρτηση της εφαρμογής"""
    
    st.title("🏫 Κατανομή Μαθητών σε Τμήματα")
    st.markdown("---")
    
    # Sidebar για παραμέτρους
    with st.sidebar:
        st.header("⚙️ Παράμετροι")
        num_classes = st.number_input("Αριθμός Τμημάτων", min_value=2, max_value=10, value=None, 
                                    help="Αφήστε κενό για αυτόματο υπολογισμό")
        
        run_all_steps = st.checkbox("Εκτέλεση όλων των βημάτων", value=True)
    
    # Upload αρχείου
    st.header("📁 Φόρτωση Δεδομένων")
    uploaded_file = st.file_uploader(
        "Επιλέξτε Excel αρχείο με δεδομένα μαθητών",
        type=['xlsx', 'xls'],
        help="Το αρχείο πρέπει να περιέχει τις στήλες: ΟΝΟΜΑ, ΦΥΛΟ, ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ, ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ"
    )
    
    if uploaded_file is not None:
        # Φόρτωση και validation
        df_original = load_excel_file(uploaded_file)
        
        if df_original is not None and validate_required_columns(df_original):
            st.success(f"✅ Φορτώθηκαν {len(df_original)} εγγραφές")
            
            # Εμφάνιση preview
            with st.expander("👀 Προεπισκόπηση δεδομένων"):
                st.dataframe(df_original.head())
                st.info(f"Στήλες: {', '.join(df_original.columns.tolist())}")
            
            # Αποθήκευση στο session state
            if 'dataframes' not in st.session_state:
                st.session_state.dataframes = {}
            
            st.session_state.dataframes['ΑΡΧΙΚΑ_ΔΕΔΟΜΕΝΑ'] = df_original
            
            # Εκτέλεση βημάτων
            st.markdown("---")
            st.header("🔄 Εκτέλεση Βημάτων")
            
            if run_all_steps:
                # Αυτόματη εκτέλεση όλων των βημάτων
                if st.button("▶️ Εκτέλεση Όλων των Βημάτων", type="primary"):
                    
                    # Βήμα 1
                    df_step1, step1_results = run_step1(df_original, num_classes)
                    if df_step1 is not None:
                        st.session_state.dataframes['ΒΗΜΑ1_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step1
                        
                        # Βήμα 2 - χρήση πρώτου σεναρίου
                        step1_columns = [col for col in df_step1.columns if col.startswith('ΒΗΜΑ1_ΣΕΝΑΡΙΟ_')]
                        if step1_columns:
                            df_step2 = run_step2(df_step1, step1_columns[0])
                            if df_step2 is not None:
                                st.session_state.dataframes['ΒΗΜΑ2_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step2
                                
                                # Βήματα 3 (προς το παρόν χρησιμοποιούμε το ίδιο DataFrame)
                                df_step3 = df_step2  # Placeholder
                                st.session_state.dataframes['ΒΗΜΑ3_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step3
                                
                                # Βήμα 4
                                step2_columns = [col for col in df_step3.columns if col.startswith('ΒΗΜΑ2_ΣΕΝΑΡΙΟ_')]
                                if step2_columns:
                                    df_step4 = run_step4(df_step3, step2_columns[0])
                                    if df_step4 is not None:
                                        st.session_state.dataframes['ΒΗΜΑ4_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step4
                                        
                                        # Βήμα 5
                                        step4_columns = [col for col in df_step4.columns if col.startswith('ΒΗΜΑ4_ΣΕΝΑΡΙΟ_')]
                                        if step4_columns:
                                            df_step5, penalty5 = run_step5(df_step4, step4_columns[0])
                                            if df_step5 is not None:
                                                st.session_state.dataframes['ΒΗΜΑ5_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step5
                                                
                                                # Βήμα 6
                                                step6_result = run_step6(df_step5)
                                                if step6_result is not None:
                                                    df_step6 = step6_result['df']
                                                    st.session_state.dataframes['ΒΗΜΑ6_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step6
                                                    
                                                    # Βήμα 7
                                                    step7_result = run_step7(df_step6)
                                                    if step7_result is not None:
                                                        st.session_state.dataframes['ΒΗΜΑ7_SCORES'] = step7_result['scores']
                                                        st.session_state.dataframes['ΤΕΛΙΚΑ_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step6
                                                        
                                                        st.success("🎉 Όλα τα βήματα ολοκληρώθηκαν επιτυχώς!")
            else:
                # Μεμονωμένα βήματα (για debugging)
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("1️⃣ Βήμα 1"):
                        df_step1, step1_results = run_step1(df_original, num_classes)
                        if df_step1 is not None:
                            st.session_state.dataframes['ΒΗΜΑ1_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step1
                
                with col2:
                    if st.button("2️⃣ Βήμα 2") and 'ΒΗΜΑ1_ΑΠΟΤΕΛΕΣΜΑΤΑ' in st.session_state.dataframes:
                        df_step1 = st.session_state.dataframes['ΒΗΜΑ1_ΑΠΟΤΕΛΕΣΜΑΤΑ']
                        step1_columns = [col for col in df_step1.columns if col.startswith('ΒΗΜΑ1_ΣΕΝΑΡΙΟ_')]
                        if step1_columns:
                            df_step2 = run_step2(df_step1, step1_columns[0])
                            if df_step2 is not None:
                                st.session_state.dataframes['ΒΗΜΑ2_ΑΠΟΤΕΛΕΣΜΑΤΑ'] = df_step2
                
                with col3:
                    if st.button("3️⃣ Βήμα 3"):
                        st.info("Βήμα 3 θα προστεθεί σύντομα")
    
    # Εμφάνιση αποτελεσμάτων
    if 'dataframes' in st.session_state and st.session_state.dataframes:
        st.markdown("---")
        st.header("📊 Αποτελέσματα")
        
        # Tabs για κάθε βήμα
        tab_names = list(st.session_state.dataframes.keys())
        tabs = st.tabs(tab_names)
        
        for i, (name, df) in enumerate(st.session_state.dataframes.items()):
            with tabs[i]:
                st.subheader(f"📋 {name}")
                st.dataframe(df, use_container_width=True)
                st.info(f"Σύνολο: {len(df)} εγγραφές, Στήλες: {len(df.columns)}")
        
        # Κουμπί εξαγωγής
        st.markdown("---")
        st.header("💾 Εξαγωγή Αποτελεσμάτων")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            filename = st.text_input("Όνομα αρχείου", value="ΑΝΑΛΥΤΙΚΑ_ΒΗΜΑΤΑ.xlsx")
        
        with col2:
            if st.button("📥 Λήψη Excel", type="primary"):
                try:
                    excel_data = export_to_excel(st.session_state.dataframes, filename)
                    st.download_button(
                        label="⬇️ Κατέβασμα",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("Αρχείο προετοιμάστηκε για λήψη!")
                except Exception as e:
                    st.error(f"Σφάλμα εξαγωγής: {e}")

if __name__ == "__main__":
    main()
