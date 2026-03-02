import streamlit as st
import pandas as pd
from supabase import create_client, Client
import math
from datetime import date

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Generator Ofert Medycznych", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

# --- 2. SYSTEM LOGOWANIA ---
def check_password():
    def password_entered():
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            st.session_state["logged_in_user"] = st.session_state["username"] 
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h1 style='text-align: center;'>Zaloguj się do systemu</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("E-mail (Login)", key="username")
            st.text_input("Hasło", type="password", key="password")
            st.button("Zaloguj", on_click=password_entered, use_container_width=True)
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<h1 style='text-align: center;'>Zaloguj się do systemu</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("E-mail (Login)", key="username")
            st.text_input("Hasło", type="password", key="password")
            st.button("Zaloguj", on_click=password_entered, use_container_width=True)
            st.error("⛔ Błędny login lub hasło. Spróbuj ponownie.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# =========================================================================
# === PONIŻEJ ZACZYNA SIĘ WŁAŚCIWA APLIKACJA ===
# =========================================================================

if 'koszyk' not in st.session_state: st.session_state['koszyk'] = []

st.markdown("""
    <style>
    .big-font { font-size:18px !important; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold;}
    .header-style { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;}
    .op-info { background-color: #e8f4f8; padding: 10px; border-radius: 5px; border-left: 5px solid #2196f3; font-size: 14px; margin-bottom: 10px;}
    .program-box { background-color: #fdfaf6; padding: 15px; border-radius: 10px; border: 1px solid #e6dace; margin-bottom: 15px;}
    </style>
    """, unsafe_allow_html=True)

# --- BAZA WIEDZY: HANDLOWCY ---
DANE_HANDLOWCOW = {
    "piotr.leszczynski@longlife.pl": {"imie": "Piotr Leszczyński", "stanowisko": "Członek Zarządu, Dyrektor Medyczny"},
    "katarzyna.czarnowska@longlife.pl": {"imie": "Katarzyna Czarnowska", "stanowisko": "Członek Zarządu, Dyrektor Operacyjny"},
    "paulina.nytko@longlife.pl": {"imie": "Paulina Nytko", "stanowisko": "Health & Wellbeing Business Manager"},
    "katarzyna.brzostek@longlife.pl": {"imie": "Katarzyna Brzostek", "stanowisko": "Health & Wellbeing Business Manager"},
    "jakub.jaruga@longlife.pl": {"imie": "Jakub Jaruga", "stanowisko": ""}
}

# --- OPISY MARKETINGOWE ---
OPISY_MARKETINGOWE = {
    "Badania Laboratoryjne": "### Mobilny Punkt Pobrań\nWygodny dostęp do diagnostyki laboratoryjnej bez konieczności dojazdów pracowników do placówek.\n* **Organizacja:** Sprawny proces rejestracji i pobrania krwi w siedzibie firmy.\n* **Wyniki:** Udostępniane online bezpośrednio pracownikowi (pełna poufność).\n* **Raportowanie:** Możliwość przygotowania anonimowego raportu zbiorczego dla pracodawcy (analiza trendów zdrowotnych).",
    "Cukrzyca BASIC": "### Profilaktyka Cukrzycy (Pakiet BASIC)\nSzybki screening w kierunku zaburzeń glikemii i ryzyka cukrzycy typu 2.\n* **Badanie:** Oznaczenie poziomu HbA1c z kropli krwi z palca – wynik dostępny natychmiast.\n* **Ocena ryzyka:** Wywiad medyczny i analiza ryzyka wystąpienia cukrzycy (wg walidowanego narzędzia).\n* **Zalecenia:** Pracownik otrzymuje kod QR ze spersonalizowanymi zaleceniami.",
    "Cukrzyca PREMIUM": "### Profilaktyka Cukrzycy (Pakiet PREMIUM)\nRozszerzona diagnostyka metaboliczna pozwalająca wykryć ukryte zagrożenia.\n* **Zakres BASIC + Analiza Składu Ciała:** Profesjonalne badanie na urządzeniu klasy medycznej (InBody).\n* **Co badamy?** Identyfikacja ryzyka metabolicznego (np. nagromadzenie tłuszczu trzewnego).\n* **Efekt:** Pełny obraz kondycji metabolicznej i konkretne wskazówki dietetyczne.",
    "Profilaktyka Serca": "### Ryzyko Sercowo-Naczyniowe\nKompleksowa ocena układu krążenia w celu zapobiegania zawałom i udarom.\n* **Badania:** Pełny lipidogram z kropli krwi z palca oraz pomiar ciśnienia tętniczego.\n* **Ocena ryzyka:** Wywiad zdrowotny i ocena ryzyka w perspektywie 10 lat.\n* **Zalecenia:** Raport i indywidualne wskazówki dotyczące diety i stylu życia.",
    "Spirometria": "### Spirometria – Zdrowe Płuca\nBadanie przesiewowe układu oddechowego, kluczowe w profilaktyce środowiskowej.\n* **Cel:** Wczesna identyfikacja schorzeń takich jak astma oskrzelowa lub POChP.\n* **Przebieg:** Badanie prowadzone przez uprawnionego medyka (najwyższe standardy higieniczne).\n* **Wynik:** Natychmiastowa informacja o wydolności płuc i zalecenia.",
    "USG": "### Mobilny Gabinet USG\nProfilaktyczne badania ultrasonograficzne na miejscu u pracodawcy.\n* **Przebieg:** Badanie trwa średnio ok. 15 minut na osobę. Wczesne wykrywanie zmian.\n* **Wynik:** Pracownik otrzymuje opis pisemny od razu po badaniu wraz z ewentualnym skierowaniem.",
    "Dermatoskopia": "### Dermatoskopia – Profilaktyka Czerniaka\nKonsultacja dermatologiczna z oceną znamion i zmian skórnych.\n* **Cel:** Wczesna identyfikacja zmian wymagających obserwacji.\n* **Specjalista:** Badanie prowadzone przez lekarza przy użyciu dermatoskopu.\n* **Zalecenia:** Informacja: kontrola, dalsza diagnostyka lub ochrona przeciwsłoneczna.",
    "Zarządzanie stresem": "### Strategia Psychologiczna i Zarządzanie Stresem\nDiagnostyka i edukacja w zakresie radzenia sobie z obciążeniem psychicznym.\n* **Diagnoza:** Weryfikacja indywidualnych strategii radzenia sobie ze stresem poprzez dedykowane narzędzia i testy psychologiczne.\n* **Edukacja:** Interwencja prowadzona przez psychologa, uświadamiająca mechanizmy stresu i dostarczająca narzędzi do budowania odporności psychicznej (rezyliencji).",
    "Zarządzanie stresem (Bez krwi)": "### Strategia Psychologiczna i Zarządzanie Stresem\nDiagnostyka i edukacja w zakresie radzenia sobie z obciążeniem psychicznym.\n* **Diagnoza:** Weryfikacja indywidualnych strategii radzenia sobie ze stresem poprzez dedykowane narzędzia i testy psychologiczne.\n* **Edukacja:** Interwencja prowadzona przez psychologa, uświadamiająca mechanizmy stresu i dostarczająca narzędzi do budowania odporności psychicznej.",
    "Zarządzanie stresem (Z krwią)": "### Strategia Psychologiczna i Zarządzanie Stresem (Rozszerzona)\nKompleksowa diagnostyka obejmująca testy oraz dedykowane badania laboratoryjne.\n* **Diagnoza i Badania:** Testy psychologiczne połączone z badaniem krwi oceniającym podłoże organiczne reakcji stresowych.\n* **Edukacja:** Interwencja psychologa oraz lekarza omawiająca wyniki i fizjologiczny wpływ stresu na organizm.",
    "Webinary Edukacyjne": "### Akademia Zdrowia – Edukacja Medyczna\nCykl interaktywnych spotkań z lekarzami i ekspertami medycyny stylu życia.\n* **Cel:** Budowanie świadomości zdrowotnej i zmiana nawyków pracowników.\n* **Forma:** Spotkania online z rozbudowaną sesją Q&A.\n* **Efekt:** Wyposażenie zespołu w rzetelną, medyczną wiedzę z zakresu żywienia, snu i aktywności.",
    "Program Roczny": "### Indywidualny Roczny Program Zdrowotny\nKompleksowa opieka zdrowotna rozłożona na 4 kwartały, zapewniająca ciągłość profilaktyki.\n* **Strategia:** Zamiast jednorazowej akcji, budujemy kulturę zdrowia w organizacji.\n* **Wygoda:** Stała miesięczna opłata i zaplanowany z góry harmonogram działań.\n* **Kompleksowość:** Połączenie badań fizykalnych, diagnostyki i edukacji (webinary)."
}

def get_opis_marketingowy(nazwa):
    if "Badania Lab" in nazwa or "Badania Laboratoryjne" in nazwa: return OPISY_MARKETINGOWE.get("Badania Laboratoryjne")
    if "Zarządzanie stresem (Z krwią)" in nazwa: return OPISY_MARKETINGOWE.get("Zarządzanie stresem (Z krwią)")
    if "Zarządzanie stresem" in nazwa: return OPISY_MARKETINGOWE.get("Zarządzanie stresem")
    if "Cukrzyca BASIC" in nazwa: return OPISY_MARKETINGOWE.get("Cukrzyca BASIC")
    if "Cukrzyca PREMIUM" in nazwa: return OPISY_MARKETINGOWE.get("Cukrzyca PREMIUM")
    if "Spirometria" in nazwa: return OPISY_MARKETINGOWE.get("Spirometria")
    if "USG" in nazwa: return OPISY_MARKETINGOWE.get("USG")
    if "Dermatoskopia" in nazwa: return OPISY_MARKETINGOWE.get("Dermatoskopia")
    if "Profilaktyka Serca" in nazwa: return OPISY_MARKETINGOWE.get("Profilaktyka Serca")
    return "Indywidualnie dopasowany moduł medyczny."

WEBINARY_TEMATY = [
    "1. Zasady zdrowego żywienia w medycynie stylu życia",
    "2. Aktywność fizyczna jako fundament prewencji chorób",
    "3. Funkcjonowanie w społeczeństwie oraz zarządzanie stresem",
    "4. Sen, regeneracja i uzależnienia w życiu codziennym",
    "5. Temat klienta – webinar na życzenie"
]

PARAMETRY_USLUG = {
    "Brak": {"wydajnosc": 9999, "koszt_mat": 0, "koszt_mat_dzien": 0, "stawka_local": 0, "stawka_remote": 0},
    "Spirometria": {"wydajnosc": 40, "koszt_mat": 5, "koszt_mat_dzien": 0, "stawka_local": 1000, "stawka_remote": 1200},
    "USG": {"wydajnosc": 30, "koszt_mat": 0, "koszt_mat_dzien": 200, "stawka_local": 5000, "stawka_remote": 5500},
    "Dermatoskopia": {"wydajnosc": 45, "koszt_mat": 0, "koszt_mat_dzien": 0, "stawka_local": 4500, "stawka_remote": 5500},
    "Cukrzyca BASIC": {"wydajnosc": 50, "koszt_mat": 40, "koszt_mat_dzien": 0, "stawka_local": 640, "stawka_remote": 1000},
    "Cukrzyca PREMIUM": {"wydajnosc": 50, "koszt_mat": 40, "koszt_mat_dzien": 320, "stawka_local": 640, "stawka_remote": 1000},
    "Profilaktyka Serca": {"wydajnosc": 50, "koszt_mat": 30, "koszt_mat_dzien": 0, "stawka_local": 640, "stawka_remote": 1000}
}

# --- BAZA DANYCH ---
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
            if 'cena' in df.columns: df['cena'] = pd.to_numeric(df['cena'], errors='coerce').fillna(0)
            if 'koszt' in df.columns: df['koszt'] = pd.to_numeric(df['koszt'], errors='coerce')
            if 'cena_rynkowa' in df.columns: df['cena_rynkowa'] = pd.to_numeric(df['cena_rynkowa'], errors='coerce').fillna(0)
            
            if 'koszt' not in df.columns:
                df['koszt'] = df['cena'] if 'cena' in df.columns else 0.0
            else:
                df['koszt'] = df['koszt'].fillna(df['cena'])
        return df
    except Exception as e:
        st.error(f"⚠️ Błąd bazy: {e}")
        return pd.DataFrame()

KOSZT_NOCLEGU = 400.0
STAWKA_KM = 1.0
LIMIT_LOKALIZACJI = 20

# --- FUNKCJE LOGICZNE ---
def dodaj_do_koszyka(nazwa, cena, cena_per_capita, cena_rynkowa, logistyka_opis, marza_procent, is_abonament=False, harmonogram=None):
    st.session_state['koszyk'].append({
        "Usługa": nazwa, 
        "Cena (Brutto)": cena, 
        "Cena za osobę": cena_per_capita,
        "Cena rynkowa (osoba)": cena_rynkowa,
        "Marża %": f"{marza_procent:.1f}%", 
        "Logistyka": logistyka_opis,
        "Abonament": is_abonament,
        "Harmonogram": harmonogram
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

def generuj_logistyke_opis(pacjenci, opis_lok): return f"Liczba uczestników: {pacjenci}\nSzczegóły:\n{opis_lok}"

def symulacja_czasu(pacjenci, wydajnosc, max_z):
    if pacjenci == 0: return ""
    opcje = [f"<b>{n} Zesp.</b> ➡ {math.ceil(pacjenci / (wydajnosc * n))} dni" for n in range(1, max_z + 1)]
    return " | ".join(opcje)

def dynamiczny_kalkulator_programu(akcje, lokalizacje, lab_koszt_osoba, lab_cena_osoba):
    total_ops = 0.0
    total_mat_std = 0.0
    total_przychod_lab = 0.0
    total_koszt_lab = 0.0
    
    for akcja in akcje:
        if akcja == "Brak": continue
        for lok in lokalizacje:
            pacjenci = lok["pacjenci"]
            km = lok["km"]
            if pacjenci == 0: continue
            
            if akcja == "Zarządzanie stresem (Bez krwi)":
                total_mat_std += (pacjenci * 100.0) 
                continue
                
            elif akcja in ["Badania Lab", "Zarządzanie stresem (Z krwią)"]:
                n_zesp = math.ceil(pacjenci / 100)
                dni = math.ceil(pacjenci / (100 * n_zesp))
                k_pieleg = (pacjenci / 12.5) * 80.0
                k_dojazd = km * 2 * STAWKA_KM * n_zesp
                k_hotel = (dni * KOSZT_NOCLEGU * n_zesp) if (km > 150 or dni > 1) else 0.0
                
                total_ops += (k_pieleg + k_dojazd + k_hotel)
                total_koszt_lab += (pacjenci * lab_koszt_osoba)
                total_przychod_lab += (pacjenci * lab_cena_osoba)
                
                if akcja == "Zarządzanie stresem (Z krwią)":
                    total_mat_std += (pacjenci * 100.0) 
            else:
                p = PARAMETRY_USLUG.get(akcja, PARAMETRY_USLUG["Brak"])
                n_zesp = 1
                dni = math.ceil(pacjenci / p["wydajnosc"]) if p["wydajnosc"] > 0 else 0
                if dni > 0:
                    is_remote = km > 150
                    stawka = p["stawka_remote"] if is_remote else p["stawka_local"]
                    k_pers = dni * stawka * n_zesp
                    k_dojazd = km * 2 * STAWKA_KM * n_zesp
                    k_hotel = (dni * KOSZT_NOCLEGU * n_zesp) if (is_remote or dni > 1) else 0.0
                    
                    total_ops += (k_pers + k_dojazd + k_hotel)
                    total_mat_std += (pacjenci * p["koszt_mat"]) + (dni * p["koszt_mat_dzien"])
                
    return total_ops, total_mat_std, total_koszt_lab, total_przychod_lab

# --- INTERFEJS USŁUG (Standardowe) ---
def render_usluga_standard(nazwa_uslugi, stawka_local, stawka_remote, koszt_mat, wydajnosc, 
                          dodatkowy_personel_local=0, dodatkowy_personel_remote=0,
                          koszt_mat_dzien=0, max_zespolow=3):
    st.header(f"🩺 {nazwa_uslugi}")
    ile_lok = st.number_input("Ile lokalizacji?", 1, value=1, key=f"loc_{nazwa_uslugi}")
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
        with c_final_1: 
            cena_klienta = st.number_input("CENA KOŃCOWA (BRUTTO/ZW):", value=total_koszt*1.8, key=f"ck_{nazwa_uslugi}")
            cena_per_capita = cena_klienta / total_pacjenci if total_pacjenci > 0 else 0
            st.caption(f"Wychodzi: **{cena_per_capita:.2f} PLN** za osobę")
            
        with c_final_2:
            st.write("Status:")
            status, msg, marza = straznik_rentownosci(total_koszt, 0.0, cena_klienta)
            if status == "error": st.error(msg)
            elif status == "warning": st.warning(msg)
            else: st.success(msg)

        if st.button(f"➕ Dodaj do Oferty", key=f"btn_{nazwa_uslugi}"):
            if status != "error":
                logistyka = generuj_logistyke_opis(total_pacjenci, opis_lok)
                dodaj_do_koszyka(nazwa_uslugi, cena_klienta, cena_per_capita, 0.0, logistyka, marza)
            else: st.error("Brak rentowności!")

# --- MENU GŁÓWNE ---
st.sidebar.title("Nawigacja")

raw_user = st.session_state.get('logged_in_user', st.session_state.get('username', ''))
current_user = str(raw_user).strip().lower()

bezpieczny_slownik = {k.strip().lower(): v for k, v in DANE_HANDLOWCOW.items()}
user_data = bezpieczny_slownik.get(current_user, {"imie": "Nieznany Handlowiec", "stanowisko": "Manager ds. Klientów"})

st.sidebar.caption(f"Zalogowano jako: **{user_data['imie']}** ({current_user})")
st.sidebar.markdown("---")

n_koszyk = len(st.session_state['koszyk'])
wybor = st.sidebar.radio(
    "Menu:", 
    [
        "ZESTAWIENIE OFERTY " + (f"📋 ({n_koszyk})" if n_koszyk>0 else "📋"), 
        "📅 Program Roczny (Abonament)",
        "Badania Laboratoryjne (Pakiet)", 
        "Zarządzanie stresem",
        "Webinary i edukacja",
        "Cukrzyca BASIC", 
        "Cukrzyca PREMIUM", 
        "Kardiologia", 
        "Spirometria", 
        "USG w Firmie", 
        "Dermatoskopia"
    ]
)
st.sidebar.markdown("---")
if st.sidebar.button("🗑️ Wyczyść koszyk"): st.session_state['koszyk'] = []; st.rerun()

# --- ZESTAWIENIE ---
if "ZESTAWIENIE OFERTY" in wybor:
    st.header("📋 Zestawienie i Export do Gammy")
    
    with st.expander("👤 DANE KLIENTA I HANDLOWCA", expanded=True):
        col_k, col_h = st.columns(2)
        with col_k:
            st.subheader("Klient")
            klient = st.text_input("Firma:", placeholder="Firma XYZ Sp. z o.o.")
            adres = st.text_input("Adres:", placeholder="ul. Prosta 1, Warszawa")
            kontakt = st.text_input("Osoba kontaktowa:", placeholder="Jan Kowalski, HR")
            kontakt_email = st.text_input("Email (Klient):", placeholder="jan@firma.pl")
        with col_h:
            st.subheader("Handlowiec (Ty)")
            handlowiec = st.text_input("Imię i Nazwisko:", value=user_data['imie'])
            stanowisko = st.text_input("Stanowisko:", value=user_data['stanowisko'])
            handlowiec_email = st.text_input("Email (Ty):", value=current_user)

    st.divider()
    if st.session_state['koszyk']:
        df = pd.DataFrame(st.session_state['koszyk'])
        st.dataframe(df[["Usługa", "Cena (Brutto)", "Cena za osobę", "Marża %"]], use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🚀 Generowanie Prezentacji")
        st.info("Poniżej znajduje się gotowy kod dla AI Gamma.")

        today = date.today().strftime("%d.%m.%Y")
        
        md = f"# Oferta Współpracy Medycznej\n### Dla: {klient if klient else 'Naszego Klienta'}\n"
        if adres: md += f"**Adres:** {adres}\n"
        if kontakt: md += f"**Osoba kontaktowa:** {kontakt}\n"
        if kontakt_email: md += f"**Email:** {kontakt_email}\n"
        md += f"**Data:** {today}\n\n---\n"
        
        md += f"# Strefa Zdrowia w Twojej Firmie\n### Profilaktyka bez wychodzenia z biura\n\nOrganizujemy profesjonalne badania i konsultacje medyczne bezpośrednio w siedzibie Twojej firmy. Nasz mobilny zespół medyczny tworzy szybkie i doskonale zorganizowane stanowiska diagnostyczne.\n\n### Proces Realizacji\n1. **Analiza:** Dobieramy odpowiednie moduły.\n2. **Realizacja:** Przyjeżdżamy z pełnym sprzętem. Potrzebujemy tylko sali.\n3. **Raport:** Indywidualne wyniki dla pracowników i anonimowy raport zbiorczy dla firmy.\n\n> **Bezpieczeństwo:** Działamy zgodnie z RODO i tajemnicą medyczną.\n\n---\n"
        
        for i, item in enumerate(st.session_state['koszyk']):
            nazwa = item['Usługa']
            
            opis_marketingowy = OPISY_MARKETINGOWE.get(nazwa, "### Szczegóły usługi\nIndywidualnie dopasowany zakres badań.")
            if "Badania Laboratoryjne" in nazwa: opis_marketingowy = OPISY_MARKETINGOWE.get("Badania Laboratoryjne")
            if "Zarządzanie stresem" in nazwa: opis_marketingowy = OPISY_MARKETINGOWE.get("Zarządzanie stresem")
            if "Roczny Program" in nazwa or "Abonament" in nazwa or "Indywidualny Program" in nazwa: opis_marketingowy = OPISY_MARKETINGOWE.get("Program Roczny")
                
            clean_logistyka = item['Logistyka'].replace("\n", "  \n")
            
            md += f"# Opcja {i+1}: {nazwa}\n{opis_marketingowy}\n\n"
            
            md += f"### Parametry Finansowe\n"
            if item.get('Abonament', False) and item['Cena za osobę'] > 0:
                miesieczna = item['Cena za osobę'] / 12
                md += f"> **Miesięczna inwestycja: {miesieczna:.2f} PLN / pracownika**\n"
                md += f"> *(Całkowity koszt roczny dla firmy: {item['Cena (Brutto)']:.2f} PLN)*\n\n"
            else:
                md += f"> **Inwestycja Całkowita: {item['Cena (Brutto)']:.2f} PLN (zw. z VAT)**\n"
                if item.get('Cena rynkowa (osoba)', 0) > 0:
                    md += f"> *Sugerowana cena rynkowa w placówce: ~~{item['Cena rynkowa (osoba)']:.2f} PLN / osobę~~*\n"
                if item['Cena za osobę'] > 0:
                    md += f"> *Nasza cena w pakiecie: **{item['Cena za osobę']:.2f} PLN / osobę***\n\n"
            
            md += f"### Parametry Realizacji\n{clean_logistyka}\n\n"
            
            if item.get("Harmonogram"):
                harm = item["Harmonogram"]
                
                md += f"---\n\n"
                md += f"## 📅 Twój Roczny Plan Zdrowia (Oś Czasu)\n"
                md += f"> **Elastyczność to podstawa:** Poniższy układ na osi czasu to nasza propozycja. Harmonogram może zostać zmodyfikowany i przesunięty w czasie zgodnie z możliwościami operacyjnymi Longlife oraz preferencjami Twojej firmy.\n\n"
                
                for kwartal in ["Kwartał 1", "Kwartał 2", "Kwartał 3", "Kwartał 4"]:
                    if kwartal in harm:
                        md += f"### {kwartal}\n"
                        md += f"- **Główne wydarzenie w firmie:** {harm[kwartal]['akcja']}\n"
                        md += f"- **Edukacja:** Webinar: {harm[kwartal]['webinar']}\n\n"
                
                md += f"---\n\n"
                md += f"## 🧩 Co dokładnie wchodzi w skład Twojego Programu?\n"
                md += f"Poniżej znajdziesz szczegółowe opisy poszczególnych modułów medycznych, które zrealizujemy dla Twojego zespołu na przestrzeni roku. Wszystkie te elementy są już zawarte w Twoim stałym abonamencie.\n\n"
                
                unikalne_akcje = []
                for q, dane in harm.items():
                    if q.startswith("Kwartał") and dane['akcja'] != "Brak" and dane['akcja'] not in unikalne_akcje:
                        unikalne_akcje.append(dane['akcja'])
                
                for akcja in unikalne_akcje:
                    opis_modulu = get_opis_marketingowy(akcja)
                    md += f"{opis_modulu}\n\n"
                
                if harm.get("dietetyk"):
                    md += f"### Konsultacje Dietetyczne w Miejscu Pracy\nIndywidualne spotkania z ekspertem żywieniowym bezpośrednio w Twoim biurze. Analiza nawyków, analiza składu ciała i spersonalizowane wskazówki. Plan obejmuje {harm.get('dni_dietetyk')} dni roboczych stacjonarnych konsultacji w firmie.\n\n"
                
                md += f"{OPISY_MARKETINGOWE['Webinary Edukacyjne']}\n\n"

            md += f"\n---\n"
            
        md += f"# Podsumowanie Opcji do Wyboru\n\n| Wariant / Opcja | Inwestycja Całkowita | Koszt na pracownika |\n|---|---|---|\n"
        for item in st.session_state['koszyk']: 
            if item.get('Abonament', False):
                mies = item['Cena za osobę'] / 12
                per_capita_str = f"{mies:.2f} PLN / msc"
            else:
                per_capita_str = f"{item['Cena za osobę']:.2f} PLN" if item['Cena za osobę'] > 0 else "-"
            md += f"| {item['Usługa']} | {item['Cena (Brutto)']:.2f} PLN | {per_capita_str} |\n"
        md += f"\n---\n"
        
        md += f"# Zapraszamy do współpracy\n### Skontaktuj się z nami\n\n**{handlowiec if handlowiec else 'Twój Opiekun'}** \n{stanowisko}  \n📧 {handlowiec_email if handlowiec_email else 'oferta@twojafirma.pl'}\n\n**Nota prawna:** Podane ceny są cenami końcowymi do zapłaty (Brutto). Usługi medyczne zwolnione z VAT na podst. art. 43 ust. 1 ustawy o VAT.\n"
        
        with st.expander("📄 KLIKNIJ TUTAJ, ABY POBRAĆ WSAD DO GAMMY (KOD MARKDOWN)", expanded=False):
            st.markdown("Instrukcja: Najedź myszką na poniższy kod i kliknij **ikonę kopiowania** (📋) w prawym górnym rogu. Wklej ten tekst w opcji 'Import -> Paste Text' w narzędziu Gamma AI.")
            st.code(md, language='markdown')

# --- ZARZĄDZANIE STRESEM ---
elif "Zarządzanie stresem" in wybor:
    st.header("🧠 Zarządzanie stresem – strategia psychologiczna")
    
    opcja = st.radio("Wybierz wariant:", ["Bez krwi (Testy psychologiczne + Webinar)", "Z krwią (Testy + Webinar + Pakiety Lab)"])
    
    df = get_supabase_data()
    suma_kosztow_lab = 0.0
    suma_cen_lab = 0.0
    wybrane_pakiety = []
    
    if "Z krwią" in opcja and not df.empty:
        wybrane_pakiety = st.multiselect("Wybierz pakiety laboratoryjne do akcji:", df['nazwa'].tolist())
        if wybrane_pakiety:
            koszyk_lab = df[df['nazwa'].isin(wybrane_pakiety)]
            suma_kosztow_lab = koszyk_lab['koszt'].sum()
            suma_cen_lab = koszyk_lab['cena'].sum()
            
            st.info(f"Cena detaliczna wybranego labu: {suma_cen_lab:.2f} PLN/osoba")
            st.caption(f"(Informacja dla handlowca: Kalkulator w tle używa kosztu hurtowego {suma_kosztow_lab:.2f} PLN/osoba)")
            
    st.divider()
    
    ile_lok = st.number_input("Ile lokalizacji?", 1, value=1, key="stres_lok")
    tabs = st.tabs([f"Lok. {i+1}" for i in range(ile_lok)])
    
    total_koszt_ops = 0.0
    total_pacjenci = 0
    opis_lok = ""

    for i, tab in enumerate(tabs):
        with tab:
            st.markdown(f"**Lokalizacja {i+1}**")
            col_m, col_z = st.columns([2, 1])
            with col_m:
                miasto = st.text_input(f"Miejscowość:", placeholder="np. Centrala", key=f"stres_city_{i}")
                nazwa_lok = miasto if miasto else f"Lok {i+1}"
            with col_z:
                n_zesp = st.number_input("Liczba Zespołów Lab", 1, 10, 1, key=f"stres_z_{i}")

            c1, c2 = st.columns(2)
            pacjenci = c1.number_input("Uczestnicy", 0, value=0, key=f"stres_p_{i}")
            km = c2.number_input("Km od Wawy", 0, value=0, key=f"stres_km_{i}")
            
            if pacjenci > 0:
                k_ops = 0.0
                if "Z krwią" in opcja:
                    dni = math.ceil(pacjenci / (100 * n_zesp))
                    k_pieleg = (pacjenci / 12.5) * 80.0
                    k_dojazd = km * 2 * STAWKA_KM * n_zesp
                    k_hotel = (dni * KOSZT_NOCLEGU * n_zesp) if (km > 150 or dni > 1) else 0.0
                    k_ops = k_pieleg + k_dojazd + k_hotel
                    st.markdown(f'<div class="op-info">⏱️ Logistyka Lab: {n_zesp} Zesp. ➡ <b>{dni} dni</b> pracy.</div>', unsafe_allow_html=True)
                
                total_koszt_ops += k_ops
                total_pacjenci += pacjenci
                opis_lok += f"- {nazwa_lok}: {pacjenci} os.\n"

    st.divider()
    if total_pacjenci > 0:
        koszt_uslugi_stres = total_pacjenci * 100.0 # Koszt psychologa
        koszt_lab = total_pacjenci * suma_kosztow_lab if "Z krwią" in opcja else 0.0
        przychod_lab = total_pacjenci * suma_cen_lab if "Z krwią" in opcja else 0.0
        
        razem_koszt = koszt_uslugi_stres + koszt_lab + total_koszt_ops
        
        s_min = przychod_lab + (koszt_uslugi_stres * 1.5) + (total_koszt_ops * 1.5)
        s_pref = przychod_lab + (koszt_uslugi_stres * 1.8) + (total_koszt_ops * 2.0)
        
        k1, k2, k3 = st.columns(3)
        k1.metric("1. KOSZT BAZOWY (z logistyką)", f"{razem_koszt:.2f} PLN")
        k2.metric("2. Min", f"{s_min:.2f} PLN")
        k3.metric("3. Pref", f"{s_pref:.2f} PLN")
        
        c_final_1, c_final_2 = st.columns([1, 1])
        with c_final_1:
            cena_klienta = st.number_input("CENA KOŃCOWA (BRUTTO/ZW):", value=s_pref, key="cena_stres")
            cena_per_capita = cena_klienta / total_pacjenci if total_pacjenci > 0 else 0
            st.caption(f"Wychodzi: **{cena_per_capita:.2f} PLN** za osobę")
        with c_final_2:
            st.write("Status:")
            status, msg, marza = straznik_rentownosci(razem_koszt, 0.0, cena_klienta)
            if status == "error": st.error(msg)
            elif status == "warning": st.warning(msg)
            else: st.success(msg)
            
        if st.button("➕ Dodaj do Oferty", key="btn_stres"):
            if status != "error":
                logistyka = f"Wariant: {opcja}\n{generuj_logistyke_opis(total_pacjenci, opis_lok)}"
                if wybrane_pakiety: logistyka += f"Pakiety Lab: {', '.join(wybrane_pakiety)}\n"
                dodaj_do_koszyka("Zarządzanie stresem", cena_klienta, cena_per_capita, 0, logistyka, marza)
            else: st.error("Brak rentowności!")

# --- WEBINARY ---
elif "Webinary i edukacja" in wybor:
    st.header("💻 Webinary i edukacja")
    st.info("Pojedynczy webinar: 3500 PLN | Pakiet 4 webinarów: 9500 PLN")
    
    wybrane_webinary = st.multiselect("Wybierz tematy:", WEBINARY_TEMATY)
    
    ilosc = len(wybrane_webinary)
    if ilosc > 0:
        if ilosc == 4: sugerowana_cena = 9500.0
        else: sugerowana_cena = ilosc * 3500.0
        
        st.metric("Sugerowana Cena Klienta", f"{sugerowana_cena:.2f} PLN")
        cena_klienta = st.number_input("Cena ostateczna brutto:", value=sugerowana_cena)
        
        if st.button("➕ Dodaj do Oferty"):
            logistyka = "Wybrane tematy:\n" + "\n".join([f"- {w}" for w in wybrane_webinary])
            dodaj_do_koszyka(f"Pakiet Edukacyjny ({ilosc} webinarów)", cena_klienta, 0, 0, logistyka, 100.0)

# --- PROGRAM ROCZNY (DYNAMICZNY SILNIK) ---
elif "Program Roczny (Abonament)" in wybor:
    st.header("📅 Tworzenie Rocznego Programu Zdrowotnego")
    st.info("Wprowadź parametry logistyczne, a system w czasie rzeczywistym przeliczy koszt wybranego harmonogramu na podstawie unikalnej wydajności każdej usługi.")
    
    st.markdown("### KROK 1: Gdzie jedziemy? (Parametry Logistyczne)")
    ile_lok_prog = st.number_input("Ile lokalizacji obejmuje program?", 1, value=1, key="prog_lok")
    tabs_prog = st.tabs([f"Lok. {i+1}" for i in range(ile_lok_prog)])
    
    lokalizacje_prog = []
    total_pacjenci_prog = 0
    opis_lok_prog = ""

    for i, tab in enumerate(tabs_prog):
        with tab:
            c1, c2, c3 = st.columns(3)
            miasto = c1.text_input(f"Miejscowość:", key=f"p_city_{i}")
            pacjenci = c2.number_input("Uczestnicy", 0, value=0, key=f"p_pac_{i}")
            km = c3.number_input("Km od Wawy", 0, value=0, key=f"p_km_{i}")
            
            if pacjenci > 0:
                lokalizacje_prog.append({"miasto": miasto, "pacjenci": pacjenci, "km": km})
                total_pacjenci_prog += pacjenci
                nazwa_lok = miasto if miasto else f"Lok {i+1}"
                opis_lok_prog += f"- {nazwa_lok}: {pacjenci} os.\n"
                
    st.divider()
    st.markdown("### KROK 2: Dobór Planu i Kalkulacja")
    
    tab1, tab2, tab3 = st.tabs(["1. Szablony Firm (Rekomendowane)", "2. Priorytety (Ankieta i Custom)", "3. Kalkulator Budżetu"])
    df_lab = get_supabase_data()
    lista_lab = df_lab['nazwa'].tolist() if not df_lab.empty else ["Brak Bazy Lab"]
    
    def zbuduj_nazwe_akcji(bazowa_akcja, wybrane_laby=None):
        if (bazowa_akcja == "Badania Lab" or bazowa_akcja == "Zarządzanie stresem (Z krwią)") and wybrane_laby:
            if isinstance(wybrane_laby, list): return f"{bazowa_akcja} (Pakiet: {', '.join(wybrane_laby)})"
            return f"{bazowa_akcja} (Pakiet: {wybrane_laby})"
        return bazowa_akcja

    with tab1:
        st.subheader("Dostosuj do charakterystyki firmy")
        profil = st.selectbox("Wybierz profil firmy:", ["Biuro / IT", "Zakład Produkcyjny / Praca fizyczna"])
        
        dietetyk = st.checkbox("➕ Dodaj Dni Konsultacji Dietetycznych (4000 PLN / dzień)", key="diet_s")
        dni_dietetyk = st.number_input("Ilość dni z dietetykiem (max 24 os/dzień):", 1, value=1, key="dni_diet_s") if dietetyk else 0
        
        st.markdown(f"#### Harmonogram ({profil}):")
        
        c1, c2, c3, c4 = st.columns(4)
        
        if profil == "Biuro / IT":
            akcje_szablon = ["Cukrzyca PREMIUM", "Dermatoskopia", "Zarządzanie stresem (Bez krwi)", "Profilaktyka Serca"]
            with c1: 
                st.info("**Q1**\nCukrzyca PREMIUM")
                web1 = st.selectbox("Webinar Q1:", WEBINARY_TEMATY, index=0, key="w1_b")
            with c2: 
                st.info("**Q2**\nDermatoskopia")
                web2 = st.selectbox("Webinar Q2:", WEBINARY_TEMATY, index=3, key="w2_b")
            with c3: 
                st.info("**Q3**\nZarządzanie stresem")
                web3 = st.selectbox("Webinar Q3:", WEBINARY_TEMATY, index=2, key="w3_b")
            with c4: 
                st.info("**Q4**\nProfilaktyka Serca")
                web4 = st.selectbox("Webinar Q4:", WEBINARY_TEMATY, index=1, key="w4_b")
                
            ops, mat_std, k_lab, p_lab = dynamiczny_kalkulator_programu(akcje_szablon, lokalizacje_prog, 0, 0)
            
            harmonogram_dict = {
                "Kwartał 1": {"akcja": akcje_szablon[0], "webinar": web1},
                "Kwartał 2": {"akcja": akcje_szablon[1], "webinar": web2},
                "Kwartał 3": {"akcja": akcje_szablon[2], "webinar": web3},
                "Kwartał 4": {"akcja": akcje_szablon[3], "webinar": web4},
                "dietetyk": dietetyk,
                "dni_dietetyk": dni_dietetyk
            }
        
        else:
            with c1: 
                st.info("**Q1**\nCukrzyca BASIC")
                web1 = st.selectbox("Webinar Q1:", WEBINARY_TEMATY, index=3, key="w1_p")
            with c2: 
                st.info("**Q2**\nSpirometria")
                web2 = st.selectbox("Webinar Q2:", WEBINARY_TEMATY, index=0, key="w2_p")
            with c3: 
                st.info("**Q3**\nProfilaktyka Serca")
                web3 = st.selectbox("Webinar Q3:", WEBINARY_TEMATY, index=1, key="w3_p")
            with c4: 
                st.info("**Q4**\nBadania Lab")
                q4_lab = st.selectbox("Pakiet Lab (Q4):", lista_lab, key="lab_p_q4")
                web4 = st.selectbox("Webinar Q4:", WEBINARY_TEMATY, index=2, key="w4_p")
            
            akcje_szablon = ["Cukrzyca BASIC", "Spirometria", "Profilaktyka Serca", "Badania Lab"]
            
            lab_koszt_os, lab_cena_os = 0.0, 0.0
            if not df_lab.empty:
                wybrany_wiersz = df_lab[df_lab['nazwa'] == q4_lab]
                if not wybrany_wiersz.empty:
                    lab_koszt_os = wybrany_wiersz.iloc[0]['koszt']
                    lab_cena_os = wybrany_wiersz.iloc[0]['cena']
            
            ops, mat_std, k_lab, p_lab = dynamiczny_kalkulator_programu(akcje_szablon, lokalizacje_prog, lab_koszt_os, lab_cena_os)
            
            harmonogram_dict = {
                "Kwartał 1": {"akcja": akcje_szablon[0], "webinar": web1},
                "Kwartał 2": {"akcja": akcje_szablon[1], "webinar": web2},
                "Kwartał 3": {"akcja": akcje_szablon[2], "webinar": web3},
                "Kwartał 4": {"akcja": zbuduj_nazwe_akcji(akcje_szablon[3], q4_lab), "webinar": web4},
                "dietetyk": dietetyk,
                "dni_dietetyk": dni_dietetyk
            }

        if total_pacjenci_prog > 0:
            cena_sugerowana = p_lab + ((ops + mat_std) * 1.8) + 9500.0 + (dni_dietetyk * 4000)
            
            st.divider()
            st.metric("Sugerowana Cena Roczna (Całość wyliczona z dokładnych wydajności)", f"{cena_sugerowana:.2f} PLN")
            cena_final = st.number_input("Ostateczna cena roczna za program:", value=cena_sugerowana, key="abon_cena_1")
            
            miesieczna = cena_final / total_pacjenci_prog / 12
            st.success(f"**Miesięczna inwestycja pracodawcy: {miesieczna:.2f} PLN / pracownika**")
            
            if st.button("➕ Dodaj Program Szablonowy do Oferty"):
                log = f"Profil: {profil}\nObjętych programem: {total_pacjenci_prog} os.\nLokalizacje:\n{opis_lok_prog}\n"
                if dietetyk: log += f"Dodatkowo: {dni_dietetyk} dni konsultacji dietetycznych."
                dodaj_do_koszyka(f"Roczny Program: {profil}", cena_final, cena_final/total_pacjenci_prog, 0, log, 100.0, is_abonament=True, harmonogram=harmonogram_dict)

    with tab2:
        st.subheader("Dostosuj na podstawie priorytetów (Custom Builder)")
        priorytet = st.selectbox("Główny cel klienta:", [
            "Choroby krążenia", "Profilaktyka otyłości / cukrzycy", 
            "Kondycja psychiczna / Stres", "Ogólny Screening Zdrowia"
        ])
        
        st.write("Sugerowane działania dla tego celu:")
        if priorytet == "Choroby krążenia": st.success("Polecamy: Profilaktyka Serca, Cukrzyca, Lab (Lipidogram), Webinar Żywieniowy")
        elif priorytet == "Kondycja psychiczna / Stres": st.success("Polecamy: Zarządzanie stresem, Dietetyk, Webinar o śnie")
        elif priorytet == "Profilaktyka otyłości / cukrzycy": st.success("Polecamy: Cukrzyca, Profilaktyka Serca, Dietetyk, Badania Lab, USG jamy brzusznej")
        elif priorytet == "Ogólny Screening Zdrowia": st.success("Polecamy: Cukrzyca, Profilaktyka Serca, Badania Lab, Dermatoskopia")
        
        dietetyk_custom = st.checkbox("➕ Dodaj Dni Konsultacji Dietetycznych (4000 PLN / dzień)", key="diet_c")
        dni_dietetyk_custom = st.number_input("Ilość dni z dietetykiem (max 24 os/dzień):", 1, value=1, key="dni_diet_c") if dietetyk_custom else 0
        
        st.markdown("Zbuduj własny harmonogram (system w locie przeliczy wydajność dla każdej opcji):")
        opcje_custom = ["Brak", "Badania Lab", "Dermatoskopia", "USG", "Spirometria", "Cukrzyca BASIC", "Cukrzyca PREMIUM", "Profilaktyka Serca", "Zarządzanie stresem (Bez krwi)", "Zarządzanie stresem (Z krwią)"]
        
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            q1_w = st.selectbox("Akcja Q1", opcje_custom, index=1)
            wb1 = st.selectbox("Web. Q1", WEBINARY_TEMATY, index=0)
        with c2:
            q2_w = st.selectbox("Akcja Q2", opcje_custom, index=2)
            wb2 = st.selectbox("Web. Q2", WEBINARY_TEMATY, index=1)
        with c3:
            q3_w = st.selectbox("Akcja Q3", opcje_custom, index=8)
            wb3 = st.selectbox("Web. Q3", WEBINARY_TEMATY, index=2)
        with c4:
            q4_w = st.selectbox("Akcja Q4", opcje_custom, index=4)
            wb4 = st.selectbox("Web. Q4", WEBINARY_TEMATY, index=3)
        
        akcje_custom = [q1_w, q2_w, q3_w, q4_w]
        
        lab_koszt_cust, lab_cena_cust = 0.0, 0.0
        wybrane_custom_lab = []
        if "Badania Lab" in akcje_custom or "Zarządzanie stresem (Z krwią)" in akcje_custom:
            wybrane_custom_lab = st.multiselect("Wybrałeś akcję wymagającą laboratorium. Zaznacz pakiety do wykonania:", lista_lab, key="lab_custom_sel")
            if wybrane_custom_lab and not df_lab.empty:
                koszyk_lab_cust = df_lab[df_lab['nazwa'].isin(wybrane_custom_lab)]
                lab_koszt_cust = koszyk_lab_cust['koszt'].sum()
                lab_cena_cust = koszyk_lab_cust['cena'].sum()

        if total_pacjenci_prog > 0:
            ops_c, mat_c, k_lab_c, p_lab_c = dynamiczny_kalkulator_programu(akcje_custom, lokalizacje_prog, lab_koszt_cust, lab_cena_cust)
            cena_sug_custom = p_lab_c + ((ops_c + mat_c) * 1.8) + 9500.0 + (dni_dietetyk_custom * 4000)
            
            st.divider()
            cena_manualna = st.number_input("Wpisz łączną cenę roczną za ten program (sugerowana z wyliczeń logistyki obok):", value=cena_sug_custom)
            mies_m = cena_manualna / total_pacjenci_prog / 12
            st.success(f"**Miesięczna inwestycja: {mies_m:.2f} PLN / pracownika**")
            
            harmonogram_custom = {
                "Kwartał 1": {"akcja": zbuduj_nazwe_akcji(q1_w, wybrane_custom_lab), "webinar": wb1},
                "Kwartał 2": {"akcja": zbuduj_nazwe_akcji(q2_w, wybrane_custom_lab), "webinar": wb2},
                "Kwartał 3": {"akcja": zbuduj_nazwe_akcji(q3_w, wybrane_custom_lab), "webinar": wb3},
                "Kwartał 4": {"akcja": zbuduj_nazwe_akcji(q4_w, wybrane_custom_lab), "webinar": wb4},
                "dietetyk": dietetyk_custom,
                "dni_dietetyk": dni_dietetyk_custom
            }
            
            if st.button("➕ Dodaj Custom Program do Oferty"):
                log = f"Priorytet: {priorytet}\nPacjenci: {total_pacjenci_prog}\nLokalizacje:\n{opis_lok_prog}\n"
                if dietetyk_custom: log += f"Dodatkowo: {dni_dietetyk_custom} dni konsultacji dietetycznych."
                dodaj_do_koszyka("Indywidualny Program Zdrowotny", cena_manualna, cena_manualna/total_pacjenci_prog, 0, log, 100.0, is_abonament=True, harmonogram=harmonogram_custom)
            
    with tab3:
        st.subheader("Odwrócona kalkulacja budżetu")
        if total_pacjenci_prog == 0:
            st.warning("Najpierw uzupełnij KROK 1 na samej górze (Lokalizacje i uczestnicy), aby system przeliczył budżet!")
        else:
            budzet_miesiac = st.number_input("Jaki jest budżet klienta (PLN / pracownika / miesiąc)?", value=30.0)
            budzet_roczny_calkowity = budzet_miesiac * 12 * total_pacjenci_prog
            st.metric("Roczny budżet całkowity firmy na program", f"{budzet_roczny_calkowity:.2f} PLN")
            
            ops_min, mat_min, _, _ = dynamiczny_kalkulator_programu(["Spirometria"]*4, lokalizacje_prog, 0, 0)
            koszt_bazowy_bez_uslug = ops_min + 9500 
            
            zostaje_na_uslugi = budzet_roczny_calkowity - koszt_bazowy_bez_uslug
            na_usluge_per_capita = zostaje_na_uslugi / total_pacjenci_prog if total_pacjenci_prog > 0 else 0
            
            st.write(f"Po odliczeniu podstawowych kosztów logistyki i edukacji (webinarów), zostaje Ci orientacyjnie **{na_usluge_per_capita:.2f} PLN na osobę** na usługi medyczne.")
            
            if na_usluge_per_capita < 50: st.warning("Budżet wystarczy na mniejsze akcje (np. Cukrzyca BASIC) lub na 2 mocne akcje zamiast 4.")
            elif na_usluge_per_capita < 150: st.info("Optymalny budżet. Pozwoli na miks (np. Laby, Dermatoskopia, Stres).")
            else: st.success("Budżet PREMIUM. Zrealizujesz za to pełne USG, szerokie pakiety Lab z krwią i dietetyka.")
            
            st.info("💡 Przejdź do zakładki '2. Priorytety (Ankieta i Custom)', zbuduj plan i sprawdź, czy Sugerowana Cena mieści się w Rocznym Budżecie z tej zakładki.")

# --- LOGIKA LAB ---
elif "Badania Laboratoryjne" in wybor:
    st.header("🧪 Kreator Pakietu Badań")
    
    vouchery = st.checkbox("🎫 Wyceń w formie voucherów (+10 PLN / osobę do sugerowanej ceny klienta)")
    badania_dodatkowe = st.checkbox("🩸 Dodaj adnotację o badaniach dodatkowych dla pracowników (-30%)")
    
    df = get_supabase_data()
    if df.empty: st.stop()
    
    c1, c2 = st.columns([1, 1])
    with c1: 
        wybrane = st.multiselect("Wybierz pakiety badań:", df['nazwa'].tolist())
    
    suma_kosztow, suma_cen, suma_rynkowa = 0.0, 0.0, 0.0
    szczegoly_pakietow_do_oferty = ""

    if wybrane:
        koszyk_lab = df[df['nazwa'].isin(wybrane)]
        suma_kosztow = koszyk_lab['koszt'].sum()
        suma_cen = koszyk_lab['cena'].sum()
        if 'cena_rynkowa' in koszyk_lab.columns: suma_rynkowa = koszyk_lab['cena_rynkowa'].sum()
        
        with c2: 
            st.markdown("**Wybrane Pakiety:**")
            for index, row in koszyk_lab.iterrows():
                sklad = row.get('skladniki', 'Brak szczegółowego opisu.')
                st.info(f"🧬 **{row['nazwa']}**\n\n*Skład:* {sklad}")
                szczegoly_pakietow_do_oferty += f"- **{row['nazwa']}**: {sklad}\n"
                
        c3, c4 = st.columns(2)
        if suma_rynkowa > 0: c3.metric("Sugerowana CENA RYNKOWA", f"{suma_rynkowa:.2f} PLN")
        c4.metric("NASZA CENA", f"{suma_cen:.2f} PLN")
    
    st.divider()
    ile_lok = st.number_input("Ile lokalizacji?", 1, value=1)
    tabs = st.tabs([f"Lok. {i+1}" for i in range(ile_lok)])
    
    total_koszt_ops, total_koszt_lab, total_przychod_lab, total_pacjenci = 0.0, 0.0, 0.0, 0
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
                if vouchery:
                    k_ops = 0.0
                    total_koszt_ops += k_ops
                    total_koszt_lab += (pacjenci * suma_kosztow)
                    total_przychod_lab += (pacjenci * suma_cen)
                    total_pacjenci += pacjenci
                    opis_lok += f"- {nazwa_lok}: {pacjenci} os. (Vouchery)\n"
                    st.markdown(f'<div class="op-info">🎫 <b>Vouchery</b> – obsługa w placówce. Brak kosztów logistyki dojazdowej i personelu.</div>', unsafe_allow_html=True)
                else:
                    dni = math.ceil(pacjenci / (100 * n_zesp))
                    symulacja = symulacja_czasu(pacjenci, 100, 5)
                    
                    k_ops = ((pacjenci / 12.5) * 80.0) + (km * 2 * STAWKA_KM * n_zesp) + ((dni * KOSZT_NOCLEGU * n_zesp) if (km > 150 or dni > 1) else 0.0)
                    
                    total_koszt_ops += k_ops
                    total_koszt_lab += (pacjenci * suma_kosztow)
                    total_przychod_lab += (pacjenci * suma_cen)
                    total_pacjenci += pacjenci
                    
                    opis_lok += f"- {nazwa_lok}: {pacjenci} os. ({n_zesp} zesp. lab)\n"
                    st.markdown(f'<div class="op-info">⏱️ {n_zesp} Zesp. Lab ➡ <b>{dni} dni</b> pracy.<br>💡 Alternatywy: {symulacja}</div>', unsafe_allow_html=True)

    razem_koszt = total_koszt_ops + total_koszt_lab
    st.divider()
    if total_pacjenci > 0:
        k1, k2, k3 = st.columns(3)
        k1.metric("1. KOSZT BAZOWY (z lab)", f"{razem_koszt:.2f} PLN")
        
        if vouchery:
            s_pref = total_przychod_lab + (total_pacjenci * 10.0)
        else:
            s_pref = total_przychod_lab + (total_koszt_ops * 2.0)
            
        k3.metric("3. Pref", f"{s_pref:.2f} PLN")
        
        c1, c2 = st.columns(2)
        with c1:
            cena = st.number_input("CENA KOŃCOWA (BRUTTO/ZW):", value=s_pref)
            cena_per_capita = cena / total_pacjenci if total_pacjenci > 0 else 0
            st.caption(f"Wychodzi: **{cena_per_capita:.2f} PLN** za osobę")
        with c2: 
            status, msg, marza = straznik_rentownosci(razem_koszt, 0.0, cena)
            if status == "error": st.error(msg)
            else: st.success(msg)
        
        if st.button("➕ Dodaj Pakiet Lab do Oferty"):
            if status!="error": 
                logistyka = f"**Wybrane Pakiety i ich skład:**\n{szczegoly_pakietow_do_oferty}\n{generuj_logistyke_opis(total_pacjenci, opis_lok)}"
                
                if vouchery:
                    logistyka += "\n\n> **Forma realizacji:** Vouchery dla pracowników (koszt obsługi wliczony w cenę całkowitą)."
                
                if badania_dodatkowe:
                    logistyka += "\n\n> **Badania Dodatkowe:** Podczas akcji pobierania krwi istnieje możliwość wykonania dodatkowych oznaczeń parametrów z tego samego pobrania. Obejmuje to badania na życzenie pacjenta, z atrakcyjnym rabatem na poziomie 30% od cen rynkowych."
                
                dodaj_do_koszyka(f"Badania Laboratoryjne: {', '.join(wybrane)}", cena, cena_per_capita, suma_rynkowa, logistyka, marza)

# --- POZOSTAŁE USŁUGI STANDARDOWE ---
elif "Cukrzyca BASIC" in wybor: 
    render_usluga_standard("Cukrzyca BASIC", 640, 1000, 40, 50, max_zespolow=5)
elif "Cukrzyca PREMIUM" in wybor: 
    render_usluga_standard("Cukrzyca PREMIUM", 640, 1000, 40, 50, 320, 500, max_zespolow=5)
elif "Kardiologia" in wybor: 
    render_usluga_standard("Profilaktyka Serca", 640, 1000, 30, 50, max_zespolow=3)
elif "Spirometria" in wybor: 
    render_usluga_standard("Spirometria", 1000, 1200, 5, 40, max_zespolow=2)
elif "USG w Firmie" in wybor: 
    render_usluga_standard("USG", 5000, 5500, 0, 30, koszt_mat_dzien=200, max_zespolow=2)
elif "Dermatoskopia" in wybor: 
    render_usluga_standard("Dermatoskopia", 4500, 5500, 0, 45, max_zespolow=3)
