#!/usr/bin/env python3
"""
Job de Automatización de Comentarios de Meta (Facebook/Instagram)
Sistema tipo ManyChat para ejecutar acciones basadas en comentarios específicos

Este job monitorea la tabla meta_comentarios_webhook y ejecuta automatizaciones
cuando detecta comentarios que coinciden con palabras clave configuradas.

Funcionalidades:
- Detección de palabras clave en comentarios
- Ejecución de acciones automáticas (respuestas, notificaciones, etc.)
- Marcado de comentarios como procesados
- Sistema de notificaciones para comentarios no procesados
- Soporte para comentarios principales y respuestas
"""

import os
import sys
import logging
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import re

# Importar dependencias del proyecto
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from automation_hub.db.supabase_client import create_client_from_env
from automation_hub.integrations.telegram.notifier import TelegramNotifier

# Configuración del job
JOB_NAME = "meta.comentarios.automation"
BATCH_SIZE = 50  # Procesar comentarios en lotes
MAX_COMENTARIOS_POR_EJECUCION = 200

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def crear_alerta(supabase, nombre: str, tipo: str, nombre_nora: str, descripcion: str, evento_origen: str, datos: dict, prioridad: str):
    """Función simple para crear alertas en la tabla alertas"""
    try:
        alerta_data = {
            'nombre': nombre,
            'tipo': tipo,
            'nombre_nora': nombre_nora,
            'descripcion': descripcion,
            'evento_origen': evento_origen,
            'datos': datos,
            'prioridad': prioridad
        }
        result = supabase.table('alertas').insert(alerta_data).execute()
        return result
    except Exception as e:
        logger.warning(f"No se pudo crear alerta: {e}")
        return None

def get_reglas_automatizacion() -> List[Dict[str, Any]]:
    """
    Obtiene las reglas de automatización desde la base de datos.
    
    Returns:
        Lista de reglas activas ordenadas por prioridad
    """
    try:
        supabase = create_client_from_env()
        
        # Obtener reglas activas ordenadas por prioridad
        result = supabase.table('meta_comentarios_reglas').select(
            '*'
        ).eq(
            'activa', True
        ).order(
            'prioridad', desc=False  # 1=alta, 10=baja
        ).execute()
        
        reglas = []
        for regla_raw in result.data:
            if not isinstance(regla_raw, dict):
                continue
                
            regla = dict(regla_raw)
            
            # Convertir estructura de BD a formato esperado por el procesador
            regla_procesada = {
                "id": regla.get('id'),
                "nombre": regla.get('nombre_regla', 'Sin nombre'),
                "nombre_nora": regla.get('nombre_nora', 'Sistema'),
                "descripcion": regla.get('descripcion', ''),
                "page_id": regla.get('page_id'),  # NULL = todas las páginas
                "post_id": regla.get('post_id'),  # NULL = todos los posts
                "palabras_clave": regla.get('palabras_clave', []),
                "accion": regla.get('accion', 'notificar_admin'),
                "parametros": regla.get('parametros', {}),
                "prioridad": regla.get('prioridad', 5),
                "activa": True
            }
            
            # Validar que tenga palabras clave
            if not regla_procesada["palabras_clave"]:
                logger.warning(f"Regla {regla_procesada['id']} sin palabras clave")
                continue
            
            reglas.append(regla_procesada)
        
        logger.info(f"✅ Cargadas {len(reglas)} reglas desde base de datos")
        return reglas
        
    except Exception as e:
        logger.error(f"Error cargando reglas desde BD: {e}")
        # Fallback a reglas hardcodeadas básicas
        return get_reglas_fallback()

def get_reglas_fallback() -> List[Dict[str, Any]]:
    """
    Reglas de respaldo en caso de error cargando desde BD.
    """
    logger.warning("⚠️ Usando reglas de fallback hardcodeadas")
    
    reglas = [
        {
            "id": "fallback_1",
            "nombre": "Comentarios Negativos (Fallback)",
            "nombre_nora": "Sistema",
            "page_id": None,
            "post_id": None,
            "palabras_clave": ["malo", "pésimo", "terrible", "no funciona"],
            "accion": "alerta_urgente",
            "parametros": {"prioridad": "alta", "notificar_inmediato": True},
            "prioridad": 1,
            "activa": True
        },
        {
            "id": "fallback_2", 
            "nombre": "Solicitud Info (Fallback)",
            "nombre_nora": "Sistema",
            "page_id": None,
            "post_id": None,
            "palabras_clave": ["info", "información", "precio"],
            "accion": "notificar_admin",
            "parametros": {"mensaje": "Solicitud de información detectada"},
            "prioridad": 3,
            "activa": True
        }
    ]
    
    return reglas

def detectar_palabras_clave(mensaje: str, palabras_clave: List[str]) -> bool:
    """
    Detecta si alguna palabra clave está presente en el mensaje.
    
    Args:
        mensaje: Texto del comentario
        palabras_clave: Lista de palabras/frases a detectar
        
    Returns:
        True si encuentra alguna palabra clave
    """
    if not mensaje:
        return False
    
    mensaje_lower = mensaje.lower()
    
    for palabra in palabras_clave:
        # Buscar palabra exacta o como parte de una frase
        if palabra.lower() in mensaje_lower:
            return True
    
    return False

def ejecutar_accion_responder_automatico(comentario: Dict[str, Any], parametros: Dict[str, Any]) -> bool:
    """
    Ejecuta una respuesta automática al comentario usando Meta Graph API.
    
    Args:
        comentario: Datos del comentario
        parametros: Parámetros de la acción (debe incluir 'mensaje')
        
    Returns:
        True si la respuesta se envió correctamente
    """
    try:
        import requests
        
        comment_id = comentario.get('comment_id')
        mensaje_respuesta = parametros.get('mensaje', '¡Hola! Gracias por tu comentario.')
        
        if not comment_id:
            logger.error("No se encontró comment_id para responder")
            return False
        
        # Obtener access token desde .env
        access_token = os.getenv('META_ACCESS_TOKEN') or os.getenv('META_USER_ACCESS_TOKEN')
        
        if not access_token:
            logger.error("No se encontró access token de Meta en variables de entorno")
            return False
        
        # URL de la API de Meta Graph para responder al comentario
        url = f"https://graph.facebook.com/v18.0/{comment_id}/comments"
        
        payload = {
            'message': mensaje_respuesta,
            'access_token': access_token
        }
        
        # Hacer la petición POST
        response = requests.post(url, data=payload)
        
        if response.status_code == 200:
            response_data = response.json()
            logger.info(f"🤖 Respuesta automática enviada exitosamente")
            logger.info(f"📝 Mensaje: {mensaje_respuesta}")
            logger.info(f"💬 Comment ID: {comment_id}")
            logger.info(f"✅ Response ID: {response_data.get('id', 'N/A')}")
            return True
        else:
            error_data = response.json() if response.content else {}
            logger.error(f"Error al enviar respuesta automática: {response.status_code}")
            logger.error(f"Error details: {error_data}")
            return False
        
    except Exception as e:
        logger.error(f"Error ejecutando respuesta automática: {e}")
        return False

def ejecutar_accion_notificar_admin(comentario: Dict[str, Any], parametros: Dict[str, Any]) -> bool:
    """
    Envía notificación al administrador sobre el comentario.
    """
    try:
        bot_token = "8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE"
        chat_id = "5674082622"
        notifier = TelegramNotifier(bot_token=bot_token, default_chat_id=chat_id)
        
        mensaje_notificacion = f"""
📢 COMENTARIO REQUIERE ATENCIÓN

🏢 Cliente: {comentario.get('nombre_nora', 'N/A')}
👤 Usuario: {comentario.get('from_name', 'Anónimo')}
💬 Comentario: "{comentario.get('mensaje', 'Sin mensaje')[:200]}..."
📅 Fecha: {datetime.fromtimestamp(comentario.get('created_time', 0)).strftime('%d/%m/%Y %H:%M') if comentario.get('created_time') else 'N/A'}

🔗 Post ID: {comentario.get('post_id', 'N/A')}
📝 Nota: {parametros.get('mensaje', 'Revisar y responder manualmente')}
        """
        
        notifier.enviar_mensaje(mensaje_notificacion)
        logger.info(f"📧 Notificación enviada al admin para comentario {comentario['comment_id']}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error enviando notificación al admin: {e}")
        return False

def ejecutar_accion_alerta_urgente(comentario: Dict[str, Any], parametros: Dict[str, Any]) -> bool:
    """
    Ejecuta alerta urgente para comentarios negativos.
    """
    try:
        supabase = create_client_from_env()
        
        # Crear alerta en BD
        crear_alerta(
            supabase=supabase,
            nombre="⚠️ COMENTARIO NEGATIVO DETECTADO",
            tipo="comentario_negativo",
            nombre_nora=comentario.get('nombre_nora', 'Sistema'),
            descripcion=f"Comentario negativo de {comentario.get('from_name', 'Usuario anónimo')}",
            evento_origen=JOB_NAME,
            datos={
                "comentario_id": comentario.get('comment_id'),
                "post_id": comentario.get('post_id'),
                "mensaje": comentario.get('mensaje'),
                "usuario": comentario.get('from_name'),
                "timestamp": comentario.get('created_time')
            },
            prioridad="alta"
        )
        
        # Notificación inmediata si está configurada
        if parametros.get('notificar_inmediato'):
            bot_token = "8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE"
            chat_id = "5674082622"
            notifier = TelegramNotifier(bot_token=bot_token, default_chat_id=chat_id)
            
            mensaje_urgente = f"""
🚨 ALERTA URGENTE - COMENTARIO NEGATIVO

🏢 Cliente: {comentario.get('nombre_nora', 'N/A')}
👤 Usuario: {comentario.get('from_name', 'Anónimo')}
😤 Comentario: "{comentario.get('mensaje', 'Sin mensaje')}"
📅 Fecha: {datetime.fromtimestamp(comentario.get('created_time', 0)).strftime('%d/%m/%Y %H:%M') if comentario.get('created_time') else 'N/A'}

🔗 Post: {comentario.get('post_id', 'N/A')}
⚡ Acción requerida: Responder INMEDIATAMENTE
            """
            
            notifier.enviar_alerta(
                nombre="🚨 COMENTARIO NEGATIVO URGENTE",
                descripcion="Requiere respuesta inmediata",
                prioridad="alta",
                datos={"mensaje": mensaje_urgente}
            )
        
        logger.info(f"🚨 Alerta urgente creada para comentario {comentario['comment_id']}")
        return True
        
    except Exception as e:
        logger.error(f"Error ejecutando alerta urgente: {e}")
        return False

def ejecutar_accion_lead_calificado(comentario: Dict[str, Any], parametros: Dict[str, Any]) -> bool:
    """
    Ejecuta acciones para leads calificados (potenciales compradores).
    """
    try:
        supabase = create_client_from_env()
        
        # Crear alerta de lead calificado
        crear_alerta(
            supabase=supabase,
            nombre="🎯 LEAD CALIFICADO DETECTADO",
            tipo="lead_potencial",
            nombre_nora=comentario.get('nombre_nora', 'Sistema'),
            descripcion=f"Lead potencial: {comentario.get('from_name', 'Usuario anónimo')}",
            evento_origen=JOB_NAME,
            datos={
                "comentario_id": comentario.get('comment_id'),
                "post_id": comentario.get('post_id'),
                "mensaje": comentario.get('mensaje'),
                "usuario": comentario.get('from_name'),
                "from_id": comentario.get('from_id'),
                "timestamp": comentario.get('created_time'),
                "asignar_vendedor": parametros.get('asignar_vendedor', False)
            },
            prioridad=parametros.get('prioridad', 'media')
        )
        
        # Notificación para equipo de ventas
        bot_token = "8488045829:AAF5hEBfqe1BgUg3ninX24M15FeeDcS3NkE"
        chat_id = "5674082622"
        notifier = TelegramNotifier(bot_token=bot_token, default_chat_id=chat_id)
        
        mensaje_lead = f"""
🎯 NUEVO LEAD CALIFICADO

🏢 Cliente: {comentario.get('nombre_nora', 'N/A')}
👤 Prospect: {comentario.get('from_name', 'Anónimo')}
💰 Interés: "{comentario.get('mensaje', 'Sin mensaje')[:150]}..."
📅 Fecha: {datetime.fromtimestamp(comentario.get('created_time', 0)).strftime('%d/%m/%Y %H:%M') if comentario.get('created_time') else 'N/A'}

🔗 Post: {comentario.get('post_id', 'N/A')}
📋 Acción: {'Asignar vendedor automáticamente' if parametros.get('asignar_vendedor') else 'Seguimiento manual'}
        """
        
        notifier.enviar_alerta(
            nombre="🎯 Lead Calificado",
            descripcion="Nuevo prospect detectado",
            prioridad=parametros.get('prioridad', 'media'),
            datos={"mensaje": mensaje_lead}
        )
        
        logger.info(f"🎯 Lead calificado procesado para comentario {comentario['comment_id']}")
        return True
        
    except Exception as e:
        logger.error(f"Error procesando lead calificado: {e}")
        return False


def ejecutar_accion_enviar_mensaje_privado(comentario: Dict[str, Any], parametros: Dict[str, Any]) -> bool:
    """
    Ejecuta la acción de enviar un mensaje privado al usuario que comentó.
    Utiliza la API de Meta para enviar un mensaje directo via Messenger.
    """
    try:
        # Verificar que tenemos los datos necesarios
        from_id = comentario.get('from_id')
        if not from_id:
            logger.error("No se puede enviar mensaje privado: falta from_id del usuario")
            return False
        
        mensaje_privado = parametros.get('mensaje', 'Hola, gracias por tu comentario.')
        
        # Configurar access token
        access_token = os.getenv('META_ACCESS_TOKEN') or os.getenv('META_USER_ACCESS_TOKEN')
        if not access_token:
            logger.error("No se encontró access token para Meta API")
            return False
        
        # URL de la API de Meta para enviar mensajes
        url = f"https://graph.facebook.com/v18.0/me/messages"
        
        # Datos del mensaje
        data = {
            'recipient': {'id': from_id},
            'message': {'text': mensaje_privado},
            'access_token': access_token
        }
        
        # Enviar mensaje privado via Meta API
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            response_data = response.json()
            message_id = response_data.get('message_id', 'N/A')
            
            logger.info(f"✅ Mensaje privado enviado exitosamente (ID: {message_id})")
            logger.info(f"   - Destinatario: {from_id}")
            logger.info(f"   - Mensaje: {mensaje_privado[:100]}...")
            
            # Crear alerta de mensaje enviado
            supabase = create_client_from_env()
            crear_alerta(
                supabase=supabase,
                nombre="💬 Mensaje Privado Enviado",
                tipo="mensaje_enviado",
                nombre_nora=comentario.get('nombre_nora', 'Sistema'),
                descripcion=f"Mensaje privado enviado a {comentario.get('from_name', 'Usuario')}",
                evento_origen=JOB_NAME,
                datos={
                    "comentario_id": comentario.get('comment_id'),
                    "post_id": comentario.get('post_id'),
                    "destinatario_id": from_id,
                    "destinatario_nombre": comentario.get('from_name'),
                    "mensaje": mensaje_privado,
                    "message_id": message_id,
                    "timestamp": datetime.now().isoformat()
                },
                prioridad="baja"
            )
            
            return True
        else:
            logger.error(f"Error enviando mensaje privado: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Error ejecutando envío de mensaje privado: {e}")
        return False


def ejecutar_accion(accion: str, comentario: Dict[str, Any], parametros: Dict[str, Any]) -> bool:
    """
    Ejecuta la acción especificada.
    
    Args:
        accion: Tipo de acción a ejecutar
        comentario: Datos del comentario
        parametros: Parámetros de la acción
        
    Returns:
        True si la acción se ejecutó correctamente
    """
    acciones = {
        "responder_automatico": ejecutar_accion_responder_automatico,
        "notificar_admin": ejecutar_accion_notificar_admin,
        "alerta_urgente": ejecutar_accion_alerta_urgente,
        "lead_calificado": ejecutar_accion_lead_calificado,
        "enviar_mensaje_privado": ejecutar_accion_enviar_mensaje_privado
    }
    
    if accion not in acciones:
        logger.warning(f"Acción '{accion}' no reconocida")
        return False
    
    return acciones[accion](comentario, parametros)

def procesar_comentario(comentario: Dict[str, Any], reglas: List[Dict[str, Any]]) -> bool:
    """
    Procesa un comentario individual contra todas las reglas.
    
    Args:
        comentario: Datos del comentario
        reglas: Lista de reglas de automatización
        
    Returns:
        True si el comentario fue procesado (activó alguna regla)
    """
    mensaje = comentario.get('mensaje', '')
    page_id = comentario.get('page_id', '')
    post_id = comentario.get('post_id', '')
    nombre_nora = comentario.get('nombre_nora', '')
    
    procesado = False
    acciones_ejecutadas = []
    
    for regla in reglas:
        # Filtrar por nombre_nora (si la regla no es del sistema)
        if regla.get('nombre_nora') != 'Sistema' and regla.get('nombre_nora') != nombre_nora:
            continue
            
        # Filtrar por page_id (si la regla especifica una página específica)
        if regla.get('page_id') and regla.get('page_id') != page_id:
            continue
            
        # Filtrar por post_id (si la regla especifica un post específico)
        if regla.get('post_id') and regla.get('post_id') != post_id:
            continue
        
        # Verificar palabras clave
        if detectar_palabras_clave(mensaje, regla['palabras_clave']):
            logger.info(f"✅ Regla '{regla['nombre']}' (ID: {regla['id']}) activada para comentario {comentario['comment_id']}")
            
            # Ejecutar la acción
            exito = ejecutar_accion(regla['accion'], comentario, regla['parametros'])
            
            if exito:
                acciones_ejecutadas.append(f"{regla['nombre']} (ID: {regla['id']})")
                procesado = True
            else:
                logger.error(f"❌ Error ejecutando acción '{regla['accion']}' para regla '{regla['nombre']}'")
    
    if acciones_ejecutadas:
        logger.info(f"🎯 Comentario {comentario['comment_id']} procesado con acciones: {', '.join(acciones_ejecutadas)}")
    
    return procesado

def marcar_como_procesado(supabase, comment_id: str) -> bool:
    """
    Marca un comentario como procesado en la base de datos.
    """
    try:
        result = supabase.table('meta_comentarios_webhook').update({
            'procesada': True,
            'procesada_en': datetime.now().isoformat()
        }).eq('comment_id', comment_id).execute()
        
        return len(result.data) > 0
        
    except Exception as e:
        logger.error(f"Error marcando comentario como procesado: {e}")
        return False

def run():
    """
    Función principal del job de automatización de comentarios.
    """
    logger.info(f"🚀 Iniciando job {JOB_NAME}")
    
    try:
        supabase = create_client_from_env()
        
        # Obtener reglas de automatización
        reglas = get_reglas_automatizacion()
        logger.info(f"📋 Cargadas {len(reglas)} reglas de automatización")
        
        if not reglas:
            logger.warning("⚠️ No hay reglas de automatización configuradas")
            return
        
        # Obtener comentarios no procesados (últimas 24 horas)
        fecha_limite = datetime.now() - timedelta(hours=24)
        
        comentarios_result = supabase.table('meta_comentarios_webhook').select(
            '*'
        ).eq(
            'procesada', False
        ).gte(
            'creada_en', fecha_limite.isoformat()
        ).order(
            'created_time', desc=False
        ).limit(MAX_COMENTARIOS_POR_EJECUCION).execute()
        
        comentarios = comentarios_result.data
        logger.info(f"📥 Encontrados {len(comentarios)} comentarios sin procesar")
        
        if not comentarios:
            logger.info("✅ No hay comentarios nuevos para procesar")
            return
        
        # Procesar comentarios
        total_procesados = 0
        total_con_acciones = 0
        
        for comentario_raw in comentarios:
            try:
                # Validar que el comentario sea un dict válido
                if not isinstance(comentario_raw, dict):
                    logger.warning(f"Comentario inválido (no es dict): {type(comentario_raw)}")
                    continue
                
                comentario = dict(comentario_raw)  # Asegurar que es un dict normal
                
                # Validar campos requeridos
                if not comentario.get('comment_id'):
                    logger.warning("Comentario sin comment_id")
                    continue
                
                # Procesar comentario contra reglas
                procesado = procesar_comentario(comentario, reglas)
                
                # Marcar como procesado (independientemente de si activó reglas)
                comment_id = comentario.get('comment_id', '')
                if isinstance(comment_id, str) and marcar_como_procesado(supabase, comment_id):
                    total_procesados += 1
                    
                    if procesado:
                        total_con_acciones += 1
                
            except Exception as e:
                comment_id = comentario_raw.get('comment_id', 'N/A') if isinstance(comentario_raw, dict) else 'N/A'
                logger.error(f"Error procesando comentario {comment_id}: {e}")
        
        # Estadísticas finales
        logger.info(f"📊 Procesamiento completado:")
        logger.info(f"   - Comentarios procesados: {total_procesados}")
        logger.info(f"   - Comentarios con acciones: {total_con_acciones}")
        logger.info(f"   - Comentarios sin activar reglas: {total_procesados - total_con_acciones}")
        
        # Crear alerta de job completado
        crear_alerta(
            supabase=supabase,
            nombre="🤖 Automatización de Comentarios Completada",
            tipo="job_completado",
            nombre_nora="Sistema",
            descripcion=f"Procesados {total_procesados} comentarios, {total_con_acciones} activaron acciones",
            evento_origen=JOB_NAME,
            datos={
                "total_comentarios": len(comentarios),
                "total_procesados": total_procesados,
                "total_con_acciones": total_con_acciones,
                "reglas_activas": len(reglas)
            },
            prioridad="baja"
        )
        
        logger.info(f"✅ Job {JOB_NAME} completado exitosamente")
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando job {JOB_NAME}: {e}", exc_info=True)
        
        # Crear alerta de error
        try:
            supabase = create_client_from_env()
            crear_alerta(
                supabase=supabase,
                nombre="❌ Error en Automatización de Comentarios",
                tipo="job_error",
                nombre_nora="Sistema",
                descripcion=f"Error ejecutando {JOB_NAME}: {str(e)}",
                evento_origen=JOB_NAME,
                datos={"error": str(e)},
                prioridad="alta"
            )
        except:
            pass  # Si no podemos crear la alerta, no queremos romper todo

if __name__ == "__main__":
    run()