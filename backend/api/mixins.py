from aiohttp.web_exceptions import HTTPNotFound, HTTPForbidden
from aiohttp.web_response import StreamResponse

from sqlalchemy import exists, select, Table


class CheckObjectsExistsMixin:
    object_id_path: str
    check_exists_table: Table

    async def _iter(self) -> StreamResponse:
        await self.check_object_exists()
        return await super()._iter()

    @property
    def object_id(self):
        return int(self.request.match_info.get(self.object_id_path))

    async def check_object_exists(self):
        query = select([
            exists().where(self.check_exists_table.c.id == self.object_id)
        ])
        if not await self.pg.fetchval(query):
            raise HTTPNotFound()


class CheckUserPermissionMixin:
    skip_methods: list = []
    permissions_classes: list = []

    async def _iter(self) -> StreamResponse:
        if self.request.method not in self.skip_methods:
            await self.check_permissions()
        return await super()._iter()

    async def check_permissions(self):
        permissions_objects = [permission() for permission in self.permissions_classes]
        for permission in permissions_objects:
            if not permission.has_permission(self.request, self):
                raise HTTPForbidden(reason='You do not have permission to perform this action.')
