from automation_hub.db.supabase_client import create_client_from_env
from datetime import datetime, timedelta

sb = create_client_from_env()

# Publicaciones de hoy
hoy_utc = datetime.utcnow().replace(hour=0, minute=0, second=0)
result = sb.table('meta_publicaciones_webhook').select(
    'id, page_id, mensaje, imagen_url, creada_en'
).gte('creada_en', hoy_utc.isoformat()).order('creada_en', desc=True).execute()

# Escribir a archivo
with open('resultado_publicaciones.txt', 'w', encoding='utf-8') as f:
    f.write(f"\n📊 PUBLICACIONES DE HOY: {len(result.data)}\n\n")
    f.write("=" * 80 + "\n")
    
    print(f"\n📊 PUBLICACIONES DE HOY: {len(result.data)}\n")
    print("=" * 80)

    
    con_imagen = 0
    sin_imagen = 0
    
    for pub in result.data:
        tiene_imagen = bool(pub.get('imagen_url') and pub['imagen_url'].strip())
        
        if tiene_imagen:
            con_imagen += 1
            emoji = "✅"
        else:
            sin_imagen += 1
            emoji = "❌"
        
        hora = datetime.fromisoformat(pub['creada_en'].replace('Z', '+00:00'))
        hora_mexico = hora - timedelta(hours=7)
        
        mensaje = (pub.get('mensaje') or 'Sin mensaje')[:60]
        
        line = f"{emoji} [{hora_mexico.strftime('%H:%M')}] ID:{pub['id']} | Pág:{pub['page_id']}\n"
        f.write(line)
        print(line.strip())
        
        line = f"   📝 {mensaje}...\n"
        f.write(line)
        print(line.strip())
        
        if tiene_imagen:
            line = f"   🖼️  {pub['imagen_url'][:70]}...\n"
            f.write(line)
            print(line.strip())
        f.write("\n")
        print()
    
    f.write("=" * 80 + "\n")
    f.write(f"\n📈 RESUMEN:\n")
    f.write(f"   🖼️  Con imagen: {con_imagen}\n")
    f.write(f"   📝 Sin imagen: {sin_imagen}\n")
    f.write(f"   📊 Total: {len(result.data)}\n\n")
    
    print("=" * 80)
    print(f"\n📈 RESUMEN:")
    print(f"   🖼️  Con imagen: {con_imagen}")
    print(f"   📝 Sin imagen: {sin_imagen}")
    print(f"   📊 Total: {len(result.data)}\n")

print("\n✅ Resultado guardado en: resultado_publicaciones.txt")
