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

# Extraer fecha desde nombre de archivo
def extraer_fecha_de_nombre(nombre_archivo):
    patrones = [
        r'(\d{2})[-_](\d{2})[-_](\d{4})',        # 31-05-2025 o 31_05_2025
        r'(\d{4})[-_](\d{2})[-_](\d{2})',        # 2025-05-31 o 2025_05_31
        r'(\d{8})'                                 # 31052025 o 20250531
    ]
    for patron in patrones:
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
    return "Fecha no encontrada"

# Normalización Pv. Rgo.
def normalizar_pvrgo(valor):
    mapeo = {
        "CA": "Capital", "BAS": "Buenos Aires", "NEU": "Neuquén", "COR": "Córdoba",
        "SAL": "Salta", "MZA": "Mendoza", "RNE": "Río Negro", "AME": "América", "VIS": "Visa", "CBU": "CBU"
    }
    return mapeo.get(valor.strip(), valor.strip())

# Formato numérico compatible con Excel
def normalizar_numero(valor):
    return valor.replace(".", "").replace(",", ".")

# Extractor actualizado
def extraer_movimientos(texto, moneda, cod_prod, fecha_liq):
    datos = []
    patron = re.compile(
        r"^\s*\d+\s+(?P<poliza>\d{6})\s+\d+\s+(?P<asegurado>.+?)\s+"
        r"(?P<pvrgo>[A-Z]{2,4})\s+"
        r"(?P<cotizacion>[\d.,]+)\s+"
        r"(?P<premio>[\d.,]+)\s+"
        r"(?P<prima>[\d.,]+)\s+"
        r"[A-Z]{2,4}\s+"
        r"(?P<com_venta>[\d.,]+)\s+"
        r"(?P<com_cobranza>[\d.,]+)"
    )

    for linea in texto.splitlines():
        linea = linea.strip()
        m = patron.match(linea)
        if m:
            datos.append({
                "Código Productor": cod_prod,
                "Fecha de Liquidación": fecha_liq,
                "Moneda": moneda,
                "R. Póliza": m.group("poliza"),
                "Sup. Asegurado": m.group("asegurado").strip(),
                "Pv. Rgo.": normalizar_pvrgo(m.group("pvrgo")),
                "Cotización": normalizar_numero(m.group("cotizacion")),
                "Premio Cobrado": normalizar_numero(m.group("premio")),
                "Prima Proporc.": normalizar_numero(m.group("prima")),
                "F. de Pago": "",
                "Comisión Sistema por Venta": normalizar_numero(m.group("com_venta")),
                "Comisión por Cobranza": normalizar_numero(m.group("com_cobranza"))
            })
    return datos

# Procesamiento PDF
def procesar_pdf(pdf_file, nombre):
    cod_prod_match = re.search(r"(\d{6})", nombre)
    cod_prod = cod_prod_match.group(1) if cod_prod_match else "000000"
    fecha_liq = extraer_fecha_de_nombre(nombre)
    datos = []

    with pdfplumber.open(pdf_file) as pdf:
        for i, pagina in enumerate(pdf.pages, start=1):
            texto = pagina.extract_text()

            if not texto and OCR_DISPONIBLE:
                imagen = convert_from_bytes(pdf_file.getvalue(), first_page=i, last_page=i)[0]
                texto = pytesseract.image_to_string(imagen, lang="spa")

            with st.expander(f"📄 Texto extraído - Página {i}"):
                st.text(texto if texto else "⚠️ No se pudo extraer texto")

            moneda = "PESOS (ARG)"
            if "DOLARES" in (texto or "").upper():
                moneda = "DOLARES EEUU"

            movimientos = extraer_movimientos(texto or "", moneda, cod_prod, fecha_liq)
            datos.extend(movimientos)

    return datos

# Interfaz Streamlit
st.set_page_config(page_title="Liquidaciones PDF a Excel", layout="wide")
st.title("📄 Liquidaciones de Comisiones → Excel")
st.markdown("Subí uno o varios archivos PDF (escaneados o digitales) y descargá un Excel estructurado.")

# Vista según rol
rol_usuario = st.session_state["rol"]

if rol_usuario in ["admin", "editor"]:
    archivos = st.file_uploader("Seleccioná PDF(s)", type="pdf", accept_multiple_files=True)

    if archivos:
        todas_filas = []
        for archivo in archivos:
            st.info(f"Procesando {archivo.name}...")
            filas = procesar_pdf(BytesIO(archivo.read()), archivo.name)
            todas_filas.extend(filas)

        if todas_filas:
            columnas = [
                "Código Productor", "Fecha de Liquidación", "Moneda",
                "R. Póliza", "Sup. Asegurado", "Pv. Rgo.", "Cotización",
                "Premio Cobrado", "Prima Proporc.", "F. de Pago",
                "Comisión Sistema por Venta", "Comisión por Cobranza"
            ]
            df = pd.DataFrame(todas_filas, columns=columnas)
            st.success(f"✅ Se extrajeron {len(df)} movimientos.")
            st.dataframe(df)

            buffer = BytesIO()
            df.to_excel(buffer, index=False, engine="openpyxl")

            if rol_usuario == "admin":
                st.download_button(
                    label="📥 Descargar Excel",
                    data=buffer.getvalue(),
                    file_name="liquidaciones_convertidas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("⚠️ No se detectaron movimientos en los PDFs.")

elif rol_usuario == "lector":
    st.info("🔐 Estás en modo lector. No tenés permiso para subir archivos.")
