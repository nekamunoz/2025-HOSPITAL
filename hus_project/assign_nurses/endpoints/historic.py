import pandas as pd
from datetime import timedelta

def extract_patient_bed(file_path):
    df = pd.read_excel(file_path)
    df_4thfloor = df[df['CAMA'].astype(str).str.startswith('4')]
    beds_and_patients = df_4thfloor[['CAMA', 'ID_PACIENTE']].values.tolist()
    beds_and_patients.sort(key=lambda x: (int(''.join(filter(str.isdigit, str(x[0])))), str(x[0])))
    patient_bed_mapping = {patient[1]: patient[0] for patient in beds_and_patients}
    control_a, control_b = {}, {}
    for patient_id, bed in patient_bed_mapping.items():
        bed_number = int(''.join(filter(str.isdigit, bed)))
        if bed_number < 431:
            control_a[patient_id] = bed
        else:
            control_b[patient_id] = bed
    return control_a, control_b

def extract_historic(file_path):
    try:
        historial_df = pd.read_excel(file_path)
        historial_df['ID_ENF'] = historial_df['ID_ENF'].fillna('').astype(str)
        historial_df['ID_ENF'] = historial_df['ID_ENF'].apply(
            lambda x: x.split('.')[0] if '.' in x and x.replace('.','').isdigit() else x
        )
        historial_df['FECHA_TOMA'] = pd.to_datetime(historial_df['FECHA_TOMA']).dt.date
        return historial_df
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None

def filter_last_6_months(historial_df, fecha_actual):
    fecha_limite = fecha_actual - timedelta(days=6*30)
    historial_df['FECHA_TOMA'] = pd.to_datetime(historial_df['FECHA_TOMA']).dt.date
    filtered_df = historial_df[
        (historial_df['FECHA_TOMA'] >= fecha_limite) &
        (historial_df['FECHA_TOMA'] <= fecha_actual)
    ]
    return filtered_df

def calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict):
    patients_in_a = len(control_a_dict)
    patients_in_b = len(control_b_dict)
    total_patients = patients_in_a + patients_in_b
    nurses_in_a = round((patients_in_a / total_patients) * total_nurses)
    nurses_in_b = total_nurses - nurses_in_a
    return {"control_A": nurses_in_a, "control_B": nurses_in_b}

def number_rooms_per_nurses_per_control(control_a_dict, control_b_dict, nurses_per_control, turno):
    if turno in ["M", "T"]:
        max_patients_per_nurse = 11
    elif turno == "N":
        max_patients_per_nurse = 17
    else:
        raise ValueError("Turno no válido. Debe ser 'M', 'T' o 'N'.")
    
    def dividir(control_dict, nurses):
        total = len(control_dict)
        base = total // nurses
        remainder = total % nurses
        return [base + (1 if i < remainder else 0) for i in range(nurses)]

    rooms_count_a = dividir(control_a_dict, nurses_per_control['control_A'])
    rooms_count_b = dividir(control_b_dict, nurses_per_control['control_B'])

    if any(count > max_patients_per_nurse for count in rooms_count_a + rooms_count_b):
        print("⚠️  Falta personal: Hay enfermeras con más pacientes del límite permitido.")

    return {"control_A": rooms_count_a, "control_B": rooms_count_b}

def treatment_historial(control_a_dict, control_b_dict, filtered_historial, enfermeras_turno):
    def proccess_historial(control_dict):
        filtered_nurse_data = filtered_historial[filtered_historial['ID_ENF'].isin(enfermeras_turno)]
        if len(filtered_nurse_data) == 0:
            print("❌ No se han encontrado enfermeras con los IDs proporcionados.")
        historial = filtered_historial[
            (filtered_historial['ID_PACIENTE'].isin(control_dict)) &
            (filtered_historial['ID_ENF'].isin(enfermeras_turno))].copy()
        resumen = historial.groupby(['ID_ENF', 'ID_PACIENTE']).agg(
            NUMERO_TRATAMIENTOS=('ID_ENF', 'count'),
            FECHA_TOMA_MÁS_RECIENTE=('FECHA_TOMA', 'max')).reset_index()

        resumen['HABITACION'] = resumen['ID_PACIENTE'].map(control_dict)

        resumen['HABITACION_ORDEN'] = resumen['HABITACION'].apply(
            lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
        resumen = resumen.sort_values(by='HABITACION_ORDEN').drop(columns=['HABITACION_ORDEN'])
        return resumen

    historial_a = proccess_historial(control_a_dict)
    historial_b = proccess_historial(control_b_dict)
    return {'control_A': historial_a, 'control_B': historial_b }

def get_historic(current_date, shift, shift_nurses, config):
    # Mapping of patients IDs to beds numbers for controls A and B
    control_a_dict, control_b_dict = extract_patient_bed(config['file_hosp'])

    # Get and filter complete historic data
    historic = extract_historic(config['file_historic'])
    filtered_historic = filter_last_6_months(historic, current_date)

    # Get rooms division based on the number of nurses
    total_nurses = len(shift_nurses)
    nurses_per_control = calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict)
    rooms_per_control = number_rooms_per_nurses_per_control(control_a_dict, control_b_dict, nurses_per_control, shift)

    # Generate summaries of treatments by nurse for both controls A and B
    historial_resume_a_b = treatment_historial(control_a_dict, control_b_dict, filtered_historic, shift_nurses)

    # Generate a list of occupied rooms for each control
    occupied_rooms_per_control = {"control_A": list(control_a_dict.values()),"control_B": list(control_b_dict.values())}

    return occupied_rooms_per_control, rooms_per_control, historial_resume_a_b





