from itertools import permutations
from dateutil.relativedelta import relativedelta
import pandas as pd

def extract_and_assign_groups(groups):
    extracted_groups = {}
    group_counter = 1
    for control, group_dict in groups.items():
        for key, patient_list in group_dict.items():
            group_name = f"G{group_counter}"
            extracted_groups[group_name] = patient_list
            group_counter += 1
    return extracted_groups

def merge_controls(history):
    merged_history = {}
    for nurse, controls in history.items():
        merged_history[nurse] = controls['control_A'] + controls['control_B']
    return merged_history

def merge_historial_resume(historial_resume_a_b):
    # Comprobamos que las claves 'A' y 'B' están presentes en el diccionario
    if 'A' in historial_resume_a_b and 'B' in historial_resume_a_b:
        # Concatenamos los historiales de A y B
        print("Concatenando historiales de A y B")
        merged_historial_treatments = pd.concat([historial_resume_a_b['A'], historial_resume_a_b['B']], ignore_index=True)
        print(merged_historial_treatments)
        return merged_historial_treatments
    
    else:
        print("Error: Las claves 'A' y 'B' no están presentes en el diccionario.")
        return None


def get_patient_index(patients, patient_number):
    try:
        return patients.index(patient_number)
    except ValueError:
        return -1

def count_group_treatments(nurse_id, group, historial_past_treatments):
    count = 0
    for patient_id in group:
        tratamientos = historial_past_treatments[
            (historial_past_treatments['ID_ENF'] == nurse_id) &
            (historial_past_treatments['HABITACION'] == patient_id)
        ]
        count += tratamientos['NUMERO_TRATAMIENTOS'].sum()
    return int(count)


def calculate_cost(group, nurse_history, patients, nurse_id, historial_past_treatments, fecha_actual):
    cost = 0
    for patient_id in group:
        patient_index = get_patient_index(patients, patient_id)

        fila = historial_past_treatments[
            (historial_past_treatments['ID_ENF'] == nurse_id) &
            (historial_past_treatments['HABITACION'] == patient_id)
        ]        
        
        if not fila.empty:
            fecha_toma = pd.to_datetime(fila.iloc[0]['FECHA_TOMA_MÁS_RECIENTE'])
            diferencia = relativedelta(fecha_actual, fecha_toma)
            meses = diferencia.years * 12 + diferencia.months

            # Penalización por antigüedad del tratamiento
            if meses > 4:
                cost += 2  # Si el tratamiento fue hace más de 4 meses
            elif meses > 2:
                cost += 1  # Si el tratamiento fue hace más de 2 meses
            else:
                cost += 0  # Sin penalización si el tratamiento fue hace menos de 2 meses

        else:
            cost += 4  # Si el paciente no ha sido tratado por el enfermero (incluyendo penalización fecha), penalización máxima
        
    return cost

def create_branch_schema(nurses, groups, history, patients, historial_past_treatments, fecha_actual):
    all_assignments = []

    for perm in permutations(nurses):
        total_cost = 0
        total_treatments = 0
        assignment = {}
        
        for i, nurse in enumerate(perm):
            group_key = list(groups.keys())[i]
            group_values = list(groups.values())[i]
            cost = calculate_cost(group_values, history[nurse], patients, nurse, historial_past_treatments, fecha_actual)
            total_cost += cost

            treatments = count_group_treatments(nurse, group_values, historial_past_treatments)
            total_treatments += treatments
            
            assignment[group_key] = (nurse, cost, treatments)
        
        all_assignments.append((perm, assignment, total_cost, total_treatments))
    
    min_cost = min(a[2] for a in all_assignments)
    min_cost_assignments = [a for a in all_assignments if a[2] == min_cost]

    # PARA ENSEÑAR QUE ESTA FUNCIONANDO BIEN
    #if len(min_cost_assignments) > 1:
    #    print("EMPATE DE COSTE - mostrando... Las siguientes asignaciones empataron en coste:")
    #    for idx, assignment in enumerate(min_cost_assignments, 1):
    #        print(f"  Asignación {idx}:")
    #        for group, (nurse, cost, treatments) in assignment[1].items():
    #            print(f"    Grupo {group} → Enfermera {nurse} | Coste: {cost} | Tratamientos previos: {treatments}")
    #        print(f"    Coste total: {assignment[2]}, Tratamientos totales: {assignment[3]}")
    #else:
    #    print("No hubo empate de coste.")

    if len(min_cost_assignments) == 1:
        best_assignment = min_cost_assignments[0]
    else:
        print("EMPATE DE COSTE")
        best_assignment = max(min_cost_assignments, key=lambda x: x[3])

    best_perm, best_mapping, best_cost, best_treatments = best_assignment
    return best_perm, best_mapping, best_cost, best_treatments


def assign_nurses(distributed_rooms, nurses_list, historic, historial_resume_a_b, patients, fecha_actual):
    all_groups = extract_and_assign_groups(distributed_rooms)
    merged_historic = merge_controls(historic)
    historial_past_treatments = merge_historial_resume(historial_resume_a_b)
    patients = patients['control_A'] + patients['control_B']

    best_perm, best_mapping, best_cost, best_treatments = create_branch_schema(nurses_list, all_groups, merged_historic, patients, historial_past_treatments, fecha_actual)

    return best_mapping
    