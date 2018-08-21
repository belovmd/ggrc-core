# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
add_due_date_to_issuetracker_issue

Create Date: 2018-08-21 13:19:03.840225
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

from alembic import op


# revision identifiers, used by Alembic.
revision = '1ec05f3e6107'
down_revision = 'b75a3fba7d6e'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute("ALTER TABLE issuetracker_issues ADD due_date DATE NULL")


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute("ALTER TABLE issuetracker_issues DROP due_date")
