# Copyright (C) 2018 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
Add people_profiles table

Create Date: 2018-05-16 13:26:42.639428
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = '5d0fa1d7d55d'
down_revision = 'b1cb47a3bb3b'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.create_table('people_profiles',
  sa.Column('id', sa.Integer(), nullable=False),
  sa.Column('person_id', sa.Integer(), nullable=False),
  sa.Column('last_seen_whats_new', sa.DateTime(), nullable=False),
  sa.ForeignKeyConstraint(['person_id'], ['people.id'], ondelete="CASCADE"),
  sa.PrimaryKeyConstraint('id')
  )

  op.execute("""
      INSERT INTO `people_profiles` (`person_id`, `last_seen_whats_new`)
      SELECT id, NOW() - INTERVAL 14 DAY
      FROM `people`
  """)

def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute(" TRUNCATE TABLE `people_profiles`")
  op.drop_table('people_profiles')
