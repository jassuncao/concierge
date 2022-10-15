"""A simple HTTP server that only accept GET request
It adopt the programming style of ESP8266WebServer 
library in ESP8266 Arduino Core
"""

import network
import machine
import socket
import uselect
import os

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# Use for checking a new client connection
poller = uselect.poll()
# Dict for registed handlers of all paths
handlers = {}
# Dict for registed handlers of POST requests
postHandlers = {}
# Function of handler for request not found
notFoundHandler = None
# The path to the web documents on MicroPython filesystem
docPath = "/"
# Data for template
tplData = {}

# MIME types
mimeTypes = {
    ".css":"text/css",
    ".jpg":"image/jpg",
    ".png":"image/png",
}

def begin(port=80):
    """Function to start http server
    """
    global server, poller
    server.bind(('0.0.0.0', port))
    server.listen(1)
    # Register for checking new client connection
    poller.register(server, uselect.POLLIN)

def close():
    """Function to stop http server
    """
    poller.unregister(server)
    server.close()

def handleClient():
    """Check for new client connection and process the request
    """
    global server, poller
    # Note:don't call poll() with 0, that would randomly cause
    # reset with "Fatal exception 28(LoadProhibitedCause)" message
    res = poller.poll(1)
    if res:  # There's a new client connection
        (socket, sockaddr) = server.accept()
        socket.settimeout(0.5) # set timeout for readline to avoid blocking
        handle(socket)
        socket.close()

def __sendPage(socket, filePath):
    """Send the file as webpage to client
    """
    try:
        f = open(filePath, "rb")
        while True:
            data = f.read(64)
            if (data == b""):
                break
            socket.write(data)
        f.close()
    except Exception as e:
        print(e)

def __beginHtmlResponse(socket, code, reason, contentType='text/html'):
    socket.write("HTTP/1.1 {} {}\r\n".format(code, reason))
    socket.write("Content-Type: {}\r\n\r\n".format(contentType))

def err(socket, code, message):
    __beginHtmlResponse(socket, code, message)
    socket.write("<h1>{}</h1>".format(message))

def ok(socket, code, *args):
    """Response successful message or webpage to client
    """
    if len(args)==1:
        content_type = "text/plain"
        msg = args[0]
    elif len(args)==2:
        content_type = args[0]
        msg = args[1]
    else:
        raise TypeError("ok() takes 3 or 4 positional arguments but "+ str(len(args)+2) +" were given")
    __beginHtmlResponse(socket, code, 'OK', content_type)
    if __fileExist(msg):
        renderFile(socket, msg)
    else:
        socket.write(msg)

def okData(socket, code, *args):
    """Response successful message
    """
    if len(args)==1:
        content_type = "text/plain"
        msg = args[0]
    elif len(args)==2:
        content_type = args[0]
        msg = args[1]
    __beginHtmlResponse(socket, code, 'OK', content_type)
    socket.write(msg)
        

def __fileExist(path):
    """Check for file existence
    """
    try:
        stat = os.stat(path)
        # stat[0] bit 15 / 14 -> file/dir
        if stat[0] & 0x8000 == 0x8000: # file            
            return True
        else:  # Dir
            return False
    except:
        print("Not Found.")
        return False

def handle(socket):
    """Processing new GET request
    """
    global docPath, handlers
    try: # capture timeout for waiting a line
        currLine = str(socket.readline(), 'utf-8')
    except:
        currLine = "" # readline timeout (not a complete line) 
    request = currLine.split(" ")
    if len(request) != 3: # Discarded if it's a bad header
        return
    (method, url, version) = request
    if "?" in url: # Check if there's query string?
        (path, query) = url.split("?", 2)
    else:
        (path, query) = (url, "")
    args = {}
    if query: # Parsing the querying string
        argPairs = query.split("&")
        for argPair in argPairs:
            arg = argPair.split("=")
            args[arg[0]] = arg[1]
    contentLen = 0
    while True: # Read until blank line after header
        header = socket.readline()
        print("header: ", header)
        if header.startswith("Content-Length:"):
            contentLen = int(header[15:])
        if header == b"":
            return
        if header == b"\r\n":
            break

    # Check for supported HTTP version
    if version != "HTTP/1.0\r\n" and version != "HTTP/1.1\r\n":
        err(socket, "505", "Version Not Supported")
    elif method == "POST":
        formData = str(socket.read(contentLen),'utf-8')
        if path in postHandlers:
            handlePost(socket, path, formData)
        else:
            err(socket, "404", "Not Found")
    elif method != "GET":  # Only accept GET request
        err(socket, "501", "Not Implemented")
    elif path in handlers: # Check for registered path
        handlers[path](socket, args)
    elif not path.startswith(docPath): # Check for wrong path
        err(socket, "400", "Bad Request")
    else: # find file in the document path
        filePath = path
        fileFound = True
        # find the file 
        if not __fileExist(filePath):
            if not path.endswith("/"):
                fileFound = False
            else:
                filePath = path + "index.html"
                # find index.html in the path
                if not __fileExist(filePath):
                    filePath = path + "index.p.html"
                    # find index.p.html in the path
                    if not __fileExist(filePath): # no default html file found
                        fileFound = False
        if not fileFound: # file or default html file specified in path not found
            if notFoundHandler:
                notFoundHandler(socket)
            else:
                err(socket, "404", "Not Found")
            return
           
        contentType = "text/html"
        for ext in mimeTypes:
            if filePath.endswith(ext):
                contentType = mimeTypes[ext]
         # Responds the header first    
        __beginHtmlResponse(socket, 200,'OK', contentType)        
        # Responds the file content
        renderFile(socket, filePath)

def handlePost(socket, path, formData):     
    params = unquote_to_bytes(formData)
    argPairs = params.split("&")
    args = {}
    for argPair in argPairs:
        arg = argPair.split("=")
        args[arg[0]] = arg[1]
    postHandlers[path](socket, args)    

def unquote_to_bytes(string):
    import binascii   
    string = string.replace('+',' ')
    bits = string.split("%")    
    if len(bits) == 1:
        return string
    res = bits[0]    
    list = [res]
    for item in bits[1:]:
        hex = item[:2]
        list.append(str(binascii.unhexlify(hex),'utf-8'))
        list.append(item[2:])
    return "".join(list)    

def renderFile(socket, filePath):    
    if filePath.endswith(".p.html"):
        print("template file.")
        f = open(filePath, "r")
        try:
            for l in f:
                socket.write(l.format(**tplData))
        except Exception as e:
            print(e)
        finally:
            f.close()
    else:
        __sendPage(socket, filePath)

def onPath(path, handler):
    """Register handler for processing request of specified path
    """
    global handlers
    handlers[path] = handler
    
def onNotFound(handler):
    """Register handler for processing request of not found path
    """
    global notFoundHandler
    notFoundHandler = handler

def onPost(path, handler):
    """Register handler for processing POST request of specified path
    """
    global postHandlers
    postHandlers[path] = handler

def setDocPath(path):
    """Set the path to documents' directory
    """
    global docPath
    docPath = path

def setTplData(data):
    """Set data for template
    """
    global tplData
    tplData = data