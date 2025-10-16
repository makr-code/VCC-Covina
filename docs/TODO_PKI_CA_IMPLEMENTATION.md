# ğŸ” PKI/CA Implementation TODO - VCC PKI Library

**Projekt:** VCC PKI (C:\VCC\PKI) - Separates Library Package fÃ¼r Covina  
**Erstellt:** 8. Oktober 2025  
**Status:** Phase 1 - Vorbereitung/Mock-Implementation  
**Ziel:** PKI/CA Infrastructure als wiederverwendbares Library Package

---

## ğŸ¯ Projektziele

1. **Standalone PKI Library:** Wiederverwendbares Package auf `C:\VCC\PKI` Ebene
2. **Mock-First Approach:** Testbare Implementierung ohne echte Kryptographie
3. **Covina Integration:** Nahtlose Integration als Dependency
4. **Production Ready:** Schrittweiser Ausbau zur produktionsreifen PKI

---

## ğŸ“ Verzeichnisstruktur

### PKI als separates Library Package (C:\VCC\PKI)

```
C:/VCC/
â”œâ”€â”€ PKI/                                    # ğŸ†• PKI Library Package (Ebene Ã¼ber Covina)
â”‚   â”œâ”€â”€ README.md                          # PKI Package Overview
â”‚   â”œâ”€â”€ setup.py                           # Package Installation (Legacy Support)
â”‚   â”œâ”€â”€ pyproject.toml                     # Modern Python Packaging
â”‚   â”œâ”€â”€ requirements.txt                   # Dependencies
â”‚   â”œâ”€â”€ requirements-dev.txt               # Development Dependencies
â”‚   â”œâ”€â”€ .gitignore                         # Git Ignore Rules
â”‚   â”œâ”€â”€ LICENSE                            # MIT License
â”‚   â”‚
â”‚   â”œâ”€â”€ vcc_pki/                           # Main Package (importierbar als "vcc_pki")
â”‚   â”‚   â”œâ”€â”€ __init__.py                    # Package Exports
â”‚   â”‚   â”œâ”€â”€ __version__.py                 # Version Info
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ ca/                            # Certificate Authority
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ base_ca.py                # Abstract Base Class
â”‚   â”‚   â”‚   â”œâ”€â”€ root_ca.py                # Root CA Management
â”‚   â”‚   â”‚   â”œâ”€â”€ intermediate_ca.py        # Intermediate CA
â”‚   â”‚   â”‚   â”œâ”€â”€ certificate_generator.py  # Cert Generation
â”‚   â”‚   â”‚   â”œâ”€â”€ certificate_validator.py  # Cert Validation
â”‚   â”‚   â”‚   â””â”€â”€ revocation_service.py     # CRL/OCSP Management
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ signing/                       # Signing Services
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ base_signer.py            # Abstract Base Class
â”‚   â”‚   â”‚   â”œâ”€â”€ document_signer.py        # Dokument-Signierung
â”‚   â”‚   â”‚   â”œâ”€â”€ code_signer.py            # Code-Signierung
â”‚   â”‚   â”‚   â”œâ”€â”€ signature_verifier.py     # Signatur-Verifikation
â”‚   â”‚   â”‚   â””â”€â”€ timestamp_authority.py    # TSA (Timestamping)
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ keystore/                      # Key Management
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ key_generator.py          # Key Generation
â”‚   â”‚   â”‚   â”œâ”€â”€ key_storage.py            # Secure Key Storage
â”‚   â”‚   â”‚   â”œâ”€â”€ hsm_adapter.py            # Hardware Security Module
â”‚   â”‚   â”‚   â””â”€â”€ software_keystore.py      # Software-basierter Keystore
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ trust/                         # Trust Management
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ trust_store.py            # Trust Anchor Management
â”‚   â”‚   â”‚   â”œâ”€â”€ chain_validator.py        # Certificate Chain Validation
â”‚   â”‚   â”‚   â””â”€â”€ policy_engine.py          # Trust Policy Enforcement
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ mock/                          # ğŸ†• Mock/Stub Implementations
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ mock_ca.py                # Mock CA fÃ¼r Testing
â”‚   â”‚   â”‚   â”œâ”€â”€ mock_signer.py            # Mock Signing Service
â”‚   â”‚   â”‚   â””â”€â”€ test_certificates.py      # Test Certificate Generator
â”‚   â”‚   â”‚
â”‚   â”‚   â”œâ”€â”€ utils/                         # Utilities
â”‚   â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”‚   â”œâ”€â”€ asn1_utils.py             # ASN.1 Encoding/Decoding
â”‚   â”‚   â”‚   â”œâ”€â”€ pem_utils.py              # PEM Format Handling
â”‚   â”‚   â”‚   â””â”€â”€ crypto_utils.py           # Cryptographic Helpers
â”‚   â”‚   â”‚
â”‚   â”‚   â””â”€â”€ api/                           # API Layer
â”‚   â”‚       â”œâ”€â”€ __init__.py
â”‚   â”‚       â”œâ”€â”€ pki_service.py            # Hauptservice API
â”‚   â”‚       â”œâ”€â”€ rest_endpoints.py         # REST API fÃ¼r PKI
â”‚   â”‚       â””â”€â”€ cli.py                    # CLI fÃ¼r PKI-Management
â”‚   â”‚
â”‚   â”œâ”€â”€ docs/                              # PKI Dokumentation
â”‚   â”‚   â”œâ”€â”€ PKI_ARCHITECTURE.md           # Architektur-Ãœbersicht
â”‚   â”‚   â”œâ”€â”€ CA_SETUP_GUIDE.md             # CA Setup Anleitung
â”‚   â”‚   â”œâ”€â”€ CERTIFICATE_LIFECYCLE.md      # Cert Lifecycle Management
â”‚   â”‚   â”œâ”€â”€ SIGNING_WORKFLOWS.md          # Signing/Verification Workflows
â”‚   â”‚   â”œâ”€â”€ TRUST_MODEL.md                # Trust Model Dokumentation
â”‚   â”‚   â”œâ”€â”€ API_REFERENCE.md              # API Dokumentation
â”‚   â”‚   â”œâ”€â”€ COMPLIANCE_NOTES.md           # Compliance-Hinweise (Sigstore, TUF)
â”‚   â”‚   â””â”€â”€ INTEGRATION_GUIDE.md          # ğŸ†• Integration in Covina
â”‚   â”‚
â”‚   â”œâ”€â”€ tests/                             # PKI Tests
â”‚   â”‚   â”œâ”€â”€ __init__.py
â”‚   â”‚   â”œâ”€â”€ conftest.py                   # Pytest Configuration
â”‚   â”‚   â”œâ”€â”€ test_ca.py
â”‚   â”‚   â”œâ”€â”€ test_signing.py
â”‚   â”‚   â”œâ”€â”€ test_validation.py
â”‚   â”‚   â”œâ”€â”€ test_keystore.py
â”‚   â”‚   â””â”€â”€ test_integration.py
â”‚   â”‚
â”‚   â”œâ”€â”€ config/                            # PKI Konfiguration
â”‚   â”‚   â”œâ”€â”€ ca_config.yaml                # CA Konfiguration
â”‚   â”‚   â”œâ”€â”€ signing_policy.yaml           # Signing Policies
â”‚   â”‚   â”œâ”€â”€ trust_anchors.yaml            # Trust Anchors
â”‚   â”‚   â””â”€â”€ test_config.yaml              # Test-Konfiguration
â”‚   â”‚
â”‚   â””â”€â”€ examples/                          # ğŸ†• Beispiele
â”‚       â”œâ”€â”€ simple_signing.py             # Einfaches Signing-Beispiel
â”‚       â”œâ”€â”€ certificate_creation.py       # Zertifikat erstellen
â”‚       â””â”€â”€ covina_integration.py         # Integration mit Covina
â”‚
â””â”€â”€ Covina/                                # Covina Projekt
    â”œâ”€â”€ requirements.txt                   # ğŸ”„ Aktualisiert mit vcc-pki
    â”œâ”€â”€ pyproject.toml                     # ğŸ”„ PKI als Dependency
    â”‚
    â”œâ”€â”€ integrations/                      # ğŸ†• Integration Layer
    â”‚   â”œâ”€â”€ __init__.py
    â”‚   â””â”€â”€ pki_integration.py            # PKI Integration fÃ¼r Covina
    â”‚
    â”œâ”€â”€ ingestion/
    â”‚   â”œâ”€â”€ handlers/
    â”‚   â”‚   â””â”€â”€ signing_handler.py        # ğŸ†• Verwendet vcc_pki
    â”‚   â””â”€â”€ job_factory.py                # ğŸ”„ Code Verification via vcc_pki
    â”‚
    â”œâ”€â”€ database/
    â”‚   â””â”€â”€ signature_metadata.py         # ğŸ†• Signature Storage
    â”‚
    â””â”€â”€ docs/
        â”œâ”€â”€ TODO_PKI_CA_IMPLEMENTATION.md # Dieses Dokument
        â””â”€â”€ PKI_INTEGRATION.md            # ğŸ†• Covina-spezifische Integration
```

### Package Installation

```bash
# Development Mode (fÃ¼r Entwicklung)
cd C:\VCC\PKI
pip install -e .

# Production Installation (lokal)
pip install C:\VCC\PKI

# Oder via Git (spÃ¤ter)
pip install git+https://github.com/covina/vcc-pki.git

# In Covina verwenden
cd C:\VCC\Covina
# requirements.txt bereits aktualisiert mit: -e C:\VCC\PKI
pip install -r requirements.txt
```

---

## ğŸ“‹ Implementierungsphasen

### âœ… Phase 1: PKI Package Setup & Mock-Implementation (1-2 Wochen)
### â³ Phase 2: Testing & Validation (1 Woche)
### â³ Phase 3: Dokumentation (3-5 Tage)
### â³ Phase 4: Echte Kryptographie (2-3 Wochen)
### â³ Phase 5: Covina Integration (2 Wochen)
### â³ Phase 6: Production Readiness (1-2 Wochen)

---

## âœ… Phase 1: PKI Package Setup & Mock-Implementation 5             „    `¶           ñ1    ğ5             Á&    (            `/     :            ù1    p3             g/    Ğ9            2    `4             	2    €7             2    Ğ7             B    H„            Í*    @C     ¸       İ    [     ­      ì    @¶            ş    ğå            Q4    ò®     %       é    P¶                ²            D    0İ            «#    ğ3     U       ô"    PV     ´       ï%    Ğ     j       E.                Œ    È‚            ƒ     Å     u      ‰9    àÇ            ^    S     	       T*     @            û*    àE             µ'  "  @=                 /            N    @ê     €      Q:   ñÿø             /    ]            O9    È            Ã  "  ğA     °       '  "  P?            Y    @¯     Ó       q)    PJ            ³+    ğ            ¤7    ;     8           ?                ğÏ            "    0'     <      ,-    À[                °ù     i       u    PG     F      ğ     Ğ     	      ø    Ğ8     Î          @<     Q       ¾(    €?            Ë+    ø            9     È            ?"    Ğò            (  "  à=     ¼       q    `û     ¬       Ì,    @\                Pù     Z       X#    €5            %     Ï            ¾	    àƒ            }
    À‚            Ã    €>            ¿
    xƒ            ø    ˜ƒ                „            ‘8    @È                `F            Y    àJ     >       F    Ø‚            ø    °ƒ                ƒ            ¯    €y            1    €     N       ,!    `Á     d           ¸…            7/    àÇ            E:   ñÿ‚             G     >     Ş           Øƒ            '  "  0?            <!     Á     2       b9    È            ¾"    ÀW     0       `!    À     .;      …    `ƒ            ^         @       0'  "  `?            L-    À[            ¯2     5            z4    ¯     &       µ2    à3            r    °[           »2    €4            î&  "  @?            ä-    @            Á2    09             __cxa_atexit LIBC libc.so libsqliteX.so __cxa_finalize _ZN7android23throw_sqlite3_exceptionEP7_JNIEnvP7sqlite3 _ZN7android23throw_sqlite3_exceptionEP7_JNIEnvP7sqlite3PKc _ZN7android23throw_sqlite3_exceptionEP7_JNIEnvPKc _ZN7android23throw_sqlite3_exceptionEP7_JNIEnviPKcS3_ _ZN7android31throw_sqlite3_exception_errcodeEP7_JNIEnviPKc jniThrowException sqlite3_errmsg sqlite3_extended_errcode sqlite3_free sqlite3_mprintf JNI_OnLoad _Z20jniThrowExceptionFmtP7_JNIEnvPKcS2_z _ZN7_JNIEnv14CallVoidMethodEP8_jobjectP10_jmethodIDz _ZN7_JNIEnv17CallBooleanMethodEP8_jobjectP10_jmethodIDz _ZN7android37register_android_database_SQLiteDebugEP7_JNIEnv _ZN7android38register_android_database_SQLiteGlobalEP7_JNIEnv _ZN7android42register_android_database_SQLiteConnectionEP7_JNIEnv _ZdlPv _Znwm __android_log_print __stack_chk_fail abort free jniRegisterNativeMethods jniThrowExceptionFmt jniThrowIOException malloc memcmp memcpy sqlite3_bind_blob sqlite3_bind_double sqlite3_bind_int64 sqlite3_bind_null sqlite3_bind_parameter_count sqlite3_bind_text16 sqlite3_busy_timeout sqlite3_changes sqlite3_clear_bindings sqlite3_close sqlite3_column_blob sqlite3_column_bytes sqlite3_column_bytes16 sqlite3_column_count sqlite3_column_double sqlite3_column_int64 pthread_create sqlite3_column_name16 sqlite3_column_text16 sqlite3_column_type sqlite3_create_collation sqlite3_create_function_v2 sqlite3_db_handle sqlite3_db_readonly sqlite3_db_status sqlite3_finalize sqlite3_last_insert_rowid dl_iterate_phdr libdl.so sqlite3_open_v2 sqlite3_prepare16_v2 sqlite3_profile sqlite3_progress_handler sqlite3_reset sqlite3_step sqlite3_stmt_readonly sqlite3_trace sqlite3_user_data sqlite3_value_bytes16 sqlite3_value_text16 strcat strlen sqlite3_config sqlite3_initialize sqlite3_release_memory sqlite3_soft_heap_limit sqlite3_status _ZN12JniConstants14referenceClassE _ZN12JniConstants19fileDescriptorClassE _ZNSt6__ndk112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE21__grow_by_and_replaceEmmmmmmPKc _ZNSt6__ndk112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6appendEPKcm _ZNSt6__ndk112basic_stringIcNS_11char_traitsIcEENS_9allocatorIcEEE6assignEPKcm __android_log_write __cxa_guard_acquire __cxa_guard_release __vsnprintf_chk asprintf jniCreateFileDescriptor jniGetFDFromFileDescriptor jniGetReferent jniLogException jniSetFileDescriptorOfFD jniStrError jniThrowNullPointerException jniThrowRuntimeException memmove strerror_r vsnprintf _ZN12JniConstants10fieldClassE _ZN12JniConstants10floatClassE _ZN12JniConstants10shortClassE _ZN12JniConstants11doubleClassE _ZN12JniConstants11methodClassE _ZN12JniConstants11objectClassE _ZN12JniConstants11socketClassE _ZN12JniConstants11stringClassE _ZN12JniConstants12bidiRunClassE _ZN12JniConstants12booleanClassE _ZN12JniConstants12integerClassE _ZN12JniConstants13calendarClassE _ZN12JniConstants13deflaterClassE _ZN12JniConstants13inflaterClassE _ZN12JniConstants14byteArrayClassE _ZN12JniConstants14characterClassE _ZN12JniConstants15bigDecimalClassE _ZN12JniConstants15charsetICUClassE _ZN12JniConstants15localeDataClassE _ZN12JniConstants15mutableIntClassE _ZN12JniConstants15socketImplClassE _ZN12JniConstants15structStatClassE _ZN12JniConstants16constructorClassE _ZN12JniConstants16inetAddressClassE _ZN12JniConstants16inputStreamClassE _ZN12JniConstants16mutableLongClassE _ZN12JniConstants16objectArrayClassE _ZN12JniConstants16structFlockClassE _ZN12JniConstants16structUcredClassE _ZN12JniConstants17gaiExceptionClassE _ZN12JniConstants17inet6AddressClassE _ZN12JniConstants17outputStreamClassE _ZN12JniConstants17realToStringClassE _ZN12JniConstants17structLingerClassE _ZN12JniConstants17structPasswdClassE _ZN12JniConstants17structPollfdClassE _ZN12JniConstants18parsePositionClassE _ZN12JniConstants18structStatVfsClassE _ZN12JniConstants18structTimevalClassE _ZN12JniConstants18structUtsnameClassE _ZN12JniConstants19errnoExceptionClassE _ZN12JniConstants19structAddrinfoClassE _ZN12JniConstants19structGroupReqClassE _ZN12JniConstants20inetUnixAddressClassE _ZN12JniConstants22inetSocketAddressClassE _ZN12JniConstants26fieldPositionIteratorClassE _ZN12JniConstants27patternSyntaxExceptionClassE _ZN12JniConstants4initEP7_JNIEnv _ZN12JniConstants9byteClassE _ZN12JniConstants9longClassE __errno __memcpy_chk __memset_chk __strlen_chk access close dlclose dlerror dlopen dlsym fchmod fchown fcntl fstat fsync ftruncate getcwd getenv geteuid getpid gettimeofday ioctl localtime log libm.so lstat memset mkdir mmap mremap munmap nanosleep open pread pthread_mutex_destroy pthread_mutex_init pthread_mutex_lock pthread_mutex_trylock pthread_mutex_unlock pthread_mutexattr_destroy pthread_mutexattr_init pthread_mutexattr_settype pwrite qsort read readlink realloc rmdir sqlite3_aggregate_context sqlite3_aggregate_count sqlite3_auto_extension sqlite3_autovacuum_pages sqlite3_backup_finish sqlite3_backup_init sqlite3_backup_pagecount sqlite3_backup_remaining sqlite3_backup_step sqlite3_bind_blob64 sqlite3_bind_int sqlite3_bind_parameter_index sqlite3_bind_parameter_name sqlite3_bind_pointer sqlite3_bind_text sqlite3_bind_text64 sqlite3_bind_value sqlite3_bind_zeroblob sqlite3_bind_zeroblob64 sqlite3_blob_bytes sqlite3_blob_close sqlite3_blob_open sqlite3_blob_read sqlite3_blob_reopen sqlite3_blob_write sqlite3_busy_handler sqlite3_cancel_auto_extension sqlite3_changes64 sqlite3_close_v2 sqlite3_collation_needed sqlite3_collation_needed16 sqlite3_column_decltype sqlite3_column_decltype16 sqlite3_column_int sqlite3_column_name sqlite3_column_text sqlite3_column_value sqlite3_commit_hook sqlite3_compileoption_get sqlite3_compileoption_used sqlite3_complete sqlite3_complete16 sqlite3_context_db_handle sqlite3_create_collation16 sqlite3_create_collation_v2 sqlite3_create_filename sqlite3_create_function sqlite3_create_function16 sqlite3_create_module sqlite3_create_module_v2 sqlite3_create_window_function sqlite3_data_count sqlite3_data_directory sqlite3_database_file_object sqlite3_db_cacheflush sqlite3_db_config sqlite3_db_filename sqlite3_db_mutex sqlite3_db_name sqlite3_db_release_memory sqlite3_declare_vtab sqlite3_deserialize sqlite3_drop_modules sqlite3_enable_load_extension sqlite3_enable_shared_cache sqlite3_errcode sqlite3_errmsg16 sqlite3_error_offset sqlite3_errstr sqlite3_exec sqlite3_expanded_sql sqlite3_expired sqlite3_extended_result_codes sqlite3_file_control sqlite3_filename_database sqlite3_filename_journal sqlite3_filename_wal sqlite3_free_filename sqlite3_free_table sqlite3_get_autocommit sqlite3_get_auxdata sqlite3_get_clientdata sqlite3_get_table sqlite3_global_recover sqlite3_hard_heap_limit64 sqlite3_interrupt sqlite3_is_interrupted sqlite3_keyword_check sqlite3_keyword_count sqlite3_keyword_name sqlite3_libversion sqlite3_libversion_number sqlite3_limit sqlite3_load_extension sqlite3_log sqlite3_malloc sqlite3_malloc64 sqlite3_memory_alarm sqlite3_memory_highwater sqlite3_memory_used sqlite3_msize sqlite3_mutex_alloc sqlite3_mutex_enter sqlite3_mutex_free sqlite3_mutex_leave sqlite3_mutex_try sqlite3_next_stmt sqlite3_open sqlite3_open16 sqlite3_os_end sqlite3_os_init sqlite3_overload_function sqlite3_prepare sqlite3_prepare16 sqlite3_prepare16_v3 sqlite3_prepare_v2 sqlite3_prepare_v3 sqlite3_randomness sqlite3_realloc sqlite3_realloc64 sqlite3_reset_auto_extension sqlite3_result_blob sqlite3_result_blob64 sqlite3_result_double sqlite3_result_error sqlite3_result_error16 sqlite3_result_error_code sqlite3_result_error_nomem __sF sqlite3_result_error_toobig android_set_abort_message sqlite3_result_int closelog sqlite3_result_int64 fputc sqlite3_result_null openlog sqlite3_result_pointer syslog sqlite3_result_subtype vasprintf sqlite3_result_text vfprintf sqlite3_result_text16 sqlite3_result_text16be sqlite3_result_text16le sqlite3_result_text64 __memmove_chk sqlite3_result_value islower sqlite3_result_zeroblob isxdigit sqlite3_result_zeroblob64 sqlite3_rollback_hook pthread_setspecific sqlite3_rtree_geometry_callback sqlite3_rtree_query_callback sqlite3_serialize pthread_cond_broadcast sqlite3_set_authorizer pthread_cond_wait sqlite3_set_auxdata syscall sqlite3_set_clientdata sqlite3_set_last_insert_rowid sqlite3_shutdown sqlite3_sleep sqlite3_snprintf sqlite3_soft_heap_limit64 sqlite3_sourceid sqlite3_sql sqlite3_status64 sqlite3_stmt_busy sqlite3_stmt_explain sqlite3_stmt_isexplain sqlite3_stmt_status sqlite3_str_append sqlite3_str_appendall calloc sqlite3_str_appendchar sqlite3_str_appendf sqlite3_str_errcode sqlite3_str_finish sqlite3_str_length sqlite3_str_new sqlite3_str_reset sqlite3_str_value sqlite3_str_vappendf sqlite3_strglob sqlite3_stricmp sqlite3_strlike sqlite3_strnicmp sqlite3_system_errno sqlite3_table_column_metadata sqlite3_temp_directory sqlite3_test_control sqlite3_thread_cleanup sqlite3_threadsafe sqlite3_total_changes sqlite3_total_changes64 sqlite3_trace_v2 sqlite3_transfer_bindings sqlite3_txn_state sqlite3_update_hook sqlite3_uri_boolean sqlite3_uri_int64 sqlite3_uri_key sqlite3_uri_parameter sqlite3_value_blob sqlite3_value_bytes sqlite3_value_double sqlite3_value_dup sqlite3_value_encoding sqlite3_value_free sqlite3_value_frombind sqlite3_value_int sqlite3_value_int64 sqlite3_value_nochange sqlite3_value_numeric_type sqlite3_value_pointer sqlite3_value_subtype sqlite3_value_text sqlite3_value_text16be sqlite3_value_text16le sqlite3_value_type sqlite3_version sqlite3_vfs_find sqlite3_vfs_register sqlite3_vfs_unregister sqlite3_vmprintf sqlite3_vsnprintf sqlite3_vtab_collation sqlite3_vtab_config sqlite3_vtab_distinct sqlite3_vtab_in sqlite3_vtab_in_first sqlite3_vtab_in_next sqlite3_vtab_nochange sqlite3_vtab_on_conflict sqlite3_vtab_rhs_value sqlite3_wal_autocheckpoint sqlite3_wal_checkpoint sqlite3_wal_checkpoint_v2 sqlite3_wal_hook stat strcmp strcspn strncmp strrchr strspn sysconf time unlink utimes write _ZNSt9bad_allocC1Ev _ZNSt9bad_allocD1Ev _ZSt15get_new_handlerv _ZSt17__throw_bad_allocv _ZSt7nothrow _ZSt9terminatev _ZTISt9bad_alloc _ZdaPv _ZdaPvRKSt9nothrow_t _ZdaPvSt11align_val_t _ZdaPvSt11align_val_tRKSt9nothrow_t _ZdaPvm _ZdaPvmSt11align_val_t _ZdlPvRKSt9nothrow_t _ZdlPvSt11align_val_t _ZdlPvSt11align_val_tRKSt9nothrow_t _ZdlPvm _ZdlPvmSt11align_val_t _Znam _ZnamRKSt9nothrow_t _ZnamSt11align_val_t _ZnamSt11align_val_tRKSt9nothrow_t _ZnwmRKSt9nothrow_t _ZnwmSt11align_val_t _ZnwmSt11align_val_tRKSt9nothrow_t __cxa_allocate_exception __cxa_begin_catch __cxa_end_catch __cxa_throw __gxx_personality_v0 posix_memalign _ZN10__cxxabiv119__getExceptionClassEPK17_Unwind_Exception _ZN10__cxxabiv119__setExceptionClassEP17_Unwind_Exceptionm _ZN10__cxxabiv121__isOurExceptionClassEPK17_Unwind_Exception _ZSt13get_terminatev _ZSt14get_unexpectedv __cxa_allocate_dependent_exception __cxa_call_unexpected __cxa_current_exception_type __cxa_current_primary_exception __cxa_decrement_exception_refcount __cxa_free_dependent_exception __cxa_free_exception __cxa_get_exception_ptr __cxa_get_globals __cxa_get_globals_fast __cxa_increment_exception_refcount __cxa_rethrow __cxa_rethrow_primary_exception __cxa_uncaught_exception __cxa_uncaught_exceptions pthread_getspecific pthread_key_create pthread_once __cxa_guard_abort _ZSt10unexpectedv _ZSt15set_new_handlerPFvvE __cxa_new_handler __cxa_terminate_handler __cxa_unexpected_handler _ZNSt13bad_exceptionD1Ev _ZTISt13bad_exception _ZTVSt13bad_exception _ZNKSt13bad_exception4whatEv _ZNKSt20bad_array_new_length4whatEv _ZNKSt9bad_alloc4whatEv _ZNKSt9exception4whatEv _ZNSt13bad_exceptionD0Ev _ZNSt13bad_exceptionD2Ev _ZNSt20bad_array_new_lengthC1Ev _ZNSt20bad_array_new_lengthC2Ev _ZNSt20bad_array_new_lengthD0Ev _ZNSt20bad_array_new_lengthD1Ev _ZNSt20bad_array_new_lengthD2Ev _ZNSt9bad_allocC2Ev _ZNSt9bad_allocD0Ev _ZNSt9bad_allocD2Ev _ZNSt9exceptionD0Ev _ZNSt9exceptionD1Ev _ZNSt9exceptionD2Ev _ZTISt20bad_array_new_length _ZTISt9exception _ZTSSt13bad_exception _ZTSSt20bad_array_new_length _ZTSSt9bad_alloc _ZTSSt9exception _ZTVN10__cxxabiv117__class_type_infoE _ZTVN10__cxxabiv120__si_class_type_infoE _ZTVSt20bad_array_new_length _ZTVSt9bad_alloc _ZTVSt9exception _ZSt13set_terminatePFvvE _ZSt14set_unexpectedPFvvE __cxa_demangle _ZNSt9type_infoD2Ev _ZTIDh _ZTIDi _ZTIDn _ZTIDs _ZTIDu _ZTIN10__cxxabiv116__enum_type_infoE _ZTIN10__cxxabiv116__shim_type_infoE _ZTIN10__cxxabiv117__array_type_infoE _ZTIN10__cxxabiv117__class_type_infoE _ZTIN10__cxxabiv117__pbase_type_infoE _ZTIN10__cxxabiv119__pointer_type_infoE _ZTIN10__cxxabiv120__function_type_infoE _ZTIN10__cxxabiv120__si_class_type_infoE _ZTIN10__cxxabiv121__vmi_class_type_infoE _ZTIN10__cxxabiv123__fundamental_type_infoE _ZTIN10__cxxabiv129__pointer_to_member_type_infoE _ZTIPDh _ZTIPDi _ZTIPDn _ZTIPDs _ZTIPDu _ZTIPKDh _ZTIPKDi _ZTIPKDn _ZTIPKDs _ZTIPKDu _ZTIPKa _ZTIPKb _ZTIPKc _ZTIPKd _ZTIPKf _ZTIPKg _ZTIPKh _ZTIPKi _ZTIPKj _ZTIPKl _ZTIPKm _ZTIPKn _ZTIPKo _ZTIPKs _ZTIPKt _ZTIPKv _ZTIPKw _ZTIPKx _ZTIPKy _ZTIPa _ZTIPb _ZTIPc _ZTIPd _ZTIPf _ZTIPg _ZTIPh _ZTIPi _ZTIPj _ZTIPl _ZTIPm _ZTIPn _ZTIPo _ZTIPs _ZTIPt _ZTIPv _ZTIPw _ZTIPx _ZTIPy _ZTISt9type_info _ZTIa _ZTIb _ZTIc _ZTId _ZTIf _ZTIg _ZTIh _ZTIi _ZTIj _ZTIl _ZTIm _ZTIn _ZTIo _ZTIs _ZTIt _ZTIv _ZTIw _ZTIx _ZTIy _ZTSDh _ZTSDi _ZTSDn _ZTSDs _ZTSDu _ZTSN10__cxxabiv116__enum_type_infoE _ZTSN10__cxxabiv116__shim_type_infoE _ZTSN10__cxxabiv117__array_type_infoE _ZTSN10__cxxabiv117__class_type_infoE _ZTSN10__cxxabiv117__pbase_type_infoE _ZTSN10__cxxabiv119__pointer_type_infoE _ZTSN10__cxxabiv120__function_type_infoE _ZTSN10__cxxabiv120__si_class_type_infoE _ZTSN10__cxxabiv121__vmi_class_type_infoE _ZTSN10__cxxabiv123__fundamental_type_infoE _ZTSN10__cxxabiv129__pointer_to_member_type_infoE _ZTSPDh _ZTSPDi _ZTSPDn _ZTSPDs _ZTSPDu _ZTSPKDh _ZTSPKDi _ZTSPKDn _ZTSPKDs _ZTSPKDu _ZTSPKa _ZTSPKb _ZTSPKc _ZTSPKd _ZTSPKf _ZTSPKg _ZTSPKh _ZTSPKi _ZTSPKj _ZTSPKl _ZTSPKm _ZTSPKn _ZTSPKo _ZTSPKs _ZTSPKt _ZTSPKv _ZTSPKw _ZTSPKx _ZTSPKy _ZTSPa _ZTSPb _ZTSPc _ZTSPd _ZTSPf _ZTSPg _ZTSPh _ZTSPi _ZTSPj _ZTSPl _ZTSPm _ZTSPn _ZTSPo _ZTSPs _ZTSPt _ZTSPv _ZTSPw _ZTSPx _ZTSPy _ZTSa _ZTSb _ZTSc _ZTSd _ZTSf _ZTSg _ZTSh _ZTSi _ZTSj _ZTSl _ZTSm _ZTSn _ZTSo _ZTSs _ZTSt _ZTSv _ZTSw _ZTSx _ZTSy _ZTVN10__cxxabiv116__enum_type_infoE _ZTVN10__cxxabiv116__shim_type_infoE _ZTVN10__cxxabiv117__array_type_infoE _ZTVN10__cxxabiv117__pbase_type_infoE _ZTVN10__cxxabiv119__pointer_type_infoE _ZTVN10__cxxabiv120__function_type_infoE _ZTVN10__cxxabiv121__vmi_class_type_infoE _ZTVN10__cxxabiv123__fundamental_type_infoE _ZTVN10__cxxabiv129__pointer_to_member_type_infoE __cxa_pure_virtual __dynamic_cast _ZNKSt10bad_typeid4whatEv _ZNKSt8bad_cast4whatEv _ZNSt10bad_typeidC1Ev _ZNSt10bad_typeidC2Ev _ZNSt10bad_typeidD0Ev _ZNSt10bad_typeidD1Ev _ZNSt10bad_typeidD2Ev _ZNSt8bad_castC1Ev _ZNSt8bad_castC2Ev _ZNSt8bad_castD0Ev _ZNSt8bad_castD1Ev _ZNSt8bad_castD2Ev _ZNSt9type_infoD0Ev _ZNSt9type_infoD1Ev _ZTISt10bad_typeid _ZTISt8bad_cast _ZTSSt10bad_typeid _ZTSSt8bad_cast _ZTSSt9type_info _ZTVSt10bad_typeid _ZTVSt8bad_cast _ZTVSt9type_info __cxa_deleted_virtual _edata __bss_start _end liblog.so 	  b   @      $@€C J    `  ¢hÀBĞ  Bt‚œ"U“cV2(òş×Ïû>{\¤€‹`GAE±÷=ÿDH @	  Ä ÀûŸ{€8ƒHB 	€ $@3 ¯`À‚1D A( B	…H€ 6A  À‘ˆ  Á   ¢8	0"ƒ£At 79½ ^µ(¤¥B‰0W©'# P€   ‡  ‘a	ËÀÀ€Œ  „ „)HŠ!ø¾ï~€O„ B”0 „ET Â`Ä@   Ìà €p@„"¢ ] ‚"rXª‚$   ’(Œ& ( @ $‘¤ -ê„€ €  @‘@L€ "         2@( ‘!ŠPd¤’Š €´I,„F,j&8	 ¨ H‚‚‚ ‚ D€# ‰V®Qø„  Jˆ2 ˜³n  Ş÷ø(/ @+´a  iÌB1„
„‚  -)À
	Äa€    ĞpT K( @îPb   e   f   h   j   l   n   o   q   r               t   u   v   w   z   {   ~   €               ‚   ƒ       …   †   ‡           ˆ   ‰   Š       Œ                ‘   ’       “           ”               –                   ˜       ™   š   ›   œ          Ÿ               ¡   ¢   ¥   ¦   ¨   ª   «   ­   ®       °   ³   ´   ¶   ¸   º           »   ½   ¾               À   Â   Å   Æ   Ç   É   Ê   Ë   Í   Î   Ğ   Ñ   Ò       Ó           Ô   Õ   Ø       Ù   Ú   Û   Ü           İ   ß   á   ã   ä       æ   ç   ê       ë   í   ï   ğ   ñ       ó   ô   õ           ÷   ø   ù   û                   ü   ş                                            	                  
                                                                          "      #  '  -              .      0  1  2  3  5  8  :      <          =                      >      ?      @  A                  D  E      F  H  J  M      O  P  R      S      T  V  X  Z  ]      `  d  f  g  i  j  k  l  n  o              p  u      w  z  |  ~            €  ‚  ƒ  „  …          †  ‡      ˆ  Œ    ’      “              •          –  —  ˜  ™  ›    Ÿ  ¢  ¦  ©  ­  ²  ´  ¶  ¸  ¹  ¿  À  Â  Ã  Å  Æ  È  Ê  Ì  Î  Ò  Ô  Ù  Ú  Ü  ß  â  ã      ä  æ  é  ì  í  ğ  ò  ô  ö  ÷  ú  ü  ı  ş  ÿ            
                                          !      "  #  %  &  '          )  *  +  ,      /          0  3      6      7  9  ;  <  >  ?  B  E  I  K  M  O  Q  S      T  V      W  X  Z  \      ]  _      c  d      f  g  h  k  l  n  q  r  s  u  x  {  €  ƒ  „  …  †  ˆ  ‰  ‹  Œ      ’  “  •  –      —  ™      š    Ÿ  ¡  £  ¤  ¦  §  ©      ª      «  ­  ®  °  ²      ³  ¶  ·  ¸  º  ½  ¾  ¿  Á          Â      Ã      Ä      Æ  Ç      È  É      Ê  Ì  Ğ  Ò  Ô      Õ          Ö  ×      Ø  Û  Ü      Ş              ß      à  á              â  è  é  ë      à¡æÜ@áè/èCáèä<2CáèÊØ4ƒEáèN¹¦(Eáè€ÆgÛâ¤±Gáèôˆ«ôIáèIáèNæz€KáèOáèOáèÍölzhôt$QdÿQáèSáè’òÜ¦$ Sáè¢?áÿUáè`æ{T‹ç³w?à¼1J„tCšÍMÑë»L‘ÙìW›4Ít—ÀµHeE×1~7ĞÕM¯—ücg'–®û§\yÃTíÓ.U˜]	¤bx×>J‡&bâ#‚A4²<sbÛñıy˜›q!–sÁ-•š­áÖ±’£GD !÷oÃBAÑW’‘‘Äî??ËR…Q~>¨Æ×k-QR¸*ÑOÍULÆ‚¥â™loÄá\«lÔk5ã\«lD®¸åLÂi”—bİ4Ö±¼—9‚üé`:-İç\«l¤PWXè¿şí\«l©ÓØî\«l“`iÑÀ8K8c_È
Ò—ë–Ë™¦oX*ÉáuÇ-<]¸lB|Èq“MP¡Åôª©éÜ¹ÒNîÁ:Õ†InQŠùEæí*HÂ¸vÎÕœc½ÅCUYb)@*1kOjùİÔaÇÙ÷û¡pFÿ
.<¢şòLA¾aş³…ßÙpoÄí lÀEòOãEˆ€É—ğ:"o„°[Î4¿†ÌÍ¼¸{=à›‹(ûÏĞE%Ş|Gí6æ^yänÄ5Y@_4Á4J­,³&ÁÎ»g¯ĞUé;ŠÜ…„†:šÔ‡CEÕìŠĞDíàFy+£‚Zw›é+öF²e<r7å!o¬w‡;´w«‰·¡‘—eĞéb&^Æ£uoÄù<”C"EÛ¸ûå(Érúö
œ‹¹ènÄ^shĞFöÖÒ#‡yÿÀà¸ù¤„³¹8ŒÔ®lƒK”Î•º ë]¡³—úOX×™+…©lã»6˜~b¥ØZ¶±»õàşş‘È‘‰§ş]Öéá¥lãj‹ñA¦69Ê°×R®÷ßá¥l#o,w"YE9á¥l…õå”£× o´t2X#á¥lôaì¼*W¹'·ô~!ÙU%á¥l0ÅM¹Á$èş)3ì3¥„N½¶GäyIk¶²Ü™º+N˜Ú®_ÕQ³ ÁC[™‘òcaH›Ø…Zf°Âú½w–”°»şÅK [£ˆĞ,¹-óàùÔgY¼O cÕf4fz#{K¾4¿ÆÖ#–¾¾Ş÷w1ì;h‰w1ìÎ=ĞÈ¼)$©y1ì€şØx1ìµñkÂ²vEoú.D%ªw{1ìœ¹ğ}1ì}1ìNX31ì1ìş]Â1ìCíƒ1ìƒ1ì…1ìpí`:Æ%¬_nô$ ¬©ùB‰1ìB=¬â‰1ìWw”pÜø‹1ì4DÃ1ìş¶ŸÅ1ì1ìó«ßv¨›¿­é… û-#Åîz¥½¾ƒã=äseµy)SEYÃ¨[Jø^·ª¼Õ¶ĞAaŒ„ÎÖ‡
~É—ÔÜÃ+b«Ñƒ÷ìÉ	‰°‰ô5R!gÈ/<W—›cæ¼;íìíìœ¯Õ7ïìì9îìÁ]«lÃ]«l(g‰¤ğìÃ]«lÔ_w¼^šoòìÅ]«lÖ¬«Uvï;óìà Úmôì’ƒ¿Ç]«lÂƒ[ORnŠ‚ØÏU ôìÇ]«l~Ş”ZÉ]«löìÉ]«løìË]«lùì:-]P<90Dì­ùBúìÌ]«l9[t›Í]«lDˆ›ÁÏ]«lÏ]«l@ºñÿìÿìğTaı+ı\ ìÓ]«lìÕ]«lì=ú%l›E|ˆ…cì×]«lØLóu×]«lòÎ!K˜B%¹ÕŒ!ùBÙ]«lÙ]«l>']ñaFÔ¸’­OÊxy‡âè|›Û—ºØwK‡âè‰âè‰âè€f‹âèdçßÜvÍOIâè Èêo8ÁyâèâèækŠ°ëâè¢?õ&??)ìâèo¶İ“°“0ˆ“âè“âè’¾”KN1µ•âè’¿û–yì™=IÛÓÒ™âè¤…m<™âèô Ñ›âè:YöiRP˜r'Éâ(v˜âèú<ºâè2ÎzbèÑ¥¨%Ÿâè¡é“KdkRÄš!§üÅ«"3ñØÖ‡™ñg’/²ùBD¸jú‘|PÕŞùàL3ÕN o›DUe y¬5yÏE¯âè•­½ÁŒŞp¥ôŞ™‘øK44Õ¬sÍ%ùB3œhqS"È|Í}yÛ|×¥!¾š¤ñ/ì*ºV\tØ'ó/ì«K*¬à6"´˜å÷/ìxk©l`©uˆ1—÷Øm,wı/ìèÁØ‡O®Hÿ/ìÊSßk[ª¬YÈWËŞ¥W5·nË¹?(—-ñ_^Âãşnü+N¨"ƒb,ëqƒbTÃú½h¦"³T1£Û¨*üd=üCİ ÎÅQ ‰b°.¨"Y?§RÃ©×Ab”méÌ!Ÿò?~báÀ~¦p¶Mõ:2Ì…t²˜.ç¤]õF‰›Kíœ*;ök£/è+Ë×™arÇ¨Š¶$~Ly÷á¥lùá¥lfVŒùá¥l¬q£ÕÒ¬ôûá¥lÏŠHıá¥l.ƒ2ıá¥l:1%t™‡ÿá¥løıéH!ÿá¥lê=¾‚Lv±‹zƒ>Jfìâ¥lp ˜ğUòiìâ¥lâ¥lâ¥l~ûØgâ¥lmìÒ¿0’›¹Q·˜ÔmòãÁ	â¥lµõ5â¥lìsìâ¥ltìâ¥lâ¥lâ¥l¦²Ò\‰hã«@zföÃe>ÛÎ·föÃeAÛîAl×Û¡nmá[û}ú²­÷ïÎÎq›÷+£y)Ñ!Ÿ¶&;JOG¥÷Ë–©ƒûRéX[ ¥A5Ì»ã’|c÷]­§/èºT§–³]BaÁTX¦ÄdCƒLtP[¼¾ƒ—Mì(•mø¬ôúšÚ;wk1èWèïe§§È…5…Q†u”K/èå\”¾J_½¢Œ„³„«ôi}Iºã"(YKMÅ˜a]ĞSı÷”˜pY4B,8‚Ú¡•+g´#~«†1º× Å`˜åxOØÇsáO×Æy]±(¼(<Vî´+jÕ!ŸÙqX7¿”KÜÛ)¹ĞeEIéí«/èywÀuœŞ¤óú(÷8Õ>TnÌT¬ô<áèË(»=áèŒ‰-f?áèR²0n‡^ç?áè    	  î      ´  ¶  ¸  ¼  $  Á       Ä  Å      È  Ê  Ì  Ğ  ¡   	    y  µ   ™        =  g  b  ç          ë  >  ¯  ©  N  ß   ï   ­    ‘      Ê      Ò    ì   b   j           ’  ”  •  –  Z   Ÿ   x   Â   Ú          Œ  Ö   =   ”       o       Œ     ]              £             Z              ?  :          s    )      ô  7      j  k  Š  p      r  t  w  z        ƒ  „  …  ‡  æ  è  ê  í  ó   c   e   g   i   k       n   p   q   š             t   u   â   å   z   }      ®  "      f   ¿  å           ¢  “    Ô       o  ¾      ¦  0      '      ğ           i  T  S   í  ·  Ç           ¤   5   ¡  °          r       ™   7            ı   Ÿ          À          ø   U          '  b              “       »       ò   ‹      h   ^  ú  @  a   {           ¸       f  Õ      Q   I   ù       Ú  ²      X   d     0  M   L  Â  ³          û     ì      
       R        ×         ]   ­   Ï  º   T         ·   ¿           m   ¼   Ä   ¾   Æ   —       ,       *  _  ë   Ş  á  â  ã  Ş  å  è  ë  ì  ï      µ  õ  ö  ù      V  ş  e          	        ;  J  ß        c  à       Ü   ‹      H  J            "   S  „      <  æ   W    [    D   Ó  ›              ~  ‚      Ã   1   Å  ˆ  \       8  -  ‘      “  »      è   ¢  £  „   Ğ   ±         x       *   `  Ş      ä      Ë             O   u  9           É  Ë  ü  Ñ  Ó  Ø  Ù  B        …        &             Í  ª      A      ^   ÿ   ¬   G   I      Ù  €   •  q  †    ¹  #  Ò   Y  Í          ƒ      a             ¡  ¥  Ö  A  ±  ³  µ  ·    ½  ¿  Á  Â      R       -      6      ©  6   †  ê   l              &  ,  L      Ò  Ü  /      ˜        4  Ô  ó      ç            K  Í  W  Y  \  ^  Ú  c  e  f    i  `   k  m  n  Á        Û  t  v  :   y  {  }  ~  ã   u      I      "  M     ±  Ï          °  ¨      F    /      F  —  ˜  š  œ         ¤  ¨  ª  °                                                                                      ç   |            ;  Ø           K      Ç          ‡                          Û   ‘       ı      ½  `                             #                   ,  4              Ê   )  l      -           ‰      _          &          ¶      È      a      d                        H   ½   j    æ  C   ×          ˆ       P       ¤        F     S              U   w       U  ~   ¶       Ä      _       Œ  —          T      ´           Y           P  š                                œ                  s   g                 O        Ñ  İ              <           %      
                  †                   ô       ¯   @                  L       í       …   G          €      A       /   d  ?              ü           Ï       –  à  Õ   ­              ¹  Ì               P          y                                     5  ‡          *  à          !               B               [  »      9                          ˜      ÷   E                  h          5      ©   ®   7       |     .              O  ø      :  N                         •   Û         ’                     €      Æ  É           ä   ?   $   ]          V  ñ       (               ²  º              ¯            Ó           ‰    V       <  ƒ           M               K          Ã                   È   ¸      º  ê                  C      %       î   ‰       Ô    N  Ø             ›  [       Å   1                  á                 ¨                            J       #      ÷     î      1  h  Æ  ¬                    ¥   á       «   D      3  À            ñ  (  r      q            W           ”          G  6  !  ¾      p  v  ş   ‚                           	   À           ¥          ‚  §           Ã  ß  >   Š   v   ®  !          s      é      Ü      ™                        ×  9  2   Q  +          .        x  ’  l      2              {  0   ³   C  é   «  ö           8  ¦  İ     D  Ç          '       Š  X      +     8       ²                      Ì      â      –                   ÿ  Ö          E  §          ¦   ¢       ä            (              ›  ¬      H                               \  E                     Î                     .   n  û                             2                     Î      ´        õ           3           >          ğ    ;   ú           Ù       +  é      Ë              Ğ  =      w  m  İ       3      Ÿ      }  |          Î   B                  ˆ  ‹       4   $          %  z                                É  œ  ã  X                      ò  «                             @       Õ  o     )   §              ¼          Z              ¹                           
          R                 Ñ   £                          ª       Q                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          ÿS                          c             Ó         c             T         c               ä            ä     (ä            ±'     0ä            ·'     @ä            »'     Hä            É'     Xä            Î'     `ä            &     pä            ×'     xä            ·'     ˆä            ã'     ä            ë'      ä            ñ'     ¨ä            ù'     ¸ä             (     Àä            
(     Ğä            (     Øä            (     èä            3(     ğä            ;(      å            Ø(     å            ì(     å            ğ0     å            ğj      å             ¢     (å            0¢     0å            Pe     8å            `e     @å            pe     Hå            `f     På            Ğf     Xå            àf     `å             g     xå            g     €å             g     ˆå            0g     å            @g     ˜å            Pg      å            `g     ¨å            pg     Èå             k     Ğå             n     Øå            0p     àå            ğp     èå            °q     ğå            Àr     øå            @s      æ            Ğw     æ             {     æ            |     æ            `      æ            à     (æ            `‚     0æ            ĞŠ     8æ                 @æ            @     Hæ            `     Pæ            À     `æ             ›     hæ             n     pæ            0p     xæ            ğp     €æ            °q     ˆæ            Àr     æ            @œ     ˜æ            Pœ      æ            `œ     ¨æ            |     °æ            `     ¸æ            à     Èæ            ĞŠ     Ğæ                 Øæ            @     àæ            `     èæ            À     øæ            pœ      ç             n     ç            0p     ç            ğp     ç            °q      ç            Àr     (ç                  0ç            °     8ç             Ÿ     @ç            |     Hç            `     Pç            à     `ç            ĞŠ     hç                 pç            @     xç            `     €ç            À     ç            @¢     ˜ç            ¤      ç             ¥     ¨ç             ¦     °ç            `¦     ¸ç            p¦     Àç            À¦     Èç            p§     Øç            Ğ§     èç            `¨     è            p¨     è            Ğ¨     (è            Pä     0è            àä     8è            Àå     @è            0è     Hè            Ğè     Pè            àè     Àè            ó7     Èè            õ7     Ğè            ÷7     Øè            ü7     àè            =8     èè            G8     ğè            R8     øè            ^8      é            i8     é            u8     é            |8     é            „8      é            Œ8     (é            ‘8     0é            –8     8é            œ8     @é            ª8     Hé            °8     Pé            º8     Xé            ¿8     `é            Ä8     hé            Ç8     pé            Í8     xé            Ô8     €é            Ø8     ˆé            â8     é            é8     ˜é            ğ8      é            ÷8     ¨é            ş8     °é            9     ¸é            9     Àé            9     Èé            %9     Ğé            +9     Øé            59     àé            ?9     èé            D9     ğé            N9     øé            Y9      ê            ^9     ê            e9     ê            p9     ê            u9      ê            z9     (ê            €9     0ê            †9     8ê            Œ9     @ê            9     Hê            “9     Pê            ™9     Xê            ¤9     `ê            ¯9     hê            ·9     pê            À9     xê            Ç9     €ê            Ï9     ˆê            Ò9     ê            Õ9     ˜ê            Ø9      ê            Û9     ¨ê            Ş9     °ê            á9     ¸ê            è9     Àê            î9     Èê            ø9     Ğê            :     Øê            :     àê            :     èê            :     ğê            &:     øê            /:      ë            6:     ë            C:     ë            N:     ë            S:      ë            [:     (ë            a:     0ë            h:     8ë            t:     @ë            y:     Hë            ‚:     Pë            ‡:     Xë            :     `ë            •:     hë            š:     pë             :     xë            ¨:     €ë            °:     ˆë            º:     ë            Â:     ˜ë            É:      ë            Ö:     ¨ë            Û:     °ë            ç:     ¸ë            ï:     Àë            ö:     Èë            ;     Ğë            ;     Øë            ;     àë            ;     èë            ";     ğë            -;     øë            3;      ì            >;     ì            H;     ì            R;     ì            Y;      ì            _;     (ì            i;     0ì            t;     8ì            x;     @ì            ;     Hì            Š;     Pì            ‘;     Xì            ›;     `ì            ¢;     hì            «;     pì            µ;     xì            ¼;     €ì            Ä;     ˆì            Ò;     ì            Ú;     ˜ì            è;      ì            ó;     ¨ì             <     °ì            <     ¸ì            <     Àì            <     Èì            &<     Ğì            .<     Øì            7<     àì            @<     èì            G<     ğì            O<     øì            V<      í            a<     í            o<     í            z<     í            ‚<      í            ˆ<     (í            <     0í            ˜<     8í            ¢<     @í            ¯<     Hí            ¹<     Pí            Æ<     Xí            Ï<     `í            Ú<     hí            â<     pí            è<     xí            ô<     €í             =     ˆí            =     í            =     ˜í            !=      í            +=     ¨í            5=     °í            :=     ¸í            F=     Àí            R=     Èí            \=     Ğí            b=     Øí            l=     àí            s=     èí            =     ğí            Š=     øí            ’=      î            ›=     î            ¤=     î            ­=     î            ´=      î            ¿=     (î            Ì=     0î            Ö=     8î            İ=     @î            å=     Hî            î=     Pî            ô=     Xî            û=     `î            >     hî            >     pî            >     xî            >     €î            &>     ˆî            1>     î            ;>     ˜î            A>      î            L>     ¨î            W>     °î            \>     ¸î            d>     Àî            n>     Èî            w>     Ğî            ~>     Øî            „>     àî            ?A     èî            CA     ğî            HA     øî            MA      ï            1     ï            UB     ï            \B      ï            hB     0ï            HF     8ï            OF     @ï            WF     Hï            [F     Pï            dF     Xï            kF     `ï            _I     hï            dI     pï            kI     xï            nI     €ï            qI     ˆï            tI     ï            wI     ˜ï            zI      ï            ‚I     ¨ï            …I     °ï            ŒI     ¸ï            ”I     Ğï            pŸ     Øï            À¡     àï            Ğ¢     ğï            @£     øï            £      ğ             ¤     ğ             ¦     ğ            ğ¦     ğ             §      ğ            P§     ğ            WJ     ¨ğ            fJ     Àğ            uJ     Øğ            J     ğğ            ‘J     ñ            J      ñ            ©J     8ñ            µJ     Pñ            ÉJ     hñ            ÙJ     €ñ            îJ     ˜ñ            ıJ     °ñ            K     Èñ            K     àñ            (K     øñ            6K     ò            IK     (ò            \K     @ò            sK     Xò            |K     pò            K     ˆò            ŸK      ò            ¬K     ¸ò            »K     Ğò            ÍK     èò            ×K      ó            åK     ó            õK     0ó            L     Hó            !L     `ó            ,L     xó            7L     ó            CL     ¨ó            SL     Àó            `L     Øó            sL     ğó            †L     ô            “L      ô            ¢L     8ô            ¬L     Pô            ¸L     hô            ÁL     €ô            ÌL     ˜ô            ÖL     °ô            âL     Èô            íL     àô            ùL     øô            
M     õ            M     (õ            7M     @õ            FM     Xõ            TM     põ            gM     ˆõ            uM      õ            …M     ¸õ            ‘M     Ğõ            œM     èõ            §M      ö            ³M     ö            ¾M     0ö            ÓM     Hö            ÛM     `ö            êM     xö            ÷M     ö            
N     ¨ö            N     Àö            ‚I     Èö            `N     Ğö            VA     Øö            dN     àö            iN     èö            lN     ğö            vN     øö            €N      ÷            †N     ÷            k!     ÷            ŠN     ÷            N      ÷            —N     (÷            ¢N     0÷            XI     8÷            ¥N     @÷            k!     H÷            ŠN     P÷            ¬N     X÷            ±N     `÷            ´N     h÷            »N     p÷            †N     x÷            k!     €÷            ÁN     ˆ÷            ÆN     ÷            ËN     ˜÷            k!      ÷            ÏN     ¨÷            ŠN     °÷            ×N     ¸÷            ÛN     À÷            àN     È÷            æN     Ğ÷            êN     Ø÷            îN     à÷            óN     è÷            øN     ğ÷            `N     ø÷            k!      ø            ıN     ø            O     ø            O     ø            VA      ø            O     (ø            …I     0ø            O     8ø            `N     @ø            k!     Hø            O     Pø            #O     Xø            (O     `ø            ,O     hø            9O     pø            BO     xø            J     €ø            IO                  G                 PT                 @T                   Z     8            «Z     P            ğk     h            ¶Z     €            ÃZ     ˜            ÍZ     °            ÓZ     È            ØZ     à            -Y     ğ            ^]     ø            ‰Y                  f]                 ä                  _                  _     (            _     0            _     8            _     @            €N     P            zg     `            g     p            „g     €            erifiziert
- âœ… Signature Metadata in PostgreSQL gespeichert
- âœ… Backend API fÃ¼r Signature Verification verfÃ¼gbar
- âœ… GUI zeigt Signature Status

---

## ğŸ› ï¸ Quick Start (Nach Phase 1)

```powershell
# PKI Package Setup
cd C:\VCC
mkdir PKI
cd PKI

# Verzeichnisstruktur erstellen
mkdir vcc_pki
mkdir vcc_pki\ca, vcc_pki\signing, vcc_pki\keystore, vcc_pki\trust, vcc_pki\mock, vcc_pki\utils, vcc_pki\api
mkdir docs, tests, config, examples

# setup.py, pyproject.toml, README.md erstellen (siehe oben)

# Package installieren
pip install -e .

# Test: Certificate erstellen
vcc-pki create-cert --common-name test.covina.local --output test_cert.json

# Test: Dokument signieren
echo "Test Document" > test.txt
vcc-pki sign -d test.txt -c test_cert.json -out test_signature.json

# Test: Verifizieren
vcc-pki verify -d test.txt -s test_signature.json -c test_cert.json
```

---

## ğŸ“š Referenzen

- **Covina Docs:**
  - `docs/SEC_SIGSTORE_PILOT.md` - Sigstore Integration Plan
  - `docs/TUF_ADOPTION.md` - TUF Framework Adoption
  - `docs/CODE_INTEGRITY_SIGNING_PLAN.md` - Code Signing Strategy
  
- **External:**
  - [cryptography Library](https://cryptography.io/)
  - [Sigstore](https://www.sigstore.dev/)
  - [TUF Framework](https://theupdateframework.io/)
  - [X.509 Certificate RFC](https://www.rfc-editor.org/rfc/rfc5280)

---

## âœ… Phase 1 Checklist

- [ ] PKI Package Verzeichnis erstellt (`C:\VCC\PKI`)
- [ ] `setup.py` und `pyproject.toml` erstellt
- [ ] `README.md` erstellt
- [ ] `__version__.py` erstellt
- [ ] `requirements.txt` und `requirements-dev.txt` erstellt
- [ ] `BaseCertificateAuthority` implementiert
- [ ] `BaseDocumentSigner` implementiert
- [ ] `MockCertificateAuthority` implementiert
- [ ] `MockDocumentSigner` implementiert
- [ ] `PKIService` API implementiert
- [ ] CLI (`cli.py`) implementiert
- [ ] Package `__init__.py` mit Exports
- [ ] Package installiert (`pip install -e .`)
- [ ] CLI funktioniert (`vcc-pki --help`)
- [ ] Manuelle Tests erfolgreich

---

**Status:** ğŸ“ Ready to Start - Phase 1  
**Next Steps:** PKI Package Setup beginnen

