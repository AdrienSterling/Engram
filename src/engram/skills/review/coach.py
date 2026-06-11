"""Review coach skill — generates questions, evaluates answers, manages review state."""

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import yaml

from engram.llm import get_llm

from .prompts import ANSWER_EVALUATION, QUESTION_GENERATION, REVIEW_SUMMARY

logger = logging.getLogger(__name__)

REVIEW_INTERVALS = [1, 3, 7, 30]

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


class ReviewCoach:
    """Manages spaced-repetition review of saved notes."""

    def __init__(self, vault_path: str):
        self.vault_path = Path(vault_path)
        self.inbox_path = self.vault_path / "Inbox"
        self.llm = get_llm()

    def _parse_frontmatter(self, content: str) -> dict:
        """Extract YAML frontmatter from markdown content."""
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}
        try:
            return yaml.safe_load(match.group(1)) or {}
        except yaml.YAMLError:
            return {}

    def _update_frontmatter(self, filepath: Path, updates: dict):
        """Update YAML frontmatter fields in a markdown file."""
        content = filepath.read_text(encoding="utf-8")

        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            return

        fm = yaml.safe_load(match.group(1)) or {}
        fm.update(updates)

        new_fm = yaml.dump(fm, allow_unicode=True, default_flow_style=False).strip()
        new_content = f"---\n{new_fm}\n---\n" + content[match.end() :]

        filepath.write_text(new_content, encoding="utf-8")

    def get_due_items(self) -> list[dict]:
        """
        Scan vault inbox for notes due for review.

        Returns:
            List of dicts with: title, filepath, summary, review_count, content
        """
        due_items = []
        today = datetime.now().date()

        if not self.inbox_path.exists():
            return due_items

        for filepath in self.inbox_path.glob("*.md"):
            if filepath.name == "临时收集箱.md":
                continue

            content = filepath.read_text(encoding="utf-8")
            fm = self._parse_frontmatter(content)

            next_review_str = fm.get("next_review")
            if not next_review_str:
                continue

            try:
                next_review = datetime.fromisoformat(str(next_review_str)).date()
            except (ValueError, TypeError):
                continue

            if next_review <= today:
                summary = self._extract_summary(content)
                due_items.append(
                    {
                        "title": fm.get("title", filepath.stem),
                        "filepath": str(filepath),
                        "summary": summary,
                        "review_count": fm.get("review_count", 0),
                        "review_status": fm.get("review_status", "pending"),
                    }
                )

        due_items.sort(key=lambda x: x["review_count"])
        return due_items

    def _extract_summary(self, content: str) -> str:
        """Extract the summary section from a note."""
        lines = content.split("\n")
        in_summary = False
        summary_lines = []

        for line in lines:
            if line.startswith("## 总结"):
                in_summary = True
                continue
            if in_summary:
                if line.startswith("## "):
                    break
                summary_lines.append(line)

        return "\n".join(summary_lines).strip() or content[:2000]

    async def generate_questions(self, title: str, summary: str, review_count: int) -> list[dict]:
        """Generate review questions based on the content."""
        prompt = QUESTION_GENERATION.format(title=title, summary=summary)

        response = await self.llm.chat(
            [type("Message", (), {"role": "user", "content": prompt})()],
            temperature=0.7,
            max_tokens=2048,
        )

        return self._parse_questions(response.content)

    def _parse_questions(self, text: str) -> list[dict]:
        """Parse Q&A pairs from LLM response."""
        questions = []
        current_q = None

        for line in text.strip().split("\n"):
            line = line.strip()
            if line.startswith("Q: ") or line.startswith("Q："):
                if current_q:
                    questions.append(current_q)
                current_q = {"question": line[3:], "answer": ""}
            elif (line.startswith("A: ") or line.startswith("A：")) and current_q:
                current_q["answer"] = line[3:]

        if current_q:
            questions.append(current_q)

        return questions

    async def evaluate_answer(self, question: str, expected_answer: str, user_answer: str) -> str:
        """Evaluate user's answer and provide feedback."""
        prompt = ANSWER_EVALUATION.format(
            question=question,
            expected_answer=expected_answer,
            user_answer=user_answer,
        )

        response = await self.llm.chat(
            [type("Message", (), {"role": "user", "content": prompt})()],
            temperature=0.5,
            max_tokens=512,
        )

        return response.content.strip()

    async def generate_review_summary(self, title: str, qa_pairs: str) -> str:
        """Generate a review session summary."""
        prompt = REVIEW_SUMMARY.format(title=title, qa_pairs=qa_pairs)

        response = await self.llm.chat(
            [type("Message", (), {"role": "user", "content": prompt})()],
            temperature=0.5,
            max_tokens=512,
        )

        return response.content.strip()

    def get_next_interval(self, review_count: int) -> int:
        """Get days until next review based on review count."""
        if review_count < len(REVIEW_INTERVALS):
            return REVIEW_INTERVALS[review_count]
        return REVIEW_INTERVALS[-1]

    def advance_review_state(self, filepath: str, review_count: int):
        """Update frontmatter after a review session."""
        next_interval = self.get_next_interval(review_count + 1)
        next_date = (datetime.now() + timedelta(days=next_interval)).date().isoformat()

        new_count = review_count + 1
        is_mastered = new_count >= len(REVIEW_INTERVALS)

        updates = {
            "review_count": new_count,
            "next_review": next_date,
            "last_review": datetime.now().isoformat(),
            "review_status": "mastered" if is_mastered else "reviewing",
        }

        self._update_frontmatter(Path(filepath), updates)

    def mark_for_review(self, filepath: str):
        """Initialize review state for a newly saved note."""
        next_date = (datetime.now() + timedelta(days=1)).date().isoformat()
        updates = {
            "review_status": "pending",
            "review_count": 0,
            "next_review": next_date,
            "last_review": None,
            "review_schedule": REVIEW_INTERVALS,
        }
        self._update_frontmatter(Path(filepath), updates)
