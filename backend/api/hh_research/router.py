from typing import Annotated, Sequence, List, Optional, Dict
from fastapi import APIRouter, Depends, status, Query, HTTPException
from .researcher import ResearcherHH
from .src.city_validator import find_city_id

router = APIRouter(tags=["hh"])

EXPERIENCE_MAPPING = {
	"noExperience": "Без опыта",
	"between1And3": "От 1 года до 3 лет",
	"between3And6": "От 3 до 6 лет",
	"moreThan6": "Более 6 лет"
}


# @router.get("/get_vacancies", status_code=status.HTTP_201_CREATED)
# async def get_vacancies(
# 		text: str = Query(..., description="Поисковый запрос для вакансий"),
# 		area: int = Query(1, description="Локация поискового запроса"),
# 		per_page: int = Query(50, description="Количество вакансий на страницу"),
# 		professional_roles: Sequence[int] = Query(
# 			[96, 10], description="Фильтр по роли в запросе"
# 		),
# 		refresh: bool = Query(False, description="Обновление кешируемых данных")
# ):
# 	hh_analyzer = ResearcherHH(options={
# 		"text": text,
# 		"area": area,
# 		"per_page": per_page,
# 		"professional_roles": professional_roles
# 	}, refresh=refresh, )
# 	hh_analyzer.update()
# 	hh_analyzer()
# 	return hh_analyzer.get_vacancies(limit=500)


@router.get("/get_statistics", status_code=status.HTTP_200_OK)
async def get_statistics(
		text: str = Query(..., description="Поисковый запрос для статистики"),
		area: str = Query('Москва', description="Локация поискового запроса"),
		per_page: int = Query(50, description="Количество вакансий на страницу"),
		refresh: bool = Query(False, description="Обновление кешируемых данных"),
		include_plots: bool = Query(True, description="Включить графики в формате base64 в ответ"),
		plots: List[str] = Query(
			None,
			description="Список требуемых графиков (from_hist, to_hist, avg_hist). Если не указан, будут возвращены все."
		),
		limit: int = Query(None, description="Ограничение количества вакансий для анализа"),
		experience: List[str] = Query(
			None,
			description="Фильтр по опыту работы (noExperience, between1And3, between3And6, moreThan6)"
		),
		age_from: Optional[int] = Query(None, description="Минимальный возраст соискателя"),
		age_to: Optional[int] = Query(None, description="Максимальный возраст соискателя"),
		key_skills: List[str] = Query(
			None,
			description="Фильтр по ключевым навыкам"
		)
):
	"""
	Возвращает статистику по вакансиям с возможностью фильтрации и отдельные графики зарплат.

	Параметры:
	- text: поисковый запрос для вакансий
	- area: локация поискового запроса (по умолчанию Москва)
	- per_page: количество вакансий на страницу
	- refresh: обновление кешируемых данных
	- include_plots: включать ли графики в формате base64 в ответ
	- plots: список требуемых графиков, доступные значения:
	  * from_hist - гистограмма минимальной зарплаты
	  * to_hist - гистограмма максимальной зарплаты
	  * avg_hist - гистограмма средней зарплаты
	- limit: ограничение количества обрабатываемых вакансий
	- experience: фильтр по опыту работы (может быть несколько значений)
	- age_from: минимальный возраст соискателя
	- age_to: максимальный возраст соискателя
	- key_skills: фильтр по ключевым навыкам (может быть несколько значений)

	Возвращает словарь с ключами:
	- vacancy_count: общее количество вакансий
	- salary_stats: статистика по зарплатам (min, max, mean, median)
	- top_keywords: наиболее часто встречающиеся ключевые навыки
	- top_description_words: наиболее часто встречающиеся слова в описаниях
	- plot_images: отдельные графики в формате base64 (если include_plots=True)
	- filters: примененные фильтры
	"""
	try:
		area_id = find_city_id(area) or '1'
		# Подготовка параметров для ResearcherHH
		options = {
			"text": text,
			"area": find_city_id,
			"per_page": per_page,
			"professional_roles": [0]
		}
		
		# Добавляем фильтры, если они указаны
		if experience:
			options["experience"] = experience
		if age_from is not None or age_to is not None:
			options["age"] = {
				"from": age_from,
				"to": age_to
			}
		if key_skills:
			options["key_skills"] = key_skills
		
		hh_analyzer = ResearcherHH(options=options, refresh=refresh)
		hh_analyzer.update()
		
		# Получаем статистику с графиками в base64
		statistics = hh_analyzer.get_statistics(
			save_plots=False,
			include_base64=include_plots,
			limit=limit,
			experience=experience,
			age=[age_from, age_to],
			key_skills=key_skills
		)
		
		# Фильтруем графики, если указан параметр plots
		if include_plots and plots and 'plot_images' in statistics:
			filtered_images = {}
			for plot_name in plots:
				if plot_name in statistics['plot_images']:
					filtered_images[plot_name] = statistics['plot_images'][plot_name]
			statistics['plot_images'] = filtered_images
		
		return statistics

	except Exception as e:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Ошибка при обработке статистики: {str(e)}"
		)


@router.get("/status", status_code=status.HTTP_200_OK)
async def status():
	return {'status': 'ok'}
