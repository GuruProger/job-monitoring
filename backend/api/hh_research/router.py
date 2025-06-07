from typing import Annotated, Sequence

from fastapi import APIRouter, Depends, status, Query, HTTPException

from .researcher import ResearcherHH

router = APIRouter(tags=["hh"])


@router.get("/get_vacancies", status_code=status.HTTP_201_CREATED)
async def get_vacancies(
		text: str = Query(..., description="Поисковый запрос для вакансий"),
		area: int = Query(1, description="Локация поискового запроса"),
		per_page: int = Query(50, description="Количество вакансий на страницу"),
		professional_roles: Sequence[int] = Query(
			[96, 10], description="Фильтр по роли в запросе"
		),
		refresh: bool = Query(False, description="Обновление кешируемых данных")
):
	hh_analyzer = ResearcherHH(options={
		"text": text,
		"area": area,
		"per_page": per_page,
		"professional_roles": professional_roles
	}, refresh=refresh, )
	hh_analyzer.update()
	hh_analyzer()
	return hh_analyzer.get_vacancies(limit=500)
