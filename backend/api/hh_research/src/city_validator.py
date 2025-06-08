import requests


def find_city_id(city_name, areas=None):
    if areas is None:
        areas = requests.get("https://api.hh.ru/areas").json()

    def search(items):
        for item in items:
            if item["name"].lower() == city_name.lower():
                return item["id"]
            if "areas" in item:
                result = search(item["areas"])
                if result:
                    return result
        return None

    return search(areas)