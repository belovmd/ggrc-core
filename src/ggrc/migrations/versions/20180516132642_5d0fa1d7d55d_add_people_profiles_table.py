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
down_revision = '8c3900f21613'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.create_table(
      'people_profiles',
      sa.Column('id', sa.Integer(), nullable=False),
      sa.Column('person_id', sa.Integer(), nullable=True),
      sa.Column('last_seen_whats_new', sa.DateTime(), nullable=True),
      sa.Column('updated_at', sa.DateTime(), nullable=False),
      sa.Column('modified_by_id', sa.Integer(), nullable=True),
      sa.Column('created_at', sa.DateTime(), nullable=False),
      sa.Column('context_id', sa.Integer(), nullable=True),
      sa.ForeignKeyConstraint(['context_id'], ['contexts.id']),
      sa.ForeignKeyConstraint(
          ['person_id'],
          ['people.id'],
          ondelete="CASCADE"),
      sa.PrimaryKeyConstraint('id'),
      sa.UniqueConstraint('person_id'))

  op.create_index(
      'fk_people_profiles_contexts',
      'people_profiles',
      ['context_id'],
      unique=False)
  op.create_index(
      'ix_people_profiles_updated_at',
      'people_profiles',
      ['updated_at'],
      unique=False)
  op.execute("""
      INSERT INTO `people_profiles`
          (`person_id`, `last_seen_whats_new`, `created_at`, `updated_at`)
      SELECT `id`, NOW() - INTERVAL 14 DAY, NOW(), NOW()
      FROM `people`
  """)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  op.execute(" TRUNCATE TABLE `people_profiles`")
  op.drop_index('ix_people_profiles_updated_at', table_name='people_profiles')
  op.drop_index('fk_people_profiles_contexts', table_name='people_profiles')
  op.drop_table('people_profiles')
