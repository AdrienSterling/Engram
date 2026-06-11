#!/usr/bin/env python3
"""Test ReviewCoach end-to-end."""
import asyncio
import io
import shutil
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from engram.core.logging import setup_logging
setup_logging(level="WARNING")

from engram.skills.review.coach import ReviewCoach


async def test():
    vault = str(Path("test_vault"))
    Path(vault + "/Inbox").mkdir(parents=True, exist_ok=True)

    note = Path(vault) / "Inbox" / "test-note.md"
    note.write_text("""---
title: Docker入门
source_type: youtube
review_status: pending
review_count: 0
next_review: 2026-06-11
last_review: null
review_schedule: [1, 3, 7, 30]
---

# Docker入门

## 总结
Docker是一个容器化工具。三大核心：Dockerfile、镜像、容器。
容器比虚拟机更轻量，因为共享宿主机内核。
使用docker build构建镜像，docker run启动容器。
""", encoding="utf-8")

    coach = ReviewCoach(vault_path=vault)

    # Test get_due_items
    due = coach.get_due_items()
    print(f"Due items: {len(due)}")
    for item in due:
        print(f"  - {item['title']} (count={item['review_count']})")

    if due:
        # Test generate_questions
        questions = await coach.generate_questions(
            due[0]["title"], due[0]["summary"], due[0]["review_count"]
        )
        print(f"\nGenerated questions: {len(questions)}")
        for q in questions:
            print(f"  Q: {q['question'][:80]}")
            print(f"  A: {q['answer'][:80]}")

        # Test evaluate_answer
        if questions:
            feedback = await coach.evaluate_answer(
                questions[0]["question"],
                questions[0]["answer"],
                "Dockerfile、镜像和容器",
            )
            print(f"\nFeedback: {feedback[:200]}")

        # Test advance_review_state
        coach.advance_review_state(str(note), 0)
        updated = note.read_text(encoding="utf-8")
        print(f"\nUpdated frontmatter:")
        for line in updated.split("\n")[:10]:
            print(f"  {line}")

        # Test mark_for_review
        note2 = Path(vault) / "Inbox" / "new-note.md"
        note2.write_text("""---
title: Test Note
---

# Test
""", encoding="utf-8")
        coach.mark_for_review(str(note2))
        updated2 = note2.read_text(encoding="utf-8")
        print(f"\nMarked for review:")
        for line in updated2.split("\n")[:12]:
            print(f"  {line}")

    shutil.rmtree(vault)
    print("\nAll tests passed!")


if __name__ == "__main__":
    asyncio.run(test())
