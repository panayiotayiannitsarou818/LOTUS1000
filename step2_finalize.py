# -*- coding: utf-8 -*-
"""
Κλείδωμα αποτελεσμάτων βήματος 2 - Όλα τα παιδιά παίρνουν οριστικό τμήμα
"""
from typing import Optional, Tuple
import pandas as pd
import re
import math

def finalize_step2_assignments(
    df: pd.DataFrame, 
    step2_col: str,
    final_col_name: Optional[str] = None
) -> Tuple[pd.DataFrame, dict]:
    """
    Κλειδώνει τα αποτελέσματα του βήματος 2, εξασφαλίζοντας ότι ΌΛΑ τα παιδιά
    έχουν τμήμα (ακόμα και αυτά που ήταν unplaced).
    
    Args:
        df: DataFrame με αποτελέσματα βήματος 2
        step2_col: Όνομα στήλης αποτελεσμάτων βήματος 2 (π.χ. "ΒΗΜΑ2_ΣΕΝΑΡΙΟ_1")
        final_col_name: Όνομα τελικής στήλης (αν None, θα είναι "ΤΕΛΙΚΟ_ΤΜΗΜΑ")
    
    Returns:
        (DataFrame με τελική στήλη, metrics dict)
    """
    if final_col_name is None:
        # Εξάγουμε το ID από το step2_col για συνέπεια
        match = re.search(r'ΣΕΝΑΡΙΟ[_\s]*(\d+)', str(step2_col))
        scenario_id = match.group(1) if match else "1"
        final_col_name = f"ΤΕΛΙΚΟ_ΤΜΗΜΑ_ΣΕΝΑΡΙΟ_{scenario_id}"
    
    result_df = df.copy()
    
    # Ξεκινάμε με τα αποτελέσματα του βήματος 2
    result_df[final_col_name] = result_df[step2_col].copy()
    
    # Βρίσκουμε όσα ακόμα δεν έχουν τμήμα (NaN)
    unplaced_mask = pd.isna(result_df[final_col_name])
    unplaced_count = unplaced_mask.sum()
    
    if unplaced_count == 0:
        # Όλα ήδη τοποθετημένα
        stats = {
            "total_students": len(result_df),
            "already_placed": len(result_df),
            "newly_placed": 0,
            "class_distribution": result_df[final_col_name].value_counts().to_dict()
        }
        return result_df, stats
    
    # Υπολογίζουμε την κατανομή των υπαρχόντων τμημάτων
    placed_classes = result_df[~unplaced_mask][final_col_name].value_counts()
    available_classes = sorted(placed_classes.index.tolist())
    
    if not available_classes:
        # Αν δεν υπάρχουν καθόλου τμήματα, δημιουργούμε βάσει συνολικού αριθμού
        num_classes = max(2, math.ceil(len(result_df) / 25))
        available_classes = [f"Α{i+1}" for i in range(num_classes)]
        placed_classes = pd.Series([0] * len(available_classes), index=available_classes)
    
    # Στρατηγική: ισοκατανομή των unplaced στα υπάρχοντα τμήματα
    # Προτεραιότητα στα τμήματα με λιγότερα παιδιά
    unplaced_names = result_df[unplaced_mask]["ΟΝΟΜΑ"].tolist()
    
    # Ταξινομούμε τα τμήματα από λιγότερα προς περισσότερα μέλη
    classes_by_size = placed_classes.sort_values().index.tolist()
    
    # Κατανέμουμε τα unplaced παιδιά cyclically
    for i, student_name in enumerate(unplaced_names):
        target_class = classes_by_size[i % len(classes_by_size)]
        student_idx = result_df[result_df["ΟΝΟΜΑ"] == student_name].index[0]
        result_df.loc[student_idx, final_col_name] = target_class
    
    # Στατιστικά
    final_distribution = result_df[final_col_name].value_counts().to_dict()
    stats = {
        "total_students": len(result_df),
        "already_placed": len(result_df) - unplaced_count,
        "newly_placed": unplaced_count,
        "class_distribution": final_distribution,
        "min_class_size": min(final_distribution.values()) if final_distribution else 0,
        "max_class_size": max(final_distribution.values()) if final_distribution else 0
    }
    
    return result_df, stats


def validate_final_assignments(df: pd.DataFrame, final_col: str) -> dict:
    """
    Επικυρώνει ότι όλα τα παιδιά έχουν τμήμα και δίνει στατιστικά.
    
    Returns:
        Dict με validation metrics
    """
    validation = {
        "total_students": len(df),
        "students_with_assignment": (~pd.isna(df[final_col])).sum(),
        "students_without_assignment": pd.isna(df[final_col]).sum(),
        "is_complete": pd.isna(df[final_col]).sum() == 0,
        "unique_classes": df[final_col].nunique(),
        "class_list": sorted(df[final_col].dropna().unique().tolist())
    }
    
    if validation["is_complete"]:
        class_sizes = df[final_col].value_counts()
        validation.update({
            "min_class_size": class_sizes.min(),
            "max_class_size": class_sizes.max(),
            "avg_class_size": class_sizes.mean(),
            "class_size_std": class_sizes.std()
        })
    
    return validation


# Βοηθητική function για εύκολη χρήση
def lock_step2_results(df: pd.DataFrame, step2_column: str) -> pd.DataFrame:
    """
    Απλή wrapper function που κλειδώνει τα αποτελέσματα βήματος 2.
    
    Args:
        df: DataFrame με αποτελέσματα βήματος 2
        step2_column: Όνομα στήλης βήματος 2
    
    Returns:
        DataFrame με κλειδωμένη τελική στήλη
    """
    final_df, stats = finalize_step2_assignments(df, step2_column)
    
    print("=== ΚΛΕΙΔΩΜΑ ΒΗΜΑΤΟΣ 2 ===")
    print(f"Συνολικά παιδιά: {stats['total_students']}")
    print(f"Ήδη τοποθετημένα: {stats['already_placed']}")
    print(f"Νέες τοποθετήσεις: {stats['newly_placed']}")
    print(f"Κατανομή ανά τμήμα:")
    for class_name, count in sorted(stats['class_distribution'].items()):
        print(f"  {class_name}: {count} παιδιά")
    
    return final_df