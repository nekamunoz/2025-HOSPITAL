import turnos_enfermeras
import get_historic

def main():
    fecha_consulta, turno_consulta, lista_enfermeras = turnos_enfermeras.main()
    print(f"IDs de enfermeras para el {fecha_consulta} turno {turno_consulta}: {lista_enfermeras}")
    get_historic.main(fecha_consulta, turno_consulta, lista_enfermeras)


if __name__ == "__main__":
    main()
