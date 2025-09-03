#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ολοκληρωμένη εφαρμογή Streamlit για την εκτέλεση των βημάτων κατανομής μαθητών
Ενσωματώνει όλα τα βήματα 1-7 με πλήρη λειτουργικότητα
Διορθωμένη έκδοση με σωστή χρήση των modules
"""
import streamlit as st
import pandas as pd
import numpy as np
import io
import tempfile
import traceback
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
import sys
import re

# Import των υπαρχόντων modules με error handling
try:
    from step1_immutable import create_immutable_step1, Step1Results, validate_step1_immutability
    STEP1_AVAILABLE = True
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής step1_immutable: {e}")
    STEP1_AVAILABLE = False

try:
    from main_step2_with_lock import run_step2_with_lock
    STEP2_AVAILABLE = True
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής main_step2_with_lock: {e}")
    STEP2_AVAILABLE = False

try:
    from step3_amivaia_filia_FIXED import apply_step3_to_dataframe
    STEP3_AVAILABLE = True
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής step3_amivaia_filia_FIXED: {e}")
    STEP3_AVAILABLE = False

try:
    from step4_corrected import run_step4_complete
    STEP4_AVAILABLE = True
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής step4_corrected: {e}")
    STEP4_AVAILABLE = False

try:
    from step5_enhanced import apply_step5_to_all_scenarios
    STEP5_AVAILABLE = True
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής step5_enhanced: {e}")
    STEP5_AVAILABLE = False

try:
    from step6_compliant import apply_step6_to_step5_scenarios
    STEP6_AVAILABLE = True
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής step6_compliant: {e}")
    STEP6_AVAILABLE = False

try:
    from step7_fixed_final import pick_best_scenario, score_to_dataframe, score_one_scenario_auto
    STEP7_AVAILABLE = True
except ImportError as e:
    st.error(f"Σφάλμα εισαγωγής step7_fixed_final: {e}")
    STEP7_AVAILABLE = False

try:
    from statistics_generator import generate_statistics_table, export_statistics_to_excel
    STATS_AVAILABLE = True
except ImportError:
    STATS_AVAILABLE = False

st.set_page_config(
    page_title="Κατανομή Μαθητών σε Τμήματα",
    page_icon="🏫",
    layout="wide"
)

def init_session_state():
    """Αρχικοποίηση session state"""
    defaults = {
        'data': None,
        'current_step': 0,
        'results': {},
        'detailed_steps': {},
        'step1_results': None,
        'debug_mode': True,
        'processing_status': 'ready'
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def safe_load_data(uploaded_file) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
    """Ασφαλής φόρτωση και κανονικοποίηση δεδομένων"""
    try:
        if uploaded_file.name.endswith('.xlsx'):
            df = pd.read_excel(uploaded_file, engine='openpyxl')
        elif uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file, encoding='utf-8')
        else:
            return None, "Μη υποστηριζόμενο format αρχείου"
        
        # Debug info
        if st.session_state.debug_mode:
            st.write("**DEBUG - Αρχικές στήλες:**", list(df.columns))
            st.write("**DEBUG - Shape:**", df.shape)
        
        # Κανονικοποίηση στηλών
        rename_map = {}
        for col in df.columns:
            col_str = str(col).strip().upper()
            col_clean = col_str.replace(' ', '_').replace('-', '_')
            
            # Αναζήτηση με περισσότερες παραλλαγές
            if any(x in col_clean for x in ['ΟΝΟΜΑ', 'ONOMA', 'NAME', 'ΜΑΘΗΤΗΣ', 'ΜΑΘΗΤΡΙΑ', 'STUDENT']):
                rename_map[col] = 'ΟΝΟΜΑ'
            elif any(x in col_clean for x in ['ΦΥΛΟ', 'FYLO', 'GENDER', 'SEX']):
                rename_map[col] = 'ΦΥΛΟ'
            elif any(pattern in col_clean for pattern in ['ΓΝΩΣΗ', 'ΓΝΩΣΕΙΣ', 'ΕΛΛΗΝΙΚ', 'ELLINIK', 'GREEK']):
                rename_map[col] = 'ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ'
            elif any(pattern in col_clean for pattern in ['ΠΑΙΔΙ', 'PAIDI', 'ΕΚΠΑΙΔΕΥΤΙΚ', 'EKPEDEFTIK', 'TEACHER', 'ΔΑΣΚΑΛ']):
                rename_map[col] = 'ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ'
            elif any(x in col_clean for x in ['ΦΙΛΟΙ', 'FILOI', 'FRIEND']):
                rename_map[col] = 'ΦΙΛΟΙ'
            elif any(x in col_clean for x in ['ΖΩΗΡ', 'ZOIR', 'ACTIVE', 'ENERGY']):
                rename_map[col] = 'ΖΩΗΡΟΣ'
            elif any(x in col_clean for x in ['ΙΔΙΑΙΤΕΡΟΤΗΤ', 'IDIETEROTIT', 'SPECIAL']):
                rename_map[col] = 'ΙΔΙΑΙΤΕΡΟΤΗΤΑ'
            elif any(x in col_clean for x in ['ΣΥΓΚΡΟΥΣ', 'SYGKROUS', 'CONFLICT']):
                rename_map[col] = 'ΣΥΓΚΡΟΥΣΗ'
        
        if rename_map:
            df = df.rename(columns=rename_map)
            if st.session_state.debug_mode:
                st.write("**DEBUG - Rename map:**", rename_map)
        
        # Κανονικοποίηση τιμών
        if 'ΦΥΛΟ' in df.columns:
            df['ΦΥΛΟ'] = df['ΦΥΛΟ'].astype(str).str.strip().str.upper()
            gender_map = {
                'Α': 'Α', 'ΑΓΟΡΙ': 'Α', 'ΑΓΟΡΙΟΥ': 'Α', 'BOY': 'Α', 'MALE': 'Α', 'M': 'Α',
                'Κ': 'Κ', 'ΚΟΡΙΤΣΙ': 'Κ', 'ΚΟΡΙΤΣΙΟΥ': 'Κ', 'GIRL': 'Κ', 'FEMALE': 'Κ', 'F': 'Κ'
            }
            df['ΦΥΛΟ'] = df['ΦΥΛΟ'].map(gender_map).fillna('Α')
        
        # Κανονικοποίηση boolean στηλών
        bool_columns = ['ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ', 'ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ', 'ΖΩΗΡΟΣ', 'ΙΔΙΑΙΤΕΡΟΤΗΤΑ']
        for col in bool_columns:
            if col in df.columns:
                df[col] = df[col].astype(str).str.strip().str.upper()
                bool_map = {
                    'Ν': 'Ν', 'ΝΑΙ': 'Ν', 'YES': 'Ν', 'Y': 'Ν', '1': 'Ν', 'TRUE': 'Ν', 'T': 'Ν',
                    'Ο': 'Ο', 'ΟΧΙ': 'Ο', 'NO': 'Ο', 'N': 'Ο', '0': 'Ο', 'FALSE': 'Ο', 'F': 'Ο'
                }
                df[col] = df[col].map(bool_map).fillna('Ο')
        
        # Καθαρισμός ονομάτων
        if 'ΟΝΟΜΑ' in df.columns:
            df['ΟΝΟΜΑ'] = df['ΟΝΟΜΑ'].astype(str).str.strip()
            df = df[df['ΟΝΟΜΑ'] != ''].copy()
        
        return df, None
        
    except Exception as e:
        return None, f"Σφάλμα φόρτωσης: {str(e)}"

def validate_required_columns(df: pd.DataFrame, debug_mode: bool = False) -> Tuple[bool, List[str]]:
    """Έλεγχος απαραίτητων στηλών"""
    required_cols = ["ΟΝΟΜΑ", "ΦΥΛΟ", "ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ", "ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ"]
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if debug_mode:
        st.write(f"**DEBUG - Έλεγχος στηλών:**")
        st.write(f"Απαιτούμενες: {required_cols}")
        st.write(f"Διαθέσιμες: {list(df.columns)}")
        st.write(f"Λείπουν: {missing_cols}")
    
    return len(missing_cols) == 0, missing_cols

def display_basic_info(df: pd.DataFrame, debug_mode: bool = False):
    """Εμφάνιση βασικών πληροφοριών"""
    st.subheader("📊 Βασικές Πληροφορίες")
    
    total_students = len(df)
    boys_count = len(df[df['ΦΥΛΟ'] == 'Α']) if 'ΦΥΛΟ' in df.columns else 0
    girls_count = len(df[df['ΦΥΛΟ'] == 'Κ']) if 'ΦΥΛΟ' in df.columns else 0
    teachers_count = len(df[df['ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ'] == 'Ν']) if 'ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ' in df.columns else 0
    greek_count = len(df[df['ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ'] == 'Ν']) if 'ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ' in df.columns else 0
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Συνολικοί Μαθητές", total_students)
    with col2:
        st.metric("Αγόρια", boys_count)
    with col3:
        st.metric("Κορίτσια", girls_count)
    with col4:
        st.metric("Παιδιά Εκπαιδευτικών", teachers_count)
    
    if debug_mode:
        st.write(f"**DEBUG - Αναλυτικά:**")
        if 'ΦΥΛΟ' in df.columns:
            st.write(f"ΦΥΛΟ: Α={boys_count}, Κ={girls_count}")
            st.write(f"ΦΥΛΟ unique values: {df['ΦΥΛΟ'].unique()}")
        if 'ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ' in df.columns:
            teachers_list = df[df['ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ'] == 'Ν']['ΟΝΟΜΑ'].tolist() if 'ΟΝΟΜΑ' in df.columns else []
            st.write(f"Παιδιά εκπαιδευτικών: {teachers_count}")
            if teachers_list:
                st.write(f"Ονόματα: {', '.join(teachers_list[:5])}{'...' if len(teachers_list) > 5 else ''}")

def display_scenario_statistics(df: pd.DataFrame, scenario_col: str, scenario_name: str):
    """Εμφάνιση στατιστικών για ένα σενάριο"""
    try:
        if scenario_col not in df.columns:
            st.warning(f"Η στήλη {scenario_col} δεν βρέθηκε")
            return None
            
        df_assigned = df[df[scenario_col].notna()].copy()
        if len(df_assigned) == 0:
            st.warning("Δεν βρέθηκαν τοποθετημένοι μαθητές")
            return None
            
        st.subheader(f"📊 Στατιστικά {scenario_name}")
        
        # Χειροκίνητη δημιουργία στατιστικών για αξιοπιστία
        stats_data = []
        for tmima in sorted(df_assigned[scenario_col].unique()):
            subset = df_assigned[df_assigned[scenario_col] == tmima]
            
            boys = len(subset[subset['ΦΥΛΟ'] == 'Α']) if 'ΦΥΛΟ' in subset.columns else 0
            girls = len(subset[subset['ΦΥΛΟ'] == 'Κ']) if 'ΦΥΛΟ' in subset.columns else 0
            educators = len(subset[subset['ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ'] == 'Ν']) if 'ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ' in subset.columns else 0
            energetic = len(subset[subset['ΖΩΗΡΟΣ'] == 'Ν']) if 'ΖΩΗΡΟΣ' in subset.columns else 0
            special = len(subset[subset['ΙΔΙΑΙΤΕΡΟΤΗΤΑ'] == 'Ν']) if 'ΙΔΙΑΙΤΕΡΟΤΗΤΑ' in subset.columns else 0
            greek = len(subset[subset['ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ'] == 'Ν']) if 'ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ' in subset.columns else 0
            
            stats_data.append({
                'ΤΜΗΜΑ': tmima,
                'ΑΓΟΡΙΑ': boys,
                'ΚΟΡΙΤΣΙΑ': girls,
                'ΕΚΠΑΙΔΕΥΤΙΚΟΙ': educators,
                'ΖΩΗΡΟΙ': energetic,
                'ΙΔΙΑΙΤΕΡΟΤΗΤΑ': special,
                'ΓΝΩΣΗ ΕΛΛ.': greek,
                'ΣΥΝΟΛΟ': len(subset)
            })
        
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True)
        
        return stats_df
        
    except Exception as e:
        st.error(f"Σφάλμα στα στατιστικά {scenario_name}: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None

def run_step1(df: pd.DataFrame, num_classes: Optional[int] = None) -> Tuple[Optional[pd.DataFrame], Optional[Any]]:
    """Εκτέλεση Βήματος 1 - Immutable"""
    if not STEP1_AVAILABLE:
        st.error("Το module step1_immutable δεν είναι διαθέσιμο")
        return None, None
        
    try:
        st.subheader("🎯 Βήμα 1: Παιδιά Εκπαιδευτικών")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Εκτέλεση Βήματος 1...")
        progress_bar.progress(50)
        
        # Χρήση του immutable step1 module
        df_step1, step1_results = create_immutable_step1(df, num_classes)
        
        progress_bar.progress(100)
        status_text.text("✅ Βήμα 1 ολοκληρώθηκε επιτυχώς!")
        
        # Αποθήκευση στο session state
        st.session_state.step1_results = step1_results
        
        # Αποθήκευση αναλυτικών βημάτων
        for scenario in step1_results.scenarios:
            st.session_state.detailed_steps[scenario.column_name] = df_step1.copy()
        
        st.success(f"Δημιουργήθηκαν {len(step1_results.scenarios)} σενάρια")
        
        # Εμφάνιση στατιστικών
        for i, scenario in enumerate(step1_results.scenarios[:3], 1):  # Εμφάνιση 3 πρώτων
            with st.expander(f"📊 Στατιστικά {scenario.column_name}"):
                display_scenario_statistics(df_step1, scenario.column_name, f"Σενάριο {i}")
        
        return df_step1, step1_results
        
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 1: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None, None

def run_step2(df_step1: pd.DataFrame, step1_column: str) -> Optional[pd.DataFrame]:
    """Εκτέλεση Βήματος 2 - Ζωηροί & Ιδιαιτερότητες"""
    if not STEP2_AVAILABLE:
        st.error("Το module main_step2_with_lock δεν είναι διαθέσιμο")
        return None
        
    try:
        st.subheader("⚡ Βήμα 2: Ζωηροί & Ιδιαιτερότητες")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Εκτέλεση Βήματος 2...")
        progress_bar.progress(50)
        
        # Χρήση temporary directory για το step2
        with tempfile.TemporaryDirectory() as temp_dir:
            # Αποθήκευση προσωρινού αρχείου
            temp_file = Path(temp_dir) / "temp_step1.xlsx"
            df_step1.to_excel(temp_file, index=False)
            
            # Εκτέλεση step2
            run_step2_with_lock(
                input_file=str(temp_file),
                step1_column=step1_column,
                output_dir=temp_dir,
                max_scenarios=3
            )
            
            # Φόρτωση αποτελεσμάτων
            result_files = list(Path(temp_dir).glob("step2_locked_scenario_*.xlsx"))
            if result_files:
                # Επιλογή πρώτου σεναρίου
                df_step2 = pd.read_excel(result_files[0])
                
                # Αποθήκευση αναλυτικών βημάτων
                step2_cols = [col for col in df_step2.columns if col.startswith('ΒΗΜΑ2_') or col.startswith('ΤΕΛΙΚΟ_')]
                if step2_cols:
                    st.session_state.detailed_steps[step2_cols[0]] = df_step2.copy()
                
                progress_bar.progress(100)
                status_text.text("✅ Βήμα 2 ολοκληρώθηκε επιτυχώς!")
                
                st.success(f"Βήμα 2: Επιτυχής ολοκλήρωση με {len(result_files)} σενάρια")
                return df_step2
            else:
                st.error("Δεν βρέθηκαν αποτελέσματα από το Βήμα 2")
                return None
                
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 2: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None

def run_step3(df_step2: pd.DataFrame, num_classes: Optional[int] = None) -> Optional[pd.DataFrame]:
    """Εκτέλεση Βήματος 3 - Αμοιβαίες Φιλίες"""
    if not STEP3_AVAILABLE:
        st.error("Το module step3_amivaia_filia_FIXED δεν είναι διαθέσιμο")
        return None
        
    try:
        st.subheader("👫 Βήμα 3: Αμοιβαίες Φιλίες")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Εκτέλεση Βήματος 3...")
        progress_bar.progress(50)
        
        # Εφαρμογή Βήματος 3
        df_step3 = apply_step3_to_dataframe(df_step2, num_classes)
        
        # Αποθήκευση αναλυτικών βημάτων
        step3_cols = [col for col in df_step3.columns if col.startswith('ΒΗΜΑ3_')]
        for col in step3_cols:
            st.session_state.detailed_steps[col] = df_step3.copy()
        
        progress_bar.progress(100)
        status_text.text("✅ Βήμα 3 ολοκληρώθηκε επιτυχώς!")
        
        st.success("Βήμα 3: Επιτυχής ολοκλήρωση")
        return df_step3
        
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 3: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None

def run_step4(df_step3: pd.DataFrame, assigned_column: str) -> Optional[pd.DataFrame]:
    """Εκτέλεση Βήματος 4 - Φιλικές Ομάδες"""
    if not STEP4_AVAILABLE:
        st.error("Το module step4_corrected δεν είναι διαθέσιμο")
        return None
        
    try:
        st.subheader("👥 Βήμα 4: Φιλικές Ομάδες")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Εκτέλεση Βήματος 4...")
        progress_bar.progress(50)
        
        df_step4 = run_step4_complete(df_step3, assigned_column)
        
        # Αποθήκευση αναλυτικών βημάτων
        step4_cols = [col for col in df_step4.columns if col.startswith('ΒΗΜΑ4_')]
        for col in step4_cols:
            st.session_state.detailed_steps[col] = df_step4.copy()
        
        progress_bar.progress(100)
        status_text.text("✅ Βήμα 4 ολοκληρώθηκε επιτυχώς!")
        
        st.success("Βήμα 4: Επιτυχής ολοκλήρωση")
        return df_step4
        
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 4: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None

def run_step5(df_step4: pd.DataFrame, scenario_col: str) -> Tuple[Optional[pd.DataFrame], Optional[int]]:
    """Εκτέλεση Βήματος 5 - Υπόλοιποι Μαθητές"""
    if not STEP5_AVAILABLE:
        st.error("Το module step5_enhanced δεν είναι διαθέσιμο")
        return None, None
        
    try:
        st.subheader("🏁 Βήμα 5: Υπόλοιποι Μαθητές")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Εκτέλεση Βήματος 5...")
        progress_bar.progress(50)
        
        # Χρήση ενός σεναρίου για απλότητα
        scenarios_dict = {"ΣΕΝΑΡΙΟ_1": df_step4}
        
        best_df, best_penalty, best_scenario = apply_step5_to_all_scenarios(
            scenarios_dict, scenario_col
        )
        
        # Αποθήκευση αναλυτικών βημάτων
        step5_cols = [col for col in best_df.columns if col.startswith('ΒΗΜΑ5_')]
        for col in step5_cols:
            st.session_state.detailed_steps[col] = best_df.copy()
        
        progress_bar.progress(100)
        status_text.text("✅ Βήμα 5 ολοκληρώθηκε επιτυχώς!")
        
        st.success(f"Βήμα 5: Επιλέχθηκε {best_scenario} με penalty score: {best_penalty}")
        return best_df, best_penalty
        
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 5: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None, None

def run_step6(df_step5: pd.DataFrame) -> Optional[Dict]:
    """Εκτέλεση Βήματος 6 - Τελικός Έλεγχος"""
    if not STEP6_AVAILABLE:
        st.error("Το module step6_compliant δεν είναι διαθέσιμο")
        return None
        
    try:
        st.subheader("🔍 Βήμα 6: Τελικός Έλεγχος")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Εκτέλεση Βήματος 6...")
        progress_bar.progress(50)
        
        # Χρήση ενός σεναρίου για απλότητα
        step5_outputs = {"ΣΕΝΑΡΙΟ_1": df_step5}
        
        results = apply_step6_to_step5_scenarios(step5_outputs)
        
        if "ΣΕΝΑΡΙΟ_1" in results:
            result = results["ΣΕΝΑΡΙΟ_1"]
            
            # Αποθήκευση αναλυτικών βημάτων
            df_step6 = result['df']
            step6_cols = [col for col in df_step6.columns if col.startswith('ΒΗΜΑ6_')]
            for col in step6_cols:
                st.session_state.detailed_steps[col] = df_step6.copy()
            
            progress_bar.progress(100)
            status_text.text("✅ Βήμα 6 ολοκληρώθηκε επιτυχώς!")
            
            summary = result.get('summary', {})
            status = summary.get('status', 'Completed')
            iterations = summary.get('iterations', 0)
            st.success(f"Βήμα 6: {status} σε {iterations} επαναλήψεις")
            return result
        else:
            st.error("Δεν βρέθηκαν αποτελέσματα από το Βήμα 6")
            return None
            
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 6: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None

def run_step7(df_step6: pd.DataFrame) -> Optional[Dict]:
    """Εκτέλεση Βήματος 7 - Τελικό Score"""
    if not STEP7_AVAILABLE:
        st.error("Το module step7_fixed_final δεν είναι διαθέσιμο")
        return None
        
    try:
        st.subheader("🏆 Βήμα 7: Τελικό Score")
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Εκτέλεση Βήματος 7...")
        progress_bar.progress(50)
        
        # Εύρεση στήλης σεναρίου
        scenario_cols = [col for col in df_step6.columns if col.startswith('ΒΗΜΑ6_')]
        if not scenario_cols:
            scenario_cols = ['ΒΗΜΑ6_ΤΜΗΜΑ', 'ΤΜΗΜΑ']
            scenario_cols = [col for col in scenario_cols if col in df_step6.columns]
        
        if scenario_cols:
            result = pick_best_scenario(df_step6, scenario_cols[:1])
            scores_df = score_to_dataframe(df_step6, scenario_cols[:1])
            
            progress_bar.progress(100)
            status_text.text("✅ Βήμα 7 ολοκληρώθηκε επιτυχώς!")
            
            st.success("Βήμα 7: Υπολογισμός τελικού score ολοκληρώθηκε")
            return {"result": result, "scores": scores_df}
        else:
            st.error("Δεν βρέθηκαν κατάλληλες στήλες σεναρίων για το Βήμα 7")
            return None
            
    except Exception as e:
        st.error(f"Σφάλμα στο Βήμα 7: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None

def create_detailed_steps_workbook():
    """Δημιουργία Excel workbook με όλα τα αναλυτικά βήματα"""
    try:
        excel_buffer = io.BytesIO()
        
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # Ταξινόμηση των βημάτων για σωστή σειρά
            step_order = ['ΒΗΜΑ1', 'ΒΗΜΑ2', 'ΒΗΜΑ3', 'ΒΗΜΑ4', 'ΒΗΜΑ5', 'ΒΗΜΑ6']
            
            sheets_written = 0
            
            for step in step_order:
                sheets_for_step = []
                for sheet_name, df in st.session_state.detailed_steps.items():
                    if step in sheet_name:
                        sheets_for_step.append((sheet_name, df))
                
                # Ταξινόμηση ανά σενάριο
                sheets_for_step.sort(key=lambda x: x[0])
                
                for sheet_name, df in sheets_for_step:
                    # Περιορισμός μήκους ονόματος sheet (Excel limit)
                    safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                    df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
                    sheets_written += 1
            
            # Προσθήκη summary αν υπάρχουν results
            if 'final_results' in st.session_state.results:
                summary_data = []
                for name, result in st.session_state.results['final_results'].items():
                    if isinstance(result, dict) and 'score' in result:
                        summary_data.append({
                            'Σενάριο': name,
                            'Score': result.get('score', 'N/A'),
                            'Status': result.get('status', 'Completed')
                        })
                
                if summary_data:
                    summary_df = pd.DataFrame(summary_data)
                    summary_df.to_excel(writer, sheet_name='ΣΥΝΟΨΗ', index=False)
                    sheets_written += 1
        
        excel_buffer.seek(0)
        st.success(f"Δημιουργήθηκαν {sheets_written} sheets με αναλυτικά βήματα")
        return excel_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Σφάλμα στη δημιουργία αναλυτικών βημάτων: {e}")
        if st.session_state.debug_mode:
            st.code(traceback.format_exc())
        return None

def export_to_excel(dataframes_dict: Dict[str, pd.DataFrame], filename: str = "ΑΝΑΛΥΤΙΚΑ_ΒΗΜΑΤΑ.xlsx") -> bytes:
    """Εξαγωγή πολλαπλών DataFrames σε Excel με διαφορετικά sheets"""
    output = io.BytesIO()
    
    try:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for sheet_name, df in dataframes_dict.items():
                # Περιορισμός μήκους ονόματος sheet
                safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
    except ImportError:
        try:
            # Fallback σε xlsxwriter
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                for sheet_name, df in dataframes_dict.items():
                    safe_sheet_name = sheet_name[:31] if len(sheet_name) > 31 else sheet_name
                    df.to_excel(writer, sheet_name=safe_sheet_name, index=False)
        except ImportError:
            st.warning("Δεν βρέθηκε Excel engine. Εξαγωγή σε CSV format.")
            import zipfile
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w') as zip_file:
                for sheet_name, df in dataframes_dict.items():
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False, encoding='utf-8')
                    zip_file.writestr(f"{sheet_name}.csv", csv_buffer.getvalue())
            return output.getvalue()
    
    return output.getvalue()

def main():
    """Κύρια συνάρτηση της εφαρμογής"""
    
    init_session_state()
    
    st.title("🏫 Κατανομή Μαθητών σε Τμήματα")
    st.markdown("*Ολοκληρωμένο σύστημα με όλα τα 7 βήματα*")
    st.markdown("---")
    
    # Sidebar για παραμέτρους
    with st.sidebar:
        st.header("⚙️ Παράμετροι")
        
        # Debug mode toggle
        debug_mode = st.checkbox("🔧 Debug Mode", 
                               value=st.session_state.debug_mode,
                               help="Εμφάνιση debug πληροφοριών")
        st.session_state.debug_mode = debug_mode
        
        num_classes = st.number_input("Αριθμός Τμημάτων", 
                                    min_value=2, max_value=10, 
                                    value=None,
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
        if st.session_state.data is None:
            with st.spinner("Φόρτωση και επεξεργασία αρχείου..."):
                df_original, error = safe_load_data(uploaded_file)
                if error:
                    st.error(f"❌ {error}")
                    return
                st.session_state.data = df_original
        
        df_original = st.session_state.data
        
        if df_original is not None:
            # Validation στηλών
            is_valid, missing_cols = validate_required_columns(df_original, debug_mode)
            
            if not is_valid:
                st.error(f"❌ Λείπουν απαραίτητες στήλες: {', '.join(missing_cols)}")
                if debug_mode:
                    st.info("Διαθέσιμες στήλες: " + ", ".join(df_original.columns.tolist()))
                return
            
            st.success(f"✅ Φορτώθηκαν {len(df_original)} εγγραφές")
            
            # Εμφάνιση βασικών στοιχείων
            display_basic_info(df_original, debug_mode)
            
            # Εμφάνιση preview
            with st.expander("👀 Προεπισκόπηση δεδομένων"):
                st.dataframe(df_original.head())
                st.info(f"Στήλες: {', '.join(df_original.columns.tolist())}")
            
            # Αρχικοποίηση detailed_steps με τα αρχικά δεδομένα
            if 'ΑΡΧΙΚΑ_ΔΕΔΟΜΕΝΑ' not in st.session_state.detailed_steps:
                st.session_state.detailed_steps['ΑΡΧΙΚΑ_ΔΕΔΟΜΕΝΑ'] = df_original
            
            # Εκτέλεση βημάτων
            st.markdown("---")
            st.header("🔄 Εκτέλεση Βημάτων")
            
            if run_all_steps:
                # Αυτόματη εκτέλεση όλων των βημάτων
                if st.button("▶️ Εκτέλεση Όλων των Βημάτων", type="primary"):
                    st.session_state.processing_status = 'running'
                    
                    try:
                        current_df = df_original
                        
                        # Βήμα 1
                        with st.status("Βήμα 1: Παιδιά Εκπαιδευτικών", expanded=True) as status:
                            df_step1, step1_results = run_step1(current_df, num_classes)
                            if df_step1 is not None:
                                current_df = df_step1
                                st.session_state.results['step1'] = {'df': df_step1, 'results': step1_results}
                                status.update(label="✅ Βήμα 1 ολοκληρώθηκε", state="complete")
                            else:
                                status.update(label="❌ Βήμα 1 απέτυχε", state="error")
                                st.stop()
                        
                        # Βήμα 2
                        with st.status("Βήμα 2: Ζωηροί & Ιδιαιτερότητες", expanded=True) as status:
                            step1_columns = [col for col in current_df.columns if col.startswith('ΒΗΜΑ1_ΣΕΝΑΡΙΟ_')]
                            if step1_columns:
                                df_step2 = run_step2(current_df, step1_columns[0])
                                if df_step2 is not None:
                                    current_df = df_step2
                                    st.session_state.results['step2'] = {'df': df_step2}
                                    status.update(label="✅ Βήμα 2 ολοκληρώθηκε", state="complete")
                                else:
                                    status.update(label="❌ Βήμα 2 απέτυχε", state="error")
                                    st.stop()
                            else:
                                status.update(label="⚠️ Βήμα 2 παραλείφθηκε", state="complete")
                        
                        # Βήμα 3
                        with st.status("Βήμα 3: Αμοιβαίες Φιλίες", expanded=True) as status:
                            df_step3 = run_step3(current_df, num_classes)
                            if df_step3 is not None:
                                current_df = df_step3
                                st.session_state.results['step3'] = {'df': df_step3}
                                status.update(label="✅ Βήμα 3 ολοκληρώθηκε", state="complete")
                            else:
                                status.update(label="⚠️ Βήμα 3 παραλείφθηκε", state="complete")
                        
                        # Βήμα 4
                        with st.status("Βήμα 4: Φιλικές Ομάδες", expanded=True) as status:
                            step3_columns = [col for col in current_df.columns if col.startswith('ΒΗΜΑ3_')]
                            if not step3_columns:
                                step3_columns = [col for col in current_df.columns if col.startswith('ΒΗΜΑ2_')]
                            if not step3_columns:
                                step3_columns = [col for col in current_df.columns if col.startswith('ΒΗΜΑ1_')]
                            
                            if step3_columns:
                                df_step4 = run_step4(current_df, step3_columns[0])
                                if df_step4 is not None:
                                    current_df = df_step4
                                    st.session_state.results['step4'] = {'df': df_step4}
                                    status.update(label="✅ Βήμα 4 ολοκληρώθηκε", state="complete")
                                else:
                                    status.update(label="⚠️ Βήμα 4 παραλείφθηκε", state="complete")
                            else:
                                status.update(label="⚠️ Βήμα 4 παραλείφθηκε", state="complete")
                        
                        # Βήμα 5
                        with st.status("Βήμα 5: Υπόλοιποι Μαθητές", expanded=True) as status:
                            step4_columns = [col for col in current_df.columns if col.startswith('ΒΗΜΑ4_')]
                            if not step4_columns:
                                step4_columns = [col for col in current_df.columns if col.startswith('ΒΗΜΑ3_')]
                            if not step4_columns:
                                step4_columns = [col for col in current_df.columns if col.startswith('ΒΗΜΑ2_')]
                            
                            if step4_columns:
                                df_step5, penalty5 = run_step5(current_df, step4_columns[0])
                                if df_step5 is not None:
                                    current_df = df_step5
                                    st.session_state.results['step5'] = {'df': df_step5, 'penalty': penalty5}
                                    status.update(label="✅ Βήμα 5 ολοκληρώθηκε", state="complete")
                                else:
                                    status.update(label="⚠️ Βήμα 5 παραλείφθηκε", state="complete")
                            else:
                                status.update(label="⚠️ Βήμα 5 παραλείφθηκε", state="complete")
                        
                        # Βήμα 6
                        with st.status("Βήμα 6: Τελικός Έλεγχος", expanded=True) as status:
                            step6_result = run_step6(current_df)
                            if step6_result is not None:
                                df_step6 = step6_result.get('df', current_df)
                                current_df = df_step6
                                st.session_state.results['step6'] = step6_result
                                status.update(label="✅ Βήμα 6 ολοκληρώθηκε", state="complete")
                            else:
                                status.update(label="⚠️ Βήμα 6 παραλείφθηκε", state="complete")
                        
                        # Βήμα 7
                        with st.status("Βήμα 7: Τελικό Score", expanded=True) as status:
                            step7_result = run_step7(current_df)
                            if step7_result is not None:
                                st.session_state.results['step7'] = step7_result
                                st.session_state.results['final_df'] = current_df
                                status.update(label="✅ Βήμα 7 ολοκληρώθηκε", state="complete")
                            else:
                                status.update(label="⚠️ Βήμα 7 παραλείφθηκε", state="complete")
                        
                        st.session_state.processing_status = 'completed'
                        st.balloons()
                        st.success("🎉 Όλα τα βήματα ολοκληρώθηκan επιτυχώς!")
                        
                    except Exception as e:
                        st.session_state.processing_status = 'error'
                        st.error(f"Σφάλμα κατά την εκτέλεση: {e}")
                        if debug_mode:
                            st.code(traceback.format_exc())
            
            else:
                # Μεμονωμένα βήματα (για debugging)
                st.info("Μεμονωμένη εκτέλεση βημάτων ενεργοποιημένη")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("1️⃣ Βήμα 1"):
                        df_step1, step1_results = run_step1(df_original, num_classes)
                        if df_step1 is not None:
                            st.session_state.results['step1'] = {'df': df_step1, 'results': step1_results}
                
                with col2:
                    if st.button("2️⃣ Βήμα 2") and 'step1' in st.session_state.results:
                        df_step1 = st.session_state.results['step1']['df']
                        step1_columns = [col for col in df_step1.columns if col.startswith('ΒΗΜΑ1_ΣΕΝΑΡΙΟ_')]
                        if step1_columns:
                            df_step2 = run_step2(df_step1, step1_columns[0])
                            if df_step2 is not None:
                                st.session_state.results['step2'] = {'df': df_step2}
                
                with col3:
                    if st.button("3️⃣ Βήμα 3") and 'step2' in st.session_state.results:
                        df_step2 = st.session_state.results['step2']['df']
                        df_step3 = run_step3(df_step2, num_classes)
                        if df_step3 is not None:
                            st.session_state.results['step3'] = {'df': df_step3}
    
    # Εμφάνιση αποτελεσμάτων
    if st.session_state.results and st.session_state.processing_status == 'completed':
        st.markdown("---")
        st.header("📊 Αποτελέσματα")
        
        # Tabs για κάθε βήμα
        available_steps = list(st.session_state.results.keys())
        if available_steps:
            tabs = st.tabs([f"Βήμα {i+1}" for i in range(len(available_steps))])
            
            for i, step_name in enumerate(available_steps):
                with tabs[i]:
                    step_data = st.session_state.results[step_name]
                    if isinstance(step_data, dict) and 'df' in step_data:
                        df_step = step_data['df']
                        st.subheader(f"📋 {step_name.upper()}")
                        st.dataframe(df_step, use_container_width=True)
                        st.info(f"Σύνολο: {len(df_step)} εγγραφές, Στήλες: {len(df_step.columns)}")
        
        # Τελικά στατιστικά
        if 'final_df' in st.session_state.results:
            st.header("🏆 Τελικά Στατιστικά")
            final_df = st.session_state.results['final_df']
            
            # Εύρεση τελικής στήλης τμήματος
            final_col = None
            for col in ['ΒΗΜΑ6_ΤΜΗΜΑ', 'ΤΜΗΜΑ_ΜΕΤΑ_ΒΗΜΑ6', 'ΤΜΗΜΑ']:
                if col in final_df.columns:
                    final_col = col
                    break
            
            if final_col:
                display_scenario_statistics(final_df, final_col, "Τελικό Αποτέλεσμα")
        
        # Κουμπί εξαγωγής
        st.markdown("---")
        st.header("💾 Εξαγωγή Αποτελεσμάτων")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            filename = st.text_input("Όνομα αρχείου", value="ΑΝΑΛΥΤΙΚΑ_ΒΗΜΑΤΑ.xlsx")
        
        with col2:
            if st.button("📥 Λήψη Excel", type="primary"):
                try:
                    excel_data = export_to_excel(st.session_state.detailed_steps, filename)
                    st.download_button(
                        label="⬇️ Κατέβασμα",
                        data=excel_data,
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                    st.success("Αρχείο προετοιμάστηκε για λήψη!")
                except Exception as e:
                    st.error(f"Σφάλμα εξαγωγής: {e}")
        
        # Αναλυτικά βήματα
        if st.button("📋 Αναλυτικά Βήματα (VIMA6 Format)"):
            detailed_excel = create_detailed_steps_workbook()
            if detailed_excel:
                st.download_button(
                    label="⬇️ Λήψη Αναλυτικών Βημάτων",
                    data=detailed_excel,
                    file_name="VIMA6_ΑΝΑΛΥΤΙΚΑ_ΒΗΜΑΤΑ.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="detailed_download"
                )
        
        # Reset
        if st.button("🔄 Επαναφορά", type="secondary"):
            # Διατήρηση μόνο των βασικών keys
            keys_to_keep = ['debug_mode']
            for key in list(st.session_state.keys()):
                if key not in keys_to_keep:
                    del st.session_state[key]
            st.rerun()
    
    else:
        st.info("👆 Παρακαλώ ανεβάστε ένα αρχείο Excel για να ξεκινήσετε")
        
        # Οδηγίες χρήσης
        with st.expander("📖 Οδηγίες Χρήσης"):
            st.markdown("""
            ### Απαιτούμενες Στήλες:
            - **ΟΝΟΜΑ**: Ονοματεπώνυμο μαθητή
            - **ΦΥΛΟ**: Α (Αγόρι) ή Κ (Κορίτσι)
            - **ΚΑΛΗ_ΓΝΩΣΗ_ΕΛΛΗΝΙΚΩΝ**: Ν (Ναι) ή Ο (Όχι)
            - **ΠΑΙΔΙ_ΕΚΠΑΙΔΕΥΤΙΚΟΥ**: Ν (Ναι) ή Ο (Όχι)
            
            ### Προαιρετικές Στήλες:
            - **ΦΙΛΟΙ**: Λίστα φίλων
            - **ΖΩΗΡΟΣ**: Ν/Ο
            - **ΙΔΙΑΙΤΕΡΟΤΗΤΑ**: Ν/Ο
            - **ΣΥΓΚΡΟΥΣΗ**: Λίστα συγκρουόμενων
            
            ### Βήματα Επεξεργασίας:
            1. **Βήμα 1**: Κατανομή παιδιών εκπαιδευτικών
            2. **Βήμα 2**: Ζωηροί & Ιδιαιτερότητες  
            3. **Βήμα 3**: Αμοιβαίες φιλίες
            4. **Βήμα 4**: Φιλικές ομάδες
            5. **Βήμα 5**: Υπόλοιποι μαθητές
            6. **Βήμα 6**: Τελικός έλεγχος
            7. **Βήμα 7**: Υπολογισμός score
            """)

if __name__ == "__main__":
    main()
