import streamlit as st
import pdfplumber
import pandas as pd
import re
from io import BytesIO
from datetime import datetime
import hashlib

# --- Seguridad con múltiples niveles de acceso ---
USUARIOS = {
    "lucas": {"password": "clave123", "rol": "admin"},
    "juan": {"password": "sololectura", "rol": "lector"},
    "carla": {"password": "edita2024", "rol": "editor"}
}

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

if "logueado" not in st.session_state:
    st.session_state["logueado"] = False
    st.session_state["usuario"] = ""
    st.session_state["rol"] = ""

def login():
    with st.form("login"):
        st.subheader("🔒 Iniciar sesión")
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        ingresar = st.form_submit_button("Ingresar")

        if ingresar:
            if usuario in USUARIOS and password == USUARIOS[usuario]["password"]:
                st.session_state["logueado"] = True
                st.session_state["usuario"] = usuario
                st.session_state["rol"] = USUARIOS[usuario]["rol"]
                st.success(f"Bienvenido, {usuario} ({st.session_state['rol']})")
            else:
                st.error("❌ Usuario o contraseña incorrectos")

if not st.session_state["logueado"]:
    login()
    st.stop()

# OCR
try:
    from pdf2image import convert_from_bytes
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r"D:\\Aplicaciones\\Tesseract-OCR\\tesseract.exe"
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False

# Extraer fecha desde nombre o contenido del PDF

def extraer_fecha_de_nombre_o_contenido(nombre_archivo, contenido_pdf):
    patrones_nombre = [
        r'(\d{2})[-_](\d{2})[-_](\d{4})',
        r'(\d{4})[-_](\d{2})[-_](\d{2})',
        r'(\d{8})'
    ]
    for patron in patrones_nombre:
        match = re.search(patron, nombre_archivo)
        if match:
            try:
                if len(match.groups()) == 3:
                    g1, g2, g3 = match.groups()
                    if int(g1) > 31:
                        fecha = datetime.strptime(f"{g1}-{g2}-{g3}", "%Y-%m-%d")
                    else:
                        fecha = datetime.strptime(f"{g1}-{g2}-{g3}", "%d-%m-%Y")
                elif len(match.groups()) == 1:
                    g = match.group(1)
                    if g.startswith("20"):
                        fecha = datetime.strptime(g, "%Y%m%d")
                    else:
                        fecha = datetime.strptime(g, "%d%m%Y")
                return fecha.strftime("%d de %B, %Y").capitalize()
            except:
                continue

    match_contenido = re.search(r'LIQUIDACI[ÓO]N DE COMISIONES AL (\d{2})/(\d{2})/(\d{4})', contenido_pdf.upper())
    if match_contenido:
        try:
            dia, mes, anio = match_contenido.groups()
            fecha = datetime.strptime(f"{dia}-{mes}-{anio}", "%d-%m-%Y")
            return fecha.strftime("%d de %B, %Y").capitalize()
        except:
            pass

    st.warning("⚠️ No se encontró la fecha ni en el nombre del archivo ni en el contenido del PDF.")
    return "Fecha no encontrada"

# (Resto del código sin cambios)
