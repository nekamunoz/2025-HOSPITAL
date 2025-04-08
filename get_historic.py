import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ==============================
# 1. FUNCIONES DE EXTRACCIÓN Y PROCESAMIENTO DE DATOS
# ==============================

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

def extract_historial(file_path):
    try:
        historial_df = pd.read_excel(file_path)
        historial_df['ID_ENF'] = historial_df['ID_ENF'].fillna(0).astype(int)
        historial_df['FECHA_TOMA'] = pd.to_datetime(historial_df['FECHA_TOMA'])
        return historial_df
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        return None

def filter_last_6_months(historial_df, fecha_actual):
    fecha_limite = fecha_actual - timedelta(days=6*30)
    filtered_df = historial_df[
        (historial_df['FECHA_TOMA'] >= fecha_limite) &
        (historial_df['FECHA_TOMA'] <= fecha_actual)
    ]
    return filtered_df

# ==============================
# 2. ASIGNACIÓN DE ENFERMERAS
# ==============================

def calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict):
    patients_in_a = len(control_a_dict)
    patients_in_b = len(control_b_dict)
    total_patients = patients_in_a + patients_in_b
    nurses_in_a = round((patients_in_a / total_patients) * total_nurses)
    nurses_in_b = total_nurses - nurses_in_a
    return nurses_in_a, nurses_in_b

def divide_rooms_by_nurses_count(control_a_dict, control_b_dict, nurses_in_a, nurses_in_b, turno):
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

    rooms_count_a = dividir(control_a_dict, nurses_in_a)
    rooms_count_b = dividir(control_b_dict, nurses_in_b)

    if any(count > max_patients_per_nurse for count in rooms_count_a + rooms_count_b):
        print("⚠️ Falta personal: Hay enfermeras con más pacientes del límite permitido.")

    return rooms_count_a, rooms_count_b

# ==============================
# 3. HISTORIAL Y TRATAMIENTOS
# ==============================

def generate_historials_by_control_and_nurses_with_rooms(filtered_historial, control_a_dict, control_b_dict, enfermeras_turno):
    def prepare(df, control_dict):
        df = df[df['ID_PACIENTE'].isin(control_dict.keys()) & df['ID_ENF'].isin(enfermeras_turno)].copy()
        df['HABITACION'] = df['ID_PACIENTE'].map(control_dict)
        df['HABITACION_ORDEN'] = df['HABITACION'].apply(lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
        return df.sort_values(by='HABITACION_ORDEN').drop(columns=['HABITACION_ORDEN'])

    return (
        prepare(filtered_historial, control_a_dict),
        prepare(filtered_historial, control_b_dict)
    )

def generate_treatment_count_by_nurse_and_patient_with_rooms_sorted(historial, control_dict):
    count = historial.groupby(['ID_ENF', 'ID_PACIENTE']).size().reset_index(name='NUMERO_TRATAMIENTOS')
    count['HABITACION'] = count['ID_PACIENTE'].map(control_dict)
    recent = historial.groupby(['ID_ENF', 'ID_PACIENTE'])['FECHA_TOMA'].max().reset_index(name='FECHA_TOMA_MÁS_RECIENTE')
    count = count.merge(recent, on=['ID_ENF', 'ID_PACIENTE'])
    count['HABITACION_ORDEN'] = count['HABITACION'].apply(lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
    return count.sort_values(by='HABITACION_ORDEN').drop(columns=['HABITACION_ORDEN'])

def generate_treatment_lists_by_nurse(treatment_count_a, treatment_count_b, control_a_dict, control_b_dict, enfermeras_turno):
    habitaciones_a = sorted(control_a_dict.values(), key=lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
    habitaciones_b = sorted(control_b_dict.values(), key=lambda x: (int(''.join(filter(str.isdigit, x))), ''.join(filter(str.isalpha, x))))
    treatment_lists = {}

    for enfermera in enfermeras_turno:
        def construir_lista(habs, control_dict, count_df):
            lista = []
            for hab in habs:
                paciente = next((k for k, v in control_dict.items() if v == hab), None)
                tratamientos = count_df[
                    (count_df['ID_ENF'] == enfermera) & (count_df['ID_PACIENTE'] == paciente)
                ]['NUMERO_TRATAMIENTOS']
                lista.append(int(tratamientos.iloc[0]) if not tratamientos.empty else 0)
            return lista

        treatment_lists[enfermera] = {
            'Control A': construir_lista(habitaciones_a, control_a_dict, treatment_count_a),
            'Control B': construir_lista(habitaciones_b, control_b_dict, treatment_count_b)
        }

    return treatment_lists

# ==============================
# 4. FUNCIÓN PRINCIPAL
# ==============================

def main(fecha_actual, turno, enfermeras_turno):
    # Rutas de archivos
    file_ingresados = r'C:\Users\Usuario\Desktop\UNI MARINA\hospi\2025-HOSPITAL\Ingresados.xlsx'
    file_historial = r'C:\Users\Usuario\Desktop\UNI MARINA\hospi\2025-HOSPITAL\hcoIngresos.xlsx'

    # Extracción de datos
    control_a_dict, control_b_dict = extract_patient_bed(file_ingresados)
    historial = extract_historial(file_historial)
    filtered_historial = filter_last_6_months(historial, fecha_actual)

    # Asignación de enfermeras
    total_nurses = len(enfermeras_turno)
    nurses_in_a, nurses_in_b = calculate_nurses_per_control(total_nurses, control_a_dict, control_b_dict)
    rooms_count_a, rooms_count_b = divide_rooms_by_nurses_count(control_a_dict, control_b_dict, nurses_in_a, nurses_in_b, turno)

    # Generar historiales filtrados con habitaciones
    control_a_historial, control_b_historial = generate_historials_by_control_and_nurses_with_rooms(
        filtered_historial, control_a_dict, control_b_dict, enfermeras_turno
    )

    # Generar conteo de tratamientos
    treatment_count_a = generate_treatment_count_by_nurse_and_patient_with_rooms_sorted(control_a_historial, control_a_dict)
    treatment_count_b = generate_treatment_count_by_nurse_and_patient_with_rooms_sorted(control_b_historial, control_b_dict)

    # Generar listas por enfermera
    treatment_lists = generate_treatment_lists_by_nurse(
        treatment_count_a, treatment_count_b, control_a_dict, control_b_dict, enfermeras_turno
    )

    # Mostrar resultados
    print(f"\n--- Distribución Habitaciones ---\nControl A: {rooms_count_a}\nControl B: {rooms_count_b}")
    for enf, datos in treatment_lists.items():
        print(f"\nEnfermera {enf}:")
        print(f"  Control A: {datos['Control A']}")
        print(f"  Control B: {datos['Control B']}")

# Ejecutar
if __name__ == "__main__":
    main()

# if __name__ == '__main__':
#     import argparse
#     parser = argparse.ArgumentParser(description="Asignar enfermeras a controles A y B.")
#     parser.add_argument('-i', type=str, help="Ruta del archivo Excel con los datos de pacientes y camas.")
#     args = parser.parse_args()
#     print(args.input)
#     main()
