import streamlit as st
import pandas as pd
from supabase import create_client, Client
import math
from datetime import date

# --- 1. KONFIGURACJA I PAMIĘĆ ---
st.set_page_config(page_title="Generator Ofert Medycznych", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

if 'koszyk' not in st.session_state: st.session_state['koszyk'] = []

st.markdown("""
    <style>
    .big-font { font-size:18px !important; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold;}
    .header-style { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;}
    .op-info { background-color: #e8f4f8; padding: 10px; border-radius: 5px; border-left: 5px solid #2196f3; font-size: 14px; margin-bottom: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. PROFESJONALNE OPISY USŁUG ---
OPISY_MARKETINGOWE = {
    "Badania Laboratoryjne": """
### Mobilny Punkt Pobrań
Wygodny dostęp do diagnostyki laboratoryjnej bez konieczności dojazdów pracowników do placówek.
* **Organizacja:** Sprawny proces rejestracji i pobrania krwi w siedzibie firmy.
* **Wyniki:** Udostępniane online bezpośrednio pracownikowi (pełna poufność).
* **Edukacja:** Opcjonalnie webinar podsumowujący – omówienie znaczenia badań i najczęstszych odchyleń w populacji.
* **Raportowanie:** Możliwość przygotowania anonimowego raportu zbiorczego dla pracodawcy (analiza trendów zdrowotnych).
""",
    "Cukrzyca BASIC": """
### Profilaktyka Cukrzycy (Pakiet BASIC)
Szybki screening w kierunku zaburzeń glikemii i ryzyka cukrzycy typu 2.
* **Badanie:** Oznaczenie poziomu HbA1c (hemoglobiny glikowanej) z kropli krwi z palca – wynik dostępny natychmiast na miejscu.
* **Ocena ryzyka:** Wywiad medyczny, pomiary antropometryczne oraz analiza ryzyka wystąpienia cukrzycy w ciągu najbliższych 10 lat (wg walidowanego narzędzia).
* **Zalecenia:** Pracownik otrzymuje indywidualny kod QR. Po jego zeskanowaniu uzyskuje spersonalizowane zalecenia i plan dalszego postępowania.
""",
    "Cukrzyca PREMIUM": """
### Profilaktyka Cukrzycy (Pakiet PREMIUM)
Rozszerzona diagnostyka metaboliczna pozwalająca wykryć ukryte zagrożenia.
* **Zakres BASIC + Analiza Składu Ciała:** Profesjonalne badanie na urządzeniu klasy medycznej (InBody).
* **Co badamy?** Identyfikacja ryzyka metabolicznego związanego z niewidocznym gołym okiem problemem (np. nagromadzenie aktywnego metabolicznie tłuszczu trzewnego lub obniżona masa mięśniowa).
* **Efekt:** Pełny obraz kondycji metabolicznej pracownika i konkretne wskazówki dietetyczne.
""",
    "Profilaktyka Chorób Serca": """
### Ryzyko Sercowo-Naczyniowe
Kompleksowa ocena układu krążenia w celu zapobiegania zawałom i udarom.
* **Badania:** Pełny lipidogram z kropli krwi z palca (wynik na miejscu) oraz pomiar ciśnienia tętniczego.
* **Ocena ryzyka:** Wywiad zdrowotny i analiza ryzyka wystąpienia incydentu sercowo-naczyniowego (zawał, udar) w perspektywie 10 lat.
* **Zalecenia:** Raport oraz kod QR z indywidualnymi wskazówkami dotyczącymi diety i stylu życia, dostosowanymi do wyników pracownika.
""",
    "Spirometria": """
### Spirometria – Zdrowe Płuca
Badanie przesiewowe układu oddechowego, kluczowe w profilaktyce po-covidowej i środowiskowej.
* **Cel:** Wczesna identyfikacja schorzeń takich jak astma oskrzelowa lub POChP.
* **Przebieg:** Badanie prowadzone przez uprawnionego medyka z zachowaniem najwyższych standardów higienicznych (ustniki jednorazowe/filtry).
* **Wynik:** Natychmiastowa informacja o wydolności płuc i zalecenia dotyczące dalszego postępowania w razie nieprawidłowości.
""",
    "USG w Miejscu Pracy": """
### Mobilny Gabinet USG
Profilaktyczne badania ultrasonograficzne wykonywane na miejscu u pracodawcy przez doświadczonych lekarzy.
* **Zakres (do wyboru):** USG tarczycy, jamy brzusznej, jąder lub piersi.
* **Przebieg:** Badanie trwa średnio ok. 15 minut na osobę. USG pozwala wcześnie wykryć zmiany niewyczuwalne w badaniu palpacyjnym.
* **Wynik:** Pracownik otrzymuje opis pisemny od razu po badaniu wraz z ewentualnym skierowaniem na dalszą diagnostykę.
""",
    "Dermatoskopia": """
### Dermatoskopia – Profilaktyka Czerniaka
Konsultacja dermatologiczna z oceną znamion i zmian skórnych.
* **Cel:** Wczesna identyfikacja zmian wymagających obserwacji lub pilnej diagnostyki (profilaktyka nowotworów skóry).
* **Specjalista:** Badanie prowadzone przez lekarza dermatologa przy użyciu dermatoskopu.
* **Zalecenia:** Pracownik otrzymuje konkretną informację: kontrola, dalsza diagnostyka lub zalecenia dotyczące ochrony przeciwsłonecznej.
"""
}

# --- 3. SUPABASE ---
@st.cache_data(ttl=600)
def get_supabase_data():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        supabase: Client = create_client(url, key)
        response = supabase.table("badania").select("*").execute()
        df = pd.DataFrame(response.data)
        if not df.empty:
            df.columns = df.columns.str.lower().str.strip()
            if 'cena' in df.columns: df['cena'] = pd.to_numeric(df['cena'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"⚠️ Błąd bazy: {e}")
        return pd.DataFrame()

# --- 4. STAŁE ---
KOSZT_NOCLEGU = 400.0
STAWKA_KM = 2.0
LIMIT_LOKALIZACJI = 20

# --- 5. FUNKCJE ---
def dodaj_do_koszyka(nazwa, cena, logistyka_opis, marza_procent):
    st.session_state['koszyk'].append({
        "Usługa": nazwa, 
        "Cena": cena, 
        "Marża %": f"{marza_procent:.1f}%", 
        "Logistyka": logistyka_opis
    })
    st.toast(f"✅ Dodano {nazwa} do zestawienia!")

def straznik_rentownosci(koszt_operacyjny, przychod_sztywny_lab, cena_koncowa):
    przychod_na_operacje = cena_koncowa - przychod_sztywny_lab
    if koszt_operacyjny <= 0:
        if przychod_na_operacje > 0: return "success", "✅ Rentowność OK", 100.0
        else: return "warning", "⚠️ Usługa bez marży", 0.0
    if przychod_na_operacje < koszt_operacyjny:
        strata = koszt_operacyjny - przychod_na_operacje
        return "error", f"⛔ STOP! Tracisz {strata:.2f} PLN.", -100
    zysk = przychod_na_operacje - koszt_operacyjny
    marza = (zysk / koszt_operacyjny) * 100
    if marza < 20: return "error", f"⛔ ODRZUCONA ({marza:.1f}%)", marza
    elif 20 <= marza < 21: return "warning", f"⚠️ SKRAJNIE NISKA ({marza:.1f}%)", marza
    elif 21 <= marza < 50: return "warning", f"⚠️ Niska rentowność ({marza:.1f}%)", marza
    else: return "success", f"✅ Rentowność OK ({marza:.1f}%)", marza

def generuj_logistyke_opis(pacjenci, opis_lok):
    return f"Liczba uczestników: {pacjenci}\nSzczegóły:\n{opis_lok}"

def symulacja_czasu(pacjenci, wydajnosc, max_z):
    if pacjenci == 0: return ""
    opcje = []
    for n in range(1, max_z + 1):
        dni = math.ceil(pacjenci / (wydajnosc * n))
        opcje.append(f"<b>{n} Zesp.</b> ➡ {dni} dni")
    return " | ".join(opcje)

# --- 6. INTERFEJS USŁUG ---
def render_usluga_standard(nazwa_uslugi, stawka_local, stawka_remote, koszt_mat, wydajnosc, 
                          dodatkowy_personel_local=0, dodatkowy_personel_remote=0,
                          koszt_mat_dzien=0, max_zespolow=3):
    st.header(f"🩺 {nazwa_uslugi}")
    ile_lok = st.number_input("Ile lokalizacji?", 1, value=1)
    tabs = st.tabs([f"Lok. {i+1}" for i in range(ile_lok)])
    
    total_koszt = 0.0
    total_pacjenci = 0
    opis_lok = "" 

    for i, tab in enumerate(tabs):
        with tab:
            st.markdown(f"**Lokalizacja {i+1}**")
            col_m, col_z = st.columns([2, 1])
            with col_m:
                miasto = st.text_input(f"Miejscowość / Oddział:", placeholder="np. Fabryka Poznań", key=f"city_{nazwa_uslugi}_{i}")
                nazwa_lokalizacji = miasto if miasto else f"Lokalizacja {i+1}"
            with col_z:
                n_zesp = st.number_input(f"Liczba Zespołów (Max {max_zespolow})", 1, max_zespolow, 1, key=f"z_{nazwa_uslugi}_{i}")

            c1, c2 = st.columns(2)
            pacjenci = c1.number_input(f"Uczestnicy (Norma 1 zesp: {wydajnosc}/dzień)", 0, value=0, key=f"p_{nazwa_uslugi}_{i}")
            km = c2.number_input("Odległość od Warszawy (km)", 0, value=0, key=f"km_{nazwa_uslugi}_{i}")
            
            if pacjenci > 0:
                dni = math.ceil(pacjenci / (wydajnosc * n_zesp))
                is_remote = km > 150
                symulacja = symulacja_czasu(pacjenci, wydajnosc, max_zespolow)
                
                # Koszty
                stawka = stawka_remote if is_remote else stawka_local
                dodatek = dodatkowy_personel_remote if is_remote else dodatkowy_personel_local
                k_pers = dni * (stawka + dodatek) * n_zesp
                k_mat = (pacjenci * koszt_mat) + (dni * koszt_mat_dzien * n_zesp)
                k_dojazd = km * 2 * STAWKA_KM * n_zesp
                
                osoby_w_zesp = 1 + (1 if dodatkowy_personel_local > 0 else 0)
                laczna_ludzi = osoby_w_zesp * n_zesp
                k_hotel = (dni * KOSZT_NOCLEGU * laczna_ludzi) if (is_remote or dni > 1) else 0.0
                
                total_koszt += k_pers + k_mat + k_dojazd + k_hotel
                total_pacjenci += pacjenci
                opis_lok += f"- {nazwa_lokalizacji}: {pacjenci} os. ({n_zesp} zesp., {dni} dni)\n"
                
                st.markdown(f'<div class="op-info">⏱️ {n_zesp} Zesp. ➡ <b>{dni} dni</b> pracy.<br>💡 {symulacja}</div>', unsafe_allow_html=True)

    st.divider()
    if total_pacjenci > 0:
        k1, k2, k3 = st.columns(3)
        k1.metric("1. Koszt BAZOWY", f"{total_koszt:.2f} PLN")
        k2.metric("2. 🔵 Min", f"{total_koszt*1.5:.2f} PLN")
        k3.metric("3. 🟢 Pref", f"{total_koszt*2.0:.2f} PLN")
        
        c_final_1, c_final_2 = st.columns([1, 1])
        with c_final_1: cena_klienta = st.number_input("CENA KOŃCOWA (BRUTTO/ZW):", value=total_koszt*1.8)
        with c_final_2:
            st.write("Status:")
            status, msg, marza = straznik_rentownosci(total_koszt, 0.0, cena_klienta)
            if status == "error": st.error(msg)
            elif status == "warning": st.warning(msg)
            else: st.success(msg)

        if st.button(f"➕ Dodaj do Oferty"):
            if status != "error":
                logistyka = generuj_logistyke_opis(total_pacjenci, opis_lok)
                dodaj_do_koszyka(nazwa_uslugi, cena_klienta, logistyka, marza)
            else: st.error("Brak rentowności!")

# --- 7. NAV ---
st.sidebar.title("Nawigacja")
n_koszyk = len(st.session_state['koszyk'])
wybor = st.sidebar.radio("Menu:", ["ZESTAWIENIE OFERTY " + (f"📋 ({n_koszyk})" if n_koszyk>0 else "📋"), "---", "Badania Laboratoryjne (Pakiet)", "Cukrzyca BASIC", "Cukrzyca PREMIUM", "Kardiologia", "Spirometria", "USG w Firmie", "Dermatoskopia"])
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Wyczyść"): st.session_state['koszyk'] = []; st.rerun()

# --- 8. ZESTAWIENIE (GAMMA MODE) ---
if "ZESTAWIENIE OFERTY" in wybor:
    st.header("📋 Zestawienie i Export do Gammy")
    
    with st.expander("👤 DANE KLIENTA I HANDLOWCA", expanded=True):
        col_k, col_h = st.columns(2)
        with col_k:
            st.subheader("Klient")
            klient = st.text_input("Firma:", placeholder="Firma XYZ Sp. z o.o.")
            adres = st.text_input("Adres:", placeholder="ul. Prosta 1, Warszawa")
            kontakt = st.text_input("Osoba kontaktowa:", placeholder="Jan Kowalski, HR")
            kontakt_email = st.text_input("Email (Klient):", placeholder="jan@firma.pl") # NOWOŚĆ
        with col_h:
            st.subheader("Handlowiec (Ty)")
            handlowiec = st.text_input("Imię i Nazwisko:", placeholder="Twoje Imię")
            stanowisko = st.text_input("Stanowisko:", value="Manager ds. Klientów")
            handlowiec_email = st.text_input("Email (Ty):", placeholder="ty@twojafirma.pl") # NOWOŚĆ

    st.divider()
    if st.session_state['koszyk']:
        df = pd.DataFrame(st.session_state['koszyk'])
        df = df.rename(columns={"Cena": "Cena (Brutto)"})
        st.dataframe(df[["Usługa", "Cena (Brutto)", "Marża %"]], use_container_width=True, hide_index=True)
        
        suma = df["Cena (Brutto)"].sum()
        
        st.divider()
        st.subheader("🚀 Generowanie Prezentacji")
        st.info("Poniżej znajduje się gotowy kod dla AI Gamma. Zawiera on Twoje wyliczenia ORAZ profesjonalne opisy marketingowe usług.")

        # --- GENEROWANIE MARKDOWN DLA GAMMY ---
        today = date.today().strftime("%d.%m.%Y")
        
        # 1. Slajd Tytułowy
        md = f"# Oferta Współpracy Medycznej\n"
        md += f"### Dla: {klient if klient else 'Naszego Klienta'}\n"
        if adres: md += f"**Adres:** {adres}\n"
        if kontakt: md += f"**Osoba kontaktowa:** {kontakt}\n"
        if kontakt_email: md += f"**Email:** {kontakt_email}\n" # DODANO DO MARKDOWN
        md += f"**Data:** {today}\n\n"
        md += "---\n"
        
        # 2. Slajd O Nas / Strefa Zdrowia
        md += f"# Strefa Zdrowia w Twojej Firmie\n"
        md += f"### Profilaktyka bez wychodzenia z biura\n\n"
        md += f"Organizujemy profesjonalne badania i konsultacje medyczne bezpośrednio w siedzibie Twojej firmy. Nasz mobilny zespół medyczny tworzy szybkie i doskonale zorganizowane stanowiska diagnostyczne.\n\n"
        md += f"### Proces Realizacji\n"
        md += f"1. **Analiza:** Dobieramy odpowiednie moduły (np. Dzień Zdrowia, Roczny Program).\n"
        md += f"2. **Realizacja:** Przyjeżdżamy z pełnym sprzętem. Potrzebujemy tylko sali.\n"
        md += f"3. **Raport:** Indywidualne wyniki dla pracowników i anonimowy raport zbiorczy dla firmy.\n\n"
        md += f"> **Bezpieczeństwo:** Działamy zgodnie z RODO i tajemnicą medyczną.\n\n"
        md += "---\n"
        
        # 3. Slajdy Produktowe
        for i, item in enumerate(st.session_state['koszyk']):
            nazwa = item['Usługa']
            opis_marketingowy = OPISY_MARKETINGOWE.get(nazwa, "### Szczegóły usługi\nIndywidualnie dopasowany zakres badań.")
            logistyka = item['Logistyka']
            
            md += f"# Opcja {i+1}: {nazwa}\n"
            md += f"{opis_marketingowy}\n\n"
            
            md += f"### Parametry Twojej Realizacji\n"
            clean_logistyka = logistyka.replace("\n", "  \n")
            md += f"{clean_logistyka}\n\n"
            
            md += f"> **Inwestycja: {item['Cena']:.2f} PLN (zw. z VAT)**\n\n"
            md += "---\n"
            
        # 4. Slajd Podsumowanie
        md += f"# Podsumowanie Kosztów\n\n"
        md += f"| Usługa | Cena (Brutto) |\n"
        md += f"|---|---|\n"
        for item in st.session_state['koszyk']:
            md += f"| {item['Usługa']} | {item['Cena']:.2f} PLN |\n"
        md += f"| **RAZEM** | **{suma:.2f} PLN** |\n\n"
        md += "---\n"
        
        # 5. Slajd Kontakt + STOPKA PRAWNA
        md += f"# Zapraszamy do współpracy\n"
        md += f"### Skontaktuj się z nami\n\n"
        md += f"**{handlowiec if handlowiec else 'Twój Opiekun'}** \n"
        md += f"{stanowisko}  \n"
        
        # EMAIL HANDLOWCA LUB DOMYŚLNY
        mail_to_show = handlowiec_email if handlowiec_email else "oferta@twojafirma.pl"
        md += f"📧 {mail_to_show}\n\n"
        
        md += f"**Nota prawna:** Podane ceny są cenami końcowymi do zapłaty (Brutto). Usługi medyczne zwolnione z VAT na podst. art. 43 ust. 1 ustawy o VAT.\n"
        
        with st.expander("📄 KLIKNIJ TUTAJ, ABY POBRAĆ WSAD DO GAMMY (KOD MARKDOWN)", expanded=False):
            st.markdown("Instrukcja: Najedź myszką na poniższy kod i kliknij **ikonę kopiowania** (📋) w prawym górnym rogu.")
            st.code(md, language='markdown')


# --- 9. LOGIKA LAB (Z ZESPOŁAMI) ---
elif "Badania Laboratoryjne" in wybor:
    st.header("🧪 Kreator Pakietu Badań")
    df = get_supabase_data()
    if df.empty: st.stop()
    
    c1, c2 = st.columns([1, 1])
    with c1: wybrane = st.multiselect("Wybierz badania:", df['nazwa'].tolist())
    
    suma_pakietu = 0.0
    if wybrane:
        koszyk_lab = df[df['nazwa'].isin(wybrane)]
        with c2: st.dataframe(koszyk_lab[['nazwa', 'cena']], hide_index=True)
        suma_pakietu = koszyk_lab['cena'].sum()
        st.metric("Cena pakietu (osoba)", f"{suma_pakietu:.2f} PLN")
    
    st.divider()
    ile_lok = st.number_input("Ile lokalizacji?", 1, value=1)
    tabs = st.tabs([f"Lok. {i+1}" for i in range(ile_lok)])
    
    total_koszt_ops, total_koszt_lab, total_pacjenci = 0.0, 0.0, 0
    opis_lok = ""

    for i, tab in enumerate(tabs):
        with tab:
            st.markdown(f"**Lokalizacja {i+1}**")
            col_m, col_z = st.columns([2, 1])
            with col_m:
                miasto = st.text_input(f"Miejscowość:", placeholder="np. Centrala", key=f"lab_city_{i}")
                nazwa_lok = miasto if miasto else f"Lok {i+1}"
            with col_z:
                n_zesp = st.number_input("Liczba Zespołów", 1, 10, 1, key=f"lz_{i}")

            c1, c2 = st.columns(2)
            pacjenci = c1.number_input("Uczestnicy (Norma ~100/dzień)", 0, value=0, key=f"lp_{i}")
            km = c2.number_input("Km od Wawy", 0, value=0, key=f"lkm_{i}")
            
            if pacjenci > 0:
                dni = math.ceil(pacjenci / (100 * n_zesp))
                godziny = math.ceil(pacjenci / (12.5 * n_zesp))
                is_remote = km > 150
                
                k_lab = pacjenci * suma_pakietu
                k_pieleg = (pacjenci / 12.5) * 80.0 
                k_dojazd = km * 2 * STAWKA_KM * n_zesp
                k_hotel = (dni * KOSZT_NOCLEGU * n_zesp) if (is_remote or dni > 1) else 0.0
                
                k_ops = k_pieleg + k_dojazd + k_hotel
                total_koszt_ops += k_ops
                total_koszt_lab += k_lab
                total_pacjenci += pacjenci
                opis_lok += f"- {nazwa_lok}: {pacjenci} os. ({n_zesp} zesp. lab)\n"
                
                st.markdown(f'<div class="op-info">⏱️ {n_zesp} Zesp. Lab ➡ <b>{dni} dni</b> pracy.</div>', unsafe_allow_html=True)

    razem = total_koszt_ops + total_koszt_lab
    st.divider()
    if total_pacjenci > 0:
        k1, k2, k3 = st.columns(3)
        k1.metric("1. BEP", f"{razem:.2f} PLN")
        s_min = (total_koszt_ops * 1.5) + total_koszt_lab
        s_pref = (total_koszt_ops * 2.0) + total_koszt_lab
        k2.metric("2. Min", f"{s_min:.2f} PLN")
        k3.metric("3. Pref", f"{s_pref:.2f} PLN")
        
        c1, c2 = st.columns(2)
        with c1: cena = st.number_input("CENA KOŃCOWA (BRUTTO/ZW):", value=razem*1.2)
        with c2: 
            st.write("Status:")
            s, m, mar = straznik_rentownosci(total_koszt_ops, total_koszt_lab, cena)
            if s == "error": st.error(m)
            elif s == "warning": st.warning(m)
            else: st.success(m)
        
        if st.button("➕ Dodaj Pakiet Lab"):
            if s!="error": 
                logistyka = f"**Pakiet Badań Lab**\nZakres: {', '.join(wybrane)}\n{generuj_logistyke_opis(total_pacjenci, opis_lok)}"
                dodaj_do_koszyka("Badania Laboratoryjne", cena, logistyka, mar)
            else: st.error("Brak rentowności!")

# --- POZOSTAŁE ---
elif "Cukrzyca BASIC" in wybor: render_usluga_standard("Cukrzyca BASIC", 640, 1000, 40, 50, max_zespolow=5)
elif "Cukrzyca PREMIUM" in wybor: render_usluga_standard("Cukrzyca PREMIUM", 640, 1000, 40, 50, 320, 500, max_zespolow=5)
elif "Kardiologia" in wybor: render_usluga_standard("Profilaktyka Chorób Serca", 640, 1000, 30, 50, max_zespolow=3)
elif "Spirometria" in wybor: render_usluga_standard("Spirometria", 1000, 1200, 5, 40, max_zespolow=2)
elif "USG" in wybor: render_usluga_standard("USG w Miejscu Pracy", 5000, 5500, 0, 30, koszt_mat_dzien=200, max_zespolow=2)
elif "Dermatoskopia" in wybor: render_usluga_standard("Dermatoskopia", 4500, 5500, 0, 45, max_zespolow=3)