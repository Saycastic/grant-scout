"""
LLM Normalizer — скармливает clean_text модели, получает JSON гранта.
Провайдер: Anthropic Claude (или OpenAI — переключается через config).
"""

import json
import os
import hashlib
from typing import Optional

SYSTEM_PROMPT = """Ты — аналитик грантов для современных визуальных художников.
Тебе дают текст со страницы сайта фонда или агрегатора. Твоя задача — извлечь все гранты, стипендии, резиденции и fellowships, которые есть в тексте, и вернуть их в виде строгого JSON.

ЦЕЛЕВАЯ АУДИТОРИЯ: художники, работающие в жанрах современного визуального искусства.
ПОДХОДЯТ дисциплины: живопись, скульптура, инсталляция, видеоарт, перформанс, медиа-арт, графика, mixed media, printmaking, drawing, site-specific art, public art, новые медиа.
НЕ ПОДХОДЯТ дисциплины (reject): фотография как самостоятельная дисциплина, иллюстрация (книжная/коммерческая), дизайн (графический/промышленный/UX), архитектура, кино/документалистика, музыка, танец, литература, театр.
ИСКЛЮЧЕНИЕ: если конкурс/грант открыт для "all visual artists" или "artists working in any medium" — он подходит, даже если фотографы тоже могут подавать.

Правила:
- Включай ТОЛЬКО гранты с активным open call — то есть приём заявок сейчас открыт или откроется в будущем. Если дедлайн уже прошёл относительно CURRENT_DATE — reject
- deadline пиши строго в формате YYYY-MM-DD или null. Не используй человеческие фразы ("next month", "rolling")
- deadline_type: "fixed" (конкретная дата), "rolling" (принимают всегда), "recurring" (повторяется циклами), "tba" (будет объявлен), "closed" (приём закрыт)
- deadline_notes: короткое пояснение если deadline_type не fixed (например "quarterly deadlines" или "annual call, next cycle TBA")
- НЕ включай: платные конкурсы (entry fee) без грантовой составляющей, выставки без денег, jobs, стажировки без оплаты, призы в виде публикации или экспозиции без денег
- Если дедлайн не указан явно — пиши null
- amount пиши как строку: "$5,000", "up to €10,000", "varies", "undisclosed"
- summary и why_relevant — ТОЛЬКО на английском, кратко (2-3 предложения). Никакого русского языка в этих полях.
- confidence: 0.0–1.0, насколько ты уверен что это релевантный грант для visual artist
- opportunity_quality: "high" / "medium" / "low" / "reject"
  high = деньги напрямую художнику, понятная заявка, visual art (живопись/скульптура/инсталляция/видеоарт и т.д.)
  medium = резиденция / travel support / fiscal sponsor нужен / широкий профиль с visual art включительно
  low = узкая география / nomination-only / unclear funding
  reject = платная ловушка / строго фотография / строго дизайн / строго кино / строго музыка / не для visual artists

Верни ТОЛЬКО валидный JSON-массив. Без markdown, без пояснений.
Если грантов нет — верни пустой массив [].
"""

GRANT_SCHEMA_EXAMPLE = {
    "title": "",
    "organization": "",
    "grant_type": "",
    "discipline": [],
    "is_visual_art_relevant": True,
    "is_contemporary_art_relevant": True,
    "applicant_type": [],
    "eligible_residency": [],
    "eligible_nationality": [],
    "amount": "",
    "currency": "",
    "deadline": None,
    "deadline_raw": "",
    "application_fee": "",
    "is_paid_opportunity": False,
    "requires_fiscal_sponsor": False,
    "open_to_international_applicants": None,
    "url": "",
    "source_url": "",
    "summary": "",
    "why_relevant": "",
    "opportunity_quality": "medium",
    "confidence": 0.8,
}


def _detect_llm_config() -> dict:
    """
    Автоматически определяет доступный LLM backend.
    Приоритет:
    1. Явный LLM_PROVIDER=openclaw в .env
    2. Явный LLM_API_KEY в .env
    3. EXME / Agent Manager — ключи в ~/.agent-manager/.env
    4. OpenClaw — если бинарник найден в PATH
    """
    provider = os.environ.get("LLM_PROVIDER", "").lower()
    api_key = os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "claude-haiku-4-5")

    # 1. Явно задан openclaw
    if provider == "openclaw":
        return {"backend": "openclaw"}

    # 2. Явно задан API-ключ в .env
    if api_key and provider in ("anthropic", "openai", ""):
        return {
            "backend": provider or "anthropic",
            "api_key": api_key,
            "model": model,
        }

    # 3. EXME / Agent Manager — ищем ключи в ~/.agent-manager/.env
    agent_manager_env = os.path.expanduser("~/.agent-manager/.env")
    if os.path.exists(agent_manager_env):
        exme_vars = {}
        for line in open(agent_manager_env).read().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                exme_vars[k.strip()] = v.strip()

        # EXME использует Anthropic через свой gateway
        if exme_vars.get("ANTHROPIC_API_KEY"):
            cfg = {
                "backend": "anthropic",
                "api_key": exme_vars["ANTHROPIC_API_KEY"],
                "model": model,
            }
            # Подставляем base_url если есть (EXME gateway)
            if exme_vars.get("ANTHROPIC_BASE_URL"):
                cfg["base_url"] = exme_vars["ANTHROPIC_BASE_URL"]
            return cfg

        if exme_vars.get("OPENAI_API_KEY"):
            cfg = {
                "backend": "openai",
                "api_key": exme_vars["OPENAI_API_KEY"],
                "model": os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            }
            if exme_vars.get("STT_OPENAI_BASE_URL") or exme_vars.get("OPENAI_BASE_URL"):
                cfg["base_url"] = exme_vars.get("STT_OPENAI_BASE_URL") or exme_vars.get("OPENAI_BASE_URL")
            return cfg

    # 4. Openclaw — если найден в PATH
    import shutil
    openclaw_bin = os.environ.get("OPENCLAW_BIN", "openclaw")
    if shutil.which(openclaw_bin):
        return {"backend": "openclaw", "bin": openclaw_bin}

    raise RuntimeError(
        "Не найден ни один LLM backend. Задай LLM_API_KEY в .env "
        "или установи openclaw, или используй EXME Agent Manager."
    )


def call_llm(text: str, source_url: str) -> list[dict]:
    """
    Отправляет текст на нормализацию.
    Автоматически определяет доступный LLM backend:
    openclaw CLI → LLM_API_KEY в .env → EXME/Agent Manager → openclaw в PATH.
    """
    from datetime import date
    cfg = _detect_llm_config()
    user_msg = f"CURRENT_DATE: {date.today().isoformat()}\nSOURCE_URL: {source_url}\n\n---\n\n{text[:12000]}"

    if cfg["backend"] == "openclaw":
        return _call_openclaw(user_msg, cfg.get("bin", "openclaw"))
    elif cfg["backend"] == "anthropic":
        return _call_anthropic(cfg["api_key"], cfg["model"], user_msg, cfg.get("base_url"))
    elif cfg["backend"] == "openai":
        return _call_openai(cfg["api_key"], cfg["model"], user_msg, cfg.get("base_url"))
    else:
        raise RuntimeError(f"Неизвестный LLM backend: {cfg['backend']}")


def _call_openclaw(user_msg: str, openclaw_bin: str = "openclaw") -> list[dict]:
    """
    Вызывает openclaw agent CLI, получает JSON в ответе.
    OpenClaw сам использует настроенного агента с его моделью.
    """
    import subprocess
    import shlex

    full_prompt = SYSTEM_PROMPT + "\n\n" + user_msg

    result = subprocess.run(
        [openclaw_bin, "agent", "--message", full_prompt, "--no-stream"],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        raise RuntimeError(f"openclaw agent error: {result.stderr[:500]}")

    raw = result.stdout.strip()
    return _parse_json(raw)


def _call_anthropic(api_key: str, model: str, user_msg: str, base_url: str = None) -> list[dict]:
    import anthropic

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    client = anthropic.Anthropic(**kwargs)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = response.content[0].text.strip()
    return _parse_json(raw)


def _call_openai(api_key: str, model: str, user_msg: str, base_url: str = None) -> list[dict]:
    import openai

    kwargs = {"api_key": api_key}
    if base_url:
        kwargs["base_url"] = base_url

    client = openai.OpenAI(**kwargs)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    raw = response.choices[0].message.content.strip()
    return _parse_json(raw)


def _parse_json(raw: str) -> list[dict]:
    """Парсит JSON из ответа LLM, терпимо к мусору вокруг."""
    # Убираем markdown-блоки если LLM вернул ```json ... ```
    if "```" in raw:
        import re
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if match:
            raw = match.group(1).strip()

    parsed = json.loads(raw)

    # LLM иногда оборачивает в объект {"grants": [...]}
    if isinstance(parsed, dict):
        for key in ("grants", "opportunities", "results", "items"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        return [parsed]

    return parsed if isinstance(parsed, list) else []


def make_canonical_key(org: str, title: str, deadline: str, url: str) -> str:
    """Детерминированный ключ для дедупликации."""
    raw = f"{org.lower().strip()}|{title.lower().strip()}|{deadline or ''}|{url or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]
