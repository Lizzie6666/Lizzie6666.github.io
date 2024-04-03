import streamlit as st
from datetime import datetime, timedelta
import numpy as np
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
import io
import base64

# Función para calcular el factor de interés
def calcular_factor_interes(TEA, días):
    return ((1 + TEA) ** (días / 360)) - 1

def calcular_tasa_diaria_seguro(SDm):
    tasa_diaria_seguro = ((1 + SDm / 100) ** (1 / 30)) - 1
    return tasa_diaria_seguro

def calcular_suma_anual_tasas(tasa_interes_diaria, tasa_seguro_diaria):
    suma_anual_tasas = ((1 + tasa_interes_diaria) * (1 + tasa_seguro_diaria)) ** 360 - 1
    return suma_anual_tasas

def calcular_valor_futuro(principal, factor_interes, días_totales):
    valor_futuro = principal * ((1 + factor_interes) ** (días_totales / 360))
    return valor_futuro

def generar_cronograma_pagos(principal, fecha_desembolso, TEA, SDm, comision, días_totales, num_pagos):
    # Convertir TEA y SDm a tasas diarias efectivas
    tasa_interes_diaria = calcular_factor_interes(TEA, 1)
    tasa_seguro_diaria = calcular_tasa_diaria_seguro(SDm)

    # Calcular el factor de interés para el total de días
    factor_interes_total = calcular_factor_interes(TEA, días_totales)

    # Calcular el valor futuro
    valor_futuro = calcular_valor_futuro(principal, factor_interes_total, días_totales)

    # Calcular el valor y cronograma de pagos
    cronograma_pagos = []
    saldo_principal = principal
    días_en_mes = 30  # Suponiendo que cada mes tiene 30 días para simplificar

    for num_pago in range(1, num_pagos + 1):
        # Calcular días desde el desembolso
        fecha_pago = fecha_desembolso + timedelta(days=días_en_mes * num_pago)
        días_desde_desembolso = (fecha_pago - fecha_desembolso).days

        # Calcular interés para el mes actual
        factor_interes_actual = calcular_factor_interes(TEA, días_desde_desembolso)
        interés_pago = saldo_principal * factor_interes_actual

        # Calcular pago de seguro
        seguro_pago = saldo_principal * tasa_seguro_diaria * días_en_mes

        # Calcular amortización
        if num_pago < num_pagos:
            # Calcular los factores de interés para los pagos restantes
            factores_interés = [calcular_factor_interes(TEA, días_totales - (días_en_mes * i)) for i in range(num_pago, num_pagos)]
            amortización = (valor_futuro / np.sum(factores_interés)) - interés_pago - seguro_pago - comision
            # Asegurar que la amortización no sea negativa y redondear para evitar problemas de precisión
            amortización = max(round(amortización, 2), 0)
        else:
            # Manejar último pago para cubrir saldo restante exactamente
            amortización = saldo_principal

        pago_total = amortización + interés_pago + seguro_pago + comision

        # Actualizar el saldo principal
        saldo_principal += amortización

        # Agregar información del pago al cronograma
        cronograma_pagos.append({
            'No.': num_pago,
            'Fecha de Pago': fecha_pago,
            'Principal': principal,
            'Amortización': amortización,
            'Interés': interés_pago,
            'Seguro': seguro_pago,
            'Comisión': comision,
            'Pago Total': pago_total
        })

    return cronograma_pagos


def generar_pdf(cronograma):
    # Crear un buffer para contener el PDF
    buffer = io.BytesIO()

    # Crear documento PDF
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Definir estilos
    estilos = getSampleStyleSheet()
    estilo = estilos["Normal"]
    estilo.alignment = 1

    # Crear datos de la tabla
    datos_tabla = []
    datos_tabla.append(['No.', 'Fecha de Pago', 'Saldo Principal', 'Amortización', 'Interés', 'Seguro', 'Comisión', 'Pago Total'])
    for pago in cronograma:
        datos_tabla.append([pago['No.'], pago['Fecha de Pago'], round(pago['Principal'], 2), round(pago['Amortización'], 2), round(pago['Interés'], 2), round(pago['Seguro'], 2), round(pago['Comisión'], 2), round(pago['Pago Total'], 2)])

    # Crear tabla
    tabla = Table(datos_tabla, repeatRows=1)

    # Estilo de la tabla
    estilo_tabla = TableStyle([('BACKGROUND', (0,0), (-1,0), colors.yellowgreen),
                              ('TEXTCOLOR', (0,0), (-1,0), colors.black),
                              ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                              ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                              ('BOTTOMPADDING', (0,0), (-1,0), 12),
                              ('BACKGROUND', (0,1), (-1,-1), colors.beige),
                              ('GRID', (0,0), (-1,-1), 1, colors.black)])
    tabla.setStyle(estilo_tabla)

    # Agregar tabla al PDF
    doc.build([Paragraph("Cronograma de Pagos", estilo), tabla])

    # Obtener PDF en bytes
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def obtener_enlace_descarga(data, filename):
    """Genera un enlace de descarga para los datos dados."""
    b64 = base64.b64encode(data).decode()
    return f'<a href="data:application/pdf;base64,{b64}" download="{filename}">Haz clic aquí para descargar el {filename}</a>'

def principal():
    st.title("Calculadora de Pagos de Préstamos")

    # Crear campos de entrada para el usuario
    principal = st.number_input("Monto Principal (D):", min_value=0.0, value=10000.00, step=100.0)
    fecha_desembolso = st.date_input("Fecha de Desembolso:")
    TEA = st.number_input("Tasa Efectiva Anual (TEA) %:", min_value=0.0, value=25.00, step=0.01)
    SDm = st.number_input("Tasa de Seguro Mensual (SDm) %:", min_value=0.0, value=0.056, step=0.001)
    comision = st.number_input("Comisión (C):", min_value=0.0, value=9.00, step=0.01)
    num_pagos = st.number_input("Plazo en Meses:", min_value=1, value=12, step=1)

    # Botón para realizar el cálculo
    if st.button("Calcular Pagos"):
        # Manejar errores si es necesario
        try:
            # Convertir la fecha de desembolso a datetime
            fecha_desembolso = datetime.combine(fecha_desembolso, datetime.min.time())

            # Generar el cronograma de pagos
            cronograma = generar_cronograma_pagos(
                principal=principal,
                fecha_desembolso=fecha_desembolso,
                TEA=TEA / 100,  # Convertir a porcentaje
                SDm=SDm / 100,  # Convertir a porcentaje
                comision=comision,
                días_totales=365,  # Suponer año no bisiesto
                num_pagos=int(num_pagos)
            )

            # Mostrar el cronograma de pagos
            st.write("Cronograma de Pagos")
            st.table(cronograma)

            # Generar el archivo PDF
            pdf_data = generar_pdf(cronograma)

            # Mostrar enlace de descarga
            st.markdown(obtener_enlace_descarga(pdf_data, "Cronograma de Pagos.pdf"), unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

# Llamar a la función principal
if __name__ == "__main__":
    principal()
