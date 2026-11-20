"""Mantiene al día dominios.json, la lista que las apps (DomainList.kt) bajan
al abrir. Para cada sitio, visita sus dominios y sigue las redirecciones: si
uno lleva a un dominio nuevo de la misma marca, ese pasa a ser el primero.
Los viejos quedan detrás, de respaldo. Corre en GitHub (fuera de la red de
Movistar, que bloquea varios por DNS), cada 6 horas y a mano.
"""
import json
import re
import ssl
import sys
import urllib.request
from urllib.parse import urlparse

ARCHIVO = "dominios.json"
# La marca que tiene que aparecer en un dominio nuevo para aceptarlo: una
# redirección a otra cosa (publicidad, una página de "bloqueado") no cuenta.
MARCAS = {"cuevana": "cuevana", "pelota": "pelotalibre"}
# Se revisan los primeros: el resto ya redirige a alguno de estos.
REVISAR = 3
UA = "Mozilla/5.0 (Linux; Android 9) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0 Mobile Safari/537.36"


def destino(dominio):
    """Dominio final al que lleva https://dominio/ (siguiendo redirecciones), o None."""
    pedido = urllib.request.Request(f"https://{dominio}/", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(pedido, timeout=20, context=ssl.create_default_context()) as r:
            if r.status >= 400:
                return None
            host = urlparse(r.geturl()).hostname or ""
            return host[4:] if host.startswith("www.") else host
    except Exception as e:  # sitio caído, certificado vencido, etc.
        print(f"  {dominio}: {e}")
        return None


def main():
    # utf-8-sig: por si el archivo se guardó con BOM desde Windows.
    with open(ARCHIVO, encoding="utf-8-sig") as f:
        datos = json.load(f)
    cambios = []
    for sitio, marca in MARCAS.items():
        lista = datos.get(sitio, [])
        for dominio in lista[:REVISAR]:
            final = destino(dominio)
            print(f"{sitio}: {dominio} -> {final}")
            if not final or final == dominio or final in lista:
                continue
            if not re.search(marca, final) or not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", final):
                print(f"  {final} no parece de {marca}, no se agrega")
                continue
            # Que el nuevo responda por sí mismo antes de ponerlo primero.
            if destino(final) != final:
                print(f"  {final} no responde bien, no se agrega")
                continue
            lista.insert(0, final)
            cambios.append(f"{sitio}: {final} (desde {dominio})")
            break
        datos[sitio] = lista
    if not cambios:
        print("sin cambios")
        return 0
    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("cambios:", "; ".join(cambios))
    with open("cambios.txt", "w", encoding="utf-8") as f:
        f.write("; ".join(cambios))
    return 0


if __name__ == "__main__":
    sys.exit(main())
