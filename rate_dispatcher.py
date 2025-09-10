import logging
from db import get_cached_rate, cache_rate, is_rate_cached, get_wage_doc, upsert_wage_doc
from calculator import convert_kzt, compute_cake_salary, _get_usd_kzt_rate
from datetime import datetime, timedelta
from config import CAKE_PRICE_KZT, UNECE_UNIT, UNECE_YEAR
import re
from salary_card import salary_card

MAX_AGE_HOURS = 24

#проверка со словарем
def _is_iso3(s: str | None) -> bool:
    return bool(re.fullmatch(r"[A-Z]{3}", (s or "").strip().upper()))


# Если у тебя уже есть эти классы в другом модуле — импортируй их и убери определения ниже
class FXError(Exception): ...
class NoWageError(Exception): ...

def _safe_float(x) -> float | None:
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None

def _parse_ts(ts_val) -> datetime | None:
    if ts_val is None:
        return None
    try:
        if hasattr(ts_val, "isoformat"):
            return datetime.fromisoformat(ts_val.isoformat().replace("Z", "+00:00")).replace(tzinfo=None)
        s = str(ts_val).strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def _is_fresh(ts_val, max_age_hours: int = MAX_AGE_HOURS) -> bool:
    ts = _parse_ts(ts_val)
    if not ts:
        return False
    return (datetime.now() - ts) <= timedelta(hours=max_age_hours)

async def serve_cached_and_update(update, ccy_code: str | None, country_iso3: str | None):
    print(f"[DEBUG] serve_cached_and_update ccy={ccy_code} iso3={country_iso3}")
    parts: list[str] = []

    # ── Блок 1: курс торта в валюте ───────────────────────────────────────────
    if ccy_code:
        try:
            title = f"KZT->{ccy_code}"
            if ccy_code == "KZT":
                parts.append(f"Казахский торт стоит {CAKE_PRICE_KZT:,.2f} KZT")
            else:
                cached = None
                try:
                    cached = get_cached_rate(title)  # (code_title, amount, ts) | None
                except Exception as e:
                    logging.warning("get_cached_rate(%s) failed: %s", title, e)

                use_cache = False
                amount = None
                code_title = ccy_code
                ts_display = None

                if cached:
                    code_title, cached_amount, ts = cached
                    if _is_fresh(ts):
                        fval = _safe_float(cached_amount)
                        if fval is not None:
                            use_cache = True
                            amount = fval
                            ts_display = ts

                if not use_cache:
                    # свежий курс (сколько CCY за 600_000 KZT)
                    try:
                        new_amount = convert_kzt(ccy_code)
                    except FXError as e:
                        logging.exception("convert_kzt(%s) FXError: %s", ccy_code, e)
                        new_amount = None
                    except Exception as e:
                        logging.exception("convert_kzt(%s) failed: %s", ccy_code, e)
                        new_amount = None

                    fval = _safe_float(new_amount)
                    if fval is None:
                        await update.message.reply_text("⚠️ Не удалось получить курс для выбранной валюты, попробуйте позже.")
                        # не выходим: дадим шанс отработать зарплату ниже, если она есть
                    else:
                        amount = fval
                        try:
                            cache_rate(title, amount)
                        except Exception as e:
                            logging.warning("cache_rate(%s) failed: %s", title, e)
                        ts_display = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if amount is not None:
                    parts.append(
                        f"{'Казахский торт стоит' if cached and use_cache else 'Казахский торт стоит'} {amount:,.2f} {ccy_code} (обновлено: {ts_display})"
                    )
                else:
                    parts.append("⚠️ Нет актуального курса для выбранной валюты.")

        except Exception as e:
            logging.exception("FX block failed: %s", e)
            parts.append("⚠️ Ошибка обработки курса валюты.")

    # ── Блок 2: зарплата по стране ────────────────────────────────────────────
    if country_iso3:
        try:
            iso3 = (country_iso3 or "").strip().upper()
            if not _is_iso3(iso3):
                # В диспетчере не мапим; если сюда долетело не-ISO3 — просто сообщаем и идём дальше
                parts.append(f"⚠️ Ожидал код страны (ISO3), получил: {iso3!r}. Попробуйте ещё раз.")
            else:
                # Нужен KZT->USD (цена торта в USD)
                usd_title = "KZT->USD"
                price_usd = None

                try:
                    usd_cached = get_cached_rate(usd_title)
                except Exception as e:
                    logging.warning("get_cached_rate(%s) failed: %s", usd_title, e)
                    usd_cached = None

                if usd_cached and _is_fresh(usd_cached[2]):
                    price_usd = _safe_float(usd_cached[1])

                if price_usd is None:
                    try:
                        val = convert_kzt("USD")  # 600k KZT в USD
                    except Exception as e:
                        logging.exception("convert_kzt(USD) failed: %s", e)
                        val = None

                    price_usd = _safe_float(val)
                    if price_usd is None:
                        parts.append("⚠️ Не удалось получить курс USD для расчёта зарплаты.")
                    else:
                        try:
                            cache_rate(usd_title, price_usd)
                        except Exception as e:
                            logging.warning("cache_rate(%s) failed: %s", usd_title, e)

                if price_usd is not None:
                    calc = append_salary_iso3(iso3, price_usd)
                    if calc:
                        # доклеиваем результат валютного блока
                        calc["amount"] = amount
                        calc["ccy_code"] = ccy_code
                        calc["ts_display"] = ts_display

                        try:
                            await update.message.reply_text(
                                salary_card(calc),
                                parse_mode="HTML",
                                disable_web_page_preview=True
                            )
                        except Exception as e:
                            logging.exception("reply_text (card) failed: %s", e)
                        return
                    else:
                        parts.append("⚠️ Зарплата для указанной страны не найдена.")
        except Exception as e:
            logging.exception("Salary block failed: %s", e)
            parts.append("⚠️ Ошибка обработки данных по зарплате.")

    # ── Ответ ─────────────────────────────────────────────────────────────────
    msg = "\n\n".join(parts) if parts else "⚠️ Ничего не распознано."
    try:
        await update.message.reply_text(msg)
    except Exception as e:
        logging.exception("reply_text failed: %s", e)

def append_salary_iso3(iso3: str, price_usd: float) -> str | None:
    iso3 = (iso3 or "").strip().upper()
    try:
        doc = get_wage_doc(iso3)
    except Exception as e:
        logging.exception("get_wage_doc(%s) failed: %s", iso3, e)
        return None

    print(f"[DEBUG] get_wage_doc({iso3}, {UNECE_YEAR}, {UNECE_UNIT}) → {doc}")
    if not doc:
        return None

    salary_usd = doc.get("salary_usd", doc.get("value"))
    salary_usd_f = _safe_float(salary_usd)
    price_usd_f = _safe_float(price_usd)

    if salary_usd_f is None or price_usd_f is None or price_usd_f == 0:
        return None

    try:
        kzt_per_usd = CAKE_PRICE_KZT / price_usd_f
        calc = compute_cake_salary(salary_usd_f, kzt_per_usd=kzt_per_usd)
    except Exception as e:
        logging.exception("compute_cake_salary failed: %s", e)
        return None

    try:
        # добавим timestamp вручную
        calc["updated_at"] = datetime.utcnow().isoformat()
        upsert_wage_doc(
            iso3,
            {"salary_kzt": calc["salary_kzt"], "cake_salary": calc["cake_salary"], "updated_at": calc["updated_at"]},
            UNECE_YEAR,
            UNECE_UNIT,
        )
    except Exception as e:
        logging.exception("upsert_wage_doc failed for %s: %s", iso3, e)

    country_name = doc.get("country", iso3)
    src = doc.get("source", {})
    src_name = src.get("name", "UNECE")
    src_year = src.get("year", UNECE_YEAR)
    src_url = src.get("url", "")
    upd_display = _fmt_ts(doc.get("updated_at") or doc.get("ingested_at") or calc.get("updated_at"))
    # 👇 ДОБАВЬ ЭТО:
    calc["country"] = doc.get("country", iso3)
    calc["unit"] = doc.get("unit", "USD")
    calc["value"] = salary_usd_f
    calc["source"] = doc.get("source", {})
    calc["converted_price"] = price_usd_f
    calc["converted_ccy"] = "USD"
    calc["conversion_time"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    try:
        return calc
    except Exception:
        return f"Средняя зарплата в {country_name}: {calc.get('salary_kzt')} KZT; ≈ {calc.get('cake_salary')} тортов."
#форматтер времени
def _fmt_ts(ts) -> str:
    if not ts:
        return "неизв."
    return str(ts).split(".")[0].replace("T", " ")


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