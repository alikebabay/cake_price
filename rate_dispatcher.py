from db import get_cached_rate, cache_rate, is_rate_cached, get_wage_doc, upsert_wage_doc
from calculator import convert_kzt, compute_cake_salary, _get_usd_kzt_rate
from datetime import datetime, timedelta
from config import CAKE_PRICE_KZT, UNECE_UNIT, UNECE_YEAR
from cake_dictionary import _CCY_TO_ISO3, iso3_from_country_name

MAX_AGE = timedelta(hours=24)
#обратный конвертер для поиска стран
ISO3_TO_COUNTRY = {v: k for k, v in _CCY_TO_ISO3.items()}

async def serve_cached_and_update(update, ccy_code: str | None, country_iso3: str | None):
    print(f"[DEBUG] serve_cached_and_update ccy={ccy_code} iso3_raw={country_iso3}")
    parts: list[str] = []

    # ── Блок 1: курс торта в валюте ───────────────────────────────────────────
    if ccy_code:
        title = f"KZT->{ccy_code}"
        if ccy_code == "KZT":
            parts.append(f"Казахский торт стоит {CAKE_PRICE_KZT:,.2f} KZT")
        else:
            cached = get_cached_rate(title)
            if cached:
                code_title, amount, ts = cached
            else:
                new_amount = convert_kzt(ccy_code)  # 600k KZT в CCY
                if new_amount is None:
                    await update.message.reply_text("⚠️ Сервис недоступен, кэша нет.")
                    return
                try:
                    amount = float(str(new_amount).replace(",", "").strip())
                except (ValueError, TypeError):
                    await update.message.reply_text("❌ Ошибка: неверный формат курса.")
                    return
                cache_rate(title, amount)
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                code_title = ccy_code

            parts.append(
                f"{'Кэш' if cached else 'Создал'} • 600000 KZT = {amount:,.2f} {code_title} (обновлено: {ts})"
            )

    # ── Блок 2: зарплата по стране ────────────────────────────────────────────
    if country_iso3:
        # Нормализация до ISO3 (если прилетело имя страны)
        key = (country_iso3 or "").strip().upper()
        if not (len(key) == 3 and key.isalpha()):
            resolved = iso3_from_country_name(key)
            if resolved:
                key = resolved
        print(f"[DEBUG] normalized country → iso3={key}")

        # Обеспечиваем цену торта в USD (600k KZT в USD), чтобы посчитать KZT/1USD
        usd_title = "KZT->USD"
        usd_cached = get_cached_rate(usd_title)
        if usd_cached:
            _, price_usd, _ = usd_cached
        else:
            val = convert_kzt("USD")  # 600k KZT в USD
            if val is None:
                await update.message.reply_text("⚠️ Не удалось получить курс USD.")
                return
            try:
                price_usd = float(str(val).replace(",", "").strip())
                cache_rate(usd_title, price_usd)
            except Exception:
                await update.message.reply_text("❌ Не удалось обработать курс USD.")
                return

        extra = append_salary_iso3(key, price_usd)
        if not extra:
            await update.message.reply_text("⚠️ Зарплата для страны не найдена.")
            return
        parts.append(extra)

    # ── Ответ ─────────────────────────────────────────────────────────────────
    msg = "\n\n".join(parts) if parts else "⚠️ Ничего не распознано."
    await update.message.reply_text(msg.replace(",", " "))

def append_salary_iso3(iso3: str, price_usd: float) -> str | None:
    iso3 = (iso3 or "").strip().upper()

    # Документ UNECE по ключу (iso3, year, unit)
    doc = get_wage_doc(iso3, UNECE_YEAR, UNECE_UNIT)
    print(f"[DEBUG] get_wage_doc({iso3}, {UNECE_YEAR}, {UNECE_UNIT}) → {doc}")
    if not doc:
        return None

    # Берём USD-зарплату из нового поля, иначе из старого value (совместимость)
    salary_usd = doc.get("salary_usd")
    if salary_usd is None:
        salary_usd = doc.get("value")
    if salary_usd is None:
        return None

    # price_usd = цена торта в USD за 600k KZT
    # KZT за 1 USD:
    kzt_per_usd = CAKE_PRICE_KZT / float(price_usd)

    calc = compute_cake_salary(float(salary_usd), kzt_per_usd=kzt_per_usd)

    # Обновляем только производные поля (и updated_at поставится в upsert)
    try:
        upsert_wage_doc(iso3, {
            "salary_kzt": calc["salary_kzt"],
            "cake_salary": calc["cake_salary"],
        }, UNECE_YEAR, UNECE_UNIT)
    except Exception as e:
        import logging
        logging.exception("upsert_wage_doc failed for %s: %s", iso3, e)

    country_name = doc.get("country", iso3)
    src = calc.get("source", {})
    src_name = src.get("name", "UNECE")
    src_year = src.get("year", UNECE_YEAR)
    src_url = src.get("url", "")
    upd_display = _fmt_ts(doc.get("updated_at") or doc.get("ingested_at") or calc["updated_at"])

    return (
        f"Средняя зарплата в {country_name}: {calc['salary_kzt']:,.0f} KZT"
        f"\nИсточник: {src_name} ({src_year}), ссылка: {src_url} ({upd_display})"
        f"\nЭто ≈ {calc['cake_salary']:,.2f} тортов (600 000 KZT за торт)"
    )

#форматтер времени
def _fmt_ts(v):
    try:
        from datetime import datetime
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
        return "" if v is None else str(v)
    except Exception:
        return ""

#тест
import asyncio

# Фейковый update с подменой reply_text
class FakeMessage:
    async def reply_text(self, text):
        print(f"[BOT]: {text}")

class FakeUpdate:
    message = FakeMessage()

# Запускаем тест
if __name__ == "__main__":
    # Подставь код валюты, например USD
    asyncio.run(serve_cached_and_update(FakeUpdate(), "rub"))