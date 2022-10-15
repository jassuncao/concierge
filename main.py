import ESP8266WebServer
import network
import machine
import os
from machine import Pin
from machine import Timer

# Wi-Fi configuration
AP_SSID = "ESP_8266"
AP_PSK = "1234567890"

GPIO_NUM = 2 # Builtin led (D4)
GPIO_BUTTON = 4
GPIO_RELAY = 5

oneshotTimer = Timer(-1)
relay = Pin(GPIO_RELAY, Pin.OUT)   
led = Pin(GPIO_NUM, Pin.OUT) 

webData = {
    "ssid": "",
    "psk": "",
    "timeOn": 500
}

def doStation(essid, password):
    # Disable AP interface
    ap_if = network.WLAN(network.AP_IF)
    if ap_if.active():
        ap_if.active(False)
    
    # Connect to Wi-Fi if not connected
    print("connecting "+essid+" psk="+password)
    sta_if = network.WLAN(network.STA_IF)
    if not ap_if.active():
        sta_if.active(True)
    if not sta_if.isconnected():
        sta_if.connect(essid, password)
        # Wait for connecting to Wi-Fi
        while not sta_if.isconnected(): 
            pass
    # Show IP address
    print("Server started @", sta_if.ifconfig())


def doAP():
    # Disable station interface
    sta_if = network.WLAN(network.STA_IF)
    if sta_if.active():
        sta_if.active(False)

    ap_if = network.WLAN(network.AP_IF)
    ap_if.active(True)
    ap_if.config(essid=AP_SSID, password=AP_PSK)
    while ap_if.active() == False:
        pass
    # Show IP address
    print("Server started @", ap_if.ifconfig())

def saveCfg():
    f = open("config.cfg", "w")
    try:
        f.write("ssid={}\n".format(webData["ssid"]))
        f.write("psk={}\n".format(webData["psk"]))
        f.write("timeOn={}\n".format(webData["timeOn"]))
    finally:
        f.close()

def loadCfg():
    f = open("config.cfg", "r")
    try:
        for line in f:                  
            pair = line.rstrip("\n").split("=",1)
            if len(pair) > 0:
                webData[pair[0]] = pair[1]
    finally:
        f.close() 

def relayOn():
    led.off()
    relay.on()

def relayOff():
    led.on()
    relay.off()        

def pulseEnd(timer):
    relayOff()
    timer.deinit()

def pulseStart(timer=None):
    relayOn()
    timeOn = int(webData["timeOn"])
    oneshotTimer.init(period=timeOn, mode=Timer.ONE_SHOT, callback=pulseEnd)

def main():
    button = machine.Pin(GPIO_BUTTON, Pin.IN, Pin.PULL_UP)
    
    #The button is inverted 
    if(button.value()):
        if ESP8266WebServer.__fileExist("config.cfg"):
            loadCfg()
        doStation(webData["ssid"], webData["psk"])
    else:
        doAP()

    led.on() # Turn LED off (it uses sinking input)

    def handlePulse(socket, args):
        if 'delay' in args:
            delay  = int(args["delay"]) * 1000
            oneshotTimer.init(period=delay, mode=Timer.ONE_SHOT, callback=pulseStart)
        else:
            pulseStart()  
        ESP8266WebServer.okData(socket, "200", "text/plain", "OK")            

    def handleSettings(socket, args):        
        ESP8266WebServer.ok(socket, "200", "text/html", "settings.p.html")        

    def handleSettingsPost(socket, args):
        resetNext = False
        if webData["ssid"] != args["ssid"] or webData["psk"] != args["psk"]:
            webData["ssid"]=args["ssid"]
            webData["psk"]=args["psk"] 
            resetNext = True
        webData["timeOn"]=int(args["timeOn"])  
        saveCfg()      
        ESP8266WebServer.ok(socket, "200", "text/html", "settings.p.html")
        if resetNext :
            machine.reset()

    
    ESP8266WebServer.begin(80)
    ESP8266WebServer.onPath("/settings", handleSettings)
    ESP8266WebServer.onPath("/pulse", handlePulse)
    ESP8266WebServer.onPost("/settings", handleSettingsPost)
    ESP8266WebServer.setDocPath("/")
    ESP8266WebServer.setTplData(webData)

    try:
        while True:
            ESP8266WebServer.handleClient()
    except Exception as ex:
        print(ex)
        ESP8266WebServer.close()


if __name__ == "__main__":
    main()