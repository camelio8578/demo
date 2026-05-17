"""
CopyGenerator: produce platform-specific marketing copy (hook, title,
caption, hashtags) for a short-form video clip.

Works fully offline via the rule-based fallback; LLM generation via
OpenAI or Anthropic is optional.
"""
from __future__ import annotations

import re
from typing import Any

import structlog

log = structlog.get_logger(__name__)

_PROMPT_VERSION = "1.0"


class CopyGenerator:
    """Generate hooks, titles, captions, and hashtags for short-form clips."""

    PLATFORM_SPECS: dict[str, dict[str, Any]] = {
        "tiktok": {
            "max_caption": 2200,
            "max_hashtags": 20,
            "hook_priority": True,
        },
        "instagram": {
            "max_caption": 2200,
            "max_hashtags": 30,
            "hook_priority": True,
        },
        "youtube": {
            "max_caption": 5000,
            "max_hashtags": 15,
            "hook_priority": False,
        },
        "twitter": {
            "max_caption": 280,
            "max_hashtags": 3,
            "hook_priority": True,
        },
        "linkedin": {
            "max_caption": 3000,
            "max_hashtags": 5,
            "hook_priority": False,
        },
    }

    # Sentence-ending punctuation pattern
    _SENTENCE_END = re.compile(r"[.!?]\s+")

    def generate_copy(
        self,
        segment_text: str,
        platform: str,
        creator_name: str = "",
        llm_provider: str = "none",
    ) -> dict:
        """
        Generate copy for the given platform.

        Args:
            segment_text: Transcript text for the candidate clip.
            platform: One of tiktok | instagram | youtube | twitter | linkedin.
            creator_name: Optional creator name for personalisation.
            llm_provider: "openai" | "anthropic" | "none".

        Returns:
            dict with keys: hook, title, caption, hashtags, llm_model_used,
            prompt_version.
        """
        platform = platform.lower()
        if platform not in self.PLATFORM_SPECS:
            log.warning("unknown_platform", platform=platform, fallback="tiktok")
            platform = "tiktok"

        result: dict | None = None

        if llm_provider not in ("none", ""):
            try:
                result = self._generate_with_llm(segment_text, platform, llm_provider)
            except Exception as exc:
                log.warning(
                    "llm_copy_failed",
                    provider=llm_provider,
                    error=str(exc),
                    fallback="rule_based",
                )

        if result is None:
            result = self._generate_rule_based(segment_text, platform)
            result["llm_model_used"] = None

        result["prompt_version"] = _PROMPT_VERSION
        log.info(
            "copy_generated",
            platform=platform,
            llm_model_used=result.get("llm_model_used"),
            hashtag_count=len(result.get("hashtags", [])),
        )
        return result

    def _generate_with_llm(
        self, segment_text: str, platform: str, provider: str
    ) -> dict:
        """Call OpenAI or Anthropic to generate copy."""
        specs = self.PLATFORM_SPECS.get(platform, {})
        max_caption = specs.get("max_caption", 2200)
        max_hashtags = specs.get("max_hashtags", 20)
        hook_priority = specs.get("hook_priority", True)

        prompt = (
            f"You are a social media copywriter expert for {platform}.\n"
            f"Given this video transcript excerpt, create:\n"
            f"1. A compelling hook (1-2 sentences, {'' if hook_priority else 'not '}hook-focused).\n"
            f"2. A title (under 100 characters).\n"
            f"3. A caption (max {max_caption} characters).\n"
            f"4. Up to {max_hashtags} relevant hashtags (without the # symbol, as a comma-separated list).\n\n"
            f"Transcript:\n{segment_text}\n\n"
            f"Respond with exactly this JSON structure:\n"
            '{"hook": "...", "title": "...", "caption": "...", "hashtags": ["...", "..."]}'
        )

        if provider == "openai":
            return self._call_openai(prompt)
        elif provider == "anthropic":
            return self._call_anthropic(prompt)
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")

    def _call_openai(self, prompt: str) -> dict:
        import json
        import os

        import openai  # type: ignore

        client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=1024,
        )
        text = response.choices[0].message.content or "{}"
        data = json.loads(text)
        data["llm_model_used"] = "gpt-4o-mini"
        return data

    def _call_anthropic(self, prompt: str) -> dict:
        import json
        import os

        import anthropic as anthropic_sdk  # type: ignore

        client = anthropic_sdk.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        message = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = message.content[0].text if message.content else "{}"
        data = json.loads(text)
        data["llm_model_used"] = "claude-3-haiku-20240307"
        return data

    def _generate_rule_based(self, segment_text: str, platform: str) -> dict:
        """
        Fallback rule-based copy generation.

        Hook = first sentence.
        Caption = first 3 sentences, truncated to platform max_caption.
        Title = first sentence, truncated to 100 chars.
        Hashtags = extracted meaningful nouns, capped to platform max.
        """
        specs = self.PLATFORM_SPECS.get(platform, {})
        max_caption = specs.get("max_caption", 2200)
        max_hashtags = specs.get("max_hashtags", 20)

        sentences = self._split_sentences(segment_text)

        hook = sentences[0] if sentences else segment_text[:150]
        title = (sentences[0] if sentences else segment_text)[:100]
        caption_sentences = sentences[:3]
        caption = " ".join(caption_sentences)
        if len(caption) > max_caption:
            caption = caption[: max_caption - 3] + "..."

        hashtags = self._extract_hashtags(segment_text, platform)

        return {
            "hook": hook,
            "title": title,
            "caption": caption,
            "hashtags": hashtags[:max_hashtags],
        }

    def _split_sentences(self, text: str) -> list[str]:
        """Split text into sentences on .!? boundaries."""
        # Split on sentence endings followed by whitespace or end of string
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]

    def _extract_hashtags(self, text: str, platform: str) -> list[str]:
        """
        Extract candidate hashtags from the transcript text.

        Keeps only meaningful words (length >= 4, not stopwords).
        Returns de-duped list of lowercase, alphanumeric hashtag tokens.
        """
        specs = self.PLATFORM_SPECS.get(platform, {})
        max_hashtags = specs.get("max_hashtags", 20)

        _STOPWORDS = frozenset([
            "this", "that", "with", "have", "from", "they", "will",
            "been", "were", "what", "when", "where", "which", "while",
            "your", "their", "there", "here", "about", "would", "could",
            "should", "going", "just", "also", "like", "know", "need",
            "some", "more", "than", "then", "them", "these", "those",
            "into", "onto", "over", "very", "even", "most", "many",
            "only", "back", "come", "make", "take", "want", "time",
        ])

        words = re.findall(r"[a-zA-Z]+", text)
        seen: set[str] = set()
        hashtags: list[str] = []

        for word in words:
            lower = word.lower()
            if (
                len(lower) >= 4
                and lower not in _STOPWORDS
                and lower not in seen
            ):
                seen.add(lower)
                hashtags.append(lower)
            if len(hashtags) >= max_hashtags:
                break

        return hashtags
