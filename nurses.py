import pandas as pd
from datetime import datetime

def cargar_datos_excel(path, sheet, skip):
    try:
        df = pd.read_excel(path, sheet_name=sheet, skiprows=skip)
        df = df.dropna(axis=1, how='all')
        if "NOMBRE Y APELLIDOS" not in df.columns:
            raise ValueError("La columna 'NOMBRE Y APELLIDOS' no se encontró en la hoja")
        df.rename(columns={"NOMBRE Y APELLIDOS": "nombre"}, inplace=True)
        return df
    except FileNotFoundError:
        raise FileNotFoundError(f"El archivo {path} no se encontró")
    except ValueError as e:
        raise ValueError(f"Error al leer la hoja {sheet}: {e}")

def extraer_columnas_dias(df, fecha_consulta):
    # Extraer mes y año de la fecha de consulta (ej. "2025-06")
    month_year = fecha_consulta.strftime("%Y-%m")
    columnas = []
    for col in df.columns:
        try:
            # Intentar convertir el nombre de la columna a fecha
            fecha_col = pd.to_datetime(str(col), errors='coerce')
            if pd.isna(fecha_col):
                continue
            # Verificar si la columna pertenece al mes y año de fecha_consulta
            if fecha_col.strftime("%Y-%m") == month_year:
                columnas.append(col)
        except (ValueError, TypeError):
            continue
    if not columnas:
        raise ValueError(f"No se encontraron columnas de fechas para el mes {month_year}")
    return columnas

def procesar_turnos(df, columnas_dias, turnos_validos):
    resultados = []
    for dia in columnas_dias:
        temp = df[['nombre', dia]].copy()
        temp['fecha'] = str(dia)[:10]
        temp['turno'] = temp[dia].astype(str).str.strip()
        temp = temp[temp['turno'].isin(turnos_validos)][['fecha', 'nombre', 'turno']]
        resultados.append(temp)
    return pd.concat(resultados, ignore_index=True) if resultados else pd.DataFrame(columns=['fecha', 'nombre', 'turno'])

def agrupar_turnos(df_resultados, orden_turnos):
    if df_resultados.empty:
        return pd.DataFrame(columns=['fecha', 'turno', 'cantidad_enfermeras', 'enfermeras'])
    resumen = df_resultados.groupby(['fecha', 'turno']).agg(
        cantidad_enfermeras=('nombre', 'count'),
        enfermeras=('nombre', lambda x: ', '.join(sorted(x)))
    ).reset_index()
    resumen['turno'] = pd.Categorical(resumen['turno'], categories=orden_turnos, ordered=True)
    resumen = resumen.sort_values(['fecha', 'turno']).reset_index(drop=True)
    return resumen

def mostrar_turno_por_dia_y_tipo(resumen_turnos, fecha, turno, orden_turnos):
    if turno not in orden_turnos:
        raise ValueError(f"Turno '{turno}' no es válido. Usa uno de: {', '.join(orden_turnos)}")

    turno_map = {
        'M': ['M'], 'T': ['T'], 'N': ['N'],
        'M;T': ['M', 'T'], 'T;N': ['T', 'N'], 'N;M': ['N', 'M'],
        'M;N': ['M', 'N'], 'T;M': ['T', 'M'], 'N;T': ['N', 'T']
    }

    resumen_turnos['fecha'] = pd.to_datetime(resumen_turnos['fecha']).dt.date
    enfermeras_encontradas = set()
    for _, row in resumen_turnos[resumen_turnos['fecha'] == fecha].iterrows():
        turnos_del_dia = turno_map.get(row['turno'], [])
        if turno in turnos_del_dia:
            enfermeras = row['enfermeras'].split(', ')
            enfermeras_encontradas.update(enfermeras)

    if not enfermeras_encontradas:
        print(f"No hay datos para el {fecha} en el turno {turno}")
        return []

    lista_ids = []
    for nombre in enfermeras_encontradas:
        try:
            id_enfermera = int(nombre.split()[-1])
            lista_ids.append(id_enfermera)
        except (ValueError, IndexError):
            print(f"Advertencia: No se pudo extraer ID de '{nombre}'. Ignorando.")
    return sorted(lista_ids)

def get_nurses_shift(config):
    turnos_validos = {'M', 'T', 'N', 'M;T', 'T;N', 'N;M'}
    orden_turnos = ['M', 'T', 'N', 'M;T', 'T;N', 'N;M']
    pd.set_option('display.max_colwidth', None)

    # Mapa de meses a nombres de hojas (en español, ajusta si es necesario)
    meses_hojas = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    # Extraer mes de fecha_consulta para seleccionar la hoja
    fecha_consulta = datetime.strptime(config['fecha_consulta'], "%Y-%m-%d")
    mes = fecha_consulta.month
    try:
        sheet_name = meses_hojas[mes]
    except KeyError:
        raise ValueError(f"No se encontró una hoja para el mes {mes}")

    # Cargar datos desde la hoja correspondiente
    df = cargar_datos_excel(config['excel_path'], sheet_name, config['fila_inicio'])
    columnas_dias = extraer_columnas_dias(df, fecha_consulta)
    df_resultados = procesar_turnos(df, columnas_dias, turnos_validos)
    resumen = agrupar_turnos(df_resultados, orden_turnos)

    turno_consulta = config['turno_consulta']
    lista_enfermeras = mostrar_turno_por_dia_y_tipo(resumen, fecha_consulta.date(), turno_consulta, orden_turnos)

    return fecha_consulta.date(), turno_consulta, lista_enfermeras