from AiContactor import AiContactor

import json

contactor = AiContactor(mode="DEEPSEEK")
contactor.generate_system_message("")
response = contactor.communicate("eighty six tell me a joke")
print(response)