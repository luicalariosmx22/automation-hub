#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📅 Google Calendar Sync Service - Sincronización bidireccional por tenant
Maneja OAuth por usuario, watch channels y sincronización completa
"""

import os
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
import requests
import pytz
from dateutil import parser as date_parser
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from automation_hub.db.supabase_client import create_client_from_env

logger = logging.getLogger(__name__)

class GoogleCalendarSyncService:
    """Servicio de sincronización con Google Calendar por tenant"""
    
    # Scopes necesarios para Calendar API
    SCOPES = [
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
    
    # Timezone por defecto si no está configurado
    DEFAULT_TIMEZONE = 'America/Mexico_City'
    
    def __init__(self, nombre_nora: str):
        self.nombre_nora = nombre_nora
        self.supabase = create_client_from_env()
        self.client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
        self.redirect_uri = self._build_redirect_uri()
        self._timezone_cache = None  # Cache para evitar consultas repetidas
        
        # Debug temporal
        logger.info(f"[DEBUG] GOOGLE_OAUTH_CLIENT_ID: {self.client_id[:20] if self.client_id else 'None'}...")
        logger.info(f"[DEBUG] GOOGLE_OAUTH_CLIENT_SECRET: {'Configured' if self.client_secret else 'None'}")
        
        if not all([self.client_id, self.client_secret]):
            logger.warning("Credenciales de Google OAuth no configuradas")
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Genera URL para iniciar flujo OAuth de Google
        
        Args:
            state: Parámetro de estado generado por oauth_google.py
            
        Returns:
            URL de autorización de Google
        """
        try:
            if not self.client_id:
                raise ValueError("GOOGLE_OAUTH_CLIENT_ID no configurado")
            
            # Usar redirect URI fijo del .env
            redirect_uri = os.getenv('GOOGLE_OAUTH_REDIRECT_URI')
            if not redirect_uri:
                redirect_uri = f"{os.getenv('BASE_URL', 'http://localhost:5000')}/oauth/google/callback"
            
            params = {
                'client_id': self.client_id,
                'redirect_uri': redirect_uri,
                'scope': ' '.join(self.SCOPES),
                'response_type': 'code',
                'access_type': 'offline',
                'prompt': 'consent',  # Forzar consent para obtener refresh_token
                'state': state or f"tenant_{self.nombre_nora}"
            }
            
            auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            logger.info(f"URL de autorización generada para {self.nombre_nora}")
            return auth_url
            
        except Exception as e:
            logger.error(f"Error generando URL de autorización: {e}")
            raise
    
    def get_tenant_timezone(self) -> str:
        """
        Obtiene la zona horaria configurada para el tenant
        
        Returns:
            Zona horaria en formato IANA (ej: 'America/Mexico_City')
        """
        try:
            # Usar cache si ya se consultó
            if self._timezone_cache:
                return self._timezone_cache
            
            # Consultar configuración del tenant
            result = self.supabase.table('configuracion_bot') \
                .select('timezone') \
                .eq('nombre_nora', self.nombre_nora) \
                .single() \
                .execute()
            
            if result.data and result.data.get('timezone'):
                configured_tz = result.data['timezone']
                
                # Normalizar timezones equivalentes
                timezone_equivalents = {
                    'America/Hermosillo': 'America/Phoenix',  # Misma zona horaria (UTC-7)
                    'America/Phoenix': 'America/Phoenix',     # Phoenix no observa DST
                }
                
                # Si el timezone configurado tiene un equivalente, usar el normalizado
                normalized_tz = timezone_equivalents.get(configured_tz, configured_tz)
                
                self._timezone_cache = normalized_tz
                logger.debug(f"Timezone para {self.nombre_nora}: configurado={configured_tz}, normalizado={normalized_tz}")
                return self._timezone_cache
            
            # Fallback al default
            self._timezone_cache = self.DEFAULT_TIMEZONE
            logger.warning(f"Timezone no configurado para {self.nombre_nora}, usando default: {self.DEFAULT_TIMEZONE}")
            return self._timezone_cache
            
        except Exception as e:
            logger.error(f"Error obteniendo timezone del tenant: {e}")
            return self.DEFAULT_TIMEZONE
    
    def handle_oauth_callback(self, code: str, state: str) -> Dict:
        """
        Maneja callback de OAuth y guarda tokens
        
        Args:
            code: Código de autorización de Google
            state: Estado enviado originalmente
            
        Returns:
            Dict con resultado del proceso
        """
        try:
            # Validar state
            if not state.endswith(f"tenant_{self.nombre_nora}"):
                raise ValueError("Estado inválido en callback")
            
            # Intercambiar código por tokens
            token_data = self._exchange_code_for_tokens(code)
            
            # Guardar tokens en BD
            self._save_tokens(token_data)
            
            # Obtener info del usuario
            user_info = self._get_user_info(token_data['access_token'])
            
            logger.info(f"OAuth completado para {self.nombre_nora}: {user_info.get('email')}")
            
            return {
                'success': True,
                'user_email': user_info.get('email'),
                'calendars_available': self._list_calendars(token_data['access_token'])
            }
            
        except Exception as e:
            logger.error(f"Error en callback OAuth: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_connection_status(self) -> Dict:
        """
        Obtiene estado actual de la conexión con Google Calendar
        
        Returns:
            Dict con estado de conexión
        """
        try:
            tokens = self._load_tokens()
            if not tokens:
                return {'connected': False, 'reason': 'No hay tokens guardados'}
            
            # Verificar si los tokens son válidos
            if self._are_tokens_valid(tokens):
                calendars = self._list_calendars(tokens['access_token'])
                return {
                    'connected': True,
                    'user_email': tokens.get('user_email'),
                    'calendars': calendars,
                    'selected_calendar': tokens.get('selected_calendar_id', 'primary')
                }
            else:
                return {'connected': False, 'reason': 'Tokens expirados o inválidos'}
                
        except Exception as e:
            logger.error(f"Error verificando estado de conexión: {e}")
            return {'connected': False, 'reason': f'Error: {str(e)}'}
    
    def select_calendar(self, calendar_id: str) -> bool:
        """
        Selecciona calendario por defecto para sincronización
        
        Args:
            calendar_id: ID del calendario a seleccionar
            
        Returns:
            True si se guardó correctamente
        """
        try:
            tokens = self._load_tokens()
            if not tokens:
                raise ValueError("No hay conexión con Google Calendar")
            
            # Validar que el calendario existe
            calendars = self._list_calendars(tokens['access_token'])
            calendar_exists = any(cal['id'] == calendar_id for cal in calendars)
            
            if not calendar_exists:
                raise ValueError(f"Calendario {calendar_id} no encontrado")
            
            # Actualizar configuración
            tokens['selected_calendar_id'] = calendar_id
            self._save_tokens(tokens)
            
            logger.info(f"Calendario seleccionado: {calendar_id} para {self.nombre_nora}")
            return True
            
        except Exception as e:
            logger.error(f"Error seleccionando calendario: {e}")
            return False
    
    def sync_to_google(self, eventos_locales: List[Dict]) -> Dict:
        """
        Sincroniza eventos locales hacia Google Calendar
        
        Args:
            eventos_locales: Lista de eventos a sincronizar
            
        Returns:
            Dict con estadísticas de sincronización
        """
        try:
            tokens = self._load_tokens()
            if not tokens:
                raise ValueError("No hay conexión con Google Calendar")
            
            service = self._build_service(tokens)
            calendar_id = tokens.get('selected_calendar_id', 'primary')
            
            stats = {'created': 0, 'updated': 0, 'errors': 0}
            
            for evento in eventos_locales:
                try:
                    google_event = self._convert_to_google_event(evento)
                    
                    if evento.get('google_event_id'):
                        # Actualizar evento existente
                        service.events().update(
                            calendarId=calendar_id,
                            eventId=evento['google_event_id'],
                            body=google_event
                        ).execute()
                        stats['updated'] += 1
                    else:
                        # Crear nuevo evento
                        created_event = service.events().insert(
                            calendarId=calendar_id,
                            body=google_event
                        ).execute()
                        
                        # Actualizar evento local con google_event_id
                        self._update_local_event_google_id(evento['id'], created_event['id'])
                        stats['created'] += 1
                        
                except Exception as e:
                    logger.error(f"Error sincronizando evento {evento.get('id')}: {e}")
                    stats['errors'] += 1
            
            logger.info(f"Sync hacia Google completado: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error en sync hacia Google: {e}")
            return {'created': 0, 'updated': 0, 'errors': -1}
    
    def sync_from_google(self, fecha_desde: str, fecha_hasta: str) -> Dict:
        """
        Sincroniza eventos desde Google Calendar hacia local
        Detecta eventos eliminados en Google y los marca como cancelados localmente
        
        Args:
            fecha_desde: Fecha inicio en formato ISO
            fecha_hasta: Fecha fin en formato ISO
            
        Returns:
            Dict con estadísticas de sincronización
        """
        try:
            tokens = self._load_tokens()
            if not tokens:
                raise ValueError("No hay conexión con Google Calendar")
            
            service = self._build_service(tokens)
            calendar_id = tokens.get('selected_calendar_id', 'primary')
            
            # Obtener eventos de Google (incluir eventos cancelados)
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=fecha_desde,
                timeMax=fecha_hasta,
                singleEvents=True,
                orderBy='startTime',
                showDeleted=True  # ← NUEVO: incluir eventos eliminados
            ).execute()
            
            google_events = events_result.get('items', [])
            stats = {'imported': 0, 'updated': 0, 'cancelled': 0, 'errors': 0}
            
            # Crear set de IDs de eventos activos en Google
            google_event_ids = set()
            
            for google_event in google_events:
                try:
                    event_id = google_event['id']
                    event_status = google_event.get('status', 'confirmed')
                    
                    # Verificar si ya existe localmente
                    local_event = self._find_local_event_by_google_id(event_id)
                    
                    if event_status == 'cancelled':
                        # Evento cancelado/eliminado en Google
                        if local_event:
                            self._cancel_local_event(local_event['id'])
                            stats['cancelled'] += 1
                            logger.info(f"Evento {event_id} cancelado localmente (eliminado en Google)")
                        continue
                    
                    # Agregar a set de eventos activos
                    google_event_ids.add(event_id)
                    
                    evento_data = self._convert_from_google_event(google_event)
                    
                    if local_event:
                        # Actualizar evento existente
                        self._update_local_event(local_event['id'], evento_data)
                        stats['updated'] += 1
                    else:
                        # Crear nuevo evento local
                        self._create_local_event(evento_data, event_id)
                        stats['imported'] += 1
                        
                except Exception as e:
                    logger.error(f"Error procesando evento de Google {google_event.get('id')}: {e}")
                    stats['errors'] += 1
            
            # NUEVO: Cancelar eventos locales que ya no están en Google
            # (fueron eliminados pero no aparecen en la API con status=cancelled)
            local_google_events = self._get_local_google_events(fecha_desde, fecha_hasta)
            for local_event in local_google_events:
                local_google_id = local_event.get('google_event_id')
                if local_google_id and local_google_id not in google_event_ids:
                    # Este evento local tiene google_event_id pero ya no existe en Google
                    if local_event.get('estado') != 'cancelada':
                        self._cancel_local_event(local_event['id'])
                        stats['cancelled'] += 1
                        logger.info(f"Evento {local_event['id']} cancelado (no encontrado en Google)")
            
            logger.info(f"Sync desde Google completado: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Error en sync desde Google: {e}")
            return {'imported': 0, 'updated': 0, 'cancelled': 0, 'errors': -1}
    
    def disconnect(self) -> bool:
        """Desconecta y elimina tokens de Google Calendar"""
        try:
            tokens = self._load_tokens()
            if tokens and tokens.get('access_token'):
                # Revocar tokens en Google
                requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': tokens['access_token']},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
            
            # Eliminar tokens locales
            self._delete_tokens()
            
            logger.info(f"Google Calendar desconectado para {self.nombre_nora}")
            return True
            
        except Exception as e:
            logger.error(f"Error desconectando Google Calendar: {e}")
            return False
    
    def delete_event(self, event_id: str) -> Dict:
        """
        Elimina un evento de Google Calendar
        
        Args:
            event_id: ID del evento en Google Calendar
            
        Returns:
            Dict con resultado de la operación
        """
        try:
            tokens = self._load_tokens()
            if not tokens:
                return {'success': False, 'error': 'No hay conexión con Google Calendar'}
            
            service = self._build_service(tokens)
            calendar_id = tokens.get('selected_calendar_id', 'primary')
            
            try:
                # Eliminar evento de Google Calendar
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=event_id
                ).execute()
                
                logger.info(f"Evento {event_id} eliminado de Google Calendar para {self.nombre_nora}")
                return {'success': True}
                
            except Exception as delete_error:
                error_str = str(delete_error)
                
                # Si el error es 410 (Gone/Deleted), significa que ya fue eliminado
                # Eso es OK para nuestro propósito
                if '410' in error_str or 'deleted' in error_str.lower():
                    logger.info(f"Evento {event_id} ya estaba eliminado en Google Calendar")
                    return {'success': True, 'already_deleted': True}
                
                # Otros errores sí son problemáticos
                raise delete_error
            
        except Exception as e:
            logger.error(f"Error eliminando evento de Google Calendar: {e}")
            return {'success': False, 'error': str(e)}
    
    def _build_redirect_uri(self) -> str:
        """Construye URI de redirección usando BASE_URL (callback agnóstico)"""
        redirect_uri = os.getenv('GOOGLE_OAUTH_REDIRECT_URI')
        if redirect_uri:
            return redirect_uri
        
        base_url = os.getenv('BASE_URL', 'http://localhost:5000')
        return f"{base_url}/oauth/google/callback"
    
    def _exchange_code_for_tokens(self, code: str) -> Dict:
        """Intercambia código de autorización por tokens"""
        try:
            response = requests.post('https://oauth2.googleapis.com/token', data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'grant_type': 'authorization_code',
                'redirect_uri': self.redirect_uri
            })
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error intercambiando código por tokens: {e}")
            raise
    
    def _save_tokens(self, token_data: Dict) -> bool:
        """Guarda tokens en Supabase"""
        try:
            tokens_to_save = {
                'nombre_nora': self.nombre_nora,
                'access_token': token_data.get('access_token'),
                'refresh_token': token_data.get('refresh_token'),
                'expires_at': (datetime.now() + timedelta(seconds=token_data.get('expires_in', 3600))).isoformat(),
                'token_type': token_data.get('token_type', 'Bearer'),
                'scope': token_data.get('scope'),
                'updated_at': datetime.now().isoformat()
            }
            
            # Verificar si ya existe configuración
            existing = self.supabase.table('google_calendar_sync') \
                .select('nombre_nora') \
                .eq('nombre_nora', self.nombre_nora) \
                .execute()
            
            if existing.data:
                # Actualizar
                self.supabase.table('google_calendar_sync') \
                    .update(tokens_to_save) \
                    .eq('nombre_nora', self.nombre_nora) \
                    .execute()
            else:
                # Insertar
                self.supabase.table('google_calendar_sync') \
                    .insert(tokens_to_save) \
                    .execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Error guardando tokens: {e}")
            return False
    
    def _load_tokens(self) -> Optional[Dict]:
        """Carga tokens desde Supabase"""
        try:
            result = self.supabase.table('google_calendar_sync') \
                .select('*') \
                .eq('nombre_nora', self.nombre_nora) \
                .single() \
                .execute()
            
            return result.data if result.data else None
            
        except Exception as e:
            logger.debug(f"No se pudieron cargar tokens: {e}")
            return None
    
    def _delete_tokens(self) -> bool:
        """Elimina tokens de Supabase"""
        try:
            self.supabase.table('google_calendar_sync') \
                .delete() \
                .eq('nombre_nora', self.nombre_nora) \
                .execute()
            return True
            
        except Exception as e:
            logger.error(f"Error eliminando tokens: {e}")
            return False
    
    def _are_tokens_valid(self, tokens: Dict) -> bool:
        """Verifica si los tokens son válidos"""
        try:
            if not tokens.get('access_token'):
                return False
            
            # Verificar expiración
            expires_at = tokens.get('expires_at')
            if expires_at and isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                if expires_at <= datetime.now(timezone.utc):
                    # Intentar refrescar token
                    return self._refresh_token(tokens)
            
            return True
            
        except Exception as e:
            logger.error(f"Error validando tokens: {e}")
            return False
    
    def _refresh_token(self, tokens: Dict) -> bool:
        """Refresca access token usando refresh token"""
        try:
            if not tokens.get('refresh_token'):
                return False
            
            response = requests.post('https://oauth2.googleapis.com/token', data={
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'refresh_token': tokens['refresh_token'],
                'grant_type': 'refresh_token'
            })
            
            response.raise_for_status()
            new_tokens = response.json()
            
            # Actualizar tokens
            tokens.update(new_tokens)
            self._save_tokens(tokens)
            
            return True
            
        except Exception as e:
            logger.error(f"Error refrescando token: {e}")
            return False
    
    def _build_service(self, tokens: Dict):
        """Construye servicio de Google Calendar API"""
        creds = Credentials(
            token=tokens['access_token'],
            refresh_token=tokens.get('refresh_token'),
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        
        return build('calendar', 'v3', credentials=creds)
    
    def _get_user_info(self, access_token: str) -> Dict:
        """Obtiene información del usuario desde Google"""
        try:
            response = requests.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Error obteniendo info de usuario: {e}")
            return {}
    
    def _list_calendars(self, access_token: str) -> List[Dict]:
        """Lista calendarios del usuario"""
        try:
            tokens = {'access_token': access_token}
            service = self._build_service(tokens)
            
            calendars_result = service.calendarList().list().execute()
            calendars = calendars_result.get('items', [])
            
            return [
                {
                    'id': cal['id'],
                    'name': cal.get('summary', 'Sin nombre'),
                    'primary': cal.get('primary', False),
                    'access_role': cal.get('accessRole', 'reader')
                }
                for cal in calendars
            ]
            
        except Exception as e:
            logger.error(f"Error listando calendarios: {e}")
            return []
    
    def _convert_to_google_event(self, evento_local: Dict) -> Dict:
        """Convierte evento local a formato Google Calendar"""
        # Obtener timezone configurado del tenant
        tenant_tz = self.get_tenant_timezone()
        
        # Extraer descripcion y ubicacion de meta si existe
        meta = evento_local.get('meta', {})
        descripcion = ''
        ubicacion = ''
        if isinstance(meta, dict):
            descripcion = meta.get('descripcion', '')
            ubicacion = meta.get('ubicacion', '')
        
        return {
            'summary': evento_local.get('titulo', evento_local.get('cliente_nombre', 'Sin título')),
            'description': descripcion,
            'location': ubicacion,
            'start': {
                'dateTime': evento_local.get('inicio', evento_local.get('fecha_inicio')),
                'timeZone': tenant_tz
            },
            'end': {
                'dateTime': evento_local.get('fin', evento_local.get('fecha_fin')),
                'timeZone': tenant_tz
            },
            'source': {
                'title': f'Nora AI - {self.nombre_nora}',
                'url': f"{os.getenv('BASE_URL', '')}/panel_cliente/{self.nombre_nora}/agenda"
            }
        }
    
    def _convert_from_google_event(self, google_event: Dict) -> Dict:
        """Convierte evento de Google a formato local - PRESERVA timezone original"""
        start = google_event.get('start', {})
        end = google_event.get('end', {})
        
        # Extraer campos principales
        descripcion = google_event.get('description', '')
        ubicacion = google_event.get('location', '')
        
        # IMPORTANTE: Convertir correctamente timezone de Google a local
        # Google envía dateTime con timezone incluido (RFC3339)
        inicio_raw = start.get('dateTime') or start.get('date')
        fin_raw = end.get('dateTime') or end.get('date')
        
        # CORREGIDO: Guardar como UTC con timezone info para evitar doble conversión
        try:
            # Parsear fechas de Google (vienen con timezone)
            if inicio_raw:
                if 'T' in inicio_raw:  # dateTime
                    inicio_dt = date_parser.parse(inicio_raw)
                    # Convertir a UTC y guardar con timezone info
                    inicio = inicio_dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
                else:  # date (evento de todo el día)
                    inicio = inicio_raw + 'T00:00:00+00:00'
            else:
                inicio = None
                
            # Parsear y convertir fin  
            if fin_raw:
                if 'T' in fin_raw:  # dateTime
                    fin_dt = date_parser.parse(fin_raw)
                    # Convertir a UTC y guardar con timezone info
                    fin = fin_dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')
                else:  # date (evento de todo el día)
                    fin = fin_raw + 'T23:59:59+00:00'
            else:
                fin = None
                
        except Exception as tz_error:
            # Fallback si hay error de conversión
            logger.warning(f"⚠️ Error convirtiendo timezone de Google Calendar: {tz_error}")
            logger.warning(f"   Evento: {google_event.get('summary', 'Sin título')}")
            logger.warning(f"   Inicio raw: {inicio_raw}")
            logger.warning(f"   Fin raw: {fin_raw}")
            inicio = inicio_raw
            fin = fin_raw
        
        # Mapear estado de Google a nuestro estado
        status = google_event.get('status', 'confirmed')
        estado_map = {
            'confirmed': 'confirmada',
            'tentative': 'pendiente',
            'cancelled': 'cancelada'
        }
        estado = estado_map.get(status, 'confirmada')
        
        return {
            'titulo': google_event.get('summary', 'Evento de Google'),
            'inicio': inicio,  # Ya incluye timezone de Google
            'fin': fin,  # Ya incluye timezone de Google
            'estado': estado,
            'origen': 'google_calendar',
            'meta': {
                # Campos básicos
                'descripcion': descripcion,
                'ubicacion': ubicacion,
                'origen': 'google_calendar_oauth',
                'google_event_id': google_event.get('id', ''),
                
                # NUEVO: Preservar timezone original de Google
                'google_timezone_start': start.get('timeZone', 'UTC'),
                'google_timezone_end': end.get('timeZone', 'UTC'),
                
                # Información del organizador
                'creator': google_event.get('creator', {}),
                'organizer': google_event.get('organizer', {}),
                
                # Asistentes
                'attendees': google_event.get('attendees', []),
                
                # Links y metadatos
                'htmlLink': google_event.get('htmlLink', ''),
                'hangoutLink': google_event.get('hangoutLink', ''),
                
                # Recurrencia y recordatorios
                'recurrence': google_event.get('recurrence', []),
                'reminders': google_event.get('reminders', {}),
                
                # Visual
                'colorId': google_event.get('colorId', ''),
                
                # Metadata de sincronización
                'google_status': status,
                'google_created': google_event.get('created', ''),
                'google_updated': google_event.get('updated', ''),
                'google_sequence': google_event.get('sequence', 0)
            }
        }
    
    def _find_local_event_by_google_id(self, google_event_id: str) -> Optional[Dict]:
        """Busca evento local por google_event_id"""
        try:
            result = self.supabase.table('agenda_citas') \
                .select('*') \
                .eq('nombre_nora', self.nombre_nora) \
                .eq('google_event_id', google_event_id) \
                .single() \
                .execute()
            
            return result.data if result.data else None
            
        except Exception:
            return None
    
    def _update_local_event_google_id(self, evento_id: str, google_event_id: str) -> bool:
        """Actualiza evento local con google_event_id"""
        try:
            self.supabase.table('agenda_citas') \
                .update({'google_event_id': google_event_id}) \
                .eq('nombre_nora', self.nombre_nora) \
                .eq('id', evento_id) \
                .execute()
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando google_event_id: {e}")
            return False
    
    def _update_local_event(self, evento_id: str, evento_data: Dict) -> bool:
        """Actualiza evento local existente"""
        try:
            self.supabase.table('agenda_citas') \
                .update(evento_data) \
                .eq('nombre_nora', self.nombre_nora) \
                .eq('id', evento_id) \
                .execute()
            return True
            
        except Exception as e:
            logger.error(f"Error actualizando evento local: {e}")
            return False
    
    def _create_local_event(self, evento_data: Dict, google_event_id: str) -> Optional[str]:
        """Crea nuevo evento local desde Google"""
        try:
            evento_data.update({
                'nombre_nora': self.nombre_nora,
                'google_event_id': google_event_id,
                'origen': 'google_calendar',
                'estado': 'confirmada'
            })
            
            result = self.supabase.table('agenda_citas') \
                .insert(evento_data) \
                .execute()
            
            if result.data:
                return result.data[0]['id']
            return None
            
        except Exception as e:
            logger.error(f"Error creando evento local: {e}")
            return None
    
    def _cancel_local_event(self, evento_id: str) -> bool:
        """Marca evento local como cancelado"""
        try:
            self.supabase.table('agenda_citas') \
                .update({'estado': 'cancelada'}) \
                .eq('nombre_nora', self.nombre_nora) \
                .eq('id', evento_id) \
                .execute()
            
            logger.info(f"Evento local {evento_id} marcado como cancelado")
            return True
            
        except Exception as e:
            logger.error(f"Error cancelando evento local {evento_id}: {e}")
            return False
    
    def _get_local_google_events(self, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
        """Obtiene todos los eventos locales que vienen de Google Calendar en el rango de fechas"""
        try:
            result = self.supabase.table('agenda_citas') \
                .select('id, google_event_id, estado') \
                .eq('nombre_nora', self.nombre_nora) \
                .eq('origen', 'google_calendar') \
                .gte('inicio', fecha_desde) \
                .lte('inicio', fecha_hasta) \
                .is_('google_event_id', 'not.null') \
                .execute()
            
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error obteniendo eventos locales de Google: {e}")
            return []
