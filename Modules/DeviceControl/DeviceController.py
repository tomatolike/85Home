import asyncio
from kasa import Discover
from Core.utility import get_logger
import json

class DeviceController:

    def __init__(self):
        self.logger = get_logger(__name__)
        self.m_devices = {}

    async def asyncFindDevices(self):
        result = {}
        devices = await Discover.discover()
        for dev in devices.values():
            await dev.update()
            result[dev.alias] = dev

        return result

    def updateDevices(self):
        self.m_devices = asyncio.run(self.asyncFindDevices())

    def getDevicesInfo(self):
        result = []
        for dev in self.m_devices:
            result.append({
                "alias": self.m_devices[dev].alias,
                "host": self.m_devices[dev].host,
                "status": "On" if self.m_devices[dev].is_on else "Off"
            })
        return result

    async def asyncTurnOnDevice(self, alias, on):
        if alias in self.m_devices:
            try:
                if on:
                    await self.m_devices[alias].turn_on()
                else:
                    await self.m_devices[alias].turn_off()
                await self.m_devices[alias].update()
                if self.m_devices[alias].is_on != on:
                    self.logger.warning(f"Device {alias} state not changed as expected, retrying...")
                    # try again
                    if on:
                        await self.m_devices[alias].turn_on()
                    else:
                        await self.m_devices[alias].turn_off()
                    await self.m_devices[alias].update()
            except Exception as e:
                self.logger.error(f"Error controlling device {alias}: {e}")
                

    def turnOnDevice(self, aliases, ons):
        index = 0
        for alias in aliases:
            asyncio.run(self.asyncTurnOnDevice(alias, ons[index]))
            index += 1

    def getActionInfo(self):
        action_list_info = (
        "\n\n"
        "Action: ControlDevice\n"
        "description: there are kasa smart devices in the home, you can turn them on or off\n"
        "parameters:\n"
        "- alias: a list of the aliases of the devices\n"
        "- on: a list of true or false, whether to turn on the device\n"
        "The list of available devices:\n"
        + json.dumps(self.getDevicesInfo(), indent=2)
        + "\n\n"
    )
        return action_list_info