from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, status, Query, HTTPException

from .researcher import ResearcherHH

router = APIRouter(tags=["hh"])


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
		area: int = Query(1, description="Локация поискового запроса"),
		per_page: int = Query(50, description="Количество вакансий на страницу"),
		refresh: bool = Query(False, description="Обновление кешируемых данных"),
		include_plots: bool = Query(True, description="Включить графики в формате base64 в ответ"),
		limit: int = Query(None, description="Ограничение количества вакансий для анализа")
):
	"""
	Возвращает статистику по вакансиям и графики зарплат.
	
	Параметры:
	- text: поисковый запрос для вакансий
	- area: локация поискового запроса (по умолчанию 1 - Москва)
	- per_page: количество вакансий на страницу
	- professional_roles: фильтр по профессиональным ролям
	- refresh: обновление кешируемых данных
	- include_plots: включать ли графики в формате base64 в ответ
	- limit: ограничение количества обрабатываемых вакансий
	
	Возвращает словарь с ключами:
	- vacancy_count: общее количество вакансий
	- salary_stats: статистика по зарплатам (min, max, mean, median)
	- top_keywords: наиболее часто встречающиеся ключевые навыки
	- top_description_words: наиболее часто встречающиеся слова в описаниях
	- plot_images: графики в формате base64 (если include_plots=True)
	"""
	try:
		hh_analyzer = ResearcherHH(options={
			"text": text,
			"area": area,
			"per_page": per_page,
			"professional_roles": [0]
		}, refresh=refresh)
		hh_analyzer.update()
		
		# Получаем статистику с графиками в base64
		statistics = hh_analyzer.get_statistics(
			save_plots=False,  # Не сохраняем в файл
			include_base64=include_plots,  # Включаем base64 в ответ, если запрошено
			limit=limit  # Передаем limit для ограничения количества вакансий
		)
		
		return statistics
	except Exception as e:
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail=f"Ошибка при обработке статистики: {str(e)}"
		)
