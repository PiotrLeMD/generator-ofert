import streamlit as st
import pandas as pd
from supabase import create_client, Client
import math
from datetime import date

# --- 1. KONFIGURACJA ---
st.set_page_config(page_title="Generator Ofert Medycznych", page_icon="🏥", layout="wide", initial_sidebar_state="expanded")

# --- 2. SYSTEM LOGOWANIA (POPRAWIONY) ---
def check_password():
    """Zwraca True, jeśli użytkownik wpisał poprawne hasło."""
    
    def password_entered():
        # Sprawdza czy login istnieje w sekcji [passwords] w Secrets i czy hasło się zgadza
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            # ZAPISUJEMY LOGIN NA STAŁE, ABY NIE ZNIKNĄŁ PO ZALOGOWANIU:
            st.session_state["logged_in_user"] = st.session_state["username"] 
            del st.session_state["password"]  # Kasujemy hasło z pamięci
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Ekran startowy (niezalogowany)
        st.markdown("<h1 style='text-align: center;'>Zaloguj się do systemu</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("E-mail (Login)", key="username")
            st.text_input("Hasło", type="password", key="password")
            st.button("Zaloguj", on_click=password_entered, use_container_width=True)
        return False
    elif not st.session_state["password_correct"]:
        # Błędne hasło
        st.markdown("<h1 style='text-align: center;'>Zaloguj się do systemu</h1>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.text_input("E-mail (Login)", key="username")
            st.text_input("Hasło", type="password", key="password")
            st.button("Zaloguj", on_click=password_entered, use_container_width=True)
            st.error("⛔ Błędny login lub hasło. Spróbuj ponownie.")
        return False
    else:
        # Zalogowano poprawnie!
        return True

# --- URUCHOMIENIE STRAŻNIKA ---
if not check_password():
    st.stop() # Jeśli False, zatrzymujemy kod i nie pokazujemy aplikacji!

# =========================================================================
# === PONIŻEJ ZACZYNA SIĘ WŁAŚCIWA APLIKACJA (UKRYTA PRZED NIEZALOGOWANYMI) ===
# =========================================================================

if 'koszyk' not in st.session_state: st.session_state['koszyk'] = []

st.markdown("""
    <style>
    .big-font { font-size:18px !important; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; font-weight: bold;}
    .header-style { background-color: #f0f2f6; padding: 15px; border-radius: 10px; margin-bottom: 20px;}
    .op-info { background-color: #e8f4f8; padding: 10px; border-radius: 5px; border-left: 5px solid #2196f3; font-size: 14px; margin-bottom: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- OPISY MARKETINGOWE ---
OPISY_MARKETINGOWE = {
    "Badania Laboratoryjne": "### Mobilny Punkt Pobrań\nWygodny dostęp do diagnostyki laboratoryjnej bez konieczności dojazdów pracowników do placówek.\n* **Organizacja:** Sprawny proces rejestracji i pobrania krwi w siedzibie firmy.\n* **Wyniki:** Udostępniane online bezpośrednio pracownikowi (pełna poufność).\n* **Edukacja:** Opcjonalnie webinar podsumowujący – omówienie znaczenia badań i najczęstszych odchyleń w populacji.\n* **Raportowanie:** Możliwość przygotowania anonimowego raportu zbiorczego dla pracodawcy (analiza trendów zdrowotnych).",
    "Cukrzyca BASIC": "### Profilaktyka Cukrzycy (Pakiet BASIC)\nSzybki screening w kierunku zaburzeń glikemii i ryzyka cukrzycy typu 2.\n* **Badanie:** Oznaczenie poziomu HbA1c (hemoglobiny glikowanej) z kropli krwi z palca – wynik dostępny natychmiast na miejscu.\n* **Ocena ryzyka:** Wywiad medyczny, pomiary antropometryczne oraz analiza ryzyka wystąpienia cukrzycy w ciągu najbliższych 10 lat (wg walidowanego narzędzia).\n* **Zalecenia:** Pracownik otrzymuje indywidualny kod QR. Po jego zeskanowaniu uzyskuje spersonalizowane zalecenia i plan dalszego postępowania.",
    "Cukrzyca PREMIUM": "### Profilaktyka Cukrzycy (Pakiet PREMIUM)\nRozszerzona diagnostyka metaboliczna pozwalająca wykryć ukryte zagrożenia.\n* **Zakres BASIC + Analiza Składu Ciała:** Profesjonalne badanie na urządzeniu klasy medycznej (InBody).\n* **Co badamy?** Identyfikacja ryzyka metabolicznego związanego z niewidocznym gołym okiem problemem (np. nagromadzenie aktywnego metabolicznie tłuszczu trzewnego lub obniżona masa mięśniowa).\n* **Efekt:** Pełny obraz kondycji metabolicznej pracownika i konkretne wskazówki dietetyczne.",
    "Profilaktyka Chorób Serca": "### Ryzyko Sercowo-Naczyniowe\nKompleksowa ocena układu krążenia w celu zapobiegania zawałom i udarom.\n* **Badania:** Pełny lipidogram z kropli krwi z palca (wynik na miejscu) oraz pomiar ciśnienia tętniczego.\n* **Ocena ryzyka:** Wywiad zdrowotny i analiza ryzyka wystąpienia incydentu sercowo-naczyniowego (zawał, udar) w perspektywie 10 lat.\n* **Zalecenia:** Raport oraz kod QR z indywidualnymi wskazówkami dotyczącymi diety i stylu życia, dostosowanymi do wyników pracownika.",
    "Spirometria": "### Spirometria – Zdrowe Płuca\nBadanie przesiewowe układu oddechowego, kluczowe w profilaktyce po-covidowej i środowiskowej.\n* **Cel:** Wczesna identyfikacja schorzeń takich jak astma oskrzelowa lub POChP.\n* **Przebieg:** Badanie prowadzone przez uprawnionego medyka z zachowaniem najwyższych standardów higienicznych (ustniki jednorazowe/filtry).\n* **Wynik:** Natychmiastowa informacja o wydolności płuc i zalecenia dotyczące dalszego postępowania w razie nieprawidłowości.",
    "USG w Miejscu Pracy": "### Mobilny Gabinet USG\nProfilaktyczne badania ultrasonograficzne wykonywane na miejscu u pracodawcy przez doświadczonych lekarzy.\n* **Zakres (do wyboru):** USG tarczycy, jamy brzusznej, jąder lub piersi.\n* **Przebieg:** Badanie trwa średnio ok. 15 minut na osobę. USG pozwala wcześnie wykryć zmiany niewyczuwalne w badaniu palpacyjnym.\n* **Wynik:** Pracownik otrzymuje opis pisemny od razu po badaniu wraz z ewentualnym skierowaniem na dalszą diagnostykę.",
    "Dermatoskopia": "### Dermatoskopia – Profilaktyka Czerniaka\nKonsultacja dermatologiczna z oceną znamion i zmian skórnych.\n* **Cel:** Wczesna identyfikacja zmian wymagających obserwacji lub pilnej diagnostyki (profilaktyka nowotworów skóry).\n* **Specjalista:** Badanie prowadzone przez lekarza dermatologa przy użyciu dermatoskopu.\n* **Zalecenia:** Pracownik otrzymuje konkretną informację: kontrola, dalsza diagnostyka lub zalecenia dotyczące ochrony przeciwsłonecznej."
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
            if 'cena' in df.columns: df['cena'] = pd.to_numeric(df['cena'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"⚠️ Błąd bazy: {e}")
        return pd.DataFrame()

KOSZT_NOCLEGU = 400.0
STAWKA_KM = 2.0
LIMIT_LOKALIZACJI = 20

# --- FUNKCJE LOGICZNE ---
def dodaj_do_koszyka(nazwa, cena, logistyka_opis, marza_procent):
    st.session_state['koszyk'].append({
        "Usługa": nazwa, "Cena": cena, "Marża %": f"{marza_procent:.1f}%", "Logistyka": logistyka_opis
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

# --- INTERFEJS USŁUG ---
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

# --- MENU GŁÓWNE ---
st.sidebar.title("Nawigacja")
# Wyświetlamy informację o tym, kto jest zalogowany (ZMIANA NA TRWAŁĄ ZMIENNĄ)
st.sidebar.caption(f"Zalogowano jako: **{st.session_state.get('logged_in_user', '')}**")
st.sidebar.markdown("---")

n_koszyk = len(st.session_state['koszyk'])
wybor = st.sidebar.radio("Menu:", ["ZESTAWIENIE OFERTY " + (f"📋 ({n_koszyk})" if n_koszyk>0 else "📋"), "---", "Badania Laboratoryjne (Pakiet)", "Cukrzyca BASIC", "Cukrzyca PREMIUM", "Kardiologia", "Spirometria", "USG w Firmie", "Dermatoskopia"])
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
            handlowiec = st.text_input("Imię i Nazwisko:", placeholder="Twoje Imię")
            stanowisko = st.text_input("Stanowisko:", value="Manager ds. Klientów")
            # Podpowiadamy login jako e-mail z trwałej zmiennej
            handlowiec_email = st.text_input("Email (Ty):", value=st.session_state.get('logged_in_user', ''))

    st.divider()
    if st.session_state['koszyk']:
        df = pd.DataFrame(st.session_state['koszyk'])
        df = df.rename(columns={"Cena": "Cena (Brutto)"})
        st.dataframe(df[["Usługa", "Cena (Brutto)", "Marża %"]], use_container_width=True, hide_index=True)
        
        suma = df["Cena (Brutto)"].sum()
        
        st.divider()
        st.subheader("🚀 Generowanie Prezentacji")
        st.info("Poniżej znajduje się gotowy kod dla AI Gamma.")

        today = date.today().strftime("%d.%m.%Y")
        md = f"# Oferta Współpracy Medycznej\n### Dla: {klient if klient else 'Naszego Klienta'}\n"
        if adres: md += f"**Adres:** {adres}\n"
        if kontakt: md += f"**Osoba kontaktowa:** {kontakt}\n"
        if kontakt_email: md += f"**Email:** {kontakt_email}\n"
        md += f"**Data:** {today}\n\n---\n"
        
        md += f"# Strefa Zdrowia w Twojej Firmie\n### Profilaktyka bez wychodzenia z biura\n\nOrganizujemy profesjonalne badania i konsultacje medyczne bezpośrednio w siedzibie Twojej firmy. Nasz mobilny zespół medyczny tworzy szybkie i doskonale zorganizowane stanowiska diagnostyczne.\n\n### Proces Realizacji\n1. **Analiza:** Dobieramy odpowiednie moduły (np. Dzień Zdrowia, Roczny Program).\n2. **Realizacja:** Przyjeżdżamy z pełnym sprzętem. Potrzebujemy tylko sali.\n3. **Raport:** Indywidualne wyniki dla pracowników i anonimowy raport zbiorczy dla firmy.\n\n> **Bezpieczeństwo:** Działamy zgodnie z RODO i tajemnicą medyczną.\n\n---\n"
        
        for i, item in enumerate(st.session_state['koszyk']):
            nazwa = item['Usługa']
            opis_marketingowy = OPISY_MARKETINGOWE.get(nazwa, "### Szczegóły usługi\nIndywidualnie dopasowany zakres badań.")
            clean_logistyka = item['Logistyka'].replace("\n", "  \n")
            md += f"# Opcja {i+1}: {nazwa}\n{opis_marketingowy}\n\n### Parametry Twojej Realizacji\n{clean_logistyka}\n\n> **Inwestycja: {item['Cena']:.2f} PLN (zw. z VAT)**\n\n---\n"
            
        md += f"# Podsumowanie Kosztów\n\n| Usługa | Cena (Brutto) |\n|---|---|\n"
        for item in st.session_state['koszyk']: md += f"| {item['Usługa']} | {item['Cena']:.2f} PLN |\n"
        md += f"| **RAZEM** | **{suma:.2f} PLN** |\n\n---\n"
        
        md += f"# Zapraszamy do współpracy\n### Skontaktuj się z nami\n\n**{handlowiec if handlowiec else 'Twój Opiekun'}** \n{stanowisko}  \n📧 {
