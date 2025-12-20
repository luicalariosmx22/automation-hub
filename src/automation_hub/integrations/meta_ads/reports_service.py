"""
Meta Ads Reports Service

Genera reportes semanales agregados desde los datos detallados de anuncios.
Calcula breakdowns por plataforma (Facebook/Instagram), métricas agregadas,
y análisis de rendimiento de campañas.

Características:
- Agregación de datos desde meta_ads_anuncios_detalle
- Breakdowns por plataforma (Facebook vs Instagram)
- Cálculo de métricas derivadas (CTR, CPC, CPM)
- Generación de insights JSON con recomendaciones
- Análisis de tipos de mensajes y objetivos de campañas
- Soft delete (archivado) de reportes previos
"""

import os
import uuid
import json
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from automation_hub.db.supabase_client import create_client_from_env

# Load environment variables
load_dotenv()


class MetaAdsReportsService:
    """Servicio para generar reportes semanales agregados de Meta Ads"""
    
    def __init__(self, supabase_client=None):
        """Initialize service with Supabase client"""
        self.supabase = supabase_client or create_client_from_env()
    
    @staticmethod
    def clean_surrogates(text: str) -> str:
        """Limpia caracteres surrogates para evitar errores de encoding UTF-8"""
        if not isinstance(text, str):
            return str(text)
        return text.encode('utf-8', errors='ignore').decode('utf-8')
    
    def get_ads_data_for_period(
        self,
        cuenta_id: str,
        fecha_inicio: str,
        fecha_fin: str,
        nombre_nora: str
    ) -> List[Dict]:
        """
        Obtiene datos de anuncios para un período específico
        
        Args:
            cuenta_id: ID de la cuenta publicitaria
            fecha_inicio: Fecha de inicio (YYYY-MM-DD)
            fecha_fin: Fecha de fin (YYYY-MM-DD)
            nombre_nora: Nombre de Nora (tenant)
            
        Returns:
            Lista de anuncios en el período
        """
        print(f"[DEBUG] Buscando anuncios con parámetros:")
        print(f"  - nombre_nora: {self.clean_surrogates(nombre_nora)}")
        print(f"  - cuenta_id: {cuenta_id}")
        print(f"  - fecha_inicio: {fecha_inicio}")
        print(f"  - fecha_fin: {fecha_fin}")
        
        try:
            # Query con overlap: fecha_fin >= inicio_periodo AND fecha_inicio <= fin_periodo
            response = self.supabase.table("meta_ads_anuncios_detalle") \
                .select("*") \
                .eq("nombre_nora", nombre_nora) \
                .eq("id_cuenta_publicitaria", cuenta_id) \
                .gte("fecha_fin", fecha_inicio) \
                .lte("fecha_inicio", fecha_fin) \
                .execute()
            
            anuncios = response.data or []
            print(f"[DEBUG] Anuncios encontrados: {len(anuncios)}")
            
            return anuncios
            
        except Exception as e:
            print(f"[DEBUG] Error en consulta de anuncios: {e}")
            return []
    
    def get_empresa_info(self, cuenta_id: str, nombre_nora: str) -> Dict[str, Any]:
        """
        Obtiene información de la empresa asociada a la cuenta
        
        Args:
            cuenta_id: ID de la cuenta publicitaria
            nombre_nora: Nombre de Nora (tenant)
            
        Returns:
            Dict con empresa_id y empresa_nombre
        """
        empresa_id = None
        empresa_nombre = None
        
        try:
            # Get empresa_id from meta_ads_cuentas
            response = self.supabase.table("meta_ads_cuentas") \
                .select("empresa_id") \
                .eq("id_cuenta_publicitaria", cuenta_id) \
                .eq("nombre_nora", nombre_nora) \
                .single() \
                .execute()
            
            if response.data:
                empresa_id = response.data.get("empresa_id")
                
                # Get empresa_nombre from cliente_empresas
                if empresa_id:
                    emp_response = self.supabase.table("cliente_empresas") \
                        .select("nombre_empresa") \
                        .eq("id", empresa_id) \
                        .single() \
                        .execute()
                    
                    if emp_response.data:
                        empresa_nombre = emp_response.data.get("nombre_empresa")
        
        except Exception as e:
            print(f"⚠️ Error obteniendo info de empresa: {e}")
        
        return {
            "empresa_id": empresa_id,
            "empresa_nombre": empresa_nombre
        }
    
    def analyze_campaign_performance(self, anuncios: List[Dict]) -> tuple[Dict, Dict]:
        """
        Analiza rendimiento de campañas y genera insights
        
        Args:
            anuncios: Lista de anuncios
            
        Returns:
            Tupla con (tipos_mensajes, objetivos_campanas)
        """
        tipos_mensajes = {}
        objetivos_campana = {}
        campanas_performance = {}
        
        def _i(x, k): return int(x.get(k, 0) or 0)
        def _f(x, k): return float(x.get(k, 0) or 0)
        
        # Analizar por campaña
        for anuncio in anuncios:
            campana_nombre = anuncio.get("nombre_campana", "Sin nombre")
            
            if campana_nombre not in campanas_performance:
                campanas_performance[campana_nombre] = {
                    'anuncios': 0,
                    'gasto_total': 0,
                    'impresiones': 0,
                    'clicks': 0,
                    'mensajes': 0,
                    'interacciones': 0
                }
            
            # Acumular métricas por campaña
            perf = campanas_performance[campana_nombre]
            perf['anuncios'] += 1
            perf['gasto_total'] += _f(anuncio, "importe_gastado")
            perf['impresiones'] += _f(anuncio, "impresiones")
            perf['clicks'] += _f(anuncio, "clicks")
            perf['mensajes'] += _f(anuncio, "mensajes_total")
            
            # Calcular interacciones (varios campos posibles)
            interacciones = (
                _f(anuncio, "page_engagement") or
                _f(anuncio, "post_engagement") or
                _f(anuncio, "post_engagements")
            )
            perf['interacciones'] += interacciones
        
        # Clasificar campañas por rendimiento
        for campana, data in campanas_performance.items():
            if data['mensajes'] > 50:
                categoria = "ALTA_CONVERSACIÓN"
            elif data['clicks'] > 1000:
                categoria = "ALTO_TRÁFICO"
            elif data['impresiones'] > 50000:
                categoria = "GRAN_ALCANCE"
            elif data['interacciones'] > 500:
                categoria = "BUEN_ENGAGEMENT"
            else:
                categoria = "RENDIMIENTO_BÁSICO"
            
            objetivos_campana[categoria] = objetivos_campana.get(categoria, 0) + data['anuncios']
        
        # Calcular métricas totales y costos
        total_mensajes = sum(_i(a, "mensajes_total") for a in anuncios)
        total_clicks = sum(_i(a, "clicks") for a in anuncios)
        total_spend = sum(_f(a, "importe_gastado") for a in anuncios)
        total_imp = sum(_i(a, "impresiones") for a in anuncios)
        total_interacciones = sum(
            _f(a, "page_engagement") or _f(a, "post_engagement") or _f(a, "post_engagements")
            for a in anuncios
        )
        total_link_clicks = sum(_i(a, "link_clicks") or _i(a, "inline_link_clicks") for a in anuncios)
        total_video_views = sum(_i(a, "video_plays") for a in anuncios)
        
        # Análisis de tipos de mensajes con costos
        if total_mensajes > 0:
            tipos_mensajes["mensajes_directos"] = total_mensajes
            tipos_mensajes["costo_por_mensaje"] = round(total_spend / total_mensajes, 2)
        
        if total_clicks > 0:
            tipos_mensajes["clicks_generales"] = total_clicks
            tipos_mensajes["costo_por_click"] = round(total_spend / total_clicks, 2)
        
        if total_link_clicks > 0:
            tipos_mensajes["clicks_enlaces"] = total_link_clicks
        
        if total_interacciones > 0:
            tipos_mensajes["interacciones_sociales"] = int(total_interacciones)
        
        if total_video_views > 0:
            tipos_mensajes["reproducciones_video"] = total_video_views
        
        if total_imp > 0:
            tipos_mensajes["impresiones_totales"] = total_imp
            tipos_mensajes["cpm"] = round((total_spend / total_imp) * 1000, 2)
        
        return tipos_mensajes, objetivos_campana
    
    def generate_insights_json(self, reporte: Dict) -> Dict:
        """
        Genera insights y recomendaciones basadas en las métricas
        
        Args:
            reporte: Dict con métricas del reporte
            
        Returns:
            Dict con insights y recomendaciones
        """
        insights = {
            "metricas": {},
            "recomendaciones": [],
            "alertas": []
        }
        
        # Calcular métricas clave
        impresiones = reporte.get("impresiones", 0)
        clicks = reporte.get("clicks", 0)
        spend = reporte.get("importe_gastado_anuncios", 0)
        
        if impresiones > 0:
            ctr = round((clicks / impresiones) * 100, 2)
            insights["metricas"]["ctr"] = ctr
            
            # Recomendaciones basadas en CTR
            if ctr < 1:
                insights["recomendaciones"].append(
                    "CTR bajo (<1%). Considera mejorar el copy o las imágenes de tus anuncios."
                )
            elif ctr > 3:
                insights["recomendaciones"].append(
                    "¡Excelente CTR (>3%)! Tus anuncios están generando buen engagement."
                )
        
        if clicks > 0 and spend > 0:
            cpc = round(spend / clicks, 2)
            insights["metricas"]["cpc"] = cpc
            
            # Recomendaciones basadas en CPC
            if cpc > 5:
                insights["alertas"].append(
                    f"CPC alto (${cpc}). Revisa tu targeting y pujas."
                )
            elif cpc < 1:
                insights["recomendaciones"].append(
                    f"Buen CPC (${cpc}). Mantén tu estrategia actual."
                )
        
        if impresiones > 0 and spend > 0:
            cpm = round((spend / impresiones) * 1000, 2)
            insights["metricas"]["cpm"] = cpm
        
        # Análisis de frecuencia
        frecuencia = reporte.get("frecuencia")
        if frecuencia and frecuencia > 3:
            insights["alertas"].append(
                "Frecuencia alta (>3). Tu audiencia está viendo los anuncios repetidamente. "
                "Considera refrescar los creativos o ampliar la audiencia."
            )
        
        return insights
    
    def derive_messages_from_actions(self, anuncios: List[Dict]) -> Dict[str, int]:
        """
        Deriva mensajes desde actions cuando el campo messaging_conversations_started es 0
        
        Args:
            anuncios: Lista de anuncios
            
        Returns:
            Dict con totals, facebook y instagram messages
        """
        def _msgs_from_actions(rows):
            total = 0
            for r in rows:
                acts = r.get("actions") or []
                if not isinstance(acts, list):
                    continue
                
                # Normalizar a dict {action_type -> float}
                adict = {}
                for a in acts:
                    k = (a or {}).get("action_type")
                    v = (a or {}).get("value")
                    if not k:
                        continue
                    try:
                        adict[k] = float(v) if v is not None else 0.0
                    except Exception:
                        try:
                            adict[k] = float(str(v))
                        except Exception:
                            adict[k] = 0.0
                
                # Prioridad de action types
                for key in (
                    "onsite_conversion.messaging_conversation_started",
                    "onsite_conversion.messaging_conversation_started_7d",
                    "messaging_conversation_started",
                    "messaging_conversation_started_7d",
                    "onsite_conversion.total_messaging_connection",
                    "total_messaging_connection",
                    "onsite_conversion.messaging_first_reply",
                    "messaging_first_reply",
                    "onsite_conversion.total_messaging",
                ):
                    if key in adict:
                        total += int(adict[key])
                        break
            
            return total
        
        fb_anuncios = [a for a in anuncios if (a.get("publisher_platform") or "").lower() == "facebook"]
        ig_anuncios = [a for a in anuncios if (a.get("publisher_platform") or "").lower() == "instagram"]
        
        return {
            "total": _msgs_from_actions(anuncios),
            "facebook": _msgs_from_actions(fb_anuncios),
            "instagram": _msgs_from_actions(ig_anuncios)
        }
    
    def archive_existing_report(
        self,
        empresa_id: Optional[str],
        cuenta_id: str,
        fecha_inicio: str,
        fecha_fin: str,
        nombre_nora: str
    ) -> None:
        """
        Archiva reporte activo previo si existe (soft delete)
        
        Args:
            empresa_id: ID de la empresa
            cuenta_id: ID de la cuenta publicitaria
            fecha_inicio: Fecha de inicio
            fecha_fin: Fecha de fin
            nombre_nora: Nombre de Nora (tenant)
        """
        try:
            query = self.supabase.table("meta_ads_reportes_semanales") \
                .select("id, public_token") \
                .eq("id_cuenta_publicitaria", cuenta_id) \
                .eq("fecha_inicio", fecha_inicio) \
                .eq("fecha_fin", fecha_fin) \
                .eq("estatus", "activo") \
                .eq("nombre_nora", nombre_nora)
            
            if empresa_id:
                query = query.eq("empresa_id", empresa_id)
            
            response = query.execute()
            existing_reports = response.data or []
            
            if existing_reports:
                for report in existing_reports:
                    self.supabase.table("meta_ads_reportes_semanales") \
                        .update({
                            "estatus": "archivado",
                            "archivado_en": datetime.now(timezone.utc).isoformat()
                        }) \
                        .eq("id", report["id"]) \
                        .execute()
                
                print(f"[DEBUG] Archivados {len(existing_reports)} reportes previos")
        
        except Exception as e:
            print(f"⚠️ Error archivando reportes previos: {e}")
    
    def generate_report_for_account(
        self,
        nombre_nora: str,
        cuenta_id: str,
        fecha_inicio: str,
        fecha_fin: str
    ) -> Dict:
        """
        Genera reporte agregado semanal para una cuenta
        
        Args:
            nombre_nora: Nombre de Nora (tenant)
            cuenta_id: ID de la cuenta publicitaria
            fecha_inicio: Fecha de inicio (YYYY-MM-DD)
            fecha_fin: Fecha de fin (YYYY-MM-DD)
            
        Returns:
            Dict con resultado de la generación
        """
        print(f"\n{'='*60}")
        print(f"📊 Generando reporte para cuenta: {cuenta_id}")
        print(f"   Período: {fecha_inicio} → {fecha_fin}")
        print(f"{'='*60}")
        
        # Obtener info de empresa
        empresa_info = self.get_empresa_info(cuenta_id, nombre_nora)
        empresa_id = empresa_info["empresa_id"]
        empresa_nombre = empresa_info["empresa_nombre"]
        
        # Obtener datos de anuncios
        anuncios = self.get_ads_data_for_period(cuenta_id, fecha_inicio, fecha_fin, nombre_nora)
        
        if not anuncios:
            return {
                "ok": False,
                "msg": f"Sin datos de anuncios en el rango. Cuenta: {cuenta_id}, Rango: {fecha_inicio}-{fecha_fin}"
            }
        
        # Separar por plataforma
        fb = [a for a in anuncios if (a.get("publisher_platform") or "").lower() == "facebook"]
        ig = [a for a in anuncios if (a.get("publisher_platform") or "").lower() == "instagram"]
        
        def _i(x, k): return int(x.get(k, 0) or 0)
        def _f(x, k): return float(x.get(k, 0) or 0)
        
        # Calcular métricas totales
        total_imp = sum(_i(a, "impresiones") for a in anuncios)
        total_clicks = sum(_i(a, "clicks") for a in anuncios)
        total_spend = sum(_f(a, "importe_gastado") for a in anuncios)
        
        # Analizar rendimiento de campañas
        tipos_mensajes, objetivos_campana = self.analyze_campaign_performance(anuncios)
        
        # Construir reporte base
        reporte = {
            "empresa_id": empresa_id,
            "id_cuenta_publicitaria": cuenta_id,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "nombre_nora": nombre_nora,
            "empresa_nombre": empresa_nombre,
            "estatus": "activo",
            "created_at": datetime.now(timezone.utc).isoformat(),
            
            # Totales de entidades
            "total_campañas": len({a.get("campana_id") for a in anuncios if a.get("campana_id")}),
            "importe_gastado_campañas": total_spend,
            "total_conjuntos": len({a.get("conjunto_id") for a in anuncios if a.get("conjunto_id")}),
            "importe_gastado_conjuntos": total_spend,
            "total_anuncios": len({a.get("ad_id") for a in anuncios if a.get("ad_id")}),
            "importe_gastado_anuncios": total_spend,
            
            # Métricas generales
            "impresiones": total_imp,
            "alcance": sum(_i(a, "alcance") for a in anuncios),
            "clicks": total_clicks,
            "link_clicks": sum(_i(a, "link_clicks") or _i(a, "inline_link_clicks") for a in anuncios),
            "mensajes": sum(_i(a, "messaging_conversations_started") for a in anuncios),
            "interacciones": sum(
                _i(a, "page_engagement") or _i(a, "post_engagement") or _i(a, "post_engagements")
                for a in anuncios
            ),
            "video_plays": sum(_i(a, "video_plays") for a in anuncios),
            "reproducciones_video_3s": sum(_i(a, "reproducciones_video_3s") for a in anuncios),
            
            # Breakdown Facebook
            "facebook_impresiones": sum(_i(a, "impresiones") for a in fb),
            "facebook_alcance": sum(_i(a, "alcance") for a in fb),
            "facebook_clicks": sum(_i(a, "clicks") for a in fb),
            "facebook_mensajes": sum(_i(a, "messaging_conversations_started") for a in fb),
            "facebook_importe_gastado": sum(_f(a, "importe_gastado") for a in fb),
            
            # Breakdown Instagram
            "instagram_impresiones": sum(_i(a, "impresiones") for a in ig),
            "instagram_alcance": sum(_i(a, "alcance") for a in ig),
            "instagram_clicks": sum(_i(a, "clicks") for a in ig),
            "instagram_mensajes": sum(_i(a, "messaging_conversations_started") for a in ig),
            "instagram_importe_gastado": sum(_f(a, "importe_gastado") for a in ig),
            
            # Análisis JSON
            "tipos_mensajes_json": tipos_mensajes,
            "objetivos_campanas_json": objetivos_campana,
        }
        
        # Fallback: derivar mensajes desde actions si es necesario
        if reporte.get("mensajes", 0) == 0:
            try:
                derived_msgs = self.derive_messages_from_actions(anuncios)
                reporte["mensajes"] = derived_msgs["total"]
                reporte["facebook_mensajes"] = derived_msgs["facebook"]
                reporte["instagram_mensajes"] = derived_msgs["instagram"]
                print(f"[DEBUG] Mensajes derivados de actions: {derived_msgs['total']}")
            except Exception as e:
                print(f"⚠️ Error derivando mensajes: {e}")
        
        # Generar insights
        try:
            insights = self.generate_insights_json(reporte)
            reporte["insights_json"] = insights
        except Exception as e:
            print(f"⚠️ Error generando insights: {e}")
            reporte["insights_json"] = {}
        
        # Archivar reporte previo si existe
        self.archive_existing_report(empresa_id, cuenta_id, fecha_inicio, fecha_fin, nombre_nora)
        
        # Generar public token único
        reporte["public_token"] = str(uuid.uuid4())
        
        # Insertar reporte
        try:
            print(f"[DEBUG] Insertando reporte...")
            print(f"  - Empresa ID: {empresa_id}")
            print(f"  - Cuenta: {cuenta_id}")
            print(f"  - Período: {fecha_inicio} → {fecha_fin}")
            print(f"  - Total anuncios: {len(anuncios)}")
            print(f"  - Mensajes: {reporte['mensajes']}")
            print(f"  - Gasto: ${total_spend:.2f}")
            
            result = self.supabase.table("meta_ads_reportes_semanales") \
                .insert(reporte) \
                .execute()
            
            if result.data:
                report_id = result.data[0].get('id')
                print(f"✅ Reporte insertado exitosamente - ID: {report_id}")
            else:
                print(f"✅ Reporte insertado (sin ID de retorno)")
            
            return {
                "ok": True,
                "reporte": {
                    "empresa_id": empresa_id,
                    "cuenta": cuenta_id,
                    "fecha_inicio": fecha_inicio,
                    "fecha_fin": fecha_fin,
                    "public_token": reporte["public_token"],
                    "total_anuncios": len(anuncios),
                    "gasto_total": total_spend,
                    "mensajes": reporte["mensajes"]
                }
            }
            
        except Exception as e:
            error_msg = f"Error insertando reporte: {e}"
            print(f"❌ {error_msg}")
            return {"ok": False, "error": error_msg}
    
    def generate_weekly_reports(
        self,
        nombre_nora: Optional[str] = None,
        fecha_inicio: Optional[str] = None,
        fecha_fin: Optional[str] = None
    ) -> Dict:
        """
        Genera reportes semanales para todas las cuentas activas
        
        Args:
            nombre_nora: Filtrar por tenant específico (opcional)
            fecha_inicio: Fecha de inicio (default: hace 7 días)
            fecha_fin: Fecha de fin (default: ayer)
            
        Returns:
            Dict con resumen de la generación
        """
        # Calcular fechas por defecto (última semana completa)
        hoy = date.today()
        
        if not fecha_fin:
            # Ayer
            fecha_fin = (hoy - timedelta(days=1)).isoformat()
        
        if not fecha_inicio:
            # Hace 7 días
            fecha_inicio = (date.fromisoformat(fecha_fin) - timedelta(days=6)).isoformat()
        
        print(f"\\n{'='*80}")
        print("📊 GENERACIÓN DE REPORTES SEMANALES META ADS")
        print(f"{'='*80}")
        print(f"🗓️ Período: {fecha_inicio} → {fecha_fin}")
        
        # Obtener cuentas activas
        try:
            query = self.supabase.table('meta_ads_cuentas') \
                .select('id_cuenta_publicitaria, nombre_cliente, nombre_nora, estado_actual')
            
            if nombre_nora:
                query = query.eq('nombre_nora', nombre_nora)
            
            query = query.neq('estado_actual', 'excluida')
            response = query.execute()
            cuentas = response.data or []
            
        except Exception as e:
            return {'ok': False, 'error': f'Error obteniendo cuentas: {e}'}
        
        if not cuentas:
            return {'ok': False, 'error': 'No se encontraron cuentas activas'}
        
        print(f"📈 Cuentas a procesar: {len(cuentas)}")
        
        # Generar reporte para cada cuenta
        results = {
            'ok': True,
            'fecha_inicio': fecha_inicio,
            'fecha_fin': fecha_fin,
            'cuentas_procesadas': 0,
            'reportes_exitosos': 0,
            'reportes_con_errores': [],
            'total_gasto': 0,
            'total_mensajes': 0
        }
        
        for cuenta in cuentas:
            cuenta_id = cuenta['id_cuenta_publicitaria']
            nombre_cliente = self.clean_surrogates(cuenta.get('nombre_cliente', 'Cliente desconocido'))
            nora = cuenta.get('nombre_nora')
            
            try:
                result = self.generate_report_for_account(
                    nombre_nora=nora,
                    cuenta_id=cuenta_id,
                    fecha_inicio=fecha_inicio,
                    fecha_fin=fecha_fin
                )
                
                if result.get('ok'):
                    results['reportes_exitosos'] += 1
                    report_data = result.get('reporte', {})
                    results['total_gasto'] += report_data.get('gasto_total', 0)
                    results['total_mensajes'] += report_data.get('mensajes', 0)
                else:
                    results['reportes_con_errores'].append({
                        'cuenta': nombre_cliente,
                        'cuenta_id': cuenta_id,
                        'error': result.get('msg') or result.get('error')
                    })
                
            except Exception as e:
                results['reportes_con_errores'].append({
                    'cuenta': nombre_cliente,
                    'cuenta_id': cuenta_id,
                    'error': str(e)
                })
            
            results['cuentas_procesadas'] += 1
        
        # Resumen final
        print(f"\\n{'='*80}")
        print("📊 RESUMEN DE GENERACIÓN DE REPORTES")
        print(f"{'='*80}")
        print(f"🗓️ Período: {fecha_inicio} → {fecha_fin}")
        print(f"📈 Cuentas procesadas: {results['cuentas_procesadas']}")
        print(f"✅ Reportes exitosos: {results['reportes_exitosos']}")
        print(f"💰 Gasto total: ${results['total_gasto']:.2f}")
        print(f"💬 Mensajes totales: {results['total_mensajes']}")
        print(f"❌ Reportes con errores: {len(results['reportes_con_errores'])}")
        
        if results['reportes_con_errores']:
            print(f"\n🚨 DETALLE DE ERRORES:")
            print("-" * 50)
            for i, error_info in enumerate(results['reportes_con_errores'], 1):
                print(f"{i}. {error_info['cuenta']} ({error_info['cuenta_id']})")
                print(f"   Error: {self.clean_surrogates(str(error_info['error']))}")
        else:
            print(f"\n🎉 ¡Todos los reportes se generaron correctamente!")
        
        print(f"{'='*80}")
        
        return results
