import argparse
import json
from typing import Dict, Optional, Sequence


class Settings:
	r"""Researcher parameters

	Parameters
	----------
	config_path : str
		Path to config file
	input_args : tuple
		Command line arguments for tests.
	no_parse : bool
		Disable parsing arguments from command line.

	Attributes
	----------
	options : dict
		Options for GET request to API.
	refresh : bool
		Refresh data from remote server.
	save_result : bool
		Save DataFrame with parsed vacancies to CSV file
	num_workers : int
		Number of workers for threading.
	rates : dict
		Dict of currencies. For example: {"RUB": 1, "USD": 0.001}
	"""
	
	def __init__(
			self, options: Dict, refresh: bool, num_workers: int, save_result: bool, rates: Dict
	):
		self.options = options
		self.refresh = refresh
		self.num_workers = num_workers
		self.save_result = save_result
		self.rates = rates

	
	def update_params(self, **kwargs):
		"""Update object params"""
		for key, value in kwargs.items():
			if hasattr(self, key) and value is not None:
				setattr(self, key, value)
	
	def __repr__(self):
		txt = "\n".join([f"{k :<16}: {v}" for k, v in self.__dict__.items()])
		return f"Settings:\n{txt}"
	
	@staticmethod
	def __parse_args(inputs_args) -> Dict:
		"""Read arguments from command line.

		Returns
		-------
		arguments : dict
			Parsed arguments from command line. Note: some arguments are positional.

		"""
		
		parser = argparse.ArgumentParser(description="HeadHunter vacancies researcher")
		parser.add_argument(
			"-t", "--text", action="store", type=str, default=None, help='Search query text (e.g. "Machine learning")',
		)
		parser.add_argument(
			"-p", "--professional_roles", action="store", type=int, default=None,
			help='Professional role filter (Possible roles can be found here https://api.hh.ru/professional_roles)',
			nargs='*'
		)
		parser.add_argument(
			"-n", "--num_workers", action="store", type=int, default=None, help="Number of workers for multithreading.",
		)
		parser.add_argument(
			"-r", "--refresh", help="Refresh cached data from HH API", action="store_true", default=None,
		)
		parser.add_argument(
			"-s", "--save_result", help="Save parsed result as DataFrame to CSV file.", action="store_true",
			default=None,
		)
		parser.add_argument(
			"-u", "--update", action="store_true", default=None, help="Save command line args to file in JSON format.",
		)
		parser.add_argument(
			"--salary_from", type=int, default=None, help="Минимальная зарплата (фильтр)"
		)
		parser.add_argument(
			"--salary_to", type=int, default=None, help="Максимальная зарплата (фильтр)"
		)
		parser.add_argument(
			"--experience", type=str, default=None, help="Опыт работы (фильтр, например: 'Нет опыта', '1–3 года')"
		)
		parser.add_argument(
			"--key_skills", nargs='*', type=str, default=None, help="Ключевые навыки (фильтр, через пробел)"
		)
		parser.add_argument(
			"--limit", type=int, default=None, help="Лимит количества вакансий"
		)
		
		params, unknown = parser.parse_known_args(inputs_args)
		# Update config from command line
		return vars(params)


if __name__ == "__main__":
	settings = Settings(
		config_path="../settings.json", input_args=("--num_workers", "5", "--refresh", "--text", "Data Scientist"),
	)
	
	print(settings)
