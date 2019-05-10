# Copyright (C) 2019 Google Inc.
# Licensed under http://www.apache.org/licenses/LICENSE-2.0 <see LICENSE file>

"""Functionality for caching db data for GGRC objects."""
from collections import defaultdict
import logging

import sqlalchemy as sa

from ggrc import db
from ggrc.models import all_models
from ggrc.utils import benchmark
from ggrc.utils import helpers


logger = logging.getLogger(__name__)


@helpers.cached
def audit_snapshot_slugs_cache(obj_ids):
  """Cached property of mapped to audit snapshots.

  Args:
      obj_ids: List of ids of Audits with mapped Snapshots.

  Returns:
      Dict with mapping of Audit id to Snapshot slug.
        Format: {object_id: {snapshot object type: {snapshot slugs}}.
  """
  # pylint: disable=protected-access
  with benchmark("Create cache of Audit snapshots"):
    snapshots = defaultdict(lambda: defaultdict(set))
    query = db.session.query(
        all_models.Revision.resource_slug,
        all_models.Snapshot.parent_id,
        all_models.Snapshot.child_type,
    ).join(all_models.Snapshot).filter(
        all_models.Snapshot.parent_type == all_models.Audit.__name__,
        all_models.Snapshot.parent_id.in_(obj_ids),
    )
    for slug, parent_id, child_type in query:
      snapshots[parent_id][child_type].add(slug)
    return snapshots


@helpers.cached
def related_snapshot_slugs_cache(obj_class, obj_ids):
  """Get snapshot slugs mapped to imported objects by relationship.

  Args:
      obj_class: Class of objects with mapped Snapshots.
      obj_ids: List of ids of objects with mapped Snapshots.

  Returns:
      Dict with mapping of object id to Snapshot slug.
        Format: {object_id: {Snapshot object type: {Snapshot slugs}}.
  """
  if obj_class not in all_models.all_models:
    return None

  with benchmark("Create cache of snapshots related to {}".format(
      obj_class.__name__
  )):
    snapshots = defaultdict(lambda: defaultdict(set))
    if not obj_ids:
      return snapshots

    query = """
        SELECT {base_table}.id,
                revisions.resource_type,
                revisions.resource_slug
        FROM {base_table}, relationships, snapshots, revisions
        WHERE relationships.source_id = {base_table}.id
            AND relationships.source_type = '{base_name}'
            AND relationships.destination_id = snapshots.id
            AND relationships.destination_type = 'Snapshot'
                AND revisions.id = snapshots.revision_id
        AND {base_table}.id IN :object_ids
        UNION ALL
        SELECT {base_table}.id,
                revisions.resource_type,
                revisions.resource_slug
        FROM {base_table}, relationships, snapshots, revisions
        WHERE relationships.source_id = snapshots.id
            AND relationships.source_type = 'Snapshot'
            AND relationships.destination_id = {base_table}.id
            AND relationships.destination_type = '{base_name}'
                AND revisions.id = snapshots.revision_id
        AND {base_table}.id IN :object_ids;
    """.format(
        base_table=obj_class.__table__.name,
        base_name=obj_class.__name__,
    )
    mapped_revs = db.session.execute(
        sa.text(query),
        {"object_ids": obj_ids}
    ).fetchall()

    for object_id, snapshot_obj_type, snapshot_obj_slug in mapped_revs:
      if not snapshot_obj_slug:
        logger.warning(
            "Snapshot for object %s with ID=%s contains invalid object slug. "
            "The value will be ignored.",
            snapshot_obj_type,
            object_id,
        )
        continue
      snapshots[object_id][snapshot_obj_type].add(snapshot_obj_slug)

    return snapshots


# pylint: disable=invalid-name
def related_cads_for_object_type(class_name, template_ids=()):
  """
    Collect GCADs and LCAs those related to object
    with possible additional filtering by assessment_templates ids.

    Args:
        class_name: string - underscored class name
        template_ids: tuple of ids of assessment_templates.

    Returns:
        List of CADs
    """
  with benchmark("Create cache of CADs related to Assessment"):
    cad = all_models.CustomAttributeDefinition
    cads = list(cad.query.filter(
        cad.definition_type == class_name,
        cad.definition_id.is_(None),
    ))

    if template_ids:
      cads.extend(cad.query.filter(
          cad.definition_type == 'assessment_template',
          cad.definition_id.in_(template_ids),
      ))

    return cads
