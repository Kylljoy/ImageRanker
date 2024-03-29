
import os
import sys
import socket
import random
import re
import webbrowser
import traceback
import threading

from baseEssentials import *

fileMap = {"html" : "text/html", "js" : "a", "css":"text/css", "jpeg":"image/jpeg", "gif" : "image/gif", "png": "image/png", "txt":"text/plain", "ico":"image/vnd.microsoft.icon "}
port = 8080
rankings_array = []

if (len(sys.argv) < 1):
    exit

try:
    fileNames = os.listdir(sys.argv[1])
    fileNames = list(filter(lambda x : x.split(".")[-1] in ["jpg", "gif", "jpeg", "png"], fileNames))
except Exception:
    print("Failed to find directory, or error opening it")
    exit

numPhotos = len(fileNames)
matchesArray = [[0 for i in range(0, numPhotos)] for j in range(0, numPhotos)]
rankingsArray = [1000 for i in range(0, numPhotos)]
currentRoundVotes = 0
numTotalVotes = 0
numVotesPerRound = 20
if (len(sys.argv) == 3):
    numVotesPerRound = int(sys.argv[2])



memlock = threading.Lock()

def serveFile(cSock, filepath):
    try:
        newFile = open(filepath, "rb")
        suffix = filepath.split(".")[-1]
        contentType = "text/plain"
        if (suffix in fileMap.keys()):
            contentType = fileMap[suffix]
        cSock.send(bytes("HTTP/1.1 200 Document follows \r\nServer: ImageRanker\r\nContent-Type: " + contentType + "\r\n\r\n", encoding = "utf- 8"))
        cSock.send(newFile.read())
        cSock.send(bytes("\r\n\r\n", encoding = "utf-8"))            
        newFile.close()
        cSock.close()
    except FileNotFoundError:
        send404(cSock)

def logResult(victor, loser):
    global memlock, numTotalVotes, currentRoundVotes, numVotesPerRound, matchesArray, rankingsArray
    memlock.acquire()
    matchesArray[victor][loser] += 1
    print("[Match Result] %d beats %d" % (victor, loser))
    numTotalVotes += 1
    currentRoundVotes += 1
    if (currentRoundVotes >= numVotesPerRound):
        newRatings = [0 for i in range(0, numPhotos)]
        ignoranceThreshold = 750
        for participant in range(0, numPhotos):
            currentELO = 0
            totalMatches = 0;
           
            for opponent in range(0, numPhotos):
                if (opponent == participant):
                    continue
                #Add up all the victories
                if matchesArray[participant][opponent] > 0:
                    #Do not consider a win if it happens against an extremely predictable opponnent
                    if (rankingsArray[participant] - rankingsArray[opponent] <= ignoranceThreshold):
                        currentELO += matchesArray[participant][opponent] * (rankingsArray[opponent] + 400)
                        totalMatches += matchesArray[participant][opponent]
                #...and all the losses
                if matchesArray[opponent][participant] > 0:
                    #Do not consider a loss if it happens against an extremely predictable opponnent
                    if (rankingsArray[opponent] - rankingsArray[participant] <= ignoranceThreshold):
                        currentELO += matchesArray[opponent][participant] * (rankingsArray[opponent] - 400)
                        totalMatches += matchesArray[opponent][participant]
            if (totalMatches > 0):     
                currentELO /= totalMatches
                newRatings[participant] = int(currentELO)
            else:
                newRatings[participant] = rankingsArray[participant]
        currentRoundVotes = 0
        rankingsArray = newRatings[::]
        print("[New Rankings Available]")
    memlock.release()

def compileRankings(cSock):
    global numTotalVotes, rankingsArray, numVotesPerRound
    sortedRankings = [(rankingsArray[i], i) for i in range(0, numPhotos)]
    sortedRankings.sort()
    table = ""
    for pair in sortedRankings[::-1]:
        table += "<tr><td><a href=\"/view/" + str(pair[1]) + "\">" + fileNames[pair[1]] + "</a></td><td>" + str(pair[1]) + "</td><td>"+ str(pair[0]) +"</td></tr>"
    newFile = open("imgRankings.html", "r")
    fileData = newFile.read()
    newFile.close()
    fileData = fileData.replace("$RANKINGS", table)
    fileData = fileData.replace("$VOTES", str(numTotalVotes))
    fileData = fileData.replace("$THRESHOLD", str(numVotesPerRound - (numTotalVotes % numVotesPerRound)))
    cSock.send(bytes("HTTP/1.1 200 Document follows \r\nServer: World ImageRanker\r\nContent-Type: text/html\r\n\r\n",encoding="utf-8"))
    cSock.send(bytes(fileData, encoding="utf-8"))
    cSock.send(bytes("\r\n\r\n", encoding="utf-8"))
    cSock.close()
    
def serveMatch(cSock):
    imgA = random.randint(0, numPhotos - 1)
    imgB = imgA
    while imgB == imgA:
        imgB = random.randint(0, numPhotos - 1)
    print("[Match Opened] %d vs %d" % (imgA, imgB))
    newFile = open("imgRank.html", "r")
    fileData = newFile.read()
    newFile.close()
    fileData = fileData.replace("$IMG_1", str(imgA))
    fileData = fileData.replace("$IMG_2", str(imgB))
    cSock.send(bytes("HTTP/1.1 200 Document follows \r\nServer: ImageRanker\r\nContent-Type: text/html\r\n\r\n",encoding="utf-8"))
    cSock.send(bytes(fileData, encoding="utf-8"))
    cSock.send(bytes("\r\n\r\n", encoding="utf-8"))
    cSock.close()

def handleRequest(cSock):
    st = b''
    while True:
        s = cSock.recv(1024)
        if s:
            st += s
            if (len(s) < 1024):
                break
        else:
            break
    header = st.decode("utf-8")
    header = header[:header.find("\r\n\r\n")]
    header = header[:header.find("\r\n")]
    regEx = re.compile("GET [^\s\?]*")
    argsregEx = re.compile("\?[\S]*")
    matches = regEx.match(header)
    argMatches = argsregEx.search(header)
    if matches == None:
        cSock.close()
        return
    fileName = header[matches.start() + 4 : matches.end()]

    args = {}
    if argMatches:
    
        argString = header[argMatches.start() + 1 : argMatches.end()]
        argsList = argString.split("&")
        for pair in argsList:
            values = pair.split("=")
            if (len(values) > 1):
                key = stripFormatting(values[0])
                value = stripFormatting(values[1])
                args[key] = value
    path = fileName.split("/")[1:]
    #print("\n\nArgs =" + str(args))
    #print("\n\nPath = " + " / ".join(path))
    suffix = fileName.split(".")[-1]

    if (fileName == "/"):
        serveMatch(cSock)
        return
    elif (path[0] == "rankings"):
        compileRankings(cSock)
    elif (path[0] == "view"):
        if (len(path) >= 1 and path[1].isdigit()):
            serveImage(cSock, int(path[1]))
            return
    elif (path[0] == "result"):
        if (len(path) >= 3 and path[1].isdigit() and path[2].isdigit()):
            logResult(int(path[1]), int(path[2]))
        redirectPage(cSock, "/")
        return
    elif (path[0].isdigit()):
        serveFile(cSock, sys.argv[1] + "/" + fileNames[int(path[0]) % numPhotos]) 
        return
    elif (".." not in fileName and suffix != "py"):
        try:
            newFile = open(fileName[1:], "rb")
            contentType = "text/plain"
            if (suffix in fileMap.keys()):
                contentType = fileMap[suffix]
            cSock.send(bytes("HTTP/1.1 200 Document follows \r\nServer: ImageRanker\r\nContent-Type: " + contentType + "\r\n\r\n", encoding = "utf- 8"))
            cSock.send(newFile.read())
            cSock.send(bytes("\r\n\r\n", encoding = "utf-8"))
            newFile.close()
            cSock.close()
            return
        except FileNotFoundError:
            send404(cSock)
            return
    send404(cSock)
    

def serveImage(cSock, imgId):
    newFile = open("imgView.html", "r")
    fileData = newFile.read()
    newFile.close()
    fileData = fileData.replace("$IMG", str(imgId))
    cSock.send(bytes("HTTP/1.1 200 Document follows \r\nServer: ImageRanker\r\nContent-Type: text/html\r\n\r\n",encoding="utf-8"))
    cSock.send(bytes(fileData, encoding="utf-8"))
    cSock.send(bytes("\r\n\r\n", encoding="utf-8"))
    cSock.close()



# Server Handling Code
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
success = False
while not success:
    try:
        server.bind(("localhost", port))
        success = True
    except OSError:
        port = 8000 + random.randint(1,1000)
webbrowser.open("localhost:" + str(port) + "/")
server.listen(5)
cSock = None
while True:
        try:
            (cSock, addr) = server.accept()
            t = threading.Thread(target = handleRequest, args = (cSock,))
            t.daemon = True
            t.start()
        except KeyboardInterrupt:
            print("Shutting Down...")
            cSock.close()
            server.close()
            break
        except BrokenPipeError:
            cSock.close()
            None
        except Exception as e:
            print("Critical Exception: " + e.__repr__())
            traceback.print_tb(e.__traceback__)
