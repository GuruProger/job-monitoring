import json
from typing import Dict

import requests


class Exchanger:
	__EXCHANGE_URL = "https://api.exchangerate-api.com/v4/latest/RUB"
	
	def update_exchange_rates(self, rates: Dict):
		"""Parse exchange rates for RUB, USD, EUR and save them to `rates`

		Parameters
		----------
		rates : dict
			Dict of currencies. For example: {"RUB": 1, "USD": 0.001}
		"""
		try:
			response = requests.get(self.__EXCHANGE_URL)
			new_rates = response.json()["rates"]
		except requests.exceptions.SSLError:
			raise AssertionError("[FAIL] Cannot get exchange rate! Try later or change the host API")

		for curr in rates:
			rates[curr] = new_rates[curr]
		
		# Change 'RUB' to 'RUR'
		rates["RUR"] = rates.pop("RUB")
