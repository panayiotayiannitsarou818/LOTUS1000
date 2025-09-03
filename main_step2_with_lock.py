#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Εκτέλεση βήματος 2 με κλείδωμα αποτελεσμάτων
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import sys

# Imports από τα existing modules
from step_2_zoiroi_idiaterotites_FIXED_v3_PATCHED import step2_apply_FIXED_v3
from step2_finalize import finalize_step2_assignments, validate_final_assignments, lock_step2_results


def load_excel_data(file_path: str, sheet_name: str = None) -> pd.DataFrame:
    """Φόρτωση Excel με error handling"""
    try:
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)
        print(f"✅ Φορτώθηκαν {len(df)} εγγραφές από {file_path}")
        return df
    except Exception as e:
        print(f"❌ Σφάλμα φόρτωσης: {e}")
        sys.exit(1)


def run_step2_with_lock(
    input_file: str,
    step1_column: str,
    output_dir: str = "output",
    max_scenarios: int = 3,
    sheet_name: str = None
) -> None:
    """
    Εκτελεί βήμα 2 και κλειδώνει τα αποτελέσματα.
    
    Args:
        input_file: Path του Excel/CSV αρχείου
        step1_column: Όνομα στήλης βήματος 1 (π.χ. "ΒΗΜΑ1_ΣΕΝΑΡΙΟ_1")
        output_dir: Φάκελος εξόδου
        max_scenarios: Μέγιστος αριθμός σεναρίων
        sheet_name: Όνομα sheet (αν Excel)
    """
    
    # Δημιουργία output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    # Φόρτωση δεδομένων
    print(f"📁 Φόρτωση από {input_file}")
    if input_file.endswith('.csv'):
        df = pd.read_csv(input_file)
    else:
        df = load_excel_data(input_file, sheet_name)
    
    print(f"📊 Βρέθηκαν στήλες: {list(df.columns)}")
    
    # Έλεγχος ύπαρξης step1 column
    if step1_column not in df.columns:
        print(f"❌ Η στήλη '{step1_column}' δεν βρέθηκε!")
        print(f"Διαθέσιμες στήλες: {list(df.columns)}")
        sys.exit(1)
    
    # Εκτέλεση βήματος 2
    print(f"\n🔄 Εκτέλεση βήματος 2 βάσει στήλης '{step1_column}'")
    scenarios = step2_apply_FIXED_v3(
        df, 
        step1_col_name=step1_column,
        max_results=max_scenarios
    )
    
    if not scenarios:
        print("❌ Δεν βρέθηκαν σενάρια!")
        sys.exit(1)
    
    print(f"✅ Βρέθηκαν {len(scenarios)} σενάρια")
    
    # Επεξεργασία κάθε σεναρίου
    for i, (scenario_name, scenario_df, metrics) in enumerate(scenarios, 1):
        print(f"\n📋 Σενάριο {i}: {scenario_name}")
        print(f"   Παιδαγωγικές συγκρούσεις: {metrics['ped_conflicts']}")
        print(f"   Σπασμένες φιλίες: {metrics['broken']}")
        print(f"   Συνολικό penalty: {metrics['penalty']}")
        
        # Εύρεση της στήλης βήματος 2
        step2_cols = [col for col in scenario_df.columns if col.startswith('ΒΗΜΑ2_')]
        if not step2_cols:
            print(f"⚠️  Δεν βρέθηκε στήλη ΒΗΜΑ2_ στο σενάριο {i}")
            continue
        
        step2_col = step2_cols[0]
        print(f"   Στήλη βήματος 2: {step2_col}")
        
        # Κλείδωμα αποτελεσμάτων
        print(f"🔒 Κλείδωμα σεναρίου {i}...")
        final_df, lock_stats = finalize_step2_assignments(scenario_df, step2_col)
        
        print(f"   Κλειδώθηκαν {lock_stats['newly_placed']} επιπλέον παιδιά")
        print(f"   Συνολικά τμήματα: {len(lock_stats['class_distribution'])}")
        
        # Validation
        final_col = [col for col in final_df.columns if col.startswith('ΤΕΛΙΚΟ_')][0]
        validation = validate_final_assignments(final_df, final_col)
        
        if validation['is_complete']:
            print(f"   ✅ ΌΛΑ τα παιδιά έχουν τμήμα!")
            print(f"   📊 Μεγέθη τμημάτων: {validation['min_class_size']}-{validation['max_class_size']}")
        else:
            print(f"   ❌ {validation['students_without_assignment']} παιδιά χωρίς τμήμα!")
        
        # Αποθήκευση
        output_file = Path(output_dir) / f"step2_locked_scenario_{i}.xlsx"
        final_df.to_excel(output_file, index=False)
        print(f"   💾 Αποθηκεύτηκε: {output_file}")
        
        # Αποθήκευση summary
        summary_file = Path(output_dir) / f"step2_summary_scenario_{i}.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"ΣΕΝΑΡΙΟ {i} - {scenario_name}\n")
            f.write("="*50 + "\n\n")
            f.write("ΜΕΤΡΙΚΕΣ ΒΗΜΑΤΟΣ 2:\n")
            f.write(f"- Παιδαγωγικές συγκρούσεις: {metrics['ped_conflicts']}\n")
            f.write(f"- Σπασμένες φιλίες: {metrics['broken']}\n")
            f.write(f"- Συνολικό penalty: {metrics['penalty']}\n\n")
            f.write("ΚΛΕΙΔΩΜΑ:\n")
            f.write(f"- Συνολικά παιδιά: {lock_stats['total_students']}\n")
            f.write(f"- Ήδη τοποθετημένα: {lock_stats['already_placed']}\n")
            f.write(f"- Νέες τοποθετήσεις: {lock_stats['newly_placed']}\n\n")
            f.write("ΚΑΤΑΝΟΜΗ ΤΜΗΜΑΤΩΝ:\n")
            for class_name, count in sorted(lock_stats['class_distribution'].items()):
                f.write(f"- {class_name}: {count} παιδιά\n")
        
        print(f"   📄 Summary: {summary_file}")


if __name__ == "__main__":
    # Παράδειγμα χρήσης
    if len(sys.argv) < 3:
        print("Χρήση: python main_step2_with_lock.py <input_file> <step1_column> [output_dir]")
        print("Παράδειγμα: python main_step2_with_lock.py data.xlsx ΒΗΜΑ1_ΣΕΝΑΡΙΟ_1 results")
        sys.exit(1)
    
    input_file = sys.argv[1]
    step1_column = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "output"
    
    run_step2_with_lock(
        input_file=input_file,
        step1_column=step1_column,
        output_dir=output_dir,
        max_scenarios=5
    )
