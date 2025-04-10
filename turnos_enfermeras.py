import pandas as pd
from datetime import datetime


def cargar_datos_excel(path, sheet, skip):
    df = pd.read_excel(path, sheet_name=sheet, skiprows=skip)
    df = df.dropna(axis=1, how='all')
    df.rename(columns={"NOMBRE Y APELLIDOS": "nombre"}, inplace=True)
    return df

def extraer_columnas_dias(df):
    return [col for col in df.columns if "2025-04" in str(col)]  # ESTO PUEDE DAR PROBLEMAS EN OTRO MES

def procesar_turnos(df, columnas_dias, turnos_validos):
    resultados = []
    for dia in columnas_dias:
        for _, fila in df.iterrows():
            turno = str(fila[dia]).strip()
            if turno in turnos_validos:
                resultados.append({
                    "fecha": str(dia)[:10],
                    "nombre": fila["nombre"],
                    "turno": turno
                })
    return pd.DataFrame(resultados)

def agrupar_turnos(df_resultados, orden_turnos):
    resumen = df_resultados.groupby(['fecha', 'turno']).agg(
        cantidad_enfermeras=('nombre', 'count'),
        enfermeras=('nombre', lambda x: ', '.join(sorted(x)))
    ).reset_index()

    resumen['turno'] = pd.Categorical(resumen['turno'], categories=orden_turnos, ordered=True)
    resumen = resumen.sort_values(['fecha', 'turno']).reset_index(drop=True)
    return resumen

def mostrar_turno_por_dia_y_tipo(resumen_turnos, fecha, turno, orden_turnos):
    if turno not in orden_turnos:
        print(f"Turno '{turno}' no es válido. Usa uno de: {', '.join(orden_turnos)}")
        return []

    resumen_turnos['fecha'] = pd.to_datetime(resumen_turnos['fecha']).dt.date
    filtro = (resumen_turnos['fecha'] == fecha) & (resumen_turnos['turno'] == turno)
    turno_df = resumen_turnos[filtro]

    if turno_df.empty:
        print(f"No hay datos para el {fecha} en el turno {turno}")
        return []
    else:
        enfermeras_str = turno_df.iloc[0]['enfermeras']
        cantidad = turno_df.iloc[0]['cantidad_enfermeras']
        print(f"\nTurno {turno} para el {fecha}: {cantidad} enfermeras")
        print(enfermeras_str)
        print('-' * 60)

        # Extraer IDs
        lista_ids = [int(nombre.split()[-1]) for nombre in enfermeras_str.split(', ')]
        return lista_ids


def main():
    excel_path = r"data\abril.xlsm" # EXTRAER
    sheet_name = 'Abril' # EXTRAER
    fila_inicio = 5 # EXTRAER
    turnos_validos = {'M', 'T', 'N', 'M;T', 'T;N', 'N;M'}
    orden_turnos = ['M', 'T', 'N', 'M;T', 'T;N', 'N;M']
    fecha_consulta = '2025-04-01' # EXTRAER
    turno_consulta = 'M' # EXTRAER
    pd.set_option('display.max_colwidth', None)

    df = cargar_datos_excel(excel_path, sheet_name, fila_inicio)

    columnas_dias = extraer_columnas_dias(df)
    df_resultados = procesar_turnos(df, columnas_dias, turnos_validos)
    resumen = agrupar_turnos(df_resultados, orden_turnos)

    fecha_consulta = datetime.strptime(fecha_consulta, "%Y-%m-%d").date()

    lista_enfermeras = mostrar_turno_por_dia_y_tipo(resumen, fecha_consulta, turno_consulta, orden_turnos)

    return fecha_consulta, turno_consulta, lista_enfermeras


if __name__ == "__main__":
    main()