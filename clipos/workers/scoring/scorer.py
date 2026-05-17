"""
Core clip scoring module for ClipOS.

Scores transcript window candidates across multiple dimensions and returns
a weighted total_score used to rank clips.
"""
from __future__ import annotations

import re
import math
from typing import TYPE_CHECKING

import structlog

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Positive / negative word lists used as VADER fallback
# ---------------------------------------------------------------------------
_POSITIVE_WORDS = frozenset([
    "good", "great", "excellent", "amazing", "awesome", "fantastic",
    "wonderful", "best", "better", "love", "like", "enjoy", "success",
    "win", "winning", "growth", "improve", "improvement", "benefit",
    "helpful", "useful", "effective", "powerful", "strong", "clear",
    "simple", "easy", "free", "gain", "positive", "happy", "excited",
    "brilliant", "perfect", "outstanding", "superb", "incredible",
    "magnificent", "beautiful", "exceptional", "remarkable", "valuable",
])

_NEGATIVE_WORDS = frozenset([
    "bad", "terrible", "awful", "horrible", "worst", "hate", "dislike",
    "failure", "fail", "loss", "losing", "decline", "weak", "difficult",
    "hard", "problem", "issue", "broken", "wrong", "mistake", "error",
    "poor", "ineffective", "useless", "dangerous", "harmful", "negative",
    "upset", "angry", "sad", "disappointed", "frustrating", "annoying",
])


class ClipScorer:
    """Score transcript window candidates for short-form video clips."""

    DEFAULT_WEIGHTS: dict[str, float] = {
        "speech_density": 0.15,
        "sentiment_score": 0.15,
        "hook_phrase_score": 0.20,
        "pause_burst_score": 0.10,
        "novelty_score": 0.10,
        "completeness_score": 0.10,
        "duration_fit_score": 0.10,
        "risk_flag_score": -0.20,  # penalty — high risk lowers total
        "prior_performance_score": 0.10,
    }

    HOOK_PHRASES: list[str] = [
        "you need to know", "nobody talks about", "most people don't",
        "here's the thing", "the truth is", "stop doing", "biggest mistake",
        "secret to", "how to", "why you", "this is why", "the real reason",
        "i'm going to show you", "what nobody tells you", "game changer",
        "this changed everything", "the problem is", "here's what happens",
        "let me show you", "the key is", "important thing", "critical",
        "you won't believe", "shocking", "actually works", "proven",
    ]

    RISK_KEYWORDS: list[str] = [
        "lawsuit", "illegal", "copyright", "defamation", "confidential",
        "off the record", "don't tell anyone", "not for public",
        "fuck", "shit", "ass", "bitch", "damn", "crap",
    ]

    # Ideal speech rate in words-per-second for engaging short-form content
    _IDEAL_WPS: float = 2.5

    def score_candidate(
        self,
        segment_text: str,
        start_time: float,
        end_time: float,
        all_segments: list[dict],
        audio_path: str | None = None,
        weights: dict | None = None,
        creator_clips_performance: list[float] | None = None,
    ) -> dict:
        """
        Score a candidate clip window and return all dimension scores plus total.

        Args:
            segment_text: Concatenated transcript text for the window.
            start_time: Window start in seconds.
            end_time: Window end in seconds.
            all_segments: Full list of segment dicts for the source video
                (each with at least a "text" key).
            audio_path: Optional path to audio file (reserved for future use).
            weights: Override DEFAULT_WEIGHTS if provided.
            creator_clips_performance: Historical performance scores for this
                creator. Used in prior_performance_score.

        Returns:
            dict with individual dimension scores (0.0–1.0 each) and
            ``total_score`` (0.0–1.0 after weighting).
        """
        weights = weights or self.DEFAULT_WEIGHTS
        duration = max(end_time - start_time, 0.001)

        all_segment_texts = [s.get("text", "") for s in all_segments]

        speech_density = self._speech_density_score(segment_text, duration)
        sentiment = self._sentiment_score(segment_text)
        hook_phrase = self._hook_phrase_score(segment_text)
        # pause_burst is computed from gap analysis when segments are available
        pause_burst = self._pause_burst_score(start_time, end_time, all_segments)
        novelty = self._novelty_score(segment_text, all_segment_texts)
        completeness = self._completeness_score(segment_text)
        duration_fit = self._duration_fit_score(duration)
        risk_flag = self._risk_flag_score(segment_text)
        prior_perf = self._prior_performance_score(creator_clips_performance or [])

        # Weighted sum — risk_flag_score has a negative weight so a high raw
        # risk value lowers the total.
        total_score = (
            weights.get("speech_density", 0) * speech_density
            + weights.get("sentiment_score", 0) * sentiment
            + weights.get("hook_phrase_score", 0) * hook_phrase
            + weights.get("pause_burst_score", 0) * pause_burst
            + weights.get("novelty_score", 0) * novelty
            + weights.get("completeness_score", 0) * completeness
            + weights.get("duration_fit_score", 0) * duration_fit
            + weights.get("risk_flag_score", 0) * risk_flag  # weight is negative
            + weights.get("prior_performance_score", 0) * prior_perf
        )

        # Clamp to [0, 1]
        total_score = max(0.0, min(1.0, total_score))

        scores = {
            "speech_density": round(speech_density, 4),
            "sentiment_score": round(sentiment, 4),
            "hook_phrase_score": round(hook_phrase, 4),
            "pause_burst_score": round(pause_burst, 4),
            "novelty_score": round(novelty, 4),
            "completeness_score": round(completeness, 4),
            "duration_fit_score": round(duration_fit, 4),
            "risk_flag_score": round(risk_flag, 4),
            "prior_performance_score": round(prior_perf, 4),
            "total_score": round(total_score, 4),
            "weights_used": weights,
        }

        log.debug(
            "clip_scored",
            start_time=start_time,
            end_time=end_time,
            total_score=total_score,
            risk_flag=risk_flag,
        )

        return scores

    # ------------------------------------------------------------------
    # Individual dimension scorers
    # ------------------------------------------------------------------

    def _speech_density_score(self, text: str, duration: float) -> float:
        """
        Score based on words-per-second compared to ideal rate (~2.5 wps).

        A score of 1.0 means the clip matches the ideal rate exactly.
        Scores decay linearly as the rate diverges, clamped to [0, 1].
        """
        words = len(text.split())
        if duration <= 0:
            return 0.0
        wps = words / duration
        # Normalise: ratio vs ideal, with 1.0 at perfect match
        ratio = wps / self._IDEAL_WPS
        # Penalise both too-slow and too-fast; best score at ratio == 1
        score = 1.0 - abs(ratio - 1.0)
        return max(0.0, min(1.0, score))

    def _sentiment_score(self, text: str) -> float:
        """
        Return positive-sentiment score in [0, 1].

        Tries VADER first; falls back to keyword ratio.
        """
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
            analyzer = SentimentIntensityAnalyzer()
            vs = analyzer.polarity_scores(text)
            # compound is in [-1, 1]; map to [0, 1]
            return (vs["compound"] + 1.0) / 2.0
        except ImportError:
            pass

        # Keyword fallback
        words = re.findall(r"[a-z]+", text.lower())
        if not words:
            return 0.5
        positive = sum(1 for w in words if w in _POSITIVE_WORDS)
        negative = sum(1 for w in words if w in _NEGATIVE_WORDS)
        total = len(words)
        # Net positivity ratio, mapped from [-1, 1] to [0, 1]
        net = (positive - negative) / total
        return max(0.0, min(1.0, (net + 1.0) / 2.0))

    def _hook_phrase_score(self, text: str) -> float:
        """
        Score based on presence of engaging hook phrases.

        One match → 0.5, two → 0.75, three+ → 1.0 (diminishing returns).
        """
        lower = text.lower()
        matches = sum(1 for phrase in self.HOOK_PHRASES if phrase in lower)
        if matches == 0:
            return 0.0
        # Logarithmic scaling capped at 1.0
        score = min(1.0, math.log(matches + 1) / math.log(4))
        return score

    def _pause_burst_score(
        self, start_time: float, end_time: float, all_segments: list[dict]
    ) -> float:
        """
        Score based on rhythm: segments with natural pauses score higher.

        Looks at gap durations between segments within the window.
        A moderate pause ratio (10-20% of window) scores highest.
        Falls back to 0.5 if segment timing data is unavailable.
        """
        window_segments = [
            s for s in all_segments
            if s.get("start_time", -1) >= start_time
            and s.get("end_time", -1) <= end_time
        ]
        if len(window_segments) < 2:
            return 0.5  # neutral when insufficient data

        window_duration = end_time - start_time
        if window_duration <= 0:
            return 0.5

        total_pause = 0.0
        sorted_segs = sorted(window_segments, key=lambda s: s.get("start_time", 0))
        for i in range(1, len(sorted_segs)):
            gap = sorted_segs[i].get("start_time", 0) - sorted_segs[i - 1].get("end_time", 0)
            if gap > 0:
                total_pause += gap

        pause_ratio = total_pause / window_duration
        # Ideal pause ratio: 10-20% of the window
        if 0.10 <= pause_ratio <= 0.20:
            return 1.0
        elif pause_ratio < 0.10:
            return max(0.0, pause_ratio / 0.10)
        else:
            # Too many pauses — penalise beyond 40%
            return max(0.0, 1.0 - (pause_ratio - 0.20) / 0.20)

    def _novelty_score(self, text: str, all_segment_texts: list[str]) -> float:
        """
        Simple TF-IDF-inspired novelty: proportion of unique content.

        Measures how much vocabulary in this segment doesn't appear
        in other segments, normalised to [0, 1].
        """
        segment_words = set(re.findall(r"[a-z]+", text.lower()))
        if not segment_words:
            return 0.0

        # Build corpus vocabulary (excluding this segment)
        corpus_words: set[str] = set()
        for t in all_segment_texts:
            if t != text:
                corpus_words.update(re.findall(r"[a-z]+", t.lower()))

        if not corpus_words:
            return 1.0  # Only segment — fully novel

        unique_to_segment = segment_words - corpus_words
        score = len(unique_to_segment) / len(segment_words)
        return max(0.0, min(1.0, score))

    def _completeness_score(self, text: str) -> float:
        """
        Score based on whether the text ends at a natural sentence boundary.

        Ends with .!? → 1.0
        Ends mid-word (no punctuation) → 0.2
        Ends with comma/semicolon → 0.5
        """
        stripped = text.rstrip()
        if not stripped:
            return 0.0
        last_char = stripped[-1]
        if last_char in ".!?":
            return 1.0
        if last_char in ",;:":
            return 0.5
        # Check if it ends mid-word
        if re.search(r"[a-zA-Z0-9]$", stripped):
            return 0.2
        return 0.3

    def _duration_fit_score(self, duration: float) -> float:
        """
        Score based on clip duration relative to ideal short-form length.

        Ideal: 45–90 s → 1.0
        Acceptable: 30–45 s or 90–120 s → 0.7
        Below 30 s or above 120 s → 0.0–0.4 (linear decay)
        """
        if 45.0 <= duration <= 90.0:
            return 1.0
        if 30.0 <= duration < 45.0:
            # Linear: 0.7 at 30, 1.0 at 45
            return 0.7 + (duration - 30.0) / (45.0 - 30.0) * 0.3
        if 90.0 < duration <= 120.0:
            # Linear: 1.0 at 90, 0.7 at 120
            return 1.0 - (duration - 90.0) / (120.0 - 90.0) * 0.3
        if duration < 30.0:
            # Linear decay from 0.7 at 30s to 0.0 at 0s
            return max(0.0, 0.7 * (duration / 30.0))
        # > 120 s
        return max(0.0, 0.7 - (duration - 120.0) / 60.0 * 0.7)

    def _risk_flag_score(self, text: str) -> float:
        """
        Return raw risk score in [0, 1].

        This is multiplied by the *negative* weight (-0.20) so a high value
        lowers total_score. 0.0 = no risk, 1.0 = high risk.
        """
        lower = text.lower()
        matches = sum(1 for kw in self.RISK_KEYWORDS if kw in lower)
        if matches == 0:
            return 0.0
        # Saturates quickly: 1 match → ~0.5, 2+ → approaches 1.0
        return min(1.0, matches / 2.0)

    def _prior_performance_score(self, creator_clips_performance: list[float]) -> float:
        """
        Estimate expected performance from historical clip scores.

        No history → 0.5 (neutral).
        Otherwise: recent scores are weighted more heavily.
        """
        if not creator_clips_performance:
            return 0.5

        # Exponential weights: more recent = higher weight
        n = len(creator_clips_performance)
        weights = [math.exp(i / n) for i in range(n)]
        total_weight = sum(weights)
        weighted_avg = sum(w * s for w, s in zip(weights, creator_clips_performance)) / total_weight
        return max(0.0, min(1.0, weighted_avg))
