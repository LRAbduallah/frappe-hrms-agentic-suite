"""Production conversation-window settings for long-running HR agents."""

from strands.agent.conversation_manager import SlidingWindowConversationManager

from app.config import settings


def conversation_manager(*, specialist: bool = False) -> SlidingWindowConversationManager:
    """Keep a rolling window and truncate large tool results before they bloat the prompt."""
    return SlidingWindowConversationManager(
        window_size=(
            settings.specialist_window_size if specialist else settings.conversation_window_size
        ),
        should_truncate_results=True,
        per_turn=True,
    )
