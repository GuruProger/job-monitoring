"""Head Hunter Researcher

Description   :
    HeadHunter (hh.ru) main research script.

    1. Get data from hh.ru by user request (i.e. 'Machine learning')
    2. Collect all vacancies.
    3. Parse JSON and get useful values: salary, experience, name,
    skills, employer name etc.
    4. Calculate some statistics: average salary, median, std, variance.

------------------------------------------------------------------------

GNU GENERAL PUBLIC LICENSE
Version 3, 29 June 2007

Copyright (c) 2020 Kapitanov Alexander

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

THERE IS NO WARRANTY FOR THE PROGRAM, TO THE EXTENT PERMITTED BY
APPLICABLE LAW. EXCEPT WHEN OTHERWISE STATED IN WRITING THE COPYRIGHT
HOLDERS AND/OR OTHER PARTIES PROVIDE THE PROGRAM "AS IS" WITHOUT
WARRANTY OF ANY KIND, EITHER EXPRESSED OR IMPLIED, INCLUDING, BUT
NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE. THE ENTIRE RISK AS TO THE QUALITY AND
PERFORMANCE OF THE PROGRAM IS WITH YOU. SHOULD THE PROGRAM PROVE
DEFECTIVE, YOU ASSUME THE COST OF ALL NECESSARY SERVICING, REPAIR OR
OR CORRECTION.

------------------------------------------------------------------------
"""
import json
import base64
import io
# Authors       : Alexander Kapitanov
# ...
# Contacts      : <empty>
# License       : GNU GENERAL PUBLIC LICENSE

import os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional, Dict, List, Union, Tuple, Any
import numbers

from .src.analyzer import Analyzer
from .src.currency_exchange import Exchanger
from .src.data_collector import DataCollector
from .src.parser import Settings
from .src.predictor import Predictor

CACHE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "cache")


def _to_builtin_type(obj: Any) -> Any:
	"""Рекурсивно преобразует numpy-типы к стандартным python-типам."""
	if isinstance(obj, dict):
		return {k: _to_builtin_type(v) for k, v in obj.items()}
	elif isinstance(obj, (list, tuple)):
		return [ _to_builtin_type(v) for v in obj ]
	elif isinstance(obj, (np.integer, np.int_, np.intc, np.intp, np.int8, np.int16, np.int32, np.int64)):
		return int(obj)
	# Исправлено: np.float_ заменено на np.float64
	elif isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
		return float(obj)
	elif isinstance(obj, np.ndarray):
		return obj.tolist()
	else:
		return obj


class ResearcherHH:
	"""Main class for searching vacancies and analyze them."""
	
	def __init__(
			self, options: dict, refresh: bool = True, num_workers: int = 10, save_result: bool = True,
			rates: dict = {
				"USD": 0.012641,
				"EUR": 0.010831,
				"UAH": 0.35902,
				"RUR": 1  # Не меняйте на RUB, т.к. это не валюта, а код валюты
			},
	):
		self.settings = Settings(
			options=options, refresh=refresh, num_workers=num_workers, save_result=save_result, rates=rates
		)
	
		self.exchanger = Exchanger()
		self.collector: Optional[DataCollector] = None
		self.analyzer: Optional[Analyzer] = None
		self.predictor = Predictor()
	
	def update(self, **kwargs):
		self.settings.update_params(**kwargs)
		if not any(self.settings.rates.values()):
			print("[INFO]: Trying to get exchange rates from remote server...")
			self.exchanger.update_exchange_rates(self.settings.rates)
		
		print(f"[INFO]: Get exchange rates: {self.settings.rates}")
		self.collector = DataCollector(self.settings.rates)
		self.analyzer = Analyzer(self.settings.save_result)
	
	def get_vacancies(self, limit: Optional[int] = 500, filters: Optional[dict] = None):
		"""Возвращает данные вакансий в формате dict (JSON) с ограничением по количеству и фильтрами."""
		print("[INFO]: Сбор данных для JSON...")
		vacancies = self.collector.collect_vacancies(
			query=self.settings.options,
			refresh=self.settings.refresh,
			num_workers=self.settings.num_workers,
			filters=filters,
			limit=limit
		)
		print("[INFO]: Подготовка DataFrame...")
		df = self.analyzer.prepare_df(vacancies)
		json_data = df.to_json(orient="records", force_ascii=False)
		print("[INFO]: Данные подготовлены в формате JSON.")
		return json.loads(json_data)
	
	def _generate_salary_plot(self, df) -> Tuple[plt.Figure, Dict[str, plt.Axes]]:
		"""Создает и возвращает график зарплат"""
		fig, axs = plt.subplots(2, 2, figsize=(12, 8))
		axes = {'box': axs[0, 0], 'swarm': axs[0, 1], 'from_hist': axs[1, 0], 'to_hist': axs[1, 1]}
		plt.suptitle("Salary Analysis")
		
		sns.boxplot(data=df[["From", "To"]].dropna() / 1000, width=0.4, ax=axes['box'])
		axes['box'].set_title("From / To: Boxplot")
		axes['box'].set_ylabel("Salary x 1000 [RUB]")
		
		sns.swarmplot(data=df[["From", "To"]].dropna() / 1000, size=6, ax=axes['swarm'])
		axes['swarm'].set_title("From / To: Swarmplot")
		
		sns.histplot(df["From"].dropna() / 1000, bins=14, color="C0", kde=True, ax=axes['from_hist'])
		axes['from_hist'].set_title("From: Distribution")
		axes['from_hist'].grid(True)
		axes['from_hist'].set_xlabel("Salary x 1000 [RUB]")
		axes['from_hist'].set_xlim([-50, df["From"].max() / 1000])
		axes['from_hist'].set_yticks([])
		
		sns.histplot(df["To"].dropna() / 1000, bins=14, color="C1", kde=True, ax=axes['to_hist'])
		axes['to_hist'].set_title("To: Distribution")
		axes['to_hist'].grid(True)
		axes['to_hist'].set_xlim([-50, df["To"].max() / 1000])
		axes['to_hist'].set_xlabel("Salary x 1000 [RUB]")
		axes['to_hist'].set_yticks([])
		
		plt.tight_layout()
		return fig, axes
	
	def get_statistics(self, output_dir: str = None, save_plots: bool = True, include_base64: bool = False) -> Dict:
		"""Собирает статистику по вакансиям и возвращает её в виде словаря.
		При необходимости сохраняет графики в файлы.

		Parameters
		----------
		output_dir : str, optional
			Директория для сохранения графиков, по умолчанию используется 
			директория кэша
		save_plots : bool, optional
			Флаг сохранения графиков, по умолчанию True
		include_base64 : bool, optional
			Включить графики в формате base64 в ответ, по умолчанию False

		Returns
		-------
		Dict
			Словарь со статистикой, содержащий следующие ключи:
			- vacancy_count: общее количество вакансий
			- salary_stats: статистика по зарплатам (min, max, mean, median)
			- top_keywords: наиболее часто встречающиеся ключевые навыки
			- top_description_words: наиболее часто встречающиеся слова в описаниях
			- plot_paths: пути к сохраненным графикам (если save_plots=True)
			- plot_images: графики в формате base64 (если include_base64=True)
		"""
		print("[INFO]: Сбор вакансий для анализа...")
		vacancies = self.collector.collect_vacancies(
			query=self.settings.options,
			refresh=self.settings.refresh,
			num_workers=self.settings.num_workers
		)
		print("[INFO]: Подготовка DataFrame...")
		df = self.analyzer.prepare_df(vacancies)
		
		# Подготовка директории для графиков
		if save_plots:
			if output_dir is None:
				output_dir = os.path.join(CACHE_DIR, "plots")
			os.makedirs(output_dir, exist_ok=True)
		
		# Собираем статистику
		statistics = {}
		statistics["vacancy_count"] = df["Ids"].count()
		
		# Статистика по зарплатам
		salary_stats = {}
		comb_ft = np.nanmean(df[df["Salary"]][["From", "To"]].to_numpy(), axis=1)
		salary_stats["min"] = int(np.min(comb_ft))
		salary_stats["max"] = int(np.max(comb_ft))
		salary_stats["mean"] = int(np.mean(comb_ft))
		salary_stats["median"] = int(np.median(comb_ft))
		
		# Добавляем статистические показатели
		df_stat = df[["From", "To"]].describe().applymap(np.int32)
		for col in ["From", "To"]:
			salary_stats[f"{col.lower()}_stats"] = {
				"min": int(df_stat.loc["min", col]),
				"max": int(df_stat.loc["max", col]),
				"mean": int(df_stat.loc["mean", col]),
				"median": int(df_stat.loc["50%", col])
			}
		
		statistics["salary_stats"] = salary_stats
		
		# Топ ключевых слов
		most_keys = self.analyzer.find_top_words_from_keys(df["Keys"].to_list())
		statistics["top_keywords"] = most_keys[:20].to_dict()
		
		# Топ слов из описаний
		most_words = self.analyzer.find_top_words_from_description(df["Description"].to_list())
		statistics["top_description_words"] = most_words[:20].to_dict()
		
		# Работа с графиками
		plot_paths = {}
		plot_images = {}
		
		# График 1: Boxplot и Swarmplot
		fig1, _ = self._generate_salary_plot(df)
		
		if include_base64:
			# Сохраняем график зарплаты в base64
			buffer = io.BytesIO()
			fig1.savefig(buffer, format='png')
			buffer.seek(0)
			plot_images["salary_analysis"] = base64.b64encode(buffer.getvalue()).decode('utf-8')
		
		if save_plots:
			salary_plot_path = os.path.join(output_dir, "salary_analysis.png")
			fig1.savefig(salary_plot_path)
			plot_paths["salary_analysis"] = salary_plot_path
		
		plt.close(fig1)
		
		# График 2: Топ ключевых слов
		fig2, ax = plt.subplots(figsize=(10, 6))
		most_keys[:15].plot(kind='bar', ax=ax)
		ax.set_title("Top Keywords")
		ax.set_ylabel("Frequency")
		ax.set_xlabel("Keywords")
		plt.tight_layout()
		
		if include_base64:
			buffer = io.BytesIO()
			fig2.savefig(buffer, format='png')
			buffer.seek(0)
			plot_images["top_keywords"] = base64.b64encode(buffer.getvalue()).decode('utf-8')
		
		if save_plots:
			keywords_plot_path = os.path.join(output_dir, "top_keywords.png")
			fig2.savefig(keywords_plot_path)
			plot_paths["top_keywords"] = keywords_plot_path
		
		plt.close(fig2)
		
		# График 3: Топ слов из описаний
		fig3, ax = plt.subplots(figsize=(10, 6))
		most_words[:15].plot(kind='bar', ax=ax)
		ax.set_title("Top Words from Description")
		ax.set_ylabel("Frequency")
		ax.set_xlabel("Words")
		plt.tight_layout()
		
		if include_base64:
			buffer = io.BytesIO()
			fig3.savefig(buffer, format='png')
			buffer.seek(0)
			plot_images["top_description_words"] = base64.b64encode(buffer.getvalue()).decode('utf-8')
		
		if save_plots:
			words_plot_path = os.path.join(output_dir, "top_description_words.png")
			fig3.savefig(words_plot_path)
			plot_paths["top_description_words"] = words_plot_path
		
		plt.close(fig3)
		
		if save_plots:
			statistics["plot_paths"] = plot_paths
		
		if include_base64:
			statistics["plot_images"] = plot_images
		
		return _to_builtin_type(statistics)
	
	def __call__(self):
		print("[INFO]: Collect data from JSON. Create list of vacancies...")
		vacancies = self.collector.collect_vacancies(
			query=self.settings.options, refresh=self.settings.refresh, num_workers=self.settings.num_workers
		)
		print("[INFO]: Prepare dataframe...")
		df = self.analyzer.prepare_df(vacancies)
		# df.to_csv(os.path.join(CACHE_DIR, "vacancies.csv"))
		print("\n[INFO]: Analyze dataframe...")
		self.analyzer.analyze_df(df)
		print("\n[INFO]: Predict None salaries...")
		# total_df = self.predictor.predict(df)
		# self.predictor.plot_results(total_df)
		print("[INFO]: Done! Exit()")


if __name__ == "__main__":
	hh_analyzer = ResearcherHH(options={
		"text": "Python",
		"area": 1,
		"per_page": 10,
	})
	hh_analyzer.update()
	# hh_analyzer()
	print(hh_analyzer.get_statistics(include_base64=True))
