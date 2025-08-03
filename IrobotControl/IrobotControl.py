import serial
import time
import json
import logging
import RPi.GPIO as GPIO

logger = logging.getLogger("Irobot")

class Irobot:
    ModeCodeMap = {
        'Passive': 128,
        'Safe': 131,
        'Full': 132
    }

    SensorDataMap = {
        'ChargingState':{
            'ID':21,
            'Len':1
        },
        'BatteryCharge':{
            'ID':25,
            'Len':2
        },
        'BatteryCapacity':{
            'ID':26,
            'Len':2
        },
        'ChargingSource':{
            'ID':34,
            'Len':1
        },
        'IOState':{
            'ID':35,
            'Len':1
        },
        'Voltage':{
            'ID':22,
            'Len':2
        },
        'Current':{
            'ID':23,
            'Len':2
        },
        'Temp':{
            'ID':24,
            'Len':1
        }
    }

    def __init__(self):
        self.m_port = serial.Serial(port='/dev/ttyS0', baudrate=57600, timeout=0.5)
        self.m_moveStatus = 'Stop'
        self.m_command = 'Stop'
        self.IOMode = 'Passive'
        self.m_lastMoveCommandTimestamp = time.time()
        self.m_lightOn = False
        self.m_constMode = False
        self.m_constStage = 'Idle'
        self.m_constTimestamp = 0
        self.m_senseData = {}
        self.SenseData()
        self.m_lowPowerWarning = 1000
        
        self.m_config = self.ReadConfig()
        self.m_lastLogTimer = 0

        self.m_moveCommands = []
        self.m_carCommands = []

        self.m_sleepMode = False

    def ReadConfig(self):
        try:
            with open('/media/lovetomatoboy/RASP1/config.json') as f:
                return json.load(f)
        except:
            pass
        return {
            'constLowBar': 2000,
            'constHighBar': 2700
        }

    def WriteConfig(self):
        try:
            with open('/media/lovetomatoboy/RASP1/config.json','w+') as f:
                json.dump(self.m_config, f, indent = 6)
        except:
            pass

    def EnterMode(self, modeStr):
        if modeStr in Irobot.ModeCodeMap:
            self.m_port.write([Irobot.ModeCodeMap[modeStr]])
            self.IOMode = modeStr

    def Dock(self):
        self.IOMode = 'Passive'
        self.m_port.write([136, 1])

    def TwitchConstMode(self):
        logger.debug(f"TwitchConstMode {self.m_constMode}")
        if self.m_constMode:
            logger.debug("LeaveConstMode")
            self.m_constMode = False
        else:
            logger.debug("EnterConstMode")
            self.m_constMode = True

    def MoveForward(self, speed = 150):
        self.m_port.write([145, 0, speed, 0, speed])

    def MoveBackward(self, speed = 150):
        self.m_port.write([145, 255, 256 - speed, 255, 256 - speed])

    def MoveLeft(self, speed = 75):
        self.m_port.write([145, 0, speed, 255, 256 - speed])

    def MoveRight(self, speed = 75):
        self.m_port.write([145, 255, 256 - speed, 0, speed])

    def ScriptMoveBack(self, distanceMM = 10):
        distanceMM = 65536 - distanceMM
        highBit = distanceMM // 256
        lowBit = distanceMM % 256
        print(highBit, lowBit)
        self.m_port.write([152, 14, 145, 255, 156, 255, 156, 156, highBit, lowBit, 145, 0, 0, 0, 0, 128])

    def ScriptMoveForward(self, distanceMM = 10):
        highBit = distanceMM // 256
        lowBit = distanceMM % 256
        self.m_port.write([152, 5, 145, 0, 156, 0, 156])

    def ShowScript(self):
        self.m_port.write([154])
        size = self.m_port.read(1)
        sizeInt = int.from_bytes(size)
        dataB = self.m_port.read(sizeInt)
        for d in dataB:
            print(int.from_bytes([d]))
    
    def RunScript(self):
        self.m_port.write([153])

    def TwichLight(self):
        if not self.m_lightOn:
            self.m_lightOn = True
            self.m_port.write([147, 4])
            logger.debug("Turned on")
        else:
            self.m_lightOn = False
            self.m_port.write([147, 0])
            logger.debug("Turned off")

    def Sense(self, name):
        if name not in Irobot.SensorDataMap:
            return 0

        self.m_port.write([142, Irobot.SensorDataMap[name]['ID']])
        try:
            _bytes = self.m_port.read(Irobot.SensorDataMap[name]['Len'])
            return int.from_bytes(_bytes)
        except:
            return 0

    def DataConversion(self, key, data):
        try:
            if key == 'ChargingState':
                chargingStateMap = ['Not charging', 'Reconditioning Charging', 'Full Charging', 'Trickle Charging', 'Waiting', 'Charging Fault Condition']
                return chargingStateMap[data]
            elif key == 'ChargingSource':
                chargingSourceMap = ['NULL', 'Internal Charger', 'Home Base']
                return chargingSourceMap[data]
            elif key == 'BatteryCharge':
                if data > 32767:
                    return data - 65536
                else:
                    return data
            elif key == 'Current':
                if data > 32767:
                    return data - 65536
                else:
                    return data
            elif key == 'Temp':
                if data > 127:
                    return data - 256
                else:
                    return data
            elif key == 'IOState':
                ioStateMap = ['Off','Passive','Safe','Full']
                return ioStateMap[data]
            else:
                return data
        except:
            return data

    def SenseData(self):
        requestKeys = ['ChargingState','BatteryCharge','BatteryCapacity', 'ChargingSource', 'IOState', 'Voltage', 'Current', 'Temp']
        for key in requestKeys:
            self.m_senseData[key] = self.DataConversion(key, self.Sense(key))

    def GetKeyValueStatus(self):
        results = []
        for key in self.m_senseData:
            results.append({'key':key, 'value':self.m_senseData[key]})

        results.append({'key':'MoveStatus','value':self.m_moveStatus})
        results.append({'key':'LightOn', 'value':self.m_lightOn})
        results.append({'key':'ConstMode', 'value':self.m_constMode})
        results.append({'key':'ConstStage', 'value':self.m_constStage})
        results.append({'key':'ConstLow', 'value':self.m_config['constLowBar']})
        results.append({'key':'ConstHigh', 'value':self.m_config['constHighBar']})
        results.append({'key':'SleepMode', 'value':self.m_sleepMode})
        return results

    def PushMoveCommand(self, command):
        self.m_moveCommands.append(command)

    def PushCarCommand(self, command):
        self.m_carCommands.append(command)

    def SetMoveCommand(self, command):
        #logger.debug("SetMoveCommand", command)
        self.m_command = command
        self.m_lastMoveCommandTimestamp = time.time()

        if self.IOMode == 'Safe' or self.IOMode == 'Full':
            if self.m_moveStatus != self.m_command:
                if self.m_command == 'Forward':
                    self.MoveForward()
                elif self.m_command == 'Back':
                    self.MoveBackward()
                elif self.m_command == 'Left':
                    self.MoveLeft()
                elif self.m_command == 'Right':
                    self.MoveRight()
                elif self.m_command == 'Stop':
                    self.MoveForward(0)
                else:
                    pass
                self.m_moveStatus = self.m_command

    def TogglePower(self):
        TOGGLE_PIN = 17  # BCM numbering (GPIO17)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(TOGGLE_PIN, GPIO.OUT)

        # Start LOW
        GPIO.output(TOGGLE_PIN, GPIO.LOW)
        time.sleep(0.1)

        # Then HIGH to trigger power toggle
        GPIO.output(TOGGLE_PIN, GPIO.HIGH)
        time.sleep(0.5)

        # Optionally set LOW again
        GPIO.output(TOGGLE_PIN, GPIO.LOW)

        # Cleanup
        GPIO.cleanup(TOGGLE_PIN)
        pass

    def SetCarCommand(self, command):
        #logger.debug("SetCarCommand", command)
        if command == 'enterPassiveMode':
            self.EnterMode('Passive')
        elif command == 'enterSafeMode':
            self.EnterMode('Safe')
        elif command == 'enterFullMode':
            self.EnterMode('Full')
        elif command == 'dock':
            self.Dock()
        elif command == 'light':
            self.TwichLight()
        elif command == 'constMode':
            self.TwitchConstMode()
        elif command == 'togglePower':
            self.TogglePower()
        elif command == 'increlowbar':
            self.m_config['constLowBar'] += 100
            self.WriteConfig()
        elif command == 'decrelowbar':
            self.m_config['constLowBar'] -= 100
            self.WriteConfig()
        elif command == 'increhighbar':
            self.m_config['constHighBar'] += 100
            self.WriteConfig()
        elif command == 'decrehighbar':
            self.m_config['constHighBar'] -= 100
            self.WriteConfig()
        elif command == 'sleepMode':
            if self.m_sleepMode:
                self.m_sleepMode = False
            else:
                self.m_sleepMode = True

    def UpdateMoveStatus(self):
        self.SenseData()
        if self.m_lastLogTimer < time.time():
            self.m_lastLogTimer = time.time() + 30
            logger.debug(self.m_senseData)
        emailNotify = False
        emailNotifyReason = ""

        # Process commands
        while len(self.m_moveCommands) > 0:
            command = self.m_moveCommands[0]
            self.SetMoveCommand(command)
            self.m_moveCommands.pop(0)

        while len(self.m_carCommands) > 0:
            command = self.m_carCommands[0]
            self.SetCarCommand(command)
            self.m_carCommands.pop(0)

        if self.m_constMode:
            if self.m_constStage == 'Idle' or self.m_constStage == 'Charging':
                batteryLevel = self.m_senseData['BatteryCharge']
                chargingState = self.m_senseData['ChargingState']
                notCharging = chargingState == 'Not charging'
                #logger.debug(batteryLevel, chargingState, notCharging)
                if notCharging:
                    self.m_constStage = 'Idle'
                else:
                    self.m_constStage = 'Charging'
                if ((not self.m_sleepMode and batteryLevel < self.m_config['constLowBar']) or (self.m_sleepMode and batteryLevel < 2000)) and notCharging:
                    logger.debug("Battery low docking")
                    emailNotify = True
                    emailNotifyReason = "Battery low docking"
                    self.m_constStage = 'Docking'
                    
                elif (batteryLevel > self.m_config['constHighBar'] or chargingState == "Trickle Charging" or chargingState == "Waiting") and not notCharging:
                    logger.debug("Full charged move back")
                    emailNotify = True
                    emailNotifyReason = "Full charged move back"
                    self.m_config['constLowBar'] = batteryLevel - 100
                    self.m_constStage = 'Backing'

            elif self.m_constStage == 'Docking':
                chargingState = self.m_senseData['ChargingState']
                notCharging = chargingState == 'Not charging'
                if not notCharging:
                    emailNotify = True
                    emailNotifyReason = "Docked"
                    self.m_constStage = 'Idle'
                else:
                    pass
            elif self.m_constStage == 'Backing':
                chargingState = self.m_senseData['ChargingState']
                notCharging = chargingState == 'Not charging'
                if notCharging:
                    self.m_constStage = 'Idle'
                else:
                    pass

        else:
            # now = time.time()
            # if now - self.m_lastMoveCommandTimestamp > 60 and self.IOMode != 'Passive' and self.m_moveStatus != 'Stop':
            #     self.SetMoveCommand('Stop')
            #     emailNotify = True
            #     emailNotifyReason = "Longtime running, stopped"
            pass

        # Battery control
        if self.m_senseData['BatteryCharge'] < self.m_lowPowerWarning:
            self.m_lowPowerWarning -= 500
            if not emailNotify:
                emailNotify = True
                emailNotifyReason = "Battery Low!"
        elif self.m_senseData['BatteryCharge'] > self.m_lowPowerWarning:
            nextLevel = self.m_lowPowerWarning + 500
            if nextLevel <= 1000 and nextLevel < self.m_senseData['BatteryCharge']:
                self.m_lowPowerWarning = nextLevel
        
        return emailNotify, emailNotifyReason