import asyncio
from kasa import Discover
from Core.utility import get_logger
import json
import time
import hashlib
import hmac
import base64
import uuid
import requests

class Device:
    def __init__(self, actual_device):
        self.actual_device = actual_device

    @staticmethod
    async def discorverDevices():
        return {}
    
    def get_alias(self):
        return "UNKNOWN"
    
    def get_status(self):
        return "UNKNOWN"
    
    def get_desc(self):
        return "UNKNOWN"
    
    async def change_status(self, new_status):
        pass

    async def update_status(self):
        pass

class SwitchBotDevice(Device):
    # Declare empty header dictionary
    apiHeader = {}

    def __init__(self, actual_device):
        super().__init__(actual_device)
        self.status = "UNKNOWN"

    @staticmethod
    async def discorverDevices():
        SwitchBotDevice.authenticate()
        result = {}
        url = "https://api.switch-bot.com/v1.1/devices"
        response = requests.get(url, headers=SwitchBotDevice.apiHeader)
        allow_device_types = ['Smart Lock']
        if response.status_code == 200:
            data = response.json()
            devices = data['body']['deviceList']
            for dev in devices:
                if dev['deviceType'] in allow_device_types:
                    result[dev['deviceName']] = SwitchBotDevice(dev)
                    await result[dev['deviceName']].update_status()
        else:
            get_logger(__name__).error(f"Error discover SW devices {response.status_code}: {response.text}")
        return result
    
    def get_alias(self):
        return self.actual_device['deviceName']
    
    def get_status(self):
        return self.status
    
    def get_desc(self):
        if self.actual_device['deviceType'] == 'Smart Lock':
            return "Status can be locked or unlocked"
        return "UNKNOWN"
    
    async def change_status(self, new_status):
        url = f"https://api.switch-bot.com/v1.1/devices/{self.actual_device['deviceId']}/commands"
        payload = {}
        if self.actual_device['deviceType'] == 'Smart Lock':
            if new_status == "locked":
                payload['command'] = "lock"
            elif new_status == "unlocked":
                payload['command'] = "unlock"
        
        response = requests.post(url, headers=SwitchBotDevice.apiHeader, json=payload)
        if response.status_code == 200:
            pass
        else:
            get_logger(__name__).error(f"Error Set SW device status {response.status_code}: {response.text}")

        # wait for execution
        if self.actual_device['deviceType'] == 'Smart Lock':
            time.sleep(10)

    async def update_status(self):
        url = f"https://api.switch-bot.com/v1.1/devices/{self.actual_device['deviceId']}/status"
        response = requests.get(url, headers=SwitchBotDevice.apiHeader)
        if response.status_code == 200:
            data = response.json()
            if self.actual_device['deviceType'] == 'Smart Lock':
                self.status = data['body']['lockState']
            else:
                self.status = "UNKNOWN"
        else:
            get_logger(__name__).error(f"Error Get SW device status {response.status_code}: {response.text}")

    @staticmethod
    def authenticate():
        f = open("credentials")
        creds = json.load(f)
        f.close()
        # open token
        token = creds['SwitchBot']['Key'] # copy and paste from the SwitchBot app V6.14 or later
        # secret key
        secret = creds['SwitchBot']['Secret'] # copy and paste from the SwitchBot app V6.14 or later
        nonce = uuid.uuid4()
        t = int(round(time.time() * 1000))
        string_to_sign = '{}{}{}'.format(token, t, nonce)

        string_to_sign = bytes(string_to_sign, 'utf-8')
        secret = bytes(secret, 'utf-8')

        sign = base64.b64encode(hmac.new(secret, msg=string_to_sign, digestmod=hashlib.sha256).digest())

        #Build api header JSON
        SwitchBotDevice.apiHeader['Authorization']=token
        SwitchBotDevice.apiHeader['Content-Type']='application/json'
        SwitchBotDevice.apiHeader['charset']='utf8'
        SwitchBotDevice.apiHeader['t']=str(t)
        SwitchBotDevice.apiHeader['sign']=str(sign, 'utf-8')
        SwitchBotDevice.apiHeader['nonce']=str(nonce)


class KasaDevice(Device):
    @staticmethod
    async def discorverDevices():
        result = {}
        devices = await Discover.discover()
        for dev in devices.values():
            await dev.update()
            result[dev.alias] = KasaDevice(dev)
        return result
    
    def get_alias(self):
        return self.actual_device.alias
    
    def get_status(self):
        return "ON" if self.actual_device.is_on else "OFF"
    
    def get_desc(self):
        return "Status could be ON or OFF"
    
    async def change_status(self, new_status):
        if new_status == "ON":
            await self.actual_device.turn_on()
        else:
            await self.actual_device.turn_off()

    async def update_status(self):
        await self.actual_device.update()

class DeviceController:

    def __init__(self):
        self.logger = get_logger(__name__)
        self.m_devices = {}

    def updateDevices(self):
        self.m_devices.update(asyncio.run(KasaDevice.discorverDevices()))
        self.m_devices.update(asyncio.run(SwitchBotDevice.discorverDevices()))

    def getDevicesInfo(self):
        result = []
        for name in self.m_devices:
            result.append({
                "alias": self.m_devices[name].get_alias(),
                "status": self.m_devices[name].get_status(),
                "description": self.m_devices[name].get_desc()
            })
        return result

    def changeDeviceStatus(self, aliases, statuses):
        index = 0
        for alias in aliases:
            retry_time = 5
            while retry_time > 0:
                try:
                    asyncio.run(self.m_devices[alias].update_status())
                    if self.m_devices[alias].get_status() == statuses[index]:
                        break
                    asyncio.run(self.m_devices[alias].change_status(statuses[index]))
                    asyncio.run(self.m_devices[alias].update_status())
                    if self.m_devices[alias].get_status() == statuses[index]:
                        break
                    retry_time -= 1
                    if retry_time == 0:
                        self.logger.error(f"Failed to chagne {alias} to {statuses[index]}")
                except Exception as e:
                    self.logger.error(f"Error controlling device {alias}: {e}")
                    break
            index += 1

    def getActionInfo(self):
        action_list_info = (
        "\n\n"
        "Action: ControlDevice\n"
        "description: there are kasa smart devices in the home, you can turn them on or off\n"
        "parameters:\n"
        "- alias: a list of the aliases of the devices\n"
        "- status: a list of target status that you want to change the device to\n"
        "The list of available devices:\n"
        + json.dumps(self.getDevicesInfo(), indent=2)
        + "\n\n"
    )
        return action_list_info