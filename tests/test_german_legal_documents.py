#!/usr/bin/env python3
"""
German Legal Documents Test

Testet das Covina System mit deutschen Gesetzen aus Y:\data\00_bund_gesetze_auswahl
Fokus auf deutsches spaCy NLP und rechtliche Entity Recognition.
"""

import logging
from pathlib import Path
import sys
import time
from datetime import datetime

# Setup
sys.path.append(str(Path.cwd()))

# Logging für detaillierte Analyse
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'german_legal_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)

def test_german_legal_documents():
    """Test German legal documents with Discovery Service"""
    
    print("⚖️ German Legal Documents Test")
    print("=" * 60)
    
    # Gesetz-Verzeichnis
    legal_docs_path = Path("Y:/data/00_bund_gesetze_auswahl")
    
    # Prüfe ob Verzeichnis existiert
    if not legal_docs_path.exists():
        print(f"❌ Verzeichnis nicht gefunden: {legal_docs_path}")
        print("   Bitte prüfen Sie den Pfad zu den Gesetzestexten.")
        return False
    
    print(f"📁 Gesetz-Verzeichnis: {legal_docs_path}")
    
    # Scanne verfügbare Gesetze
    legal_files = []
    for pattern in ['*.txt', '*.pdf', '*.md', '*.doc', '*.docx', '*.rtf']:
        legal_files.extend(legal_docs_path.glob(pattern))
    
    if not legal_files:
        # Prüfe Unterverzeichnisse
        for subdir in legal_docs_path.iterdir():
            if subdir.is_dir():
                for pattern in ['*.txt', '*.pdf', '*.md', '*.doc', '*.docx', '*.rtf']:
                    legal_files.extend(subdir.glob(pattern))
    
    print(f"📊 Gefundene Gesetzes-Dateien: {len(legal_files)}")
    
    if not legal_files:
        print("⚠️ Keine Gesetzesdateien gefunden. Unterstützte Formate: .txt, .pdf, .md, .doc, .docx, .rtf")
        return False
    
    # Zeige die ersten 10 Dateien
    print(f"\n📋 Erste {min(10, len(legal_files))} Dateien:")
    for i, file_path in enumerate(legal_files[:10], 1):
        file_size = file_path.stat().st_size if file_path.exists() else 0
        print(f"   {i:2d}. {file_path.name} ({file_size:,} bytes)")
    
    if len(legal_files) > 10:
        print(f"   ... und {len(legal_files) - 10} weitere Dateien")
    
    # Discovery Service Setup
    print(f"\n🔧 Initialisiere Discovery Service...")
    
    try:
        from ingestion.scanner import DirectoryScanner
        from ingestion.discovery_service import FileDiscoveryService
        
        # Mock Job Factory für Test
        class LegalDocumentJobFactory:
            def __init__(self):
                self.processed_docs = []
                self.legal_entities = []
                self.pii_findings = []
                self.processing_stats = {
                    'total_files': 0,
                    'successful': 0,
                    'errors': 0,
                    'total_entities': 0,
                    'legal_terms': 0,
                    'persons': 0,
                    'organizations': 0,
                    'locations': 0
                }
                
                # Interne Metriken für Ingestion-Analyse
                self.processing_times = []
                self.classification_stats = {}
                self.extraction_stats = {'total_characters': 0, 'avg_characters_per_file': 0}
                self.metadata_stats = {'avg_completeness': 0, 'completeness_values': []}
                self.ai_stats = {'files_processed': 0, 'avg_confidence': 0, 'confidence_values': []}
                self.backend_stats = {
                    'vector_database': {'documents': 0, 'chunks': 0, 'embeddings': 0, 'keywords': 0},
                    'graph_database': {'documents': 0, 'internal_relations': 0, 'external_relations': 0, 'entities': 0},
                    'relational_database': {'documents': 0, 'metadata_fields': 0, 'classifications': 0, 'timestamps': 0},
                    'file_system': {'documents': 0, 'raw_files': 0, 'processed_files': 0, 'backups': 0}
                }
                self.error_stats = {}
            
            def submit(self, event):
                self.processed_docs.append({
                    'file': Path(event.path).name,
                    'path': event.path,
                    'timestamp': datetime.now()
                })
                self.processing_stats['total_files'] += 1
                print(f"📋 Gesetz verarbeitet: {Path(event.path).name}")
            
            def add_processing_time(self, duration):
                """Fügt Verarbeitungszeit hinzu"""
                self.processing_times.append(duration)
            
            def add_classification(self, doc_type):
                """Fügt Klassifikationsergebnis hinzu"""
                self.classification_stats[doc_type] = self.classification_stats.get(doc_type, 0) + 1
            
            def add_extraction_metrics(self, char_count):
                """Fügt Content-Extraktion-Metriken hinzu"""
                self.extraction_stats['total_characters'] += char_count
                if self.processing_stats['total_files'] > 0:
                    self.extraction_stats['avg_characters_per_file'] = self.extraction_stats['total_characters'] / self.processing_stats['total_files']
            
            def add_metadata_completeness(self, completeness):
                """Fügt Metadata-Completeness hinzu"""
                if 'total_completeness' not in self.metadata_stats:
                    self.metadata_stats['total_completeness'] = 0
                    self.metadata_stats['file_count'] = 0
                
                self.metadata_stats['total_completeness'] += completeness
                self.metadata_stats['file_count'] += 1
                self.metadata_stats['completeness_values'].append(completeness)
                if self.metadata_stats['completeness_values']:
                    self.metadata_stats['avg_completeness'] = sum(self.metadata_stats['completeness_values']) / len(self.metadata_stats['completeness_values'])
            
            def add_ai_confidence(self, confidence):
                """Fügt AI-Confidence-Score hinzu"""
                if 'confidence_scores' not in self.ai_stats:
                    self.ai_stats['confidence_scores'] = []
                    self.ai_stats['total_entities_found'] = 0
                    self.ai_stats['total_pii_found'] = 0
                
                self.ai_stats['files_processed'] += 1
                self.ai_stats['confidence_scores'].append(confidence)
                self.ai_stats['confidence_values'].append(confidence)
                if self.ai_stats['confidence_values']:
                    self.ai_stats['avg_confidence'] = sum(self.ai_stats['confidence_values']) / len(self.ai_stats['confidence_values'])
            
            def add_ai_entities_found(self, count):
                """Fügt Anzahl gefundener AI-Entitäten hinzu"""
                if 'total_entities_found' not in self.ai_stats:
                    self.ai_stats['total_entities_found'] = 0
                self.ai_stats['total_entities_found'] += count
            
            def add_ai_pii_found(self, count):
                """Fügt Anzahl gefundener PII-Elemente hinzu"""
                if 'total_pii_found' not in self.ai_stats:
                    self.ai_stats['total_pii_found'] = 0
                self.ai_stats['total_pii_found'] += count
            
            def add_classification_stat(self, doc_type):
                """Fügt Klassifikationsergebnis hinzu"""
                if not hasattr(self, 'classification_stats'):
                    self.classification_stats = {}
                self.classification_stats[doc_type] = self.classification_stats.get(doc_type, 0) + 1
            
            def add_backend_metrics(self, document_name):
                """Simuliert Backend-Schreibvorgänge basierend auf Dokumenttyp"""
           <?xml version="1.0" encoding="utf-8"?>
<resources xmlns:ns1="urn:oasis:names:tc:xliff:document:1.2" xmlns:ns2="http://schemas.android.com/tools">
    <plurals name="mtrl_badge_content_description">
    <item quantity="one">%d nytt varsel</item>
    <item quantity="other">%d nye varsler</item>
  </plurals>
    <string msgid="5976598919945601918" name="abc_action_bar_home_description">"Naviger hjem"</string>
    <string msgid="8388173803310557296" name="abc_action_bar_up_description">"Gå opp"</string>
    <string msgid="3937310113216875497" name="abc_action_menu_overflow_description">"Flere alternativer"</string>
    <string msgid="4692188335987374352" name="abc_action_mode_done">"Ferdig"</string>
    <string msgid="1189761859438369441" name="abc_activity_chooser_view_see_all">"Se alle"</string>
    <string msgid="2165779757652331008" name="abc_activitychooserview_choose_application">"Velg en app"</string>
    <string msgid="4215997306490295099" name="abc_capital_off">"AV"</string>
    <string msgid="884982626291842264" name="abc_capital_on">"PÅ"</string>
    <string msgid="8833365367933412986" name="abc_menu_alt_shortcut_label">"Alt+"</string>
    <string msgid="2223301931652355242" name="abc_menu_ctrl_shortcut_label">"Ctrl+"</string>
    <string msgid="838001238306846836" name="abc_menu_delete_shortcut_label">"slett"</string>
    <string msgid="7986526966204849475" name="abc_menu_enter_shortcut_label">"enter"</string>
    <string msgid="375214403600139847" name="abc_menu_function_shortcut_label">"Funksjon+"</string>
    <string msgid="4192209724446364286" name="abc_menu_meta_shortcut_label">"Meta+"</string>
    <string msgid="4741552369836443843" name="abc_menu_shift_shortcut_label">"Shift+"</string>
    <string msgid="5473865519181928982" name="abc_menu_space_shortcut_label">"mellomrom"</string>
    <string msgid="6180552449598693998" name="abc_menu_sym_shortcut_label">"Sym+"</string>
    <string msgid="5520303668377388990" name="abc_prepend_shortcut_label">"Meny+"</string>
    <string msgid="7208076849092622260" name="abc_search_hint">"Søk"</string>
    <string msgid="3741173234950517107" name="abc_searchview_description_clear">"Slett søket"</string>
    <string msgid="693312494995508443" name="abc_searchview_description_query">"Søkeord"</string>
    <string msgid="3417662926640357176" name="abc_searchview_description_search">"Søk"</string>
    <string msgid="1486535517437947103" name="abc_searchview_description_submit">"Utfør søket"</string>
    <string msgid="2293578557972875415" name="abc_searchview_description_voice">"Talesøk"</string>
    <string msgid="8875138169939072951" name="abc_shareactionprovider_share_with">"Del med"</string>
    <string msgid="9055268688411532828" name="abc_shareactionprovider_share_with_application">"Del med <ns1:g id="APPLICATION_NAME">%s</ns1:g>"</string>
    <string msgid="1656852541809559762" name="abc_toolbar_collapse_description">"Skjul"</string>
    <string msgid="389117264260014992" name="autofill">"Autofyll"</string>
    <string name="bottomsheet_action_collapse">Skjul feltet nederst</string>
    <string name="bottomsheet_action_expand">Vis feltet nederst</string>
    <string name="bottomsheet_action_expand_halfway">Vis halve feltet nederst</string>
    <string name="bottomsheet_drag_handle_content_description">Håndtak</string>
    <string msgid="881409763997275156" name="call_notification_answer_action">"Svar"</string>
    <string msgid="8793775615905189152" name="call_notification_answer_video_action">"Video"</string>
    <string msgid="3229508546291798546" name="call_notification_decline_action">"Avvis"</string>
    <string msgid="2659457946726154263" name="call_notification_hang_up_action">"Legg på"</string>
    <string msgid="6107532579223922871" name="call_notification_incoming_text">"Innkommende anrop"</string>
    <string msgid="8623827134497363134" name="call_notification_ongoing_text">"Pågående samtale"</string>
    <string msgid="59049573811482460" name="call_notification_screening_text">"Filtrerer et innkommende anrop"</string>
    <string name="character_counter_content_description">%1$d av %2$d tegn er skrevet inn</string>
    <string name="character_counter_overflowed_content_description">Tegngrensen er overskredet – %1$d av %2$d</string>
    <string name="clear_text_end_icon_content_description">Fjern teksten</string>
    <string msgid="406453423630273620" name="close_drawer">"Lukk navigasjonsmenyen"</string>
    <string msgid="7573152094250666567" name="close_sheet">"Lukk arket"</string>
    <string msgid="2523291102206661146" name="common_google_play_services_enable_button">Aktivér</string>
    <string msgid="227660514972886228" name="common_google_play_services_enable_text">%1$s fungerer ikke med mindre du slår på Google Play-tjenester.</string>
    <string msgid="5122002158466380389" name="common_google_play_services_enable_title">Slå på Google Play-tjenester</string>
    <string msgid="7153882981874058840" name="common_google_play_services_install_button">Installer</string>
    <string name="common_google_play_services_install_text">%1$s kan ikke kjøre uten Google Play-tjenester, som ikke er installert på enheten din.</string>
    <string msgid="7215213145546190223" name="common_google_play_services_install_title">Installer Google Play-tjenester</string>
    <string name="common_google_play_services_notification_channel_name">Google Play Tjenester-tilgjengelighet</string>
    <string name="common_google_play_services_notification_ticker">Google Play Tjenester-feil</string>
    <string name="common_google_play_services_unknown_issue">%1$s har problemer med Google Play-tjenester. Prøv på nytt.</string>
    <string name="common_google_play_services_unsupported_text">%1$s kan ikke kjøre uten Google Play-tjenester, som ikke støttes av enheten din.</string>
    <string msgid="6556509956452265614" name="common_google_play_services_update_button">Oppdater</string>
    <string msgid="9053896323427875356" name="common_google_play_services_update_text">%1$s kjører ikke med mindre du oppdaterer Google Play Tjenester.</string>
    <string msgid="6006316683626838685" name="common_google_play_services_update_title">Oppdater Google Play-tjenester</string>
    <string name="common_google_play_services_updating_text">%1$s kjører ikke uten Google Play-tjenester, som oppdateres akkurat nå.</string>
    <string name="common_google_play_services_wear_update_text">Du må installere en ny versjon av Google Play-tjenester. Appen oppdateres automatisk om en kort stund.</string>
    <string name="common_open_on_phone">Åpne på telefonen</string>
    <string name="common_signin_button_text">Logg på</string>
    <string name="common_signin_button_text_long">Logg på med Google</string>
    <string msgid="6083905920877235314" name="copy">"Kopiér"</string>
    <string msgid="8038256446254964252" name="default_error_message">"Ugyldige inndata"</string>
    <string msgid="6312721426453364202" name="default_popup_window_title">"Forgrunnsvindu"</string>
    <string msgid="1890207353314751437" name="dropdown_menu">"Rullegardinmeny"</string>
    <string name="error_a11y_label">Feil: ugyldig</string>
    <string name="error_icon_content_description">Feil</string>
    <string msgid="2427401033573778270" name="expand_button_title">"Avansert"</string>
    <string name="exposed_dropdown_menu_content_description">Vis rullegardinmenyen</string>
    <string msgid="2863935784364843033" name="glance_error_layout_text">"Sjekk den nøyaktige feilen ved å bruke "<b><tt>"adb logcat"</tt></b>" og søke etter "<b><tt>"GlanceAppWidget"</tt></b></string>
    <string msgid="5191168365305634625" name="glance_error_layout_text_v2">"Kan ikke vise innhold"</string>
    <string msgid="3631961919234443531" name="glance_error_layout_title"><b>"Modulfeil med Kort fortalt-appen"</b></string>
    <string name="icon_content_description">Dialogboksikon</string>
    <string msgid="6827826412747255547" name="in_progress">"Pågår"</string>
    <string msgid="7933458017204019916" name="indeterminate">"Delvis avmerket"</string>
    <string name="item_view_role_description">Fane</string>
    <string name="m3_loading_indicator_content_description">Laster inn</string>
    <string msgid="2988463736136100848" name="m3c_bottom_sheet_collapse_description">"Skjul feltet nederst"</string>
    <string msgid="1555567894577437024" name="m3c_bottom_sheet_dismiss_description">"Lukk feltet nederst"</string>
    <string msgid="8403354765404029791" name="m3c_bottom_sheet_drag_handle_description">"Håndtak"</string>
    <string msgid="6670819569745899763" name="m3c_bottom_sheet_expand_description">"Vis feltet nederst"</string>
    <string msgid="3010635850035863127" name="m3c_bottom_sheet_pane_title">"Felt nederst"</string>
    <string msgid="8166741421776570875" name="m3c_date_input_headline">"Angitt dato"</string>
    <string msgid="229313757840775812" name="m3c_date_input_headline_description">"Angitt dato: %1$s"</string>
    <string msgid="6116910750161463197" name="m3c_date_input_invalid_for_pattern">"Datoen matcher ikke det forventede mønsteret: %1$s"</string>
    <string msgid="2521768508935305279" name="m3c_date_input_invalid_not_allowed">"Datoen er ikke tillatt: %1$s"</string>
    <string msgid="7052898923934555305" name="m3c_date_input_invalid_year_range">"Datoen er utenfor det forventede årsintervallet %1$s–%2$s"</string>
    <string msgid="2895559812010326913" name="m3c_date_input_label">"Dato"</string>
    <string msgid="1237013946323089826" name="m3c_date_input_no_input_description">"Ingen"</string>
    <string msgid="7306227249789210568" name="m3c_date_input_title">"Velg dato"</string>
    <string msgid="7605002211875882969" name="m3c_date_picker_headline">"Valgt dato"</string>
    <string msgid="3664277305226978227" name="m3c_date_picker_headline_description">"Valgt: %1$s"</string>
    <string msgid="8436650776581492840" name="m3c_date_picker_navigate_to_year_description">"Gå til år %1$s"</string>
    <string msgid="5811000998184572395" name="m3c_date_picker_no_selection_description">"Ingen"</string>
    <string msgid="7813882352367152251" name="m3c_date_picker_scroll_to_earlier_years">"Rull for å vise tidligere år"</string>
    <string msgid="5727367015496556177" name="m3c_date_picker_scroll_to_later_years">"Rull for å vise senere år"</string>
    <string msgid="1804346892470238807" name="m3c_date_picker_switch_to_calendar_mode">"Bytt til kalendermodus for inndata"</string>
    <string msgid="395627960681594326" name="m3c_date_picker_switch_to_day_selection">"Sveip for å velge år, eller trykk for å bytte tilbake til valg av dag"</string>
    <string msgid="2219746470065162704" name="m3c_date_picker_switch_to_input_mode">"Bytt til tekstmodus for inndata"</string>
    <string msgid="7142101321095356500" name="m3c_date_picker_switch_to_next_month">"Bytt til neste måned"</string>
    <string msgid="228438865139394590" name="m3c_date_picker_switch_to_previous_month">"Bytt til forrige måned"</string>
    <string msgid="791651718641787594" name="m3c_date_picker_switch_to_year_selection">"Bytt til å velge et år"</string>
    <string msgid="7430790972741451689" name="m3c_date_picker_title">"Velg dato"</string>
    <string msgid="3199387177749801575" name="m3c_date_picker_today_description">"I dag"</string>
    <string msgid="2068382232816991922" name="m3c_date_picker_year_picker_pane_title">"Årsvelgeren er synlig"</string>
    <string msgid="3190049423327661366" name="m3c_date_range_input_invalid_range_input">"En ugyldig datoperiode er valgt"</string>
    <string msgid="3148384720560189467" name="m3c_date_range_input_title">"Legg inn datoer"</string>
    <string msgid="2138321128465719402" name="m3c_date_range_picker_day_in_range">"Innenfor området"</string>
    <string msgid="4947636797751277713" name="m3c_date_range_picker_end_headline">"Sluttdato"</string>
    <string msgid="602077859540990149" name="m3c_date_range_picker_scroll_to_next_month">"Rull for å vise den neste måneden"</string>
    <string msgid="4592174524846109496" name="m3c_date_range_picker_scroll_to_previous_month">"Rull for å vise den forrige måneden"</string>
    <string msgid="4665981448952749820" name="m3c_date_range_picker_start_headline">"Startdato"</string>
    <string msgid="3134165431120340385" name="m3c_date_range_picker_title">"Velg datoer"</string>
    <string msgid="7617233117134790350" name="m3c_dialog">"Dialogboks"</string>
    <string msgid="3177828188723359358" name="m3c_dropdown_menu_collapsed">"Skjules"</string>
    <string msgid="2360841780724299882" name="m3c_dropdown_menu_expanded">"Vises"</string>
    <string msgid="8687821690726149911" name="m3c_dropdown_menu_toggle">"Slå rullegardinmeny av/på"</string>
    <string msgid="6152806324422087846" name="m3c_search_bar_search">"Søk"</string>
    <string msgid="6152755701819882931" name="m3c_snackbar_dismiss">"Lukk"</string>
    <string msgid="7655536806087401899" name="m3c_suggestions_available">"Du finner forslag nedenfor"</string>
    <string msgid="2786685010796619560" name="m3c_time_picker_am">"AM"</string>
    <string msgid="2349193472625211372" name="m3c_time_picker_hour">"Time"</string>
    <string msgid="9179527532316922345" name="m3c_time_picker_hour_24h_suffix">"%1$d timer"</string>
    <string msgid="8876759303332837035" name="m3c_time_picker_hour_selection">"Velg time"</string>
    <string msgid="3458167507790628988" name="m3c_time_picker_hour_suffix">"%1$d"</string>
    <string msgid="6973808109666874069" name="m3c_time_picker_hour_text_field">"for timer"</string>
    <string msgid="4313071914266462005" name="m3c_time_picker_minute">"Minutt"</string>
    <string msgid="4699133535056739733" name="m3c_time_picker_minute_selection">"Velg minutter"</string>
    <string msgid="5064177921781937179" name="m3c_time_picker_minute_suffix">"%1$d minutter"</string>
    <string msgid="7661234488295443182" name="m3c_time_picker_minute_text_field">"for minutter"</string>
    <string msgid="5865171949528594571" name="m3c_time_picker_period_toggle_description">"Velg AM eller PM"</string>
    <string msgid="6616362054113087709" name="m3c_time_picker_pm">"PM"</string>
    <string msgid="1805687647081129904" name="m3c_tooltip_long_press_label">"Vis verktøytips"</string>
    <string msgid="5460405025248574620" name="m3c_tooltip_pane_description">"Verktøytips"</string>
    <string name="material_clock_toggle_content_description">Velg AM eller PM</string>
    <string name="material_hour_24h_suffix">%1$s timer</string>
    <string name="material_hour_selection">Velg time</string>
    <string name="material_hour_suffix">%1$s null-null</string>
    <string name="material_minute_selection">Angi minutter</string>
    <string name="material_minute_suffix">%1$s minutter</string>
    <string name="material_slider_range_end">Områdeslutt</string>
    <string name="material_slider_range_start">Områdestart</string>
    <string name="material_slider_value">Verdi</string>
    <string name="material_timepicker_am">AM</string>
    <string name="material_timepicker_clock_mode_description">Bytt til klokkemodus for tidsinndata.</string>
    <string name="material_timepicker_hour">Time</string>
    <string name="material_timepicker_minute">Minutt</string>
    <string name="material_timepicker_pm">PM</string>
    <string name="material_timepicker_select_time">Velg tidspunkt</string>
    <string name="material_timepicker_text_input_mode_description">Bytt til tekstinndatamodus for tidsinndata.</string>
    <string name="mtrl_badge_numberless_content_description">Nytt varsel</string>
    <string name="mtrl_checkbox_state_description_checked">Avmerket</string>
    <string name="mtrl_checkbox_state_description_indeterminate">Delvis avmerket</string>
    <string name="mtrl_checkbox_state_description_unchecked">Ikke avmerket</string>
    <string name="mtrl_chip_close_icon_content_description">Fjern %1$s</string>
    <string name="mtrl_exceed_max_badge_number_content_description" ns2:ignore="PluralsCandidate">Flere enn %1$d nye varsler</string>
    <string name="mtrl_picker_a11y_next_month">Endre til neste måned</string>
    <string name="mtrl_picker_a11y_prev_month">Endre til forrige måned</string>
    <string name="mtrl_picker_announce_current_range_selection">Valg av startdato: %1$s – Valg av sluttdato: %2$s</string>
    <string name="mtrl_picker_announce_current_selection">Gjeldende valg: %1$s</string>
    <string name="mtrl_picker_announce_current_selection_none">ingen</string>
    <string name="mtrl_picker_cancel">Avbryt</string>
    <string name="mtrl_picker_confirm">OK</string>
    <string name="mtrl_picker_date_header_selected">%1$s</string>
    <string name="mtrl_picker_date_header_title">Velg dato</string>
    <string name="mtrl_picker_date_header_unselected">Valgt dato</string>
    <string name="mtrl_picker_day_of_week_column_header">%1$s</string>
    <string name="mtrl_picker_end_date_description">Sluttdato %1$s</string>
    <string name="mtrl_picker_invalid_format">Ugyldig format.</string>
    <string name="mtrl_picker_invalid_format_example">Eksempel: %1$s</string>
    <string name="mtrl_picker_invalid_format_use">Bruk: %1$s</string>
    <string name="mtrl_picker_invalid_range">Ugyldig område.</string>
    <string name="mtrl_picker_navigate_to_current_year_description">Gå til dette året %1$d</string>
    <string name="mtrl_picker_navigate_to_year_description">Naviger til år %1$d</string>
    <string name="mtrl_picker_out_of_range">Utenfor rekkevidde: %1$s</string>
    <string name="mtrl_picker_range_header_only_end_selected">Startdato – %1$s</string>
    <string name="mtrl_picker_range_header_only_start_selected">%1$s–Sluttdato</string>
    <string name="mtrl_picker_range_header_selected">%1$s–%2$s</string>
    <string name="mtrl_picker_range_header_title">Velg periode</string>
    <string name="mtrl_picker_range_header_unselected">Startdato – Sluttdato</string>
    <string name="mtrl_picker_save">Lagre</string>
    <string name="mtrl_picker_start_date_description">Startdato %1$s</string>
    <string name="mtrl_picker_text_input_date_hint">Dato</string>
    <string name="mtrl_picker_text_input_date_range_end_hint">Sluttdato</string>
    <string name="mtrl_picker_text_input_date_range_start_hint">Startdato</string>
    <string name="mtrl_picker_text_input_day_abbr">d</string>
    <string name="mtrl_picker_text_input_month_abbr">m</string>
    <string name="mtrl_picker_text_input_year_abbr">å</string>
    <string name="mtrl_picker_today_description">I dag %1$s</string>
    <string name="mtrl_picker_toggle_to_calendar_input_mode">Bytt til kalenderinndatamodus</string>
    <string name="mtrl_picker_toggle_to_day_selection">Bytt til kalendervisning</string>
    <string name="mtrl_picker_toggle_to_text_input_mode">Bytt til tekstinndatamodus</string>
    <string name="mtrl_picker_toggle_to_year_selection">Bytt til årsvisning</string>
    <string name="mtrl_picker_toggled_to_day_selection">Byttet til kalendervisning</string>
    <string name="mtrl_picker_toggled_to_year_selection">Byttet til årsvisning</string>
    <string name="mtrl_timepicker_cancel">Avbryt</string>
    <string name="mtrl_timepicker_confirm">OK</string>
    <string msgid="6301633601645100427" name="nav_app_bar_navigate_up_description">"Naviger opp"</string>
    <string msgid="7456070600745802113" name="nav_app_bar_open_drawer_description">"Åpne uttrekksmenyen"</string>
    <string msgid="542007171693138492" name="navigation_menu">"Navigasjonsmeny"</string>
    <string msgid="6610465462668679431" name="not_selected">"Ikke valgt"</string>
    <string msgid="6573031135582639649" name="not_set">"Ikke angitt"</string>
    <string name="password_toggle_content_description">Vis passordet</string>
    <string msgid="6685851473431805375" name="preference_copied">"«<ns1:g id="SUMMARY">%1$s</ns1:g>» er kopiert til utklippstavlen."</string>
    <string msgid="5941395253238309765" name="range_end">"Områdeslutt"</string>
    <string msgid="7097486360902471446" name="range_start">"Områdestart"</string>
    <string msgid="6264217191555673260" name="search_menu_title">"Søk"</string>
    <string name="searchview_clear_text_content_description">Fjern teksten</string>
    <string name="searchview_navigation_content_description">Tilbake</string>
    <string msgid="6043586758067023" name="selected">"Valgt"</string>
    <string name="side_sheet_accessibility_pane_title">Sideark</string>
    <string msgid="2792228137354697160" name="snackbar_pane_title">"Varsel"</string>
    <string msgid="4139871816613051306" name="state_empty">"Tom"</string>
    <string msgid="5834637030682409883" name="state_off">"Av"</string>
    <string msgid="1490883874751719580" name="state_on">"På"</string>
    <string msgid="6277540029070332960" name="status_bar_notification_info_overflow">"999+"</string>
    <string msgid="9167775378838880170" name="summary_collapsed_preference_list">"<ns1:g id="CURRENT_ITEMS">%1$s</ns1:g>, <ns1:g id="ADDED_ITEMS">%2$s</ns1:g>"</string>
    <string msgid="2561197295334830845" name="switch_role">"Bryter"</string>
    <string msgid="1672349317127674378" name="tab">"Fane"</string>
    <string msgid="5946805113151406391" name="template_percent">"<ns1:g id="PERCENTAGE">%1$d</ns1:g> prosent."</string>
    <string msgid="3765533235322692011" name="tooltip_description">"verktøytips"</string>
    <string msgid="3124740595719787496" name="tooltip_label">"vis verktøytips"</string>
    <string msgid="3140233346420563315" name="v7_preference_off">"AV"</string>
    <string msgid="89551595707643515" name="v7_preference_on">"PÅ"</string>
</resources>                                                                                                                                                                                                                                                                                                                                          ente: {graph_stats.get('documents', 0)}")
                print(f"         • Interne Relationen: {graph_stats.get('internal_relations', 0)}")
                print(f"         • Externe Relationen: {graph_stats.get('external_relations', 0)}")
                print(f"         • Entitäten: {graph_stats.get('entities', 0)}")
            
            # Relational Database
            relational_stats = backend_stats.get('relational_database', {})
            if relational_stats.get('documents', 0) > 0:
                print(f"      🗄️ Relational Database:")
                print(f"         • Dokumente: {relational_stats.get('documents', 0)}")
                print(f"         • Metadaten-Felder: {relational_stats.get('metadata_fields', 0)}")
                print(f"         • Klassifikationen: {relational_stats.get('classifications', 0)}")
                print(f"         • Timestamps: {relational_stats.get('timestamps', 0)}")
            
            # File System
            fs_stats = backend_stats.get('file_system', {})
            if fs_stats.get('documents', 0) > 0:
                print(f"      📁 File System:")
                print(f"         • Dokumente: {fs_stats.get('documents', 0)}")
                print(f"         • Rohdateien: {fs_stats.get('raw_files', 0)}")
                print(f"         • Verarbeitete Dateien: {fs_stats.get('processed_files', 0)}")
                print(f"         • Backups: {fs_stats.get('backups', 0)}")
                
        else:
            print(f"   💾 Backend-Verteilung: Keine Daten erfasst")
        
        return True
        
    except Exception as e:
        print(f"❌ Test fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_legal_corpus():
    """Analysiert das gesamte Gesetzeskorpus"""
    
    legal_docs_path = Path("Y:/data/00_bund_gesetze_auswahl")
    
    if not legal_docs_path.exists():
        return
    
    print(f"\n📊 Corpus-Analyse: {legal_docs_path}")
    
    # Sammle alle Dateien
    all_files = []
    total_size = 0
    
    for pattern in ['*.txt', '*.pdf', '*.md', '*.doc', '*.docx', '*.rtf']:
        files = list(legal_docs_path.rglob(pattern))
        all_files.extend(files)
    
    print(f"📁 Gesamt-Dateien: {len(all_files)}")
    
    # Größenanalyse
    if all_files:
        sizes = [f.stat().st_size for f in all_files if f.exists()]
        total_size = sum(sizes)
        avg_size = total_size / len(sizes) if sizes else 0
        
        print(f"💾 Gesamtgröße: {total_size:,} bytes ({total_size/1024/1024:.1f} MB)")
        print(f"📏 Durchschnittsgröße: {avg_size:,.0f} bytes")
        print(f"📄 Größte Datei: {max(sizes):,} bytes" if sizes else "")
        print(f"📄 Kleinste Datei: {min(sizes):,} bytes" if sizes else "")
    
    # Format-Verteilung
    extensions = {}
    for file_path in all_files:
        ext = file_path.suffix.lower()
        extensions[ext] = extensions.get(ext, 0) + 1
    
    print(f"\n📊 Format-Verteilung:")
    for ext, count in sorted(extensions.items()):
        percentage = (count / len(all_files)) * 100 if all_files else 0
        print(f"   {ext}: {count} Dateien ({percentage:.1f}%)")

if __name__ == "__main__":
    print("🇩🇪⚖️ German Legal Documents Processing Test")
    print("=" * 70)
    
    # Corpus-Analyse
    analyze_legal_corpus()
    
    # Haupttest
    success = test_german_legal_documents()
    
    if success:
        print(f"\n🎉 German Legal Documents Test erfolgreich!")
        print("=" * 70)
        print("✅ Deutsche Gesetze erfolgreich mit spaCy NLP verarbeitet")
        print("✅ Rechtliche Entitäten erkannt (Personen, Organisationen, Orte)")
        print("✅ DSGVO-konforme PII-Erkennung in Rechtstexten")
        print("✅ Discovery Service bereit für deutsche Rechtsdokumente")
    else:
        print(f"\n❌ Test fehlgeschlagen!")
        print("Bitte prüfen Sie den Pfad und die Dateiformate.")