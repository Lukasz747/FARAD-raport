import streamlit as st
import pandas as pd
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from io import BytesIO

# --- KONFIGURACJA ---
st.set_page_config(page_title="FARAD - System Protokołów", page_icon="⚡", layout="wide")
PRIMARY_COLOR = "#003366"

# CSS - Wąski sidebar i style
st.markdown(f"""
    <style>
    /* TŁO APLIKACJI */
    .stApp {{ background-color: #f9f9f9; }}
    
    /* NAGŁÓWKI OGÓLNE (Dla głównej części) */
    h1, h2, h3 {{ color: {PRIMARY_COLOR} !important; }}
    
    /* --- WYMUSZENIE KOLORU ETYKIET (GŁÓWNA CZĘŚĆ) --- */
    /* Używamy koloru #262730 dla tekstu etykiet w głównej części */
    div[data-testid="stWidgetLabel"] *,
    label,
    label *,
    div[data-testid="stMarkdownContainer"] p {{
        color: #262730 !important;
    }}
    /* -------------------------------- */

    /* --- POPRAWKA KOLORÓW W SIDEBARZE --- */
    /* Wymuszenie białego koloru dla wszystkich tekstów i nagłówków TYLKO wewnątrz sidebara */
    /* Nadpisuje to poprzednie reguły, dzięki czemu tekst jest widoczny na ciemnym tle */
    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] p {{
        color: #FFFFFF !important;
    }}
    /* ------------------------------------ */

    /* ZWĘŻENIE SIDEBARA */
    section[data-testid="stSidebar"] {{
        width: 200px !important;
        min-width: 200px !important;
        max-width: 200px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# CSS - Wąski sidebar i style
st.markdown(f"""
    <style>
    .stApp {{ background-color: #f9f9f9; }}
    h1, h2, h3 {{ color: {PRIMARY_COLOR}; }}
    
    /* ZWĘŻENIE SIDEBARA */
    section[data-testid="stSidebar"] {{
        width: 200px !important;
        min-width: 200px !important;
        max-width: 200px !important;
    }}
    </style>
    """, unsafe_allow_html=True)

# --- OBSŁUGA CZCIONEK OFFLINE ---
HAS_POLISH_FONT = False

def register_fonts_offline():
    global HAS_POLISH_FONT
    font_name = "font.ttf"
    if os.path.exists(font_name):
        try:
            pdfmetrics.registerFont(TTFont('CustomFont', font_name))
            pdfmetrics.registerFont(TTFont('CustomFont-Bold', font_name)) 
            HAS_POLISH_FONT = True
            return 'CustomFont'
        except:
            pass
    HAS_POLISH_FONT = False
    return 'Helvetica'

FONT_NAME = register_fonts_offline()
FONT_NAME_BOLD = 'CustomFont-Bold' if HAS_POLISH_FONT else 'Helvetica-Bold'

def clean_text(text):
    if HAS_POLISH_FONT: return str(text)
    replacements = {
        'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
        'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z'
    }
    text = str(text)
    for k, v in replacements.items(): text = text.replace(k, v)
    return text

# --- GENERATOR PDF ---
class EICR_PDF:
    def __init__(self, buffer, data):
        self.buffer = buffer
        self.data = data
        self.doc = SimpleDocTemplate(
            self.buffer, pagesize=A4, 
            rightMargin=10*mm, leftMargin=10*mm, topMargin=10*mm, bottomMargin=10*mm
        )
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        # 1. Nagłówek Główny
        self.style_header = ParagraphStyle(
            'FaradHeader', parent=self.styles['Heading1'], fontName=FONT_NAME_BOLD, 
            fontSize=14, textColor=colors.HexColor(PRIMARY_COLOR), spaceAfter=5
        )
        # 2. Podtytuły sekcji (Biały tekst na granatowym tle)
        self.style_subheader = ParagraphStyle(
            'FaradSub', parent=self.styles['Heading2'], fontName=FONT_NAME_BOLD, 
            fontSize=10, textColor=colors.white, backColor=colors.HexColor(PRIMARY_COLOR),
            leading=14, spaceBefore=6, spaceAfter=0, borderPadding=2
        )
        # 3. Etykiety w tabelach (Bold)
        self.style_label = ParagraphStyle(
            'FaradLabel', parent=self.styles['Normal'], fontName=FONT_NAME_BOLD, fontSize=8, leading=10
        )
        # 4. Wartości w tabelach
        self.style_value = ParagraphStyle(
            'FaradValue', parent=self.styles['Normal'], fontName=FONT_NAME, fontSize=8, leading=10
        )
        # 5. Mały tekst (np. listy kontrolne)
        self.style_small = ParagraphStyle(
            'FaradSmall', parent=self.styles['Normal'], fontName=FONT_NAME, fontSize=7, leading=9
        )
        # 6. Normalny tekst (Przywrócony - naprawia błąd)
        self.style_normal = ParagraphStyle(
            'FaradNormal', parent=self.styles['Normal'], fontName=FONT_NAME, fontSize=9, leading=11
        )

    def generate(self):
        elements = []

        # 1. LOGO I NAGŁÓWEK
        logo_path = "logo.png"
        logo_img = clean_text("[BRAK LOGO]")
        if os.path.exists(logo_path):
            try:
                utils_img = ImageReader(logo_path)
                iw, ih = utils_img.getSize()
                aspect = ih / float(iw)
                target_width = 40*mm
                logo_img = Image(logo_path, width=target_width, height=target_width * aspect)
            except: pass

        t_head = Table([[logo_img, Paragraph(f"<b>{clean_text('PROTOKÓŁ BADAŃ INSTALACJI ELEKTRYCZNEJ')}</b><br/>{clean_text('zgodny z PN-HD 60364-6')}", self.style_header)]], colWidths=[50*mm, 140*mm])
        t_head.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('ALIGN', (1,0), (1,0), 'RIGHT')]))
        elements.append(t_head)
        elements.append(Spacer(1, 2*mm))

        # 2. DANE ZLECENIA
        meta = self.data['meta']
        info_data = [
            [Paragraph(f"<b>{clean_text('ZLECENIODAWCA:')}</b>", self.style_label), Paragraph(clean_text(meta['klient']), self.style_value),
             Paragraph(f"<b>{clean_text('OBIEKT:')}</b>", self.style_label), Paragraph(clean_text(meta['obiekt']), self.style_value)],
            [Paragraph(f"<b>{clean_text('DATA BADANIA:')}</b>", self.style_label), Paragraph(str(meta['data']), self.style_value),
             Paragraph(f"<b>{clean_text('PROTOKÓŁ NR:')}</b>", self.style_label), Paragraph(clean_text(meta['nr_protokolu']), self.style_value)]
        ]
        t_info = Table(info_data, colWidths=[30*mm, 65*mm, 30*mm, 65*mm])
        t_info.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (0,-1), colors.HexColor("#f0f0f0")),
            ('BACKGROUND', (2,0), (2,-1), colors.HexColor("#f0f0f0")),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_info)
        elements.append(Spacer(1, 2*mm))

        # 3. PRZYRZĄD POMIAROWY
        dev = self.data['device']
        meter_text = f"<b>Użyty przyrząd:</b> {clean_text(dev['nazwa'])} | <b>Producent:</b> {clean_text(dev['producent'])} | <b>Typ:</b> {clean_text(dev['typ'])} | <b>Nr seryjny:</b> {clean_text(dev['nr_seryjny'])}"
        
        t_meter = Table([[Paragraph(meter_text, self.style_small)]], colWidths=[190*mm])
        t_meter.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor(PRIMARY_COLOR)),
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#e6efff")), 
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
        ]))
        elements.append(t_meter)
        elements.append(Spacer(1, 3*mm))

        # 4. ZASILANIE I UZIEMIENIE (GRID LAYOUT)
        elements.append(Paragraph(clean_text("I. CHARAKTERYSTYKA ZASILANIA (PN-HD 60364)"), self.style_subheader))
        supply = self.data['supply']
        
        def cell_L(txt): return Paragraph(f"<b>{clean_text(txt)}</b>", self.style_label)
        def cell_V(txt): return Paragraph(clean_text(txt), self.style_value)

        supply_data = [
            [cell_L("Układ sieci"), cell_V(supply['uklad']), cell_L("Napięcie"), cell_V(f"{supply['napiecie']} V")],
            [cell_L("Uziom"), cell_V(supply['uziom_typ']), cell_L("Częstotliwość"), cell_V(f"{supply['czestotliwosc']} Hz")],
            [cell_L("Rez. Uziomu RA"), cell_V(f"{supply['ra']} Ohm"), cell_L("Zab. Przedlicz."), cell_V(f"{supply['zab_typ']} {supply['zab_prad']}A")],
            [cell_L("Impedancja Ze"), cell_V(f"{supply['ze']} Ohm"), cell_L("Spodziewany Ipf"), cell_V(f"{supply['ipf']} kA")],
            [cell_L("Przewód PE"), cell_V(supply['przewod_pe']), cell_L("Wyłącznik Gł."), cell_V(supply['wyl_glowny'])]
        ]
        
        t_supply = Table(supply_data, colWidths=[30*mm, 65*mm, 30*mm, 65*mm])
        t_supply.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke), 
            ('BACKGROUND', (2,0), (2,-1), colors.whitesmoke), 
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_supply)
        
        bonds = []
        if supply['bond_woda']: bonds.append("Woda")
        if supply['bond_gaz']: bonds.append("Gaz")
        if supply['bond_konstr']: bonds.append("Konstr.")
        if supply['bond_co']: bonds.append("C.O.")
        bond_txt = "Brak" if not bonds else ", ".join(bonds)
        
        t_bond = Table([[cell_L("Połączenia wyrównawcze główne:"), cell_V(bond_txt)]], colWidths=[60*mm, 130*mm])
        t_bond.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,0), (0,0), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_bond)
        elements.append(Spacer(1, 4*mm))

        # 5. OGLĘDZINY
        elements.append(Paragraph(clean_text("II. WYNIKI OGLĘDZIN (PN-HD 60364-6 p. 6.4.2)"), self.style_subheader))
        insp_df = self.data['inspekcja']
        insp_items = list(insp_df.items())
        half = (len(insp_items) + 1) // 2
        col1_data = insp_items[:half]
        col2_data = insp_items[half:]
        
        insp_rows = []
        for i in range(len(col1_data)):
            k1, v1 = col1_data[i]
            res1 = "POZYTYWNY" if v1 == "POZYTYWNY" else ("NEGATYWNY" if v1 == "NEGATYWNY" else "N/D")
            c1_txt = f"{clean_text(k1)}: <b>{clean_text(res1)}</b>"
            
            c2_txt = ""
            if i < len(col2_data):
                k2, v2 = col2_data[i]
                res2 = "POZYTYWNY" if v2 == "POZYTYWNY" else ("NEGATYWNY" if v2 == "NEGATYWNY" else "N/D")
                c2_txt = f"{clean_text(k2)}: <b>{clean_text(res2)}</b>"
                
            insp_rows.append([Paragraph(c1_txt, self.style_small), Paragraph(c2_txt, self.style_small)])

        t_insp = Table(insp_rows, colWidths=[95*mm, 95*mm])
        t_insp.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_insp)
        elements.append(Spacer(1, 4*mm))

        # 6. TABELE POMIAROWE
        custom_cols = self.data.get('column_names', {})
        h_obwod = clean_text(custom_cols.get("Nazwa_Obwodu", "Obwód / Opis"))
        h_przewody = clean_text("Przewody")
        h_rodzaj = clean_text(custom_cols.get("Typ_Przewodu", "Typ"))
        h_zab = clean_text("Zabezp.")
        h_typ_zab = clean_text(custom_cols.get("Zab_Typ", "Typ"))
        h_riso = clean_text(custom_cols.get("R_ISO", "R_ISO"))
        h_imp = clean_text(custom_cols.get("Zs_pom", "Pętla (Zs)"))
        h_ocena = clean_text("Ocena")

        for table_name, df in self.data['tables'].items():
            elements.append(Paragraph(clean_text(f"III. WYNIKI POMIARÓW: {table_name}"), self.style_subheader))
            
            table_data = [
                [h_obwod, h_przewody, "", h_zab, "", h_riso, h_imp, "", "RCD", h_ocena],
                ["", h_rodzaj, "mm2", h_typ_zab, "In", "M_Ohm", "Z_pom", "Z_dop", "ms", ""]
            ]

            for _, row in df.iterrows():
                status = clean_text("POZ")
                try:
                    if float(row['Zs_pom']) > float(row['Zs_dop']): status = clean_text("NEG")
                except: pass
                
                table_data.append([
                    clean_text(row['Nazwa_Obwodu']),
                    clean_text(row['Typ_Przewodu']),
                    str(row['Przekroj']),
                    clean_text(row['Zab_Typ']),
                    str(row['Zab_In']),
                    str(row['R_ISO']),
                    str(row['Zs_pom']),
                    str(row['Zs_dop']),
                    str(row['RCD_t']),
                    status
                ])

            col_widths = [48*mm, 15*mm, 10*mm, 14*mm, 11*mm, 18*mm, 18*mm, 18*mm, 15*mm, 23*mm]
            t_meas = Table(table_data, colWidths=col_widths, repeatRows=2)
            ts = TableStyle([
                ('SPAN', (0,0), (0,1)), ('SPAN', (1,0), (2,0)), ('SPAN', (3,0), (4,0)),
                ('SPAN', (5,0), (5,1)), ('SPAN', (6,0), (7,0)), ('SPAN', (8,0), (8,1)), ('SPAN', (9,0), (9,1)),
                ('FONTNAME', (0,0), (-1,-1), FONT_NAME), 
                ('FONTSIZE', (0,0), (-1,-1), 7),
                ('FONTNAME', (0,0), (-1,1), FONT_NAME_BOLD),
                ('BACKGROUND', (0,0), (-1,1), colors.HexColor(PRIMARY_COLOR)),
                ('TEXTCOLOR', (0,0), (-1,1), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'), 
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('ALIGN', (0,2), (0,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('LEFTPADDING', (0,0), (-1,-1), 2),
                ('RIGHTPADDING', (0,0), (-1,-1), 2),
            ])
            t_meas.setStyle(ts)
            elements.append(t_meas)
            elements.append(Spacer(1, 5*mm))

        # 7. STOPKA
        elements.append(Spacer(1, 5*mm))
        elements.append(Paragraph(f"<b>{clean_text('IV. UWAGI KOŃCOWE I ORZECZENIE')}</b>", self.style_header))
        
        orzeczenie = self.data['meta']['orzeczenie']
        uwagi = self.data['uwagi']
        
        uwagi_style = TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ])
        
        t_uwagi = Table([[Paragraph(f"<b>Orzeczenie: {clean_text(orzeczenie)}</b><br/><br/>Uwagi: {clean_text(uwagi)}", self.style_normal)]], colWidths=[190*mm])
        t_uwagi.setStyle(uwagi_style)
        elements.append(t_uwagi)
        
        elements.append(Spacer(1, 10*mm))
        
        footer_data = [[
            Paragraph(f"Badanie wykonał:<br/><b>{clean_text(meta['wykonawca'])}</b>", self.style_normal),
            Paragraph(f"Nr uprawnień:<br/><b>{clean_text(meta['nr_uprawnien'])}</b>", self.style_normal),
            clean_text("Podpis: .............................")
        ]]
        t_foot = Table(footer_data, colWidths=[63*mm, 63*mm, 64*mm])
        elements.append(t_foot)

        self.doc.build(elements)

# --- UI ---
def main():
    if os.path.exists("logo.png"):
        st.sidebar.image("logo.png", width=100)
    
    st.sidebar.title("FARAD v2.3")
    if not HAS_POLISH_FONT:
        st.sidebar.info("Wgraj 'font.ttf' dla polskich znaków.")

    menu = st.sidebar.radio("Etapy:", ["1. Dane Zlecenia", "2. Zasilanie", "3. Oględziny", "4. Pomiary", "5. Generuj PDF"])

    # Inicjalizacja stanu
    if 'tables' not in st.session_state:
        st.session_state.tables = {
            "Rozdzielnica Główna": pd.DataFrame([
                {"Nazwa_Obwodu": "WLZ", "Typ_Przewodu": "YDY", "Przekroj": 10.0, "Zab_Typ": "gG", "Zab_In": 25, "R_ISO": 500, "Zs_pom": 0.22, "Zs_dop": 1.4, "RCD_t": 0}
            ])
        }
    
    if 'column_names' not in st.session_state:
        st.session_state.column_names = {
            "Nazwa_Obwodu": "Nazwa Obwodu", "Typ_Przewodu": "Przewód", "Zab_Typ": "Zab. Typ",
            "R_ISO": "R_iso (MΩ)", "Zs_pom": "Zs pom (Ω)"
        }

    # --- 1. DANE ---
    if menu == "1. Dane Zlecenia":
        st.header("Dane Podstawowe")
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Inwestor")
            st.session_state.klient = st.text_input("Zleceniodawca", "Wspólnota Mieszkaniowa")
            st.session_state.obiekt = st.text_input("Obiekt", "ul. Testowa 1")
            st.session_state.data = st.date_input("Data", datetime.now())
        with col2:
            st.subheader("Wykonawca")
            st.session_state.wykonawca = st.text_input("Wykonawca", "Jan Kowalski")
            st.session_state.nr_uprawnien = st.text_input("Nr uprawnień", "E/123/2026")
            st.session_state.nr_protokolu = st.text_input("Nr protokołu", "1/2026")
            
        st.divider()
        st.subheader("Użyty Przyrząd Pomiarowy")
        c3, c4, c5, c6 = st.columns(4)
        st.session_state.dev_nazwa = c3.text_input("Nazwa przyrządu", "Miernik inst.")
        st.session_state.dev_prod = c4.text_input("Producent", "Sonel")
        st.session_state.dev_typ = c5.text_input("Typ", "MPI-540")
        st.session_state.dev_sn = c6.text_input("Nr fabryczny", "AB123456")

    # --- 2. ZASILANIE ---
    elif menu == "2. Zasilanie":
        st.header("Charakterystyka Zasilania")
        c1, c2 = st.columns(2)
        with c1:
            st.caption("Parametry Sieci")
            st.session_state.sup_uklad = st.selectbox("Układ Sieci", ["TN-C-S", "TN-S", "TN-C", "TT", "IT"])
            st.session_state.sup_nap = st.number_input("Napięcie (V)", 230, 400, 230)
            st.session_state.sup_freq = st.number_input("Częstotliwość (Hz)", 50, 60, 50)
            st.session_state.sup_ipf = st.text_input("Ipf (kA)", "6.0")
            st.caption("Zabezpieczenie Główne")
            st.session_state.sup_zab_typ = st.text_input("Typ zab.", "gG")
            st.session_state.sup_zab_prad = st.number_input("Prąd (A)", 0, 1000, 63)
            st.session_state.sup_main_sw = st.text_input("Wyłącznik Gł.", "FR 100A 3P")

        with c2:
            st.caption("Uziemienie")
            st.session_state.sup_uziom_typ = st.text_input("Rodzaj uziomu", "Fundamentowy")
            st.session_state.sup_ra = st.text_input("Rezystancja RA (Ω)", "2.5")
            st.session_state.sup_ze = st.text_input("Impedancja Ze (Ω)", "0.22")
            st.session_state.sup_pe = st.text_input("Przewód PE (mm2)", "LgY 16mm2")
            st.caption("Połączenia Wyrównawcze")
            st.session_state.bond_woda = st.checkbox("Woda", True)
            st.session_state.bond_gaz = st.checkbox("Gaz", True)
            st.session_state.bond_konstr = st.checkbox("Konstrukcja", False)
            st.session_state.bond_co = st.checkbox("C.O.", True)

    # --- 3. OGLĘDZINY ---
    elif menu == "3. Oględziny":
        st.header("Oględziny (PN-HD 60364-6)")
        ck_list = [
            "Ochrona podstawowa (izolacja/obudowy)", "Ochrona przy uszkodzeniu (SWZ)", 
            "Dobór przewodów do obciążalności", "Dobór i nastawy zabezpieczeń",
            "Obecność schematów i oznaczeń", "Ciągłość przewodów ochronnych",
            "Dostęp do urządzeń", "Stan osprzętu łączeniowego"
        ]
        st.session_state.inspekcja = {item: st.radio(item, ["POZYTYWNY", "NEGATYWNY", "ND"], horizontal=True, key=item) for item in ck_list}

    # --- 4. POMIARY ---
    elif menu == "4. Pomiary":
        st.header("Tabele Pomiarowe")
        
        # Konfiguracja nazw
        with st.expander("Nazwy kolumn w PDF"):
            c1, c2, c3 = st.columns(3)
            st.session_state.column_names["Nazwa_Obwodu"] = c1.text_input("Nagłówek: Nazwa", st.session_state.column_names["Nazwa_Obwodu"])
            st.session_state.column_names["R_ISO"] = c2.text_input("Nagłówek: R_ISO", st.session_state.column_names["R_ISO"])
            st.session_state.column_names["Zs_pom"] = c3.text_input("Nagłówek: Zs", st.session_state.column_names["Zs_pom"])

        tab_names = list(st.session_state.tables.keys())
        active_tab = st.selectbox("Wybierz tabelę:", tab_names)
        
        # Dodawanie tabeli
        new_tab = st.text_input("Nowa tabela (np. Garaż)", "")
        if st.button("Dodaj") and new_tab:
            if new_tab not in st.session_state.tables:
                st.session_state.tables[new_tab] = pd.DataFrame([{"Nazwa_Obwodu": "Nowy", "Typ_Przewodu": "YDYp", "Przekroj": 1.5, "Zab_Typ": "B", "Zab_In": 16, "R_ISO": 999, "Zs_pom": 0.5, "Zs_dop": 2.8, "RCD_t": 0}])
                st.rerun()

        st.subheader(f"Edycja: {active_tab}")
        col_cfg = {
            "Nazwa_Obwodu": st.column_config.TextColumn(st.session_state.column_names["Nazwa_Obwodu"], width="medium"),
            # ZMIANA: Z SelectboxColumn na TextColumn
            "Typ_Przewodu": st.column_config.TextColumn("Przewód", width="small"),
            "Przekroj": st.column_config.NumberColumn("mm²", format="%.1f"),
            "R_ISO": st.column_config.NumberColumn(st.session_state.column_names["R_ISO"], format="%d"),
            "Zs_pom": st.column_config.NumberColumn(st.session_state.column_names["Zs_pom"], format="%.2f"),
        }
        
        # ZMIANA: Przypisanie wyniku bezpośrednio do stanu, aby uniknąć problemu "podwójnego wpisywania"
        st.session_state.tables[active_tab] = st.data_editor(
            st.session_state.tables[active_tab],
            num_rows="dynamic",
            column_config=col_cfg,
            use_container_width=True,
            key=f"editor_{active_tab}"
        )
        
        if len(st.session_state.tables) > 1 and st.button("Usuń tę tabelę"):
            del st.session_state.tables[active_tab]
            st.rerun()

    # --- 5. GENERUJ ---
    elif menu == "5. Generuj PDF":
        st.header("Zakończenie")
        st.session_state.orzeczenie = st.selectbox("Orzeczenie", ["INSTALACJA NADAJE SIĘ DO EKSPLOATACJI", "INSTALACJA NIE NADAJE SIĘ DO EKSPLOATACJI"])
        st.session_state.uwagi = st.text_area("Uwagi", "Instalacja wykonana zgodnie z normami.")
        
        st.divider()
        
        data = {
            'meta': {
                'klient': st.session_state.get('klient', ''), 'obiekt': st.session_state.get('obiekt', ''),
                'data': st.session_state.get('data', ''), 'wykonawca': st.session_state.get('wykonawca', ''),
                'nr_uprawnien': st.session_state.get('nr_uprawnien', ''), 'nr_protokolu': st.session_state.get('nr_protokolu', ''),
                'orzeczenie': st.session_state.get('orzeczenie', '')
            },
            'device': {
                'nazwa': st.session_state.get('dev_nazwa', ''), 'producent': st.session_state.get('dev_prod', ''),
                'typ': st.session_state.get('dev_typ', ''), 'nr_seryjny': st.session_state.get('dev_sn', '')
            },
            'supply': {
                'uklad': st.session_state.get('sup_uklad', 'TN-C-S'), 'napiecie': st.session_state.get('sup_nap', 230),
                'czestotliwosc': st.session_state.get('sup_freq', 50), 'ipf': st.session_state.get('sup_ipf', ''),
                'zab_typ': st.session_state.get('sup_zab_typ', ''), 'zab_prad': st.session_state.get('sup_zab_prad', ''),
                'uziom_typ': st.session_state.get('sup_uziom_typ', ''), 'ra': st.session_state.get('sup_ra', ''),
                'ze': st.session_state.get('sup_ze', ''), 'przewod_pe': st.session_state.get('sup_pe', ''),
                'wyl_glowny': st.session_state.get('sup_main_sw', ''),
                'bond_woda': st.session_state.get('bond_woda', False), 'bond_gaz': st.session_state.get('bond_gaz', False),
                'bond_konstr': st.session_state.get('bond_konstr', False), 'bond_co': st.session_state.get('bond_co', False),
            },
            'inspekcja': st.session_state.get('inspekcja', {}),
            'tables': st.session_state.tables,
            'column_names': st.session_state.column_names,
            'uwagi': st.session_state.get('uwagi', '')
        }
        
        pdf_buffer = BytesIO()
        try:
            EICR_PDF(pdf_buffer, data).generate()
            st.download_button("⬇️ POBIERZ PDF", pdf_buffer.getvalue(), f"Protokol_{datetime.now().strftime('%Y%m%d')}.pdf", "application/pdf", type="primary")
        except Exception as e:
            st.error(f"Błąd: {e}")

if __name__ == "__main__":
    main()