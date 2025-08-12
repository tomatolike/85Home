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
        allow_device_types = ['Bot']
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
        elif self.actual_device['deviceType'] == 'Bot':
            return "Status can be off or on"
        return "UNKNOWN"
    
    async def change_status(self, new_status):
        url = f"https://api.switch-bot.com/v1.1/devices/{self.actual_device['deviceId']}/commands"
        payload = {}
        if self.actual_device['deviceType'] == 'Bot':
            if new_status == "on":
                payload['command'] = "turnOn"
            elif new_status == "off":
                payload['command'] = "turnOff"
        else:
            return
        
        response = requests.post(url, headers=SwitchBotDevice.apiHeader, json=payload)
        if response.status_code == 200:
            pass
        else:
            get_logger(__name__).error(f"Error Set SW device status {response.status_code}: {response.text}")

        # wait for execution
        if self.actual_device['deviceType'] == 'Smart Lock':
            time.sleep(10)
        elif self.actual_device['deviceType'] == 'Bot':
            time.sleep(40)

    async def update_status(self):
        url = f"https://api.switch-bot.com/v1.1/devices/{self.actual_device['deviceId']}/status"
        response = requests.get(url, headers=SwitchBotDevice.apiHeader)
        if response.status_code == 200:
            data = response.json()
            if self.actual_device['deviceType'] == 'Smart Lock':
                self.status = data['body']['lockState']
            elif self.actual_device['deviceType'] == 'Bot':
                self.status = data['body']['power']
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
        return "on" if self.actual_device.is_on else "off"
    
    def get_desc(self):
        return "Status could be on or off"
    
    async def change_status(self, new_status):
        retry_limit = 3
        while retry_limit > 0:
            try:
                if new_status == "on":
                    await self.actual_device.turn_on()
                else:
                    await self.actual_device.turn_off()
                break
            except Exception as e:
                get_logger(__name__).error(f"Error controlling Kasa device {self.get_alias()}: {e}")
                retry_limit -= 1

    async def update_status(self):
        retry_limit = 3
        while retry_limit > 0:
            try:
                await self.actual_device.update()
                break
            except Exception as e:
                get_logger(__name__).error(f"Error updating Kasa device {self.get_alias()}: {e}")
                retry_limit -= 1

class DeviceController:

    def __init__(self):
        self.logger = get_logger(__name__)
        self.m_devices = {}

    def updateDevices(self):
        self.m_devices = {}
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

    def local_filter(self, text):
        filter_texts = []
        for device_info in self.getDevicesInfo():
            filter_texts.append(f"打开{device_info['alias']}")
            filter_texts.append(f"关闭{device_info['alias']}")
        
        for filter_text in filter_texts:
            if filter_text in text:
                self.logger.info(f"Local filter matched: {filter_text}")
                return True, {
                    "action": "ControlDevice",
                    "action_params": {
                        "alias": [device_info['alias']],
                        "status": ["on" if "打开" in filter_text else "off"]
                    },
                    "message": f"好，{'打开' if '打开' in filter_text else '关闭'} {device_info['alias']}"
                }
        return False, {}

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