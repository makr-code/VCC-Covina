#!/usr/bin/env python3
"""
Covi@dataclass
class MailConfig:
    """Mail-Server Konfiguration"""
    smtp_server: str = "192.168.178.94"
    smtp_port: int = 25
    username: str = "system@fritz.box"
    password: str = "v3f3b1d7"
    use_tls: bool = False
    use_ssl: bool = False
    timeout: int = 30
    sender_email: str = "system@fritz.box"
    sender_name: str = "Covina System"ice
==================

E-Mail-Benachrichtigungssystem fÃ¼r Covina Backend:
- SMTP-Integration
- Template-basierte E-Mails
- Benachrichtigungen fÃ¼r Job-Status
- Fehler-Alerts
- HTML und Text E-Mails

Autor: Covina System
Datum: Oktober 2025
"""

import logging
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
import asyncio
import aiosmtplib

# Logging Setup
logger = logging.getLogger("covina_mail")

@dataclass
class MailConfig:
    """Mail-Server Konfiguration"""
    smtp_server: str = "192.168.178.94"
    smtp_port: int = 5272
    username: str = "system@fritz.box"
    password: str = "v3f3b1d7"
    use_tls: bool = True
    use_ssl: bool = False
    timeout: int = 30
    sender_email: str = ""
    sender_name: str = "Covina System"

@dataclass
class MailRecipient:
    """E-Mail EmpfÃ¤nger"""
    email: str
    name: str = ""
    type: str = "primary"  # primary, cc, bcc

@dataclass
class MailTemplate:
    """E-Mail Template Struktur"""
    subject: str
    html_body: str = ""
    text_body: str = ""
    variables: Dict[str, Any] = field(default_factory=dict)

class MailTemplateManager:
    """Manager fÃ¼r E-Mail Templates"""
    
    def __init__(self):
        self.templates = self._load_default_templates()
    
    def _load_default_templates(self) -> Dict[str, MailTemplate]:
        """Lade Standard-Templates"""
        return {
            "job_completed": MailTemplate(
                subject="âœ… Covina Job abgeschlossen - {job_id}",
                html_body="""
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .header { background-color: #4CAF50; color: white; padding: 20px; border-radius: 5px; }
                        .content { padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }
                        .metrics { background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin: 10px 0; }
                        .success { color: #4CAF50; font-weight: bold; }
                        .footer { margin-top: 20px; color: #666; font-size: 12px; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>ğŸ‰ Dokumentenverarbeitung erfolgreich abgeschlossen!</h2>
                    </div>
                    
                    <div class="content">
                        <p><strong>Job-ID:</strong> {job_id}</p>
                        <p><strong>Abgeschlossen am:</strong> {completion_time}</p>
                        <p><strong>Verarbeitungszeit:</strong> {processing_duration}</p>
                        
                        <div class="metrics">
                            <h3>ğŸ“Š Verarbeitungsstatistiken</h3>
                            <ul>
                                <li><span class="success">Dateien erfolgreich:</span> {successful_files} von {total_files}</li>
                                <li><strong>Fehlerhafte Dateien:</strong> {failed_files}</li>
                                <li><strong>Content extrahiert:</strong> {content_chars:,} Zeichen</li>
                                <li><strong>KI-EntitÃ¤ten gefunden:</strong> {ai_entities}</li>
                                <li><strong>Metadata-VollstÃ¤ndigkeit:</strong> {metadata_completeness:.1f}%</li>
                            </ul>
                        </div>
                        
                        <div class="metrics">
                            <h3>ğŸ›ï¸ Dokumentklassifikation</h3>
                            <ul>
                                <li><strong>Gesetze (LAW):</strong> {law_count}</li>
                                <li><strong>Verordnungen (REGULATION):</strong> {regulation_count}</li>
                                <li><strong>Aktennotizen (FILE_NOTE):</strong> {file_note_count}</li>
                            </ul>
                        </div>
                        
                        <div class="metrics">
                            <h3>ğŸ’¾ Backend-SchreibvorgÃ¤nge</h3>
                            <p><strong>Vector Database:</strong> {vector_chunks} Chunks, {vector_keywords} Keywords</p>
                            <p><strong>Graph Database:</strong> {graph_relations} Relationen, {graph_entities} EntitÃ¤ten</p>
                            <p><strong>Relational Database:</strong> {relational_fields} Metadatenfelder</p>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>Diese E-Mail wurde automatisch vom Covina System generiert.</p>
                        <p>Zeitpunkt: {timestamp}</p>
                    </div>
                </body>
                </html>
                """,
                text_body="""
Covina Dokumentenverarbeitung abgeschlossen
==========================================

Job-ID: {job_id}
Abgeschlossen: {completion_time}
Verarbeitungszeit: {processing_duration}

Statistiken:
- Erfolgreich: {successful_files} von {total_files} Dateien
- Fehler: {failed_files} Dateien
- Content: {content_chars:,} Zeichen extrahiert
- KI-EntitÃ¤ten: {ai_entities} gefunden
- Metadata: {metadata_completeness:.1f}% vollstÃ¤ndig

Klassifikation:
- Gesetze: {law_count}
- Verordnungen: {regulation_count} 
- Aktennotizen: {file_note_count}

Backend-SchreibvorgÃ¤nge:
- Vector DB: {vector_chunks} Chunks, {vector_keywords} Keywords
- Graph DB: {graph_relations} Relationen, {graph_entities} EntitÃ¤ten
- Relational DB: {relational_fields} Metadatenfelder

---
Covina System - {timestamp}
                """
            ),
            
            "job_failed": MailTemplate(
                subject="âŒ Covina Job fehlgeschlagen - {job_id}",
                html_body="""
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .header { background-color: #f44336; color: white; padding: 20px; border-radius: 5px; }
                        .content { padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }
                        .error { background-color: #ffebee; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #f44336; }
                        .footer { margin-top: 20px; color: #666; font-size: 12px; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>âš ï¸ Dokumentenverarbeitung fehlgeschlagen</h2>
                    </div>
                    
                    <div class="content">
                        <p><strong>Job-ID:</strong> {job_id}</p>
                        <p><strong>Fehlgeschlagen am:</strong> {failure_time}</p>
                        <p><strong>Verarbeitete Dateien:</strong> {processed_files} von {total_files}</p>
                        
                        <div class="error">
                            <h3>ğŸš¨ Fehlermeldung</h3>
                            <pre>{error_message}</pre>
                        </div>
                        
                        <h3>ğŸ“‹ Empfohlene MaÃŸnahmen</h3>
                        <ul>
                            <li>ÃœberprÃ¼fen Sie die Dateiformate (PDF, DOCX, TXT unterstÃ¼tzt)</li>
                            <li>Stellen Sie sicher, dass Dateien nicht beschÃ¤digt sind</li>
                            <li>PrÃ¼fen Sie die DateigrÃ¶ÃŸe (max. 50MB pro Datei)</li>
                            <li>Kontaktieren Sie den Support bei wiederholten Fehlern</li>
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <p>Diese E-Mail wurde automatisch vom Covina System generiert.</p>
                        <p>Zeitpunkt: {timestamp}</p>
                    </div>  
                </body>
                </html>
                """,
                text_body="""
Covina Dokumentenverarbeitung fehlgeschlagen
===========================================

Job-ID: {job_id}
Fehlgeschlagen: {failure_time}
Verarbeitet: {processed_files} von {total_files} Dateien

FEHLER:
{error_message}

Empfohlene MaÃŸnahmen:
- Dateiformate prÃ¼fen (PDF, DOCX, TXT)
- Dateien auf BeschÃ¤digungen prÃ¼fen
- DateigrÃ¶ÃŸe beachten (max. 50MB)
- Bei wiederholten Fehlern Support kontaktieren

---
Covina System - {timestamp}
                """
            ),
            
            "system_alert": MailTemplate(
                subject="ğŸš¨ Covina System Alert - {alert_type}",
                html_body="""
                <html>
                <head>
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; }
                        .header { background-color: #ff9800; color: white; padding: 20px; border-radius: 5px; }
                        .content { padding: 20px; border: 1px solid #ddd; border-radius: 5px; margin-top: 10px; }
                        .alert { background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ff9800; }
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h2>ğŸš¨ System Alert</h2>
                    </div>
                    
                    <div class="content">
                        <p><strong>Alert-Typ:</strong> {alert_type}</p>
                        <p><strong>Zeitpunkt:</strong> {alert_time}</p>
                        
                        <div class="alert">
                            <h3>Details</h3>
                            <p>{alert_message}</p>
                        </div>
                        
                        <h3>System-Status</h3>
                        <ul>
                            <li><strong>Aktive Jobs:</strong> {active_jobs}</li>
                            <li><strong>CPU-Auslastung:</strong> {cpu_usage}%</li>
                            <li><strong>Speicher-Auslastung:</strong> {memory_usage}%</li>
                        </ul>
                    </div>
                </body>
                </html>
                """
            )
        }
    
    def get_template(self, template_name: str) -> Optional[MailTemplate]:
        """Hole Template nach Name"""
        return self.templates.get(template_name)
    
    def render_template(self, template: MailTemplate, variables: Dict[str, Any]) -> MailTemplate:
        """Rendere Template mit Variablen"""
        rendered = MailTemplate(
            subject=template.subject.format(**variables),
            html_body=template.html_body.format(**variables) if template.html_body else "",
            text_body=template.text_body.format(**variables) if template.text_body else ""
        )
        return rendered

class CovinaMailService:
    """Hauptklasse fÃ¼r E-Mail-Service"""
    
    def __init__(self, config: MailConfig):
        self.config = config
        self.template_manager = MailTemplateManager()
        
        logger.info(f"ğŸ“§ Mail Service initialisiert - Server: {config.smtp_server}:{config.smtp_port}")
    
    async def send_email_async(
        self,
        recipients: List[MailRecipient],
        template_name: str,
        variables: Dict[str, Any],
        attachments: List[str] = None
    ) -> bool:
        """Sende E-Mail asynchron"""
        try:
            # Template laden und rendern
            template = self.template_manager.get_template(template_name)
            if not template:
                logger.error(f"âŒ Template nicht gefunden: {template_name}")
                return False
            
            # Variablen ergÃ¤nzen
            variables["timestamp"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            
            rendered_template = self.template_manager.render_template(template, variables)
            
            # E-Mail erstellen
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.config.sender_name} <{self.config.sender_email}>"
            msg['Subject'] = rendered_template.subject
            
            # EmpfÃ¤nger hinzufÃ¼gen
            primary_recipients = [r.email for r in recipients if r.type == "primary"]
            cc_recipients = [r.email for r in recipients if r.type == "cc"]
            bcc_recipients = [r.email for r in recipients if r.type == "bcc"]
            
            msg['To'] = ", ".join(primary_recipients)
            if cc_recipients:
                msg['Cc'] = ", ".join(cc_recipients)
            
            # Text und HTML Parts
            if rendered_template.text_body:
                text_part = MIMEText(rendered_template.text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            if rendered_template.html_body:
                html_part = MIMEText(rendered_template.html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # AnhÃ¤nge (falls vorhanden)
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {Path(attachment_path).name}'
                            )
                            msg.attach(part)
            
            # E-Mail senden
            all_recipients = primary_recipients + cc_recipients + bcc_recipients
            
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                username=self.config.username,
                password=self.config.password,
                use_tls=self.config.use_tls,
                timeout=self.config.timeout
            )
            
            logger.info(f"âœ… E-Mail gesendet: {template_name} an {len(all_recipients)} EmpfÃ¤nger")
            return True
            
        except Exception as e:
            logger.error(f"âŒ E-Mail-Versand fehlgeschlagen: {e}")
            return False
    
    def send_email_sync(
        self,
        recipients: List[MailRecipient],
        template_name: str,
        variables: Dict[str, Any],
        attachments: List[str] = None
    ) -> bool:
        """Sende E-Mail synchron"""
        try:
            # Verwende asyncio fÃ¼r synchronen Aufruf
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.send_email_async(recipients, template_name, variables, attachments)
            )
            loop.close()
            return result
            
        except Exception as e:
            logger.error(f"âŒ Synchroner E-Mail-Versand fehlgeschlagen: {e}")
            return False
    
    async def send_job_completion_email(
        self,
        recipients: List[MailRecipient],
        job_id: str,
        metrics: Dict[str, Any]
    ) -> bool:
        """Sende Job-Abschluss E-Mail"""
        
        # Extrahiere Metriken
        variables = {
            "job_id": job_id,
            "completion_time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "processing_duration": f"{metrics.get('avg_processing_time', 0):.2f}s",
            "successful_files": metrics.get('successful_files', 0),
            "total_files": metrics.get('total_files', 0),
            "failed_files": metrics.get('failed_files', 0),
            "content_chars": metrics.get('content_extraction', {}).get('content_extracted_chars', 0),
            "ai_entities": metrics.get('ai_processing', {}).get('entities_found', 0),
            "metadata_completeness": metrics.get('metadata_extraction', {}).get('avg_completeness', 0),
            "law_count": metrics.get('classification_stats', {}).get('LAW', 0),
            "regulation_count": metrics.get('classification_stats', {}).get('REGULATION', 0),
            "file_note_count": metrics.get('classification_stats', {}).get('FILE_NOTE', 0),
            "vector_chunks": metrics.get('backend_metrics', {}).get('vector_database', {}).get('chunks', 0),
            "vector_keywords": metrics.get('backend_metrics', {}).get('vector_database', {}).get('keywords', 0),
            "graph_relations": metrics.get('backend_metrics', {}).get('graph_database', {}).get('internal_relations', 0),
            "graph_entities": metrics.get('backend_metrics', {}).get('graph_database', {}).get('entities', 0),
            "relational_fields": metrics.get('backend_metrics', {}).get('relational_database', {}).get('metadata_fields', 0)
        }
        
        return await self.send_email_async(recipients, "job_completed", variables)
    
    async def send_job_failure_email(
        self,
        recipients: List[MailRecipient],
        job_id: str,
        error_message: str,
        processed_files: int = 0,
        total_files: int = 0
    ) -> bool:
        """Sende Job-Fehler E-Mail"""
        
        variables = {
            "job_id": job_id,
            "failure_time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "error_message": error_message,
            "processed_files": processed_files,
            "total_files": total_files
        }
        
        return await self.send_email_async(recipients, "job_failed", variables)
    
    async def send_system_alert(
        self,
        recipients: List[MailRecipient],
        alert_type: str,
        alert_message: str,
        system_stats: Dict[str, Any] = None
    ) -> bool:
        """Sende System-Alert E-Mail"""
        
        variables = {
            "alert_type": alert_type,
            "alert_time": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "alert_message": alert_message,
            "active_jobs": system_stats.get('active_jobs', 0) if system_stats else 0,
            "cpu_usage": system_stats.get('cpu_usage', 0) if system_stats else 0,
            "memory_usage": system_stats.get('memory_usage', 0) if system_stats else 0
        }
        
        return await self.send_email_async(recipients, "system_alert", variables)
    
    async def test_connection(self) -> bool:
        """Teste SMTP-Verbindung ohne E-Mail zu senden"""
        try:
            logger.info(f"ğŸ” Teste SMTP-Verbindung zu {self.config.smtp_server}:{self.config.smtp_port}")
            
            # SMTP-Verbindung testen
            smtp = aiosmtplib.SMTP(
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                timeout=self.config.timeout
            )
            
            # Verbindung herstellen
            await smtp.connect()
            logger.info("âœ… SMTP-Verbindung hergestellt")
            
            # TLS/SSL Setup
            if self.config.use_tls:
                await smtp.starttls()
                logger.info("âœ… TLS-VerschlÃ¼sselung aktiviert")
            
            # Authentifizierung testen
            if self.config.username and self.config.password:
                await smtp.login(self.config.username, self.config.password)
                logger.info("âœ… SMTP-Authentifizierung erfolgreich")
            
            # Verbindung schlieÃŸen
            await smtp.quit()
            logger.info("âœ… SMTP-Verbindungstest erfolgreich")
            
            return True
            
        except Exception as e:
            logger.error(f"âŒ SMTP-Verbindungstest fehlgeschlagen: {e}")
            return False
    
    async def send_email(
        self,
        recipients: List[MailRecipient],
        subject: str,
        html_body: str = "",
        text_body: str = "",
        attachments: List[str] = None
    ) -> bool:
        """Sende E-Mail direkt mit Inhalt (ohne Template)"""
        try:
            # E-Mail erstellen
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.config.sender_name} <{self.config.sender_email}>"
            msg['Subject'] = subject
            
            # EmpfÃ¤nger hinzufÃ¼gen
            primary_recipients = [r.email for r in recipients if r.type == "primary"]
            cc_recipients = [r.email for r in recipients if r.type == "cc"]
            bcc_recipients = [r.email for r in recipients if r.type == "bcc"]
            
            msg['To'] = ", ".join(primary_recipients)
            if cc_recipients:
                msg['Cc'] = ", ".join(cc_recipients)
            
            # Text und HTML Parts
            if text_body:
                text_part = MIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
            
            # AnhÃ¤nge (falls vorhanden)
            if attachments:
                for attachment_path in attachments:
                    if Path(attachment_path).exists():
                        with open(attachment_path, "rb") as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {Path(attachment_path).name}'
                            )
                            msg.attach(part)
            
            # E-Mail senden
            all_recipients = primary_recipients + cc_recipients + bcc_recipients
            
            await aiosmtplib.send(
                msg,
                hostname=self.config.smtp_server,
                port=self.config.smtp_port,
                username=self.config.username,
                password=self.config.password,
                use_tls=self.config.use_tls,
                timeout=self.config.timeout
            )
            
            logger.info(f"âœ… E-Mail gesendet: '{subject}' an {len(all_recipients)} EmpfÃ¤nger")
            return True
            
        except Exception as e:
            logger.error(f"âŒ E-Mail-Versand fehlgeschlagen: {e}")
            return False

# Factory fÃ¼r einfache Verwendung
def create_mail_service(
    smtp_server: str,
    smtp_port: int = 587,
    username: str = "",
    password: str = "",
    sender_email: str = "",
    sender_name: str = "Covina System"
) -> CovinaMailService:
    """Factory fÃ¼r Mail Service"""
    
    config = MailConfig(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        sender_email=sender_email,
        sender_name=sender_name
    )
    
    return CovinaMailService(config)

# Test-Funktion
async def test_mail_service():
    """Test des Mail Service"""
    
    # Test-Konfiguration (f¦±€   ˜   0 P  LJ6p
>Üh"l  $¬!D	(   
 ª e 
èÊ2f8N +—"¡'LÁHƒB4äm Zo  NN®hCı
'ÿÿ ÿ€ ÿ????ÿ????????ÿ????????ÿ????????ÿ?ÿÿÿÿÿÿÿÿÿÿÿÿÿ°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü°ÿü                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      