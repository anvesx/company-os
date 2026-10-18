"""A read-only view of the brain limited to the areas one run may see. The library needs the `playbooks` area."""
from company_memory import AreaDenied

from .brain_store import LIBRARY


class ScopedBrain:
    def __init__(self, store, area_ids):
        self._store = store
        self.area_ids = frozenset(area_ids)

    def _check(self, area_id):
        if area_id not in self.area_ids:
            raise AreaDenied(f"area {area_id!r} is not allowed here")

    def _areas(self, area_ids):
        if area_ids is None:
            return sorted(self.area_ids)
        areas = [area_ids] if isinstance(area_ids, str) else list(area_ids)
        for area in areas:
            self._check(area)
        return areas

    def get_source(self, source_id):
        source = self._store.get_source(source_id)
        if source is not None:
            self._check(source["area_id"])
        return source

    def source_lines(self, source_id):
        if self.get_source(source_id) is None:
            return []
        return self._store.source_lines(source_id)

    def sources(self, area_ids=None, *, status=None, kind=None):
        return self._store.sources(self._areas(area_ids), status=status, kind=kind)

    def get_brain_item(self, item_id):
        item = self._store.get_brain_item(item_id)
        if item is not None:
            self._check(item["area_id"])
        return item

    def brain_items(self, area_ids=None, **filters):
        return self._store.brain_items(self._areas(area_ids), **filters)

    def projects(self, area_ids=None):
        return self._store.projects(self._areas(area_ids))

    def deals(self, area_ids=None, **filters):
        return self._store.deals(self._areas(area_ids), **filters)

    def revenue(self, area_ids=None):
        return self._store.revenue(self._areas(area_ids))

    def reviews(self, area_ids=None, **filters):
        return self._store.reviews(self._areas(area_ids), **filters)

    def unconfirmed_count(self, area_id, project_id=None, deal_id=None):
        self._check(area_id)
        return self._store.unconfirmed_count(area_id, project_id=project_id, deal_id=deal_id)

    def playbooks(self, **filters):
        self._check(LIBRARY)
        return self._store.playbooks(**filters)

    def checklist(self, **filters):
        self._check(LIBRARY)
        return self._store.checklist(**filters)
