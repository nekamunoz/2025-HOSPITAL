import pandas as pd
from datetime import datetime

def load_excel_data(path, sheet, skip_rows):
    """
    Load data from an Excel file and validate the presence of the 'NOMBRE Y APELLIDOS' column.
    """
    try:
        df = pd.read_excel(path, sheet_name=sheet, skiprows=skip_rows)
        df = df.dropna(axis=1, how='all')
        if "NOMBRE Y APELLIDOS" not in df.columns:
            raise ValueError("La columna 'NOMBRE Y APELLIDOS' no se encontró en la hoja")
        df.rename(columns={"NOMBRE Y APELLIDOS": "name"}, inplace=True)
        return df
    except FileNotFoundError:
        raise FileNotFoundError(f"El archivo {path} no se encontró")
    except ValueError as e:
        raise ValueError(f"Error al leer la hoja {sheet}: {e}")

def extract_day_columns(df, query_date):
    """
    Extract columns corresponding to the days of the specified month and year.
    """
    month_year = query_date.strftime("%Y-%m")
    columns = []
    for col in df.columns:
        try:
            col_date = pd.to_datetime(str(col), errors='coerce')
            if pd.isna(col_date):
                continue
            if col_date.strftime("%Y-%m") == month_year:
                columns.append(col)
        except (ValueError, TypeError):
            continue
    if not columns:
        raise ValueError(f"No se encontraron columnas de fechas para el mes {month_year}")
    return columns

def process_shifts(df, day_columns, valid_shifts):
    """
    Process shifts for each day, filtering by valid shifts.
    """
    results = []
    for day in day_columns:
        temp = df[['name', day]].copy()
        temp['date'] = str(day)[:10]
        temp['shift'] = temp[day].astype(str).str.strip()
        temp = temp[temp['shift'].isin(valid_shifts)][['date', 'name', 'shift']]
        results.append(temp)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame(columns=['date', 'name', 'shift'])

def group_shifts(df_results, shift_order):
    """
    Group shifts by date and shift type, summarizing nurse counts and names.
    """
    if df_results.empty:
        return pd.DataFrame(columns=['date', 'shift', 'nurse_count', 'nurses'])
    summary = df_results.groupby(['date', 'shift']).agg(
        nurse_count=('name', 'count'),
        nurses=('name', lambda x: ', '.join(sorted(x)))
    ).reset_index()
    summary['shift'] = pd.Categorical(summary['shift'], categories=shift_order, ordered=True)
    summary = summary.sort_values(['date', 'shift']).reset_index(drop=True)
    return summary

def display_shift_by_day_and_type(shift_summary, date, shift, shift_order):
    """
    Display nurses for a specific date and shift type, returning their IDs.
    """
    if shift not in shift_order:
        raise ValueError(f"Turno '{shift}' no es válido. Usa uno de: {', '.join(shift_order)}")

    shift_map = {
        'M': ['M'], 'T': ['T'], 'N': ['N'],
        'M;T': ['M', 'T'], 'T;N': ['T', 'N'], 'N;M': ['N', 'M'],
        'M;N': ['M', 'N'], 'T;M': ['T', 'M'], 'N;T': ['N', 'T']
    }

    shift_summary['date'] = pd.to_datetime(shift_summary['date']).dt.date
    found_nurses = set()
    for _, row in shift_summary[shift_summary['date'] == date].iterrows():
        day_shifts = shift_map.get(row['shift'], [])
        if shift in day_shifts:
            nurses = row['nurses'].split(', ')
            found_nurses.update(nurses)

    if not found_nurses:
        print(f"No hay datos para el {date} en el turno {shift}")
        return []

    nurse_ids = []
    for name in found_nurses:
        try:
            nurse_id = str(name.split()[-1])
            nurse_ids.append(nurse_id)
        except (ValueError, IndexError):
            print(f"Advertencia: No se pudo extraer ID de '{name}'. Ignorando.")
    return sorted(nurse_ids)

def get_nurse_shift(config):
    """
    Main function to retrieve nurses for a specific shift and date.
    """
    valid_shifts = {'M', 'T', 'N', 'M;T', 'T;N', 'N;M'}
    shift_order = ['M', 'T', 'N', 'M;T', 'T;N', 'N;M']
    pd.set_option('display.max_colwidth', None)

    month_sheets = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    query_date = datetime.strptime(config['query_date'], "%Y-%m-%d")
    month = query_date.month
    try:
        sheet_name = month_sheets[month]
    except KeyError:
        raise ValueError(f"No se encontró una hoja para el mes {month}")

    df = load_excel_data(config['excel_path'], sheet_name, config['start_row'])
    day_columns = extract_day_columns(df, query_date)
    shift_results = process_shifts(df, day_columns, valid_shifts)
    summary = group_shifts(shift_results, shift_order)

    query_shift = config['query_shift']
    nurse_list = display_shift_by_day_and_type(summary, query_date.date(), query_shift, shift_order)

    return query_date.date(), query_shift, nurse_list