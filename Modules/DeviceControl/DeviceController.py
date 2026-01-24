import asyncio
from kasa import Discover
from Core.utility import get_logger
from pylitterbot import Account
import json
import time
import hashlib
import hmac
import base64
import uuid
import requests
from roborock import HomeDataProduct, DeviceData, RoborockCommand
from roborock.version_1_apis import RoborockMqttClientV1, RoborockLocalClientV1
from roborock.web_api import RoborockApiClient

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
    credentials = {}

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
        creds = SwitchBotDevice.credentials
        # open token
        token = creds['Key'] # copy and paste from the SwitchBot app V6.14 or later
        # secret key
        secret = creds['Secret'] # copy and paste from the SwitchBot app V6.14 or later
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
        try:
            devices = await Discover.discover()
            for dev in devices.values():
                try:
                    await dev.update()
                    result[dev.alias] = KasaDevice(dev)
                except Exception as e:
                    get_logger(__name__).error(f"Error updating Kasa device {dev.alias}: {e}")
        except Exception as e:
            get_logger(__name__).error(f"Error discovering Kasa devices: {e}")
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

class RoborockDevice(Device):
    credentials = {}
    
    @staticmethod
    async def discorverDevices():
        results = {}
        try:
            web_api = RoborockApiClient(username=RoborockDevice.credentials["username"])
            user_data = await web_api.pass_login(password=RoborockDevice.credentials["password"])

            home_data = await web_api.get_home_data_v2(user_data)
            # Get product ids:
            product_info: dict[str, HomeDataProduct] = {
                    product.id: product for product in home_data.products
                }
            for device in home_data.devices:
                device_data = DeviceData(device, product_info[device.product_id].model)
                name = device_data.device.name
                results[name] = RoborockDevice(name)
        except Exception as e:
            get_logger(__name__).error(f"Error connecting to Roborock: {e}")
        return results
    
    def __init__(self, name):
        super().__init__(None)
        self.name = name
        self.status = "unknown"

    async def do_thing(self, what_thing):
        try:
            web_api = RoborockApiClient(username=RoborockDevice.credentials["username"])
            user_data = await web_api.pass_login(password=RoborockDevice.credentials["password"])

            home_data = await web_api.get_home_data_v2(user_data)
            # Get product ids:
            product_info: dict[str, HomeDataProduct] = {
                    product.id: product for product in home_data.products
                }
            for device in home_data.devices:
                device_data = DeviceData(device, product_info[device.product_id].model)
                name = device_data.device.name
                if name == self.name:
                    mqtt_client = RoborockMqttClientV1(user_data, device_data)
                    networking = await mqtt_client.get_networking()
                    local_device_data = DeviceData(device, product_info[device.product_id].model, networking.ip)
                    local_client = RoborockLocalClientV1(local_device_data)
                    
                    status = await local_client.get_status()
                    
                    if what_thing == "clean":
                        await local_client.send_command(RoborockCommand.APP_START)
                    elif what_thing == "stop":
                        await local_client.send_command(RoborockCommand.APP_PAUSE)
                    elif what_thing == "return":
                        await local_client.send_command(RoborockCommand.APP_CHARGE)
                    else:
                        pass
                    
                    time.sleep(5)
                    status = await local_client.get_status()
                    status = status.state
                    if status == 8 or status == 100 or status == 103 or status == 12 or status == 101 or status == 15 or status == 6:
                        self.status = "docked"
                    elif status == 5:
                        self.status = "cleaning"
                    elif status == 3 or status == 10:
                        self.status = "stopped"
                    else:
                        self.status = "unknown"
                    print(f"device status {status} and self {self.status}")
                    break
            return "Done"
        except Exception as e:
            get_logger(__name__).error(f"Failed to connect Roborock {e}")
            return "Done"
        finally:
            return "Done"
    
    def get_alias(self):
        return self.name
    
    def get_status(self):
        return self.status
    
    def get_desc(self):
        return "Status could be docked, cleaning, stopped or unknown. Changing the status to docked means returning it to dock."
    
    async def change_status(self, new_status):
        retry_limit = 3
        while retry_limit > 0:
            try:
                if new_status == "docked":
                    await self.do_thing("return")
                elif new_status == "cleaning":
                    await self.do_thing("clean")
                elif new_status == "stopped":
                    await self.do_thing("stop")
                else:
                    pass
                break
            except Exception as e:
                get_logger(__name__).error(f"Error controlling Roborock device {self.get_alias()}: {e}")
                retry_limit -= 1

    async def update_status(self):
       #await self.do_thing("get_status")
       pass

class WhiskerDevice(Device):
    credentials = {}
    
    @staticmethod
    async def discorverDevices():
        result = {}
        try:
            account = Account()
            # Connect to the API and load robots.
            await account.connect(username=WhiskerDevice.credentials['username'], password=WhiskerDevice.credentials['password'], load_robots=True)

            # Print robots associated with account.
            for robot in account.robots:
                result[robot.name] = WhiskerDevice(robot)
        except Exception as e:
            get_logger(__name__).error(f"Failed to connect Whisker {e}")
        finally:
            await account.disconnect()
        return result
    
    def __init__(self, actual_device):
        super().__init__(actual_device)
        self.name = actual_device.name
        self.status_ = "unknown"

    async def do_thing(self, what_thing):
        account = None
        try:
            account = Account()
            # Connect to the API and load robots.
            await account.connect(username=WhiskerDevice.credentials['username'], password=WhiskerDevice.credentials['password'], load_robots=True)

            # Print robots associated with account.
            for robot in account.robots:
                if robot.name == self.name:
                    if what_thing == "get_status":
                        status = robot.status
                        if status.value == "RDY":
                            return "on"
                        elif status.value == "OFF":
                            return "off"
                        elif status.value == "CCP":
                            return "cleaning"
                        else:
                            return "unknown"
                    elif what_thing == "turn_on":
                        await robot.set_power_status(True)
                    elif what_thing == "turn_off":
                        await robot.set_power_status(False)
                    elif what_thing == "clean":
                        await robot.start_cleaning()
                    else:
                        pass
                    break
            return "Done"
        except Exception as e:
            get_logger(__name__).error(f"Failed to connect Whisker {e}")
            return "unknown" if what_thing == "get_status" else "Done"
        finally:
            if account:
                try:
                    await account.disconnect()
                except:
                    pass
    
    def get_alias(self):
        return self.name
    
    def get_status(self):
        return self.status_
    
    def get_desc(self):
        return "Status could be on, off, cleaning or unknown."
    
    async def change_status(self, new_status):
        retry_limit = 3
        while retry_limit > 0:
            try:
                if new_status == "on":
                    await self.do_thing("turn_on")
                elif new_status == "off":
                    await self.do_thing("turn_off")
                elif new_status == "cleaning":
                    await self.do_thing("clean")
                else:
                    pass
                break
            except Exception as e:
                get_logger(__name__).error(f"Error controlling Whisker device {self.get_alias()}: {e}")
                retry_limit -= 1

    async def update_status(self):
        self.status_ = await self.do_thing("get_status")

class DeviceController:

    def __init__(self, switch_bot_creds, whisker_creds, roborock_creds):
        self.logger = get_logger(__name__)
        self.m_devices = {}
        SwitchBotDevice.credentials = switch_bot_creds
        WhiskerDevice.credentials = whisker_creds
        RoborockDevice.credentials = roborock_creds

    def updateDevices(self):
        self.m_devices = {}
        try:
            self.m_devices.update(asyncio.run(KasaDevice.discorverDevices()))
        except Exception as e:
            self.logger.error(f"Error updating Kasa devices: {e}")
        try:
            self.m_devices.update(asyncio.run(SwitchBotDevice.discorverDevices()))
        except Exception as e:
            self.logger.error(f"Error updating SwitchBot devices: {e}")
        try:
            self.m_devices.update(asyncio.run(WhiskerDevice.discorverDevices()))
        except Exception as e:
            self.logger.error(f"Error updating Whisker devices: {e}")
        #self.m_devices.update(asyncio.run(RoborockDevice.discorverDevices()))

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
                    print(f"Try Change {alias} to {statuses[index]}")
                    asyncio.run(self.m_devices[alias].update_status())
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
        text = text.replace(" ", "")
        aliases = []
        statuses = []
        message = "好，"
        filtered_len = 0
        for device_info in self.getDevicesInfo():
            filter_texts = []
            filter_texts.append(f"打开{device_info['alias']}")
            filter_texts.append(f"关闭{device_info['alias']}")
            filter_texts.append(f"关上{device_info['alias']}")
            filter_texts.append(f"清洁{device_info['alias']}")

            for filter_text in filter_texts:
                if filter_text in text:
                    filtered_len += len(filter_text)
                    self.logger.info(f"Local filter matched: {filter_text}")
                    aliases.append(device_info['alias'])
                    statuses.append("on" if "打开" in filter_text else ("cleaning" if "清洁" in filter_text else "off"))
                    message += f"{'打开' if '打开' in filter_text else ('清洁' if '清洁' in filter_text else '关闭')} {device_info['alias']}，"
        
        if len(text) - filtered_len >= 3:
            return False, {}

        if len(aliases) > 0:
            return True, {
                        "action": "ControlDevice",
                        "action_params": {
                            "alias": aliases,
                            "status": statuses
                        },
                        "message": message
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
