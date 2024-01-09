import random

def send404(cSock):
    cSock.send(bytes("HTTP/1.1 404 File Not Found \r\nServer: ImageRanker \r\nContent-Type: text/html \r\n\r\n", encoding = "utf=8"))
    page = open("404.html","r")
    text = page.read()
    cSock.send(bytes(text, encoding="utf-8"))
    cSock.send(bytes("\r\n\r\n", encoding="utf-8"))
    page.close()
    cSock.close()

def encodeString(s):
    #out = s.replace("\\","\\\\")
    out = s.replace("\"", "&quot;")
    out = out.replace("\'", "&apos;")
    return out

def decodeString(s):
    out = s.replace("\n", "<br>")
    out = out.replace("\\\\", "\\")
    out = out.replace("&quot;", "\"")
    out = out.replace("&apos;", "\'")
    return out    

def redirectPage(cSock, url):
    cSock.send(bytes("HTTP/1.1 200 Document follows \r\nServer: World ImageRanker\r\nContent-Type: text/html\r\n\r\n",encoding="utf-8"))
    cSock.send(bytes("<!DOCTYPE html><body></body><script>window.location.replace(\"" + url + "\");</script></html>", encoding="utf-8"))
    cSock.send(bytes("\r\n\r\n", encoding="utf-8"))
    cSock.close()

