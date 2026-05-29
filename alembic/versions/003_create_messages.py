from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, Sequence[str], None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE messages (
            id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID        NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            role       TEXT        NOT NULL,
            content    TEXT        NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );
        """
    )
    op.execute("CREATE INDEX ix_messages_session_id ON messages (session_id, created_at ASC);")


def downgrade() -> None:
    op.execute("DROP TABLE messages;")
