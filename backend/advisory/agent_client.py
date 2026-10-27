"""Privacy-minimizing, fail-safe client for the isolated agent service."""

from __future__ import annotations

from typing import Any

import httpx


class AgentClient:
    def __init__(self, base_url: str, service_token: str, timeout_seconds: float = 10.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        if timeout_seconds <= 0 or timeout_seconds > 10:
            raise ValueError("Agent timeout must be greater than 0 and no more than 10 seconds")
        self._base_url = base_url.rstrip("/")
        self._headers = {"X-Service-Token": service_token}
        self._timeout = timeout_seconds
        self._transport = transport

    @staticmethod
    def opportunity_payload(skills: list[str], interests: list[str], opportunities: list[dict[str, Any]]) -> dict[str, Any]:
        """Build the allowlisted structured payload; never pass user/profile free text."""
        return {
            "student": {"skills": list(skills), "interests": list(interests)},
            "opportunities": [{
                "id": item["id"], "domain": item.get("domain", ""),
                "required_skills": list(item.get("required_skills", [])),
            } for item in opportunities],
        }

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as client:
                response = await client.post(f"{self._base_url}{path}", json=payload, headers=self._headers)
                response.raise_for_status()
                body = response.json()
                return body if isinstance(body, dict) and isinstance(body.get("items"), list) else None
        except (httpx.HTTPError, ValueError):
            return None

    async def match_opportunities(self, skills: list[str], interests: list[str],
                                  opportunities: list[dict[str, Any]]) -> dict[str, Any] | None:
        return await self._post("/internal/v1/match/opportunities",
                                self.opportunity_payload(skills, interests, opportunities))

    async def recommendations_or_unavailable(self, skills: list[str], interests: list[str],
                                             opportunities: list[dict[str, Any]]) -> dict[str, Any]:
        result = await self.match_opportunities(skills, interests, opportunities)
        return {"available": True, "items": result["items"]} if result is not None else {
            "available": False, "items": [], "message": "Recommendations are not available right now."}
