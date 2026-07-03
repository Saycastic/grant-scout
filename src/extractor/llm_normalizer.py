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

Правила:
- Извлекай ТОЛЬКО возможности с реальным финансированием (гранты, стипендии, fellowships, оплачиваемые резиденции)
- НЕ включай: платные конкурсы без грантовой составляющей, выставки без денег, jobs, стажировки без оплаты
- Если дедлайн не указан явно — пиши null
- amount пиши как строку: "$5,000", "up to €10,000", "varies", "undisclosed"
- summary_ru и why_relevant_ru — на русском, кратко (2-3 предложения)
- confidence: 0.0–1.0, насколько ты уверен что это релевантный грант для visual artist
- opportunity_quality: "high" / "medium" / "low" / "reject"
  high = деньги напрямую художнику, понятная заявка, visual art
  medium = резиденция / travel support / fiscal sponsor нужен
  low = узкая география / nomination-only / unclear funding
  reject = платная ловушка / не для visual artists

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
    "summary_ru": "",
    "why_relevant_ru": "",
    "opportunity_quality": "medium",
    "confidence": 0.8,
}


def call_llm(text: str, source_url: str) -> list[dict]:
    """
    Отправляет текст на нормализацию.
    По умолчанию — через OpenClaw agent CLI (не нужен отдельный API-ключ).
    Fallback — прямой вызов Anthropic/OpenAI если LLM_API_KEY задан.
    """
    api_key = os.environ.get("LLM_API_KEY", "")
    user_msg = f"URL источника: {source_url}\n\n---\n\n{text[:12000]}"

    if api_key:
        # Прямой вызов если ключ есть
        provider = os.environ.get("LLM_PROVIDER", "anthropic")
        model = os.environ.get("LLM_MODEL", "claude-haiku-4-5")
        if provider == "anthropic":
            return _call_anthropic(api_key, model, user_msg)
        else:
            return _call_openai(api_key, model, user_msg)
    else:
        # Через OpenClaw agent — никакого отдельного ключа не нужно
        return _call_openclaw(user_msg)


def _call_openclaw(user_msg: str) -> list[dict]:
    """
    Вызывает openclaw agent CLI, получает JSON в ответе.
    OpenClaw сам использует настроенного агента с его моделью.
    """
    import subprocess
    import shlex

    full_prompt = SYSTEM_PROMPT + "\n\n" + user_msg

    openclaw_bin = os.environ.get("OPENCLAW_BIN", "openclaw")

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


def _call_anthropic(api_key: str, model: str, user_msg: str) -> list[dict]:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = response.content[0].text.strip()
    return _parse_json(raw)


def _call_openai(api_key: str, model: str, user_msg: str) -> list[dict]:
    import openai

    client = openai.OpenAI(api_key=api_key)
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
