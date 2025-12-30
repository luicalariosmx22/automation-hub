import requests

# Probar una de las URLs de imagen_local
url = "https://app.soynoraai.com/static/uploads/feed_images/aura/2025/12/1087327651347326_20241223_172713.jpg"

print(f"🔍 Probando URL: {url}\n")

try:
    print("1️⃣ HEAD request...")
    response = requests.head(url, timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Headers: {dict(response.headers)}\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")

try:
    print("2️⃣ GET request...")
    response = requests.get(url, timeout=5)
    print(f"   Status: {response.status_code}")
    print(f"   Content-Type: {response.headers.get('content-type')}")
    print(f"   Content-Length: {len(response.content)} bytes\n")
except Exception as e:
    print(f"   ❌ Error: {e}\n")

print("\n✅ URL accesible!" if response.status_code == 200 else "❌ URL no accesible")
