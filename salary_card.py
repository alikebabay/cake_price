from config import UNECE_YEAR

def salary_card(calc: dict, cake_price_kzt: int = 600_000) -> str:
    """
    Возвращает текстовую карточку по зарплате и торту, устойчивую к отсутствию данных.
    """
    country_name = calc.get("country", "неизвестно")
    salary_kzt = calc.get("salary_kzt")
    salary_usd = calc.get("value")
    unit = calc.get("unit", "USD")
    cake_salary = calc.get("cake_salary")

    # Источник
    src = calc.get("source", {})
    src_name = src.get("name", "неизвестный источник")
    src_year = src.get("year", UNECE_YEAR)
    src_url = src.get("url")

    # Дата обновления
    updated_at = calc.get("ingested_at") or calc.get("updated_at")

    # Конвертация торта
    converted_price = calc.get("converted_price")
    converted_ccy = calc.get("converted_ccy", "???")
    converted_at = calc.get("conversion_time")

    lines = []

    if converted_price:
        lines.append(f"🇰🇿 Казахский торт в {country_name} стоит {converted_price:,.2f} {converted_ccy}")
        if converted_at:
            lines.append(f"💰 Обновлено: {converted_at}")
    else:
        lines.append(f"❌ Курс {converted_ccy} недоступен")

    if cake_salary:
        lines.append(f"💼 Жители {country_name} зарабатывают {cake_salary:,.2f} тортов в месяц")
    elif salary_kzt:
        lines.append(f"💼 Зарплата в {country_name}: {salary_kzt:,.0f} KZT → тортов не рассчитано")
    else:
        lines.append(f"💼 Зарплата в {country_name} недоступна")

    if salary_kzt:
        lines.append(f"👛 Средняя зарплата: {salary_kzt:,.0f} KZT")
    if salary_usd:
        lines.append(f"• {salary_usd:,.1f} {unit}")

    if src_url:
        src_line = f"📊 [{src_name}, {src_year}]({src_url})"
    else:
        src_line = f"📊 {src_name}, {src_year}"

    if updated_at:
        src_line += f" (обновлено: {updated_at})"

    lines.append(src_line)

    return "\n".join(lines)