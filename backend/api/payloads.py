import json
from datetime import datetime, timedelta
from decimal import Decimal
from functools import partial, singledispatch
from typing import Any

from aiohttp.payload import JsonPayload as BaseJsonPayload, Payload
from aiohttp.typedefs import JSONEncoder
from asyncpg import Record

__all__ = ('JsonPayload', 'AsyncGenJSONListPayload')


@singledispatch
def convert(value):
    """
    The json module allows you to specify a function that will be called to process
    non-JSON-serializable objects. The function must return either a JSON-serializable
    value or a TypeError exception:
    https://docs.python.org/3/library/json.html#json.dump
    """
    raise TypeError(f'Unserializable value: {value!r}')


@convert.register(Record)
def convert_asyncpg_record(value: Record):
    """
    Allows automatic serialization of query results returned by asyncpg.
    """
    return dict(value)


@convert.register(datetime)
def convert_datetime(value: datetime):
    return value.isoformat()


@convert.register(timedelta)
def convert_timedelta(value: timedelta):
    return int(value.total_seconds())


@convert.register(Decimal)
def convert_decimal(value: Decimal):
    return float(value)


dumps = partial(json.dumps, default=convert, ensure_ascii=False)


class JsonPayload(BaseJsonPayload):
    """
    Replaces the serialization function with a smarter one (able to pack
    asyncpg.Record and other entities into JSON objects).
    """
    def __init__(self,
                 value: Any,
                 encoding: str = 'utf-8',
                 content_type: str = 'application/json',
                 dumps: JSONEncoder = dumps,
                 *args: Any,
                 **kwargs: Any) -> None:
        super().__init__(value, encoding, content_type, dumps, *args, **kwargs)


class AsyncGenJSONListPayload(Payload):
    """
    It iterates over AsyncIterable objects, serializes data from them in parts
    to JSON and sends it to the client.
    """
    def __init__(self, value, encoding: str = 'utf-8',
                 content_type: str = 'application/json',
                 root_object: str = 'data',
                 *args, **kwargs):
        self.root_object = root_object
        super().__init__(value, content_type=content_type, encoding=encoding,
                         *args, **kwargs)

    async def write(self, writer):
        # Start of object
        await writer.write(
            (f'{{"{self.root_object}":[').encode(self._encoding)
        )

        first = True
        async for row in self._value:
            # No comma required before the first line
            if not first:
                await writer.write(b',')
            else:
                first = False

            await writer.write(dumps(row).encode(self._encoding))

        # End of object
        await writer.write(b']}')
