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
		return [_to_builtin_type(v) for v in obj]
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
		print(self.settings)
		
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
	
	# def get_vacancies(self, limit: Optional[int] = 500, filters: Optional[dict] = None):
	# 	"""Возвращает данные вакансий в формате dict (JSON) с ограничением по количеству и фильтрами."""
	# 	print("[INFO]: Сбор данных для JSON...")
	# 	vacancies = self.collector.collect_vacancies(
	# 		query=self.settings.options,
	# 		refresh=self.settings.refresh,
	# 		num_workers=self.settings.num_workers,
	# 		filters=filters,
	# 		limit=limit
	# 	)
	# 	print("[INFO]: Подготовка DataFrame...")
	# 	df = self.analyzer.prepare_df(vacancies)
	# 	json_data = df.to_json(orient="records", force_ascii=False)
	# 	print("[INFO]: Данные подготовлены в формате JSON.")
	# 	return json.loads(json_data)
	
	def _generate_salary_plot(self, df) -> Tuple[plt.Figure, Dict[str, plt.Axes]]:
		"""Создает и возвращает графики распределения зарплат From, To и Avg"""
		fig, axs = plt.subplots(1, 3, figsize=(18, 5))
		axes = {'from_hist': axs[0], 'to_hist': axs[1], 'avg_hist': axs[2]}
		plt.suptitle("Salary Distribution")
		
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
		
		# Новый график: распределение средней зарплаты (avg)
		avg_salary = df[["From", "To"]].dropna()
		avg_salary = avg_salary.mean(axis=1) / 1000
		sns.histplot(avg_salary, bins=14, color="C2", kde=True, ax=axes['avg_hist'])
		axes['avg_hist'].set_title("Avg: Distribution")
		axes['avg_hist'].grid(True)
		axes['avg_hist'].set_xlabel("Salary x 1000 [RUB]")
		if not avg_salary.empty:
			axes['avg_hist'].set_xlim([-50, avg_salary.max()])
		axes['avg_hist'].set_yticks([])
		
		plt.tight_layout()
		return fig, axes
	
	def _generate_salary_plots(self, df) -> Dict[str, plt.Figure]:
		"""Создает и возвращает отдельные графики распределения зарплат From, To и Avg"""
		plots = {}
		
		# График распределения From
		fig_from = plt.figure(figsize=(10, 6))
		ax_from = fig_from.add_subplot(1, 1, 1)
		sns.histplot(df["From"].dropna() / 1000, bins=14, color="C0", kde=True, ax=ax_from)
		ax_from.set_title("From: Distribution")
		ax_from.grid(True)
		ax_from.set_xlabel("Salary x 1000 [RUB]")
		ax_from.set_xlim([-50, df["From"].max() / 1000])
		ax_from.set_yticks([])
		fig_from.tight_layout()
		plots['from_hist'] = fig_from
		
		# График распределения To
		fig_to = plt.figure(figsize=(10, 6))
		ax_to = fig_to.add_subplot(1, 1, 1)
		sns.histplot(df["To"].dropna() / 1000, bins=14, color="C1", kde=True, ax=ax_to)
		ax_to.set_title("To: Distribution")
		ax_to.grid(True)
		ax_to.set_xlabel("Salary x 1000 [RUB]")
		ax_to.set_xlim([-50, df["To"].max() / 1000])
		ax_to.set_yticks([])
		fig_to.tight_layout()
		plots['to_hist'] = fig_to
		
		# График распределения Avg
		fig_avg = plt.figure(figsize=(10, 6))
		ax_avg = fig_avg.add_subplot(1, 1, 1)
		avg_salary = df[["From", "To"]].dropna()
		avg_salary = avg_salary.mean(axis=1) / 1000
		sns.histplot(avg_salary, bins=14, color="C2", kde=True, ax=ax_avg)
		ax_avg.set_title("Avg: Distribution")
		ax_avg.grid(True)
		ax_avg.set_xlabel("Salary x 1000 [RUB]")
		if not avg_salary.empty:
			ax_avg.set_xlim([-50, avg_salary.max()])
		ax_avg.set_yticks([])
		fig_avg.tight_layout()
		plots['avg_hist'] = fig_avg
		
		return plots
	
	def get_statistics(
			self,
			output_dir: str = None, save_plots: bool = True, include_base64: bool = False, limit: Optional[int] = None,
			experience: Optional[List[str]] = None,
			age: Optional[List[int]] = None,
			key_skills: Optional[List[str]] = None,
	) -> Dict:
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
		limit : int, optional
			Ограничение количества вакансий для анализа

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
			num_workers=self.settings.num_workers,
			limit=limit  # Передаем limit в collect_vacancies
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
		
		# Генерируем отдельные графики
		figures = self._generate_salary_plots(df)
		
		for plot_name, fig in figures.items():
			if include_base64:
				buffer = io.BytesIO()
				fig.savefig(buffer, format='png')
				buffer.seek(0)
				plot_images[plot_name] = base64.b64encode(buffer.getvalue()).decode('utf-8')
			
			if save_plots:
				plot_path = os.path.join(output_dir, f"{plot_name}.png")
				fig.savefig(plot_path)
				plot_paths[plot_name] = plot_path
			
			plt.close(fig)
		
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
