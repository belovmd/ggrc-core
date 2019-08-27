# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""
add external name for CAD

Create Date: 2019-09-14 14:14:56.986452
"""
# disable Invalid constant name pylint warning for mandatory Alembic variables.
# pylint: disable=invalid-name


from alembic import op


# revision identifiers, used by Alembic.
revision = '75ad21f0622b'
down_revision = '8937c6e26f00'


def upgrade():
  """Upgrade database schema and/or data, creating a new revision."""
  op.execute("""
    ALTER TABLE `external_custom_attribute_definitions`
    ADD `external_name` VARCHAR(255) DEFAULT NULL,
    ADD CONSTRAINT `uq_external_name`
    UNIQUE (`external_name`)
  """)


def downgrade():
  """Downgrade database schema and/or data back to the previous revision."""
  raise NotImplementedError("Downgrade is not supported")
