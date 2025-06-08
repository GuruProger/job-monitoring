import hashlib
import os
import pickle
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Optional
from urllib.parse import urlencode

import requests
from tqdm import tqdm


def parse_superjob(text: str) -> Dict[str, str]:
	url = "https://api.superjob.ru/2.0/vacancies/"
	params = {
		"page": 0,
		"count": 3,
		"keyword": text,
		"sort_new": 1,
	}
	headers = {
		"X-Api-App-Id": "v3.h.4905791.f72938d0c57d8956a4524c02a06d50409fcb4198.0e4294e23cc795178fe05e210746a2aa21881acc"
	}
	
	response = requests.get(url, params=params, headers=headers)
	response_data = response.json()
	
	transformed_vacancies = [
		transform_superjob_to_hh(vacancy) for vacancy in response_data["objects"]
	]


CACHE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache")


def transform_superjob_to_hh(sj_vacancy):
	# Преобразование даты
	from datetime import datetime
	
	published_at = datetime.fromtimestamp(sj_vacancy.get("date_published", 0)).strftime(
		"%Y-%m-%dT%H:%M:%S+0300"
	)
	
	# Преобразование зарплаты
	salary_from = sj_vacancy.get("payment_from")
	salary_to = sj_vacancy.get("payment_to")
	salary = None
	salary_range = None
	
	if salary_from or salary_to:
		salary = {
			"from": salary_from if salary_from else None,
			"to": salary_to if salary_to else None,
			"currency": sj_vacancy.get("currency", "RUR").upper(),
			"gross": False,  # По умолчанию в SuperJob
		}
		
		salary_range = {
			"from": salary_from if salary_from else None,
			"to": salary_to if salary_to else None,
			"currency": sj_vacancy.get("currency", "RUR").upper(),
			"gross": True,
			"mode": {"id": "MONTH", "name": "За месяц"},
			"frequency": {"id": "MONTHLY", "name": "Раз в месяц"},
		}
	
	# Преобразование опыта работы
	experience_map = {
		1: {"id": "between1And3", "name": "От 1 года до 3 лет"},
		2: {"id": "between1And3", "name": "От 1 года до 3 лет"},
		3: {"id": "between3And6", "name": "От 3 до 6 лет"},
		4: {"id": "moreThan6", "name": "Более 6 лет"},
		5: {"id": "noExperience", "name": "Нет опыта"},
	}
	experience = experience_map.get(
		sj_vacancy.get("experience", {}).get("id", 0), {"id": None, "name": None}
	)
	
	# Преобразование графика работы
	schedule_map = {
		6: {"id": "fullDay", "name": "Полный день"},
		7: {"id": "shift", "name": "Сменный график"},
		8: {"id": "flexible", "name": "Гибкий график"},
		9: {"id": "remote", "name": "Удаленная работа"},
		10: {"id": "flyInFlyOut", "name": "Вахтовый метод"},
	}
	schedule = schedule_map.get(
		sj_vacancy.get("type_of_work", {}).get("id", 0), {"id": None, "name": None}
	)
	
	# Преобразование типа занятости
	employment_map = {
		0: {"id": "full", "name": "Полная занятость"},
		1: {"id": "part", "name": "Частичная занятость"},
		2: {"id": "project", "name": "Проектная работа"},
		3: {"id": "volunteer", "name": "Волонтерство"},
		4: {"id": "probation", "name": "Стажировка"},
	}
	employment = employment_map.get(
		sj_vacancy.get("place_of_work", {}).get("id", 0),
		{"id": "full", "name": "Полная занятость"},
	)
	
	# Преобразование работодателя
	employer = {
		"id": str(sj_vacancy.get("id_client", "")),
		"name": sj_vacancy.get("firm_name", ""),
		"url": f"https://api.hh.ru/employers/{sj_vacancy.get('id_client', '')}",
		"alternate_url": sj_vacancy.get("client", {}).get("link", ""),
		"logo_urls": (
			{
				"original": sj_vacancy.get("client_logo", ""),
				"90": sj_vacancy.get("client_logo", ""),
				"240": sj_vacancy.get("client_logo", ""),
			}
			if sj_vacancy.get("client_logo")
			else None
		),
		"vacancies_url": f"https://api.hh.ru/vacancies?employer_id={sj_vacancy.get('id_client', '')}",
		"accredited_it_employer": False,
		"trusted": True,
	}
	
	# Преобразование города
	area = {
		"id": str(sj_vacancy.get("town", {}).get("id", "")),
		"name": sj_vacancy.get("town", {}).get("title", ""),
		"url": f"https://api.hh.ru/areas/{sj_vacancy.get('town', {}).get('id', '')}",
	}
	
	# Создание итогового объекта вакансии
	transformed = {
		"id": str(sj_vacancy.get("id", "")),
		"premium": False,
		"billing_type": {"id": "standard", "name": "Стандарт"},
		"relations": [],
		"name": sj_vacancy.get("profession", ""),
		"insider_interview": None,
		"response_letter_required": False,
		"area": area,
		"salary": salary,
		"salary_range": salary_range,
		"type": {"id": "open", "name": "Открытая"},
		"address": (
			{"raw": sj_vacancy.get("address", "")}
			if sj_vacancy.get("address")
			else None
		),
		"allow_messages": True,
		"experience": experience,
		"schedule": schedule,
		"employment": employment,
		"department": None,
		"show_contacts": not sj_vacancy.get("contacts_hidden", True),
		"contacts": (
			{"phone": sj_vacancy.get("phone", ""), "email": None}
			if sj_vacancy.get("phone")
			else None
		),
		"description": sj_vacancy.get("vacancyRichText", ""),
		"branded_description": None,
		"vacancy_constructor_template": None,
		"key_skills": [],  # Нет информации о навыках в исходных данных
		"accept_handicapped": True,
		"accept_kids": False,
		"archived": sj_vacancy.get("is_archive", False),
		"response_url": None,
		"specializations": [],
		"professional_roles": (
			[{"id": "96", "name": "Программист, разработчик"}]
			if "python" in sj_vacancy.get("profession", "").lower()
			   or "разработ" in sj_vacancy.get("profession", "").lower()
			else []
		),
		"code": None,
		"hidden": False,
		"quick_responses_allowed": False,
		"driver_license_types": [],
		"accept_incomplete_resumes": False,
		"employer": employer,
		"published_at": published_at,
		"created_at": published_at,
		"initial_created_at": published_at,
		"negotiations_url": None,
		"suitable_resumes_url": None,
		"apply_alternate_url": sj_vacancy.get("link", ""),
		"has_test": False,
		"test": None,
		"alternate_url": sj_vacancy.get("link", ""),
		"working_days": [],
		"working_time_intervals": [],
		"working_time_modes": [],
		"accept_temporary": True,
		"languages": [],
		"approved": True,
		"employment_form": {"id": "FULL", "name": "Полная"},
		"fly_in_fly_out_duration": [],
		"internship": False,
		"night_shifts": False,
		"work_format": [
			{
				"id": (
					"REMOTE"
					if sj_vacancy.get("place_of_work", {}).get("id") == 2
					else "OFFICE"
				),
				"name": (
					"Удалённо"
					if sj_vacancy.get("place_of_work", {}).get("id") == 2
					else "В офисе"
				),
			}
		],
		"work_schedule_by_days": (
			[{"id": "FIVE_ON_TWO_OFF", "name": "5/2"}]
			if sj_vacancy.get("type_of_work", {}).get("id") == 6
			else []
		),
		"working_hours": [{"id": "HOURS_8", "name": "8 часов"}],
		"show_logo_in_search": None,
	}
	
	return transformed


class DataCollector:
	r"""Researcher parameters

	Parameters
	----------
	exchange_rates : dict
		Dict of exchange rates: RUR, USD, EUR.

	"""
	__API_BASE_URL = "https://api.hh.ru/vacancies/"
	__DICT_KEYS = (
		"Ids",
		"Employer",
		"Name",
		"Salary",
		"From",
		"To",
		"Experience",
		"Schedule",
		"Keys",
		"Description",
	)
	
	def __init__(self, exchange_rates: Optional[Dict]):
		self._rates = exchange_rates
	
	@staticmethod
	def clean_tags(html_text: str) -> str:
		"""Remove HTML tags from the string

		Parameters
		----------
		html_text: str
			Input string with tags

		Returns
		-------
		result: string
			Clean text without HTML tags

		"""
		pattern = re.compile("<.*?>")
		return re.sub(pattern, "", html_text)
	
	@staticmethod
	def __convert_gross(is_gross: bool) -> float:
		return 0.87 if is_gross else 1
	
	def get_vacancy(self, vacancy_id: str):
		# Get data from URL
		url = f"{self.__API_BASE_URL}{vacancy_id}"
		vacancy = requests.get(url).json()
		# print(vacancy)
		
		# Extract salary
		salary = vacancy.get("salary")
		
		# Calculate salary:
		# Get salary into {RUB, USD, EUR} with {Gross} parameter and
		# return a new salary in RUB.
		from_to = {"from": None, "to": None}
		if salary:
			is_gross = vacancy["salary"].get("gross")
			for k, v in from_to.items():
				if vacancy["salary"][k] is not None:
					_value = self.__convert_gross(is_gross)
					from_to[k] = int(_value * salary[k] / self._rates[salary["currency"]])
		
		# Create pages tuple
		return (
			vacancy_id,
			vacancy.get("name", ""),
			vacancy.get("employer", {}).get("name", ""),
			salary is not None,
			from_to["from"],
			from_to["to"],
			vacancy.get("experience", {}).get("name", ""),
			vacancy.get("schedule", {}).get("name", ""),
			[el["name"] for el in vacancy.get("key_skills", [])],
			self.clean_tags(vacancy.get("description", "")),
		)
	
	@staticmethod
	def __encode_query_for_url(query: Optional[Dict]) -> str:
		# if 'professional_roles' in query:
		#     query_copy = query.copy()
		#
		#     roles = '&'.join([f'professional_role={r}' for r in query_copy.pop('professional_roles')])
		#
		#     return roles + (f'&{urlencode(query_copy)}' if len(query_copy) > 0 else '')
		
		return urlencode(query)
	
	def collect_vacancies(
			self,
			query: Optional[Dict],
			refresh: bool = False,
			num_workers: int = 1,
			filters: Optional[Dict] = None,
			limit: Optional[int] = None
	) -> Dict:
		"""Parse vacancy JSON: get vacancy name, salary, experience etc.

		Parameters
		----------
		query : dict
			Search query params for GET requests.
		refresh :  bool
			Refresh cached data
		num_workers :  int
			Number of workers for threading.
		filters : dict
			Фильтры для вакансий (название, зарплата, опыт, навыки).
		limit : int
			Лимит количества вакансий.

		Returns
		-------
		dict
			Dict of useful arguments from vacancies

		"""
		if num_workers is None or num_workers < 1:
			num_workers = 1
		
		url_params = self.__encode_query_for_url(query)
		
		# Get cached data if exists...
		cache_name: str = url_params
		cache_hash = hashlib.md5(cache_name.encode()).hexdigest()
		cache_file = os.path.join(CACHE_DIR, cache_hash)
		try:
			if not refresh:
				print(f"[INFO]: Get results from cache! Enable refresh option to update results.")
				return pickle.load(open(cache_file, "rb"))
		except (FileNotFoundError, pickle.UnpicklingError):
			pass
		
		# Check number of pages...
		target_url = self.__API_BASE_URL + "?" + url_params
		num_pages = requests.get(target_url).json()["pages"]
		
		# Collect vacancy IDs...
		ids = []
		for idx in range(num_pages + 1):
			response = requests.get(target_url, {"page": idx})
			data = response.json()
			if "items" not in data:
				break
			ids.extend(x["id"] for x in data["items"])
		
		# Collect vacancies...
		jobs_list = []
		if limit and len(ids) >= limit:
			ids = ids[:limit]
		
	
		jobs_list = []
		with ThreadPoolExecutor(max_workers=num_workers) as executor:
			for vacancy in tqdm(
					executor.map(self.get_vacancy, ids),
					desc="Get data via HH API",
					ncols=100,
					total=len(ids),
			):
				jobs_list.append(vacancy)
		
		# Фильтрация вакансий
		if filters:
			def vacancy_filter(vac):
				# vac: (id, name, employer, salary_bool, from, to, experience, schedule, keys, description)
				name, from_, to_, experience, keys = vac[1], vac[4], vac[5], vac[6], vac[8]
				# Фильтр по названию
				if filters.get("name") and filters["name"].lower() not in name.lower():
					return False
				# Фильтр по вилке зп
				salary_from = filters.get("salary_from")
				salary_to = filters.get("salary_to")
				if salary_from is not None and (from_ is None or from_ < salary_from):
					return False
				if salary_to is not None and (to_ is None or to_ > salary_to):
					return False
				# Фильтр по опыту
				if filters.get("experience") and filters["experience"].lower() not in experience.lower():
					return False
				# Фильтр по ключевым навыкам
				if filters.get("key_skills"):
					required_skills = set(map(str.lower, filters["key_skills"]))
					vacancy_skills = set(map(str.lower, keys))
					if not required_skills.issubset(vacancy_skills):
						return False
				return True
			
			jobs_list = list(filter(vacancy_filter, jobs_list))
		
		# Лимит вакансий
		if limit is not None:
			jobs_list = jobs_list[:limit]
		
		if not jobs_list:
			return {k: [] for k in self.__DICT_KEYS}
		
		unzipped_list = list(zip(*jobs_list))
		
		result = {}
		
		for idx, key in enumerate(self.__DICT_KEYS):
			result[key] = unzipped_list[idx]
		
		pickle.dump(result, open(cache_file, "wb"))
		return result


if __name__ == "__main__":
	dc = DataCollector(exchange_rates={"USD": 0.01264, "EUR": 0.01083, "RUR": 1.00000})
	
	vacancies = dc.collect_vacancies(
		query={"text": "FPGA", "area": 1, "per_page": 50},
		# refresh=True
	)
	print(vacancies["Employer"])
